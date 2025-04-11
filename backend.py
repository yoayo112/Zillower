from flask import Flask, request, jsonify, render_template
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import base64
import os
import json
import requests
from datetime import datetime

# Initialize Flask app
app = Flask(
    __name__,
    static_folder="static",  # Serve CSS and JS from here
    template_folder="templates"  # Serve HTML from here
)

# File for saving listings
LISTINGS_FILE = "listings.json"

#Google API vars
GOOGLE_MAPS_API_KEY = None # put your own API key for google cloud/ google maps distance matrix API here
with open("googleapi.txt","r") as file: GOOGLE_MAPS_API_KEY = file.read() # Or make a file called "googleapi.txt" to put it in so that its not published.
ORIGIN_ADDRESS = "120 1/2 W Laurel St A, Fort Collins, CO 80524"

# Function to load saved listings
def load_listings():
    if os.path.exists(LISTINGS_FILE):
        with open(LISTINGS_FILE, "r") as file:
            return json.load(file)
    else:
        return []

def currency_to_float(currency_string):
    if isinstance(currency_string, str):
        try:
            cleaned_string = currency_string.replace("$", "").replace(",", "")
            return float(cleaned_string)
        except ValueError:
            return None  # Return None instead of 0
    return None  # Return None for invalid inputs

def assign_scores(listings):
    if len(listings) == 1:
        listings[0]["score"] = "N/A"
        return listings  # Return immediately for a single listing
    
    # Extract values for normalization
    rents = [currency_to_float(listing["price"]) for listing in listings if currency_to_float(listing["price"]) is not None and listing["price"] is not None]
    square_feet = [listing["square_footage"] for listing in listings if isinstance(listing["square_footage"], int)]
    bedrooms = [listing["bedrooms"] for listing in listings if isinstance(listing["bedrooms"], int)]
    bathrooms = [listing["bathrooms"] for listing in listings if isinstance(listing["bathrooms"], float)]
    distances = [float(listing["distance"].split()[0]) for listing in listings if listing["distance"] not in ["N/A", None]]

    # Compute the average square footage if needed
    avg_sqft = sum(square_feet) // len(square_feet) if square_feet else 0

    # Helper function for normalization
    def normalize(value, min_val, max_val, reverse=False):
        if min_val == max_val:
            return 50  # Neutral score when all values are the same
        score = (value - min_val) / (max_val - min_val) * 100
        return 100 - score if reverse else score  # Reverse scales lower-better criteria

    # Get min/max values
    rent_min, rent_max = min(rents, default=0), max(rents, default=1)
    sqft_min, sqft_max = min(square_feet, default=0), max(square_feet, default=1)
    bed_min, bed_max = min(bedrooms, default=0), max(bedrooms, default=1)
    bath_min, bath_max = min(bathrooms, default=0), max(bathrooms, default=1)
    dist_min, dist_max = min(distances, default=0), max(distances, default=1)

    # Assign scores to listings
    for listing in listings:
        # Ensure square footage is valid, else assign average
        if not isinstance(listing["square_footage"], int):
            listing["square_footage"] = avg_sqft

        listing["rent_score"] = normalize(currency_to_float(listing["price"]), rent_min, rent_max, reverse=True) if currency_to_float(listing["price"]) is not None and listing["price"] is not None else 0
        listing["sqft_score"] = normalize(listing["square_footage"], sqft_min, sqft_max) if listing["square_footage"] > 0 else 0
        listing["bedrooms_score"] = normalize(listing["bedrooms"], bed_min, bed_max) if isinstance(listing["bedrooms"], int) else 0
        listing["bathrooms_score"] = normalize(listing["bathrooms"], bath_min, bath_max) if isinstance(listing["bathrooms"], int) else 0
        listing["distance_score"] = normalize(float(listing["distance"].split()[0]), dist_min, dist_max, reverse=True) if listing["distance"] not in ["N/A", None] else 0

        # Final weighted score
        listing["score"] = round((
            listing["rent_score"] * 0.3 +
            listing["sqft_score"] * 0.2 +
            listing["bedrooms_score"] * 0.2 +
            listing["bathrooms_score"] * 0.2 +
            listing["distance_score"] * 0.1
        ),2)

    return listings

# Load saved listings on startup
listings = load_listings()
listings = assign_scores(listings)

# Function to save listings
def save_listings():
    with open(LISTINGS_FILE, "w") as file:
        json.dump(listings, file, indent=4)

def get_distance(destination_address):
    url = f"https://maps.googleapis.com/maps/api/distancematrix/json?origins={ORIGIN_ADDRESS}&destinations={destination_address}&units=imperial&key={GOOGLE_MAPS_API_KEY}"
    
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        try:
            distance_text = data["rows"][0]["elements"][0]["distance"]["text"]  # e.g., "12.3 mi"
            return distance_text
        except (KeyError, IndexError):
            print(Exception)
            return "N/A"
    else:
        print(response.status_code)
        return "N/A"

def scrape_zillow(url):

    # Set up Selenium WebDriver
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(url)

    # Retrieve rendered HTML
    html = driver.page_source
    driver.quit()

    # Parse the rendered HTML with BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")

    # Extract first image
    gallery = soup.find("div", {"data-testid": "hollywood-gallery-images-tile-list"})
    first_li = gallery.find("li")
    first_image = first_li.find("img")["src"] if first_li else None
    
    response = requests.get(first_image)
    encoded_string = None
    if response.status_code == 200:
        encoded_string = base64.b64encode(response.content).decode("utf-8")

    # Extract Rent (Price)
    price_element = soup.find("span", class_="Text-c11n-8-109-3__sc-aiai24-0 sc-lknQiW knxFxJ jMCwlu")
    rent = None
    if price_element:
        inner_price_element = price_element.find("span")
        if inner_price_element:
            rent = float(inner_price_element.text.strip().replace("$", "").replace(",", "").replace("/mo", ""))

    # Extract Address
    address_element = soup.find("h1", class_="Text-c11n-8-109-3__sc-aiai24-0 cEHZrB")
    address = address_element.text.strip() if address_element else "Address not found"

    # Calculate distance from the origin
    distance = get_distance(address) 

    # Extract Bedrooms, Bathrooms, and Square Footage
    bedrooms_element = soup.find("span", string="beds")
    bedrooms = bedrooms_element.find_previous("span").text.strip() if bedrooms_element else None

    bathrooms_element = soup.find("span", string="baths")
    bathrooms = bathrooms_element.find_previous("span").text.strip() if bathrooms_element else None

    sqft_element = soup.find("span", string="sqft")
    sqft = sqft_element.find_previous("span").text.strip().replace(",", "") if sqft_element else None

    # Extract Date Available
    date_available_element = soup.find("span", string=lambda s: s and "Available" in s)
    date_available = date_available_element.text.strip() if date_available_element else "Not Listed"

    # Return scraped data including distance
    return {
        "image": encoded_string,
        "price": rent,
        "address": address,
        "bedrooms": int(bedrooms) if bedrooms else -1,
        "bathrooms": bathrooms if bathrooms else -1,
        "square_footage": int(sqft) if (sqft and sqft.isdigit()) else -1,
        "date_available": date_available,
        "distance": distance,  # Add distance in miles here
    }

# Route to serve the main page
@app.route("/")
def home():
    return render_template("UI.html")

@app.route("/update_origin", methods=["POST"])
def update_origin():
    data = request.json
    origin_address = data.get("originAddress")

    if origin_address:
        global ORIGIN_ADDRESS 
        ORIGIN_ADDRESS = origin_address
        return jsonify({"success": True, "message": "Origin address updated!"})
    
    return jsonify({"success": False, "error": "Invalid address"})



@app.route("/add_listing", methods=["POST"])
def add_listing():
    global listings  # Ensure updates apply across requests
    data = request.json
    url = data.get("url")
    roommates = data.get("roommates", 1)

    # Scrape the provided URL
    scraped_data = scrape_zillow(url)

    # Reload current listings before checking duplicates
    listings = load_listings()

    # Check for duplicate address
    if all(listing.get("address") != scraped_data.get("address") for listing in listings):
        rent = scraped_data.get("price")
        sqft = scraped_data.get("square_footage")

        if sqft > 0:
            scraped_data["cost_per_sqft"] = f"{rent / sqft:.2f}"
        else:
            scraped_data["square_footage"] = "N/A"
            scraped_data["cost_per_sqft"] = "N/A"

        scraped_data["cost_per_roommate"] = f"{(rent + 250) / roommates:.2f}" if rent > 0 and roommates > 0 else "N/A"
        
        
        # Get current date and time
        timestamp = int(datetime.now().strftime("%Y%m%d%H%M%S"))


        scraped_data.update({
            "overall_rating": data.get("overall_rating"),
            "contacted": data.get("contacted", False),
            "applied": data.get("applied", False),
            "id": timestamp,
            "url":url,
        })

        # Add to the global listings variable
        listings.append(scraped_data)
        listings= assign_scores(listings)

        # Save listings to file
        save_listings()

        print("Listings successfully added:")
        return jsonify({"success": True, "listing": scraped_data})

    else:
        print("Failed to add. Listing already exists.")
        return jsonify({"success": False})

@app.route("/edit_listing", methods=["POST"])
def edit_listing():
    data = request.json
    listing_id = int(data.get("id")) if data.get("id") else None  # Convert to int safely

    for listing in listings:
        stored_id = int(listing.get("id"))  # Ensure comparison uses integers
        print(f"Checking Listing ID {stored_id} == {listing_id}")

        if stored_id == listing_id:
            listing.update(data)
            save_listings()
            return jsonify({"success": True, "listing": listing})

    return jsonify({"success": False, "error": "Listing not found"})

@app.route("/delete_listing", methods=["POST"])
def delete_listing():
    data = request.json
    listing_id = data.get("id")
    global listings
    listings = [listing for listing in listings if listing.get("id") != listing_id]
    save_listings()
    return jsonify({"success": True, "id":listing_id})

@app.route("/listings", methods=["GET"])
def get_listings():
    sort_by = request.args.get("sort_by", "price")
    sorted_listings = sorted(listings, key=lambda x: x.get(sort_by, 0) if isinstance(x.get(sort_by, 0), (int, float)) else 0)

    return jsonify(sorted_listings)

if __name__ == "__main__":
    app.run(debug=True)
