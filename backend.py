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
SCORE_WEIGHTS ={
    "rent": 0.3,
    "sqft":0.2,
    "bedrooms":0.2,
    "bathrooms":0.2,
    "distance":0.1
}

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
    elif isinstance(currency_string,int):
        return float(currency_string)
    elif isinstance(currency_string, float):
        return currency_string
    else:
        return None  # Return None for invalid inputs

def assign_scores(listings):
    if len(listings) == 1:
        listings[0]["score"] = "N/A"
        return listings  # Return immediately for a single listing
    
    # Extract values for normalization
    price = [currency_to_float(listing["cost_per_roommate"]) for listing in listings if currency_to_float(listing["cost_per_roommate"]) is not None]
    square_feet = [listing["square_footage"] for listing in listings if isinstance(listing["square_footage"], int)]
    bedrooms = [listing["bedrooms"] for listing in listings if isinstance(listing["bedrooms"], int)]
    bathrooms = [listing["bathrooms"] for listing in listings if isinstance(listing["bathrooms"], float)]
    distances = [float(listing["distance"].split()[0]) for listing in listings if listing["distance"] not in ["N/A", None]]

    # Compute the average square footage if needed
    avg_sqft = sum(square_feet) // len(square_feet) if square_feet else 0

    # Normalization with proportional scaling
    def normalize(value, min_val, max_val, reverse=False):
        if min_val == max_val:
            return 50  # Neutral score when all values are the same
        score = 100 * (value - min_val) / (max_val - min_val)
        return 100 - score if reverse else score

    # Get min/max values for normalization
    rent_min, rent_max = min(price, default=0), max(price, default=1)
    sqft_min, sqft_max = min(square_feet, default=0), max(square_feet, default=1)
    bed_min, bed_max = min(bedrooms, default=0), max(bedrooms, default=1)
    bath_min, bath_max = min(bathrooms, default=0), max(bathrooms, default=1)
    dist_min, dist_max = min(distances, default=0), max(distances, default=1)

    # Assign scores proportionally with weights applied
    for listing in listings:
        print(f"---------------LISTING: ${listing['id']} ")
        if not isinstance(listing["square_footage"], int):
            listing["square_footage"] = avg_sqft  # Assign average if missing

        rent_score = normalize(currency_to_float(listing["cost_per_roommate"]), rent_min, rent_max, reverse=True) if currency_to_float(listing["cost_per_roommate"]) is not None else 0
        rent_score *= SCORE_WEIGHTS["rent"]
        listing["rent_score"] = rent_score
        print(rent_score)

        sqft_score = normalize(listing["square_footage"], sqft_min, sqft_max) if listing["square_footage"] > 0 else 0
        sqft_score *= SCORE_WEIGHTS["sqft"]
        listing["sqft_score"] = sqft_score
        print(sqft_score)

        bedrooms_score = normalize(int(listing["bedrooms"]), bed_min, bed_max)
        bedrooms_score *= SCORE_WEIGHTS["bedrooms"]
        listing["bedrooms_score"] = bedrooms_score
        print(bedrooms_score)

        bathrooms_score = normalize(float(listing["bathrooms"]), bath_min, bath_max)
        bathrooms_score *= SCORE_WEIGHTS["bathrooms"]
        listing["bathrooms_score"] = bathrooms_score
        print(bathrooms_score)

        distance_score = normalize(float(listing["distance"].split()[0]), dist_min, dist_max, reverse=True) if listing["distance"] not in ["N/A", None] else 0
        distance_score *= SCORE_WEIGHTS["distance"]
        listing["distance_score"] = distance_score

        # Final weighted score
        listing["score"] = round((
            listing["rent_score"] +
            listing["sqft_score"] +
            listing["bedrooms_score"] +
            listing["bathrooms_score"] +
            listing["distance_score"]
        ), 2)

    return listings

# Function to save listings
def save_listings():
    with open(LISTINGS_FILE, "w") as file:
        global listings
        json.dump(listings, file, indent=4)

# Load saved listings on startup
listings = load_listings()
listings = assign_scores(listings)
save_listings()

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
    options.binary_location="E:\_Applications\Program Files\Google\Chrome\Application\chrome.exe"
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

@app.route("/update_settings", methods=["POST"])
def update_origin():
    data = request.json
    address = data.get("address")

    if address:
        global ORIGIN_ADDRESS 
        ORIGIN_ADDRESS = address
        SCORE_WEIGHTS["rent"] = float(data.get("rent"))
        SCORE_WEIGHTS["sqft"] = float(data.get("sqft"))
        SCORE_WEIGHTS["bedrooms"] = float(data.get("beds"))
        SCORE_WEIGHTS["bathrooms"] = float(data.get("baths"))
        SCORE_WEIGHTS["distance"] = float(data.get("dist"))
        global listings
        listings = load_listings()
        listings = assign_scores(listings)
        save_listings()

        return jsonify({"success": True, "message": "Settings updated!"})
    
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
            "group":"none",
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

@app.route("/contacted", methods=["POST"])
def contacted():
    data = request.json
    listing_id = int(data.get("id")) if data.get("id") else None
    checked = data.get("selected") if data.get("selected") else False
    global listings
    for listing in listings:
        stored_id = int(listing.get("id"))  # Ensure comparison uses integers
        print(f"Checking Listing ID {stored_id} == {listing_id}")

        if stored_id == listing_id:
            listing["contacted"] = checked
            save_listings()
            return jsonify({"success": True, "listing": listing})
        
@app.route("/applied", methods=["POST"])
def applied():
    data = request.json
    listing_id = int(data.get("id")) if data.get("id") else None
    checked = data.get("selected") if data.get("selected") else False
    global listings
    for listing in listings:
        stored_id = int(listing.get("id"))  # Ensure comparison uses integers
        print(f"Checking Listing ID {stored_id} == {listing_id}")

        if stored_id == listing_id:
            listing["applied"] = checked
            save_listings()
            return jsonify({"success": True, "listing": listing})

@app.route("/update_group", methods=["POST"])
def update_group():
    data = request.json
    listing = next((l for l in listings if l["id"] == data["id"]), None)
    
    if listing:
        listing["group"] = data["group"]
        return jsonify({"success": True, "listing": listing})
    
    return jsonify({"success": False, "message": "Listing not found"}), 404

@app.route("/edit_listing", methods=["POST"])
def edit_listing():
    data = request.json
    listing_id = int(data.get("id")) if data.get("id") else None  # Convert to int safely
    global listings

    for listing in listings:
        stored_id = int(listing.get("id"))  # Ensure comparison uses integers
        print(f"Checking Listing ID {stored_id} == {listing_id}")

        if stored_id == listing_id:
            listing.update(data)
            assign_scores(listings)
            save_listings()
            return jsonify({"success": True, "listing": listing})

    return jsonify({"success": False, "error": "Listing not found"})

@app.route("/delete_listing", methods=["POST"])
def delete_listing():
    data = request.json
    listing_id = data.get("id")

    global listings
    temp_listings = []

    print(f"Attempting to delete listing with ID: {listing_id}")

    for listing in listings:
        stored_id = listing.get("id")
        if stored_id != listing_id:
            print(f"Keeping listing: {stored_id}")
            temp_listings.append(listing)
        else:
            print(f"Deleted listing: {stored_id}")

    listings = temp_listings
    print(f"listings: ${temp_listings}")

    if listings:  # Prevent saving an empty list
        save_listings()
        assign_scores(listings)
        return jsonify({"success": True, "id": listing_id})
    
    print("All listings removed—returning error.")
    return jsonify({"success": False, "error": "No listings left after deletion!"})

@app.route("/listings", methods=["GET"])
def get_listings():
    sort_by = request.args.get("sort_by", "price")  # Default to price
    reverse_sort = False

    if sort_by in {"square_footage", "score"}:
        reverse_sort = True


    def sort_key(listing):
        value = listing.get(sort_by, 0)
        if sort_by == "price" and isinstance(value, str):
            try:
                return currency_to_float(value)
            except: 
                return 0
        if sort_by == "distance" and isinstance(value, str):
            try:
                return float(value.split()[0])  # Ensure numeric sorting
            except ValueError:
                return float("inf")  # Place invalid distances last
        if isinstance(value, str) and sort_by == "date_available":
            try:
                return datetime.strptime(value, "%Y-%m-%d")  # Convert date string to datetime object
            except ValueError:
                return datetime.max  # Handle invalid dates by placing them last
        return value if isinstance(value, (int, float)) else 0  # Default sorting fallback
    
    print("Before sorting:", [listing["distance"] for listing in listings])
    sorted_listings = sorted(listings, key=sort_key, reverse=reverse_sort)
    print("After sorting:", [listing["distance"] for listing in sorted_listings])

    return jsonify(sorted_listings)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
