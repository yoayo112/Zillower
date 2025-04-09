from flask import Flask, request, jsonify, render_template
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import os
import json

# Initialize Flask app
app = Flask(
    __name__,
    static_folder="static",  # Serve CSS and JS from here
    template_folder="templates"  # Serve HTML from here
)

# File for saving listings
LISTINGS_FILE = "listings.json"

# Function to load saved listings
def load_listings():
    if os.path.exists(LISTINGS_FILE):
        with open(LISTINGS_FILE, "r") as file:
            return json.load(file)
    return []

# Function to save listings
def save_listings():
    with open(LISTINGS_FILE, "w") as file:
        json.dump(listings, file, indent=4)

# Load saved listings on startup
listings = load_listings()

# Function to scrape Zillow with Selenium
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

    # Return scraped data
    return {
        "price": rent,
        "address": address,
        "bedrooms": int(bedrooms) if bedrooms else None,
        "bathrooms": int(bathrooms) if bathrooms else None,
        "square_footage": int(sqft) if sqft else None,
        "date_available": date_available,
    }

# Route to serve the main page
@app.route("/")
def home():
    return render_template("UI.html")

@app.route("/add_listing", methods=["POST"])
def add_listing():
    data = request.json
    url = data.get("url")
    roommates = data.get("roommates", 1)

    # Scrape the provided URL
    scraped_data = scrape_zillow(url)

    # Ensure `price` (rent) is defined for calculations
    rent = scraped_data.get("price") or 0  # Default to 0 if price is None
    sqft = scraped_data.get("square_footage") or 0  # Default to 0 if square footage is None

    # Additional Calculations
    scraped_data["cost_per_sqft"] = rent / sqft if sqft else 0
    scraped_data["cost_per_roommate"] = (rent + 250) / roommates if roommates else 0
    scraped_data.update({
        "distance_rating": data.get("distance_rating"),
        "overall_rating": data.get("overall_rating"),
        "contacted": data.get("contacted", False),
        "applied": data.get("applied", False),
        "id": len(listings) + 1,  # Assign a unique ID
    })

    # Add to the database and save
    listings.append(scraped_data)
    save_listings()
    return jsonify({"success": True, "listing": scraped_data})

@app.route("/edit_listing", methods=["POST"])
def edit_listing():
    data = request.json
    listing_id = data.get("id")
    for listing in listings:
        if listing.get("id") == listing_id:
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
    sorted_listings = sorted(listings, key=lambda x: x.get(sort_by, 0))
    return jsonify(sorted_listings)

if __name__ == "__main__":
    app.run(debug=True)
