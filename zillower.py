## Sky Vercauteren
## Zillower
## Updated july 2025

from flask import Flask, request, jsonify, render_template
from bs4 import BeautifulSoup
from datetime import datetime
import os

# Import functions and configurations from other modules
import utils # For data loading, saving, scoring, scraping, etc.

import config # For constants like API keys, file paths, score weights

# Initialize Flask app
app = Flask(
    __name__,
    static_folder="static",
    template_folder="templates"
)

# Global variable for listings.
# This list will hold the current state of your listings in memory.
# It's loaded once at startup and modified by routes, then saved.
listings = []

# --- Application Setup ---
# This decorator ensures 'initialize_listings' runs once before the first request.
# This prevents issues with Flask's reloader potentially calling it multiple times
# during development.
@app.before_request
def initialize_listings():
    global listings
    # Only load if the 'listings' list is currently empty.
    # This prevents reloading on every request in development with Flask's reloader.
    if not listings: 
        listings = utils.load_listings()
        listings = utils.assign_scores(listings) # Assign initial scores
        utils.save_listings(listings) # Save after initial score assignment

# --- Routes ---

@app.route("/")
def home():
    """Renders the main UI.html page."""
    return render_template("UI.html")

@app.route("/update_settings", methods=["POST"])
def update_settings():
    """Updates the origin address and score weights."""
    data = request.json
    address = data.get("address")

    if address:
        config.ORIGIN_ADDRESS = address # Update the global in config.py
        
        # Update score weights in config.py
        # Ensure these keys match the frontend settings form
        config.SCORE_WEIGHTS["rent"] = float(data.get("rent_weight"))
        config.SCORE_WEIGHTS["sqft"] = float(data.get("sqft_weight"))
        config.SCORE_WEIGHTS["bedrooms"] = float(data.get("bedrooms_weight"))
        config.SCORE_WEIGHTS["bathrooms"] = float(data.get("bathrooms_weight"))
        config.SCORE_WEIGHTS["distance"] = float(data.get("distance_weight"))
        
        global listings
        listings = utils.load_listings() # Re-load to ensure the latest state before re-scoring
        # Re-calculate cost_per_roommate for all listings based on current roommates if utilities are added
        for listing in listings:
            rent = utils.currency_to_float(listing.get("price")) # Get clean rent
            num_roommates = listing.get("roommates", 1)
            utility_est = listing.get("utility_estimate") # Get existing utility estimate

            listing["cost_per_roommate"] = utils.calculate_cost_per_occupant(rent, num_roommates, utility_estimate=utility_est)

        listings = utils.assign_scores(listings) # Re-assign scores with new weights
        utils.save_listings(listings) # Save the updated listings

        return jsonify({"success": True, "message": "Settings updated!", "new_origin": config.ORIGIN_ADDRESS})
    
    return jsonify({"success": False, "error": "Invalid address"})

@app.route("/add_listing_from_html", methods=["POST"])
def add_listing_from_html():
    """Adds a new listing by parsing raw HTML provided by the user."""
    global listings
    data = request.json
    raw_html = data.get("raw_html")
    original_url = data.get("url")
    # Ensure roommates is treated as an int. If 0, it means living alone.
    roommates = int(data.get("roommates", 1)) # Change default to 0 for "living by myself"
    overall_rating = int(data.get("overall_rating", 5))

    if not raw_html:
        return jsonify({"success": False, "error": "No HTML content provided."})

    try:
        soup = BeautifulSoup(raw_html, "html.parser")
        scraped_data = utils._parse_zillow_html(soup, original_url) # Use utility function for parsing

        if not scraped_data or not scraped_data.get("address") or scraped_data.get("address") == "Address not found":
            print("Manual HTML parsing failed or no valid address found.")
            return jsonify({"success": False, "error": "Could not parse listing details from the provided HTML. Please ensure it's the full page source of a Zillow listing."})

        # Load current listings to check for duplicates
        listings = utils.load_listings()

        scraped_address_normalized = scraped_data.get("address", "").strip().lower()
        if all(listing.get("address", "").strip().lower() != scraped_address_normalized for listing in listings):
            rent = utils.currency_to_float(scraped_data.get("price")) # Clean rent early
            sqft = scraped_data.get("square_footage")

            # Calculate cost per sqft
            if sqft is not None and sqft > 0 and rent is not None and rent > 0:
                scraped_data["cost_per_sqft"] = f"{rent / sqft:.2f}"
            else:
                scraped_data["square_footage"] = -1 # Indicate missing/invalid sqft
                scraped_data["cost_per_sqft"] = "N/A"

            # Calculate cost per roommate using the new utility function
            scraped_data["cost_per_roommate"] = utils.calculate_cost_per_occupant(rent, roommates)
            
            timestamp = int(datetime.now().strftime("%Y%m%d%H%M%S"))

            scraped_data.update({
                "overall_rating": overall_rating, # Use parsed overall_rating
                "contacted": data.get("contacted", False),
                "applied": data.get("applied", False),
                "id": timestamp,
                "url": original_url,
                "group": "none", # Default group
                "roommates": roommates, # Store the actual roommate count
                "utility_estimate": None, # New field, default to None
                "comments": '' # Nothing yet. 
            })

            listings.append(scraped_data)
            listings = utils.assign_scores(listings) # Re-score all listings
            utils.save_listings(listings) # Save updated listings

            print("Listing successfully added from manual HTML and saved.")
            return jsonify({"success": True, "listing": scraped_data})

        else:
            print("Failed to add from manual HTML. Listing already exists based on address.")
            return jsonify({"success": False, "error": "Listing with this address already exists."})

    except Exception as e:
        print(f"Error processing manual HTML: {e}")
        import traceback
        traceback.print_exc() # Print full traceback for debugging
        return jsonify({"success": False, "error": f"An error occurred while processing HTML: {str(e)}"})

@app.route("/add_listing", methods=["POST"])
def add_listing():
    """Adds a new listing by scraping a URL."""
    global listings
    data = request.json
    url = data.get("url")
    roommates = int(data.get("roommates", 0)) # Change default to 0 for "living by myself"
    overall_rating = int(data.get("overall_rating", 5))

    print(f"Attempting to add listing from {url}. Launching Playwright browser.")
    scraped_data = utils.scrape_zillow(url, headless=False) # Use utility function for scraping

    if "error" in scraped_data:
        print(f"Scraping failed with error: {scraped_data['error']}")
        return jsonify({"success": False, "error": scraped_data["error"]})
    
    if not scraped_data or not scraped_data.get("address") or scraped_data.get("address") == "Address not found":
        print("Scraping failed or returned incomplete data. Cannot add listing.")
        return jsonify({"success": False, "error": "Scraping failed or no valid address found. Please check URL and solve any challenges."})

    # Load current listings to check for duplicates
    listings = utils.load_listings()

    scraped_address_normalized = scraped_data.get("address", "").strip().lower()
    if all(listing.get("address", "").strip().lower() != scraped_address_normalized for listing in listings):
        rent = utils.currency_to_float(scraped_data.get("price")) # Clean rent early
        sqft = scraped_data.get("square_footage")

        # Calculate cost per sqft
        if sqft is not None and sqft > 0 and rent is not None and rent > 0:
            scraped_data["cost_per_sqft"] = f"{rent / sqft:.2f}"
        else:
            scraped_data["square_footage"] = -1
            scraped_data["cost_per_sqft"] = "N/A"

        # Calculate cost per roommate using the new utility function
        scraped_data["cost_per_roommate"] = utils.calculate_cost_per_occupant(rent, roommates)
        
        timestamp = int(datetime.now().strftime("%Y%m%d%H%M%S"))

        scraped_data.update({
            "overall_rating": overall_rating, # Use parsed overall_rating
            "contacted": data.get("contacted", False),
            "applied": data.get("applied", False),
            "id": timestamp,
            "group": "none",
            "roommates": roommates, # Store the actual roommate count
            "utility_estimate": None, # New field, default to None
            "comments": '' # Nothing yet. 
        })

        listings.append(scraped_data)
        listings = utils.assign_scores(listings) # Re-score all listings
        utils.save_listings(listings) # Save updated listings

        print("Listing successfully added and saved.")
        return jsonify({"success": True, "listing": scraped_data})

    else:
        print("Failed to add. Listing already exists based on address.")
        return jsonify({"success": False, "error": "Listing with this address already exists."})

@app.route("/contacted", methods=["POST"])
def contacted():
    """Updates the 'contacted' status of a listing."""
    data = request.json
    listing_id = int(data.get("id")) if data.get("id") else None
    checked = data.get("selected") if data.get("selected") else False
    
    global listings
    for listing in listings:
        stored_id = int(listing.get("id"))

        if stored_id == listing_id:
            listing["contacted"] = checked
            utils.save_listings(listings)
            return jsonify({"success": True, "listing": listing})
        
    return jsonify({"success": False, "error": "Listing not found"}), 404
        
@app.route("/applied", methods=["POST"])
def applied():
    """Updates the 'applied' status of a listing."""
    data = request.json
    listing_id = int(data.get("id")) if data.get("id") else None
    checked = data.get("selected") if data.get("selected") else False
    
    global listings
    for listing in listings:
        stored_id = int(listing.get("id"))

        if stored_id == listing_id:
            listing["applied"] = checked
            utils.save_listings(listings)
            return jsonify({"success": True, "listing": listing})
    
    return jsonify({"success": False, "error": "Listing not found"}), 404

@app.route("/update_group", methods=["POST"])
def update_group():
    """Updates the 'group' for a given listing."""
    data = request.json
    listing_id = data.get("id")
    
    global listings
    listing = next((l for l in listings if l.get("id") == listing_id), None)
    
    if listing:
        listing["group"] = data["group"]
        utils.save_listings(listings)
        return jsonify({"success": True, "listing": listing})
    
    return jsonify({"success": False, "message": "Listing not found"}), 404

@app.route("/edit_listing", methods=["POST"])
def edit_listing():
    """Edits details of an existing listing."""
    data = request.json
    listing_id = int(data.get("id")) if data.get("id") else None
    
    global listings

    found_listing = False
    for listing in listings:
        stored_id = int(listing.get("id"))

        if stored_id == listing_id:
            new_image_data_uri = data.get("new_image_base64")
            if new_image_data_uri and isinstance(new_image_data_uri, str) and new_image_data_uri.startswith("data:") and len(new_image_data_uri) > 50:
                if 'image' not in listing or not isinstance(listing['image'], list):
                    listing['image'] = []
                listing['image'].append(new_image_data_uri)
                print(f"Appended new image to listing {listing_id}. Total images: {len(listing['image'])}")
                # If only adding an image, save and return early
                if len(data) == 2 and "id" in data and "new_image_base64" in data:
                    utils.save_listings(listings)
                    return jsonify({"success": True, "listing": listing})
            elif new_image_data_uri:
                print(f"Warning: Invalid image data URI received for listing {listing_id}. Not appended. Data URI starts with: {new_image_data_uri[:50]}...")
            
            # Update other fields if present in the request
            if "address" in data: listing["address"] = data["address"]
            if "price" in data: listing["price"] = utils.currency_to_float(data["price"])
            if "square_footage" in data: listing["square_footage"] = int(float(data["square_footage"])) if data["square_footage"] is not None else -1
            if "bedrooms" in data: listing["bedrooms"] = int(float(data["bedrooms"])) if data["bedrooms"] is not None else -1
            if "bathrooms" in data: listing["bathrooms"] = float(data["bathrooms"]) if data["bathrooms"] is not None else -1.0
            if "date_available" in data: listing["date_available"] = data["date_available"]
            if "overall_rating" in data: listing["overall_rating"] = int(data["overall_rating"])
            # Update roommates count
            if "roommates" in data: listing["roommates"] = int(data["roommates"])
            # New: Update utility estimate
            if "utility_estimate" in data: 
                # Convert to float, None if empty string or "N/A"
                utility_val = data["utility_estimate"]
                listing["utility_estimate"] = float(utility_val) if utility_val not in ["", None, "N/A"] else None

            # Recalculate derived fields
            rent = listing.get("price")
            sqft = listing.get("square_footage")
            num_roommates = listing.get("roommates", 0) # Use the updated roommates
            utility_est = listing.get("utility_estimate") # Use the updated utility estimate

            if sqft is not None and sqft > 0 and rent is not None and rent > 0:
                listing["cost_per_sqft"] = f"{rent / sqft:.2f}"
            else:
                listing["cost_per_sqft"] = "N/A"

            # Calculate cost per roommate using the utility function
            listing["cost_per_roommate"] = utils.calculate_cost_per_occupant(rent, num_roommates, utility_estimate=utility_est)

            found_listing = True
            break

    if found_listing:
        listings = utils.assign_scores(listings) # Re-score all listings after edit
        utils.save_listings(listings)
        return jsonify({"success": True, "listing": listing})

    return jsonify({"success": False, "error": "Listing not found"})

@app.route("/delete_listing", methods=["POST"])
def delete_listing():
    """Deletes a listing by its ID."""
    data = request.json
    listing_id = data.get("id")

    global listings
    initial_len = len(listings)
    
    # Filter out the listing to be deleted
    listings = [listing for listing in listings if listing.get("id") != listing_id]
    
    if len(listings) < initial_len:
        print(f"Deleted listing with ID: {listing_id}")
        # Only re-assign scores if there are listings left
        if listings:
            # Re-calculate cost_per_roommate for all listings if needed (less critical here)
            for listing in listings:
                rent = utils.currency_to_float(listing.get("price"))
                num_roommates = listing.get("roommates", 0)
                utility_est = listing.get("utility_estimate")
                listing["cost_per_roommate"] = utils.calculate_cost_per_occupant(rent, num_roommates, utility_estimate=utility_est)

            listings = utils.assign_scores(listings)
        utils.save_listings(listings)
        return jsonify({"success": True, "id": listing_id})
    
    print(f"Listing with ID: {listing_id} not found for deletion.")
    return jsonify({"success": False, "error": "Listing not found for deletion."}), 404

@app.route("/listings", methods=["GET"])
def get_listings():
    """Retrieves and returns all listings, optionally sorted."""
    sort_by = request.args.get("sort_by", "score") # Default sort by score
    reverse_sort = True # Default for score, higher is better

    # For these fields, lower values are generally better, so reverse_sort is False
    if sort_by in {"price", "distance", "cost_per_sqft", "cost_per_roommate"}:
        reverse_sort = False

    listings = utils.load_listings()

    def sort_key(listing):
        """Helper function to extract the correct value for sorting."""
        value = listing.get(sort_by)
        
        # Handle missing or 'N/A' values for sorting
        if value is None or value == "N/A":
            # If sorting ascending, put 'N/A' at the very end (inf),
            # if sorting descending, put 'N/A' at the very end too (inf)
            # unless it's a "score" or similar where higher is always better
            if sort_by == "score" and reverse_sort: # For score, 'N/A' means lowest value
                return float('-inf') 
            return float('inf') 


        if sort_by in {"price", "cost_per_sqft", "cost_per_roommate", "rent_score"}:
            return utils.currency_to_float(value)
        elif sort_by == "distance":
            try:
                return float(value.split()[0]) # Extract numeric part from "X miles"
            except (ValueError, AttributeError):
                return float('inf')
        elif sort_by == "date_available":
            try:
                # Try parsing common date formats
                return datetime.strptime(value, "%B %d, %Y") if value != "Not Listed" else datetime.max
            except ValueError:
                try:
                    return datetime.strptime(value, "%Y-%m-%d") if value != "Not Listed" else datetime.max
                except ValueError:
                    return datetime.max # Put unparsable dates at the end
        elif isinstance(value, (int, float)):
            return value
        else:
            return 0 # Fallback for other types or unexpected values

    print(f"Sorting by: {sort_by}, Reverse: {reverse_sort}")
    # Perform the sort
    sorted_listings = sorted(listings, key=sort_key, reverse=reverse_sort)

    return jsonify(sorted_listings)

# --- NEW COMMENT ENDPOINT ---
@app.route('/update_comment', methods=['POST'])
def update_comment():
    data = request.get_json()
    listing_id = str(data.get('id'))
    comments = data.get('comments') # This will be the string from the textarea
    print(f"Comments: {comments}")

    if not listing_id:
        return jsonify({"success": False, "error": "Listing ID is required."}), 400

    listings = utils.load_listings()
    found = False
    for listing in listings:
        if str(listing.get('id')) == listing_id:
            listing['comments'] = comments # Update the comments field
            found = True
            break
    
    if found:
        utils.save_listings(listings)
        return jsonify({"success": True, "message": "Comment updated successfully."})
    else:
        return jsonify({"success": False, "error": "Listing not found."}), 404

# -- save the spiel to a .txt
@app.route('/save_spiel', methods=['POST'])
def save_spiel():
    """
    Receives a 'spiel' string from the frontend and saves it to 'application-spiel.txt'.
    """
    data = request.get_json()
    spiel_string = data.get('spiel')

    if spiel_string is None:
        return jsonify({"success": False, "error": "No 'spiel' string provided."}), 400

    file_path = "application-spiel.txt"
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(spiel_string)
        return jsonify({"success": True, "message": f"Application spiel saved to {file_path}"})
    except IOError as e:
        # Log the error for debugging on the server side
        print(f"Error saving spiel to file: {e}")
        return jsonify({"success": False, "error": f"Failed to save application spiel: {str(e)}"}), 500

@app.route('/get_spiel_content', methods=['GET'])
def get_spiel_content():
    """
    Reads the content of 'application-spiel.txt' and returns it.
    Returns an empty string if the file doesn't exist or is empty.
    """
    file_path = "application-spiel.txt"
    spiel_content = ""
    try:
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            with open(file_path, 'r', encoding='utf-8') as f:
                spiel_content = f.read()
        return jsonify({"success": True, "spiel": spiel_content})
    except IOError as e:
        print(f"Error reading spiel file: {e}")
        return jsonify({"success": False, "error": f"Failed to read spiel file: {str(e)}"}), 500


# --- Application Entry Point ---
if __name__ == "__main__":
    # If run directly, start the Flask development server.
    # The @app.before_request will handle initial loading and scoring.
    app.run(host="0.0.0.0", port=8080, debug=True)