## Sky Vercauteren
## Zillower
## Updated july 2025



import json
import os
import requests
import base64
from datetime import datetime
import time
import random
import re
import shutil
import tempfile
import logging
import config # Allows access to constants like LISTINGS_FILE, Maps_API_KEY, etc.

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from playwright_stealth.stealth import Stealth
from typing import List, Dict, Any, Optional

# For scraping (keeping Selenium for now as in the previous `util.py` example)
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException


def currency_to_float(currency_string):
    """Converts a currency string (e.g., '$1,234.56/mo') to a float."""
    if isinstance(currency_string, str):
        try:
            if '-' in currency_string: # Handle ranges like "$1,000 - $1,200"
                cleaned_string = currency_string.split('-')[0].replace("$", "").replace(",", "").strip()
            else:
                cleaned_string = currency_string.replace("$", "").replace(",", "").replace("/mo", "").strip()
            return float(cleaned_string)
        except ValueError:
            return None
    elif isinstance(currency_string, (int, float)):
        return float(currency_string)
    else:
        return None

def load_listings():
    """Loads listings from the JSON file."""
    if os.path.exists(config.LISTINGS_FILE):
        with open(config.LISTINGS_FILE, "r") as file:
            try:
                data = json.load(file)
                # Ensure 'image' field is a list of data URIs
                for listing in data:
                    if 'image' not in listing or not isinstance(listing['image'], list):
                        if 'image' in listing and isinstance(listing['image'], str):
                            # Convert old raw Base64 string to a list containing a data URI
                            if listing['image'].startswith("data:"):
                                listing['image'] = [listing['image']]
                            else:
                                print(f"Converting old raw Base64 image for listing {listing.get('id')} to Data URI (assuming JPEG).")
                                listing['image'] = [f"data:image/jpeg;base64,{listing['image']}"]
                        else:
                            print(f"Warning: Listing {listing.get('id')} has malformed or missing 'image' field. Resetting to empty list.")
                            listing['image'] = []
                    
                    # Validate existing images in the list
                    valid_images = []
                    for img_data in listing['image']:
                        if isinstance(img_data, str) and img_data.startswith("data:") and len(img_data) > 50:
                            valid_images.append(img_data)
                        else:
                            print(f"Warning: Invalid image data found in listing {listing.get('id')}'s image list. Skipping this image.")
                    listing['image'] = valid_images
                return data
            except json.JSONDecodeError:
                print(f"Warning: {config.LISTINGS_FILE} is empty or malformed. Returning empty list.")
                return []
    else:
        return []

def save_listings(listings_data):
    """Saves listings to the JSON file."""
    with open(config.LISTINGS_FILE, "w") as file:
        json.dump(listings_data, file, indent=4)

def assign_scores(listings_data):
    """
    Calculates and assigns a score to each listing based on predefined weights.
    Returns the updated list of listings.
    """
    if not listings_data:
        return []
    if len(listings_data) == 1:
        listings_data[0]["score"] = (listings_data[0]["overall_rating"]/10)*100 # Cannot normalize with only one item
        return listings_data
    
    # Extract values for normalization, handling None gracefully
    price = [currency_to_float(listing["cost_per_roommate"]) for listing in listings_data if currency_to_float(listing["cost_per_roommate"]) is not None]
    square_feet = [listing["square_footage"] for listing in listings_data if isinstance(listing["square_footage"], int) and listing["square_footage"] > 0]
    bedrooms = [listing["bedrooms"] for listing in listings_data if isinstance(listing["bedrooms"], int) and listing["bedrooms"] >= 0]
    bathrooms = [listing["bathrooms"] for listing in listings_data if isinstance(listing["bathrooms"], (float, int)) and listing["bathrooms"] >= 0]
    distances = []
    for listing in listings_data:
        dist_str = listing.get("distance")
        if dist_str and dist_str != "N/A":
            try:
                distances.append(float(dist_str.split()[0]))
            except (ValueError, IndexError):
                pass

    # Calculate averages for fallback values
    avg_sqft = sum(square_feet) / len(square_feet) if square_feet else 1
    avg_bedrooms = sum(bedrooms) / len(bedrooms) if bedrooms else 0
    avg_bathrooms = sum(bathrooms) / len(bathrooms) if bathrooms else 0.0
    avg_rent = sum(price) / len(price) if price else 1

    def normalize(value, min_val, max_val, reverse=False):
        """Normalizes a value to a 0-100 scale."""
        if min_val == max_val:
            return 50 # Return a neutral score if min and max are the same
        score = 100 * (value - min_val) / (max_val - min_val)
        return 100 - score if reverse else score

    # Determine min/max for normalization, handle empty lists
    rent_min, rent_max = (min(price), max(price)) if price else (0, 1)
    sqft_min, sqft_max = (min(square_feet), max(square_feet)) if square_feet else (0, 1)
    bed_min, bed_max = (min(bedrooms), max(bedrooms)) if bedrooms else (0, 1)
    bath_min, bath_max = (min(bathrooms), max(bathrooms)) if bathrooms else (0, 1)
    dist_min, dist_max = (min(distances), max(distances)) if distances else (0, 1)

    for listing in listings_data:
        print(f"---------------LISTING: ID {listing.get('id', 'N/A')} ")
        
        # Assign average values if data is missing or invalid
        if not isinstance(listing.get("square_footage"), int) or listing["square_footage"] <= 0:
            listing["square_footage"] = avg_sqft
        if not isinstance(listing.get("bedrooms"), int) or listing["bedrooms"] < 0:
            listing["bedrooms"] = avg_bedrooms
        if not isinstance(listing.get("bathrooms"), (float, int)) or listing["bathrooms"] < 0:
            listing["bathrooms"] = avg_bathrooms
        if currency_to_float(listing.get("cost_per_roommate")) is None:
             listing["cost_per_roommate"] = avg_rent

        # Calculate individual scores based on weights
        rent_val = currency_to_float(listing["cost_per_roommate"])
        rent_score = normalize(rent_val, rent_min, rent_max, reverse=True) if rent_val is not None and rent_max != rent_min else 50
        rent_score *= config.SCORE_WEIGHTS["rent"]
        listing["rent_score"] = round(rent_score, 2)

        sqft_score = normalize(listing["square_footage"], sqft_min, sqft_max) if listing["square_footage"] > 0 and sqft_max != sqft_min else 50
        sqft_score *= config.SCORE_WEIGHTS["sqft"]
        listing["sqft_score"] = round(sqft_score, 2)

        bedrooms_score = normalize(int(listing["bedrooms"]), bed_min, bed_max) if bed_max != bed_min else 50
        bedrooms_score *= config.SCORE_WEIGHTS["bedrooms"]
        listing["bedrooms_score"] = round(bedrooms_score, 2)

        bathrooms_score = normalize(float(listing["bathrooms"]), bath_min, bath_max) if bath_max != bath_min else 50
        bathrooms_score *= config.SCORE_WEIGHTS["bathrooms"]
        listing["bathrooms_score"] = round(bathrooms_score, 2)
        
        distance_val_str = listing.get("distance")
        distance_val = None
        if distance_val_str and distance_val_str != "N/A" and isinstance(distance_val_str, str):
            try:
                distance_val = float(distance_val_str.split()[0])
            except (ValueError, IndexError):
                pass

        distance_score = normalize(distance_val, dist_min, dist_max, reverse=True) if distance_val is not None and dist_max != dist_min else 50
        distance_score *= config.SCORE_WEIGHTS["distance"]
        listing["distance_score"] = round(distance_score, 2)

        # Calculate overall score
        listing["score"] = round((
            listing["rent_score"] +
            listing["sqft_score"] +
            listing["bedrooms_score"] +
            listing["bathrooms_score"] +
            listing["distance_score"]
        ), 2)
        print(f"Overall Score: {listing['score']:.2f}")

    return listings_data

def get_distance(destination_address):
    """Uses Google Maps Distance Matrix API to get travel distance."""
    if not config.Maps_API_KEY or config.Maps_API_KEY == "YOUR_Maps_API_KEY_HERE":
        print("Google Maps API key is not set. Cannot calculate distance.")
        return "N/A"
        
    encoded_origin = requests.utils.quote(config.ORIGIN_ADDRESS)
    encoded_destination = requests.utils.quote(destination_address)
    url = f"https://maps.googleapis.com/maps/api/distancematrix/json?origins={encoded_origin}&destinations={encoded_destination}&units=imperial&key={config.Maps_API_KEY}"
    
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        try:
            if data['status'] == 'OK' and data['rows'][0]['elements'][0]['status'] == 'OK':
                distance_text = data["rows"][0]["elements"][0]["distance"]["text"]
                return distance_text
            else:
                error_status = data['rows'][0]['elements'][0]['status']
                print(f"Google Maps API element status not OK: {error_status}. Message: {data.get('error_message', 'No error message.')}")
                return "N/A"
        except (KeyError, IndexError) as e:
            print(f"Error parsing Google Maps API response: {e}")
            print(f"Google Maps API raw response: {data}")
            return "N/A"
    else:
        print(f"Google Maps API request failed with status code: {response.status_code}")
        return "N/A"



# Assuming a 'config.py' exists with these variables
# If you don't have a config.py, you'll need to define these directly or provide it.
try:
    import config
except ImportError:
    # Fallback if config.py doesn't exist (for standalone testing)
    class ConfigFallback:
        LISTINGS_FILE = 'listings_test.json'
        ORIGIN_ADDRESS = "120 1/2 W Laurel St A, Fort Collins, CO 80524"
        SCORE_WEIGHTS = {
            "rent": 0.3,
            "sqft": 0.2,
            "bedrooms": 0.2,
            "bathrooms": 0.2,
            "distance": 0.1
        }
    config = ConfigFallback()
    logging.warning("No config.py found. Using default configurations for testing.")


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_listings() -> List[Dict[str, Any]]:
    """Loads listings from a JSON file."""
    if not os.path.exists(config.LISTINGS_FILE):
        return []
    with open(config.LISTINGS_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            logging.error(f"Error decoding JSON from {config.LISTINGS_FILE}. Returning empty list.")
            return []

def save_listings(listings: List[Dict[str, Any]]):
    """Saves listings to a JSON file."""
    with open(config.LISTINGS_FILE, 'w') as f:
        json.dump(listings, f, indent=4)
    logging.info(f"Saved {len(listings)} listings to {config.LISTINGS_FILE}")

def currency_to_float(currency_str: Optional[Any]) -> Optional[float]:
    """Converts a currency string (e.g., "$1,200") to a float (e.g., 1200.0)."""
    if currency_str is None or isinstance(currency_str, (int, float)):
        return currency_str
    try:
        # Remove '$', ',', and any other non-numeric characters except '.'
        clean_str = re.sub(r'[$,]', '', str(currency_str)).strip()
        return float(clean_str)
    except ValueError:
        return None

def _parse_zillow_html(soup, url):
    """
    Parses a BeautifulSoup object (Zillow HTML) to extract listing details.
    This is an internal helper for scrape_zillow and add_listing_from_html.
    """
    listing_data = {}
    session = requests.Session() # Use a session for potentially better performance/connection reuse

    # Attempt to parse data from JSON-LD script (preferred method)
    script_json_ld = soup.find('script', type='application/ld+json')
    if script_json_ld:
        try:
            json_data = json.loads(script_json_ld.string)
            json_items = [json_data] if isinstance(json_data, dict) else json_data # Handle single object or list of objects

            for item in json_items:
                if item.get('@type') in ['Product', 'Residence', 'House', 'RealEstateListing']:
                    # Extract price
                    price_offer = item.get('offers', {}).get('price')
                    print(f" PRICE ___ ${price_offer}")
                    listing_data['price'] = float(price_offer) if price_offer else None

                    # Extract address
                    address_obj = item.get('address', {})
                    address_parts = [
                        address_obj.get('streetAddress'),
                        address_obj.get('addressLocality'),
                        address_obj.get('addressRegion'),
                        address_obj.get('postalCode')
                    ]
                    listing_data['address'] = ", ".join(filter(None, address_parts))

                    # Extract bedrooms/bathrooms
                    rooms_text = item.get('numberOfRooms')
                    if isinstance(rooms_text, str):
                        beds_match = re.search(r'(\d+)\s*Bed', rooms_text, re.IGNORECASE)
                        baths_match = re.search(r'(\d+(\.\d+)?)\s*Bath', rooms_text, re.IGNORECASE)
                        listing_data['bedrooms'] = int(beds_match.group(1)) if beds_match else -1
                        listing_data['bathrooms'] = float(baths_match.group(1)) if baths_match else -1
                    elif isinstance(rooms_text, (int, float)):
                        listing_data['bedrooms'] = int(rooms_text)
                    
                    # Also check direct 'bed' and 'bath' fields if present
                    if 'bed' in item and isinstance(item['bed'], (int, float)):
                        listing_data['bedrooms'] = int(item['bed'])
                    if 'bath' in item and isinstance(item['bath'], (int, float)):
                        listing_data['bathrooms'] = float(item['bath'])

                    # Extract square footage
                    floor_size = item.get('floorSize', {})
                    if isinstance(floor_size, dict):
                        sqft_val = floor_size.get('value')
                        sqft_unit = floor_size.get('unitCode')
                        if sqft_val and sqft_unit == 'SQF':
                            listing_data['square_footage'] = int(sqft_val)
                    
                    # Extract image URL
                    image_url_from_json = item.get('image')
                    if isinstance(image_url_from_json, list) and image_url_from_json:
                        listing_data['image_url_for_fetch'] = image_url_from_json[0]
                    elif isinstance(image_url_from_json, str):
                        listing_data['image_url_for_fetch'] = image_url_from_json

                    # If we found sufficient data, break the loop
                    if listing_data.get('address') and listing_data.get('price'):
                        break
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON-LD script: {e}")
        except Exception as e:
            print(f"Unexpected error processing JSON-LD: {e}")

    # Fallback to direct HTML parsing if JSON-LD fails or is incomplete
    # Price element attempt 1.
    if listing_data.get('price') is None:
        #price_element = soup.find("span", class_="Text-c11n-8-109-3__sc-aiai24-0 sc-lknQiW knxFxJ jMCwlu")
        # Attempt 2
      #if not price_element:
      #    price_element = soup.find("span", class_="Text-c11n-8-109-3__sc-aiai24-0 WduMe").parent

        # Attempt 3
        inner_span = soup.find('span', class_=['Text-c11n-8-109-3__sc-aiai24-0', 'WduMe'], text="/mo")
        if inner_span:
            # Get the parent of this inner span, which is our target outer span
            outer_span = inner_span.parent
        
            # Get only the direct text content of the outer_span
            # .contents gives you a list of children (tags and NavigableString objects)
            # Filter for NavigableString (text) and join them
            direct_text_parts = [
                str(content) for content in outer_span.contents
                if isinstance(content, str) and content.strip()
            ]
            price_text = "".join(direct_text_parts).strip()
        
            print(f"Extracted price: {price_text}") # Output: Extracted price: $1,100
            match = re.search(r'(\d[\d,.]*\d|\d+)', price_text)
            if match:
                listing_data['price'] = float(match.group(1).replace(",", ""))
            else:
                listing_data['price'] = None
        else:
            print("Inner span not found.")
        
    if not listing_data.get('address'):
        address_element_h2 = soup.find("h2", {"data-test-id": "bdp-building-address"})
        if address_element_h2:
            listing_data['address'] = address_element_h2.text.strip()
        else:
            address_element_h1 = soup.find("h1", class_="Text-c11n-8-109-3__sc-aiai24-0 cEHZrB")
            listing_data['address'] = address_element_h1.text.strip() if address_element_h1 else "Address not found"

    if listing_data.get('bedrooms', -1) < 0:
        bedrooms_element = soup.find("span", string=lambda s: s and "beds" in s.lower())
        if bedrooms_element:
            try:
                beds_text = bedrooms_element.find_previous("span").text.strip()
                listing_data['bedrooms'] = int(re.search(r'\d+', beds_text).group(0)) if re.search(r'\d+', beds_text) else -1
            except (AttributeError, ValueError):
                listing_data['bedrooms'] = -1

    if listing_data.get('bathrooms', -1) < 0:
        bathrooms_element = soup.find("span", string=lambda s: s and "baths" in s.lower())
        if bathrooms_element:
            try:
                baths_text = bathrooms_element.find_previous("span").text.strip()
                listing_data['bathrooms'] = float(re.search(r'\d+(\.\d+)?', baths_text).group(0)) if re.search(r'\d+(\.\d+)?', baths_text) else -1
            except (AttributeError, ValueError):
                listing_data['bathrooms'] = -1
    
    # Attempt 1 sq ft
    #if listing_data.get('square_footage', -1) < 0:
     #   sqft_element = soup.find("span", string=lambda s: s and "sqft" in s.lower())
    # Attempt 2 sq ft
    if listing_data.get('square_footage', -1) < 0:
        sqft_element = soup.find_all("span", class_="Text-c11n-8-109-3__sc-aiai24-0 styles__StyledValueText-fshdp-8-106-0__sc-12ivusx-1 cEHZrB bfIPme --medium")[2]
        if sqft_element:
            listing_data['square_footage']=sqft_element.text
            print(f"sqft ___ {sqft_element.text}")
            try:
                sqft_text = sqft_element.find_previous("span").text.strip().replace(",", "")
                listing_data['square_footage'] = int(re.search(r'\d+', sqft_text).group(0)) if re.search(r'\d+', sqft_text) else -1
            except (AttributeError, ValueError):
                listing_data['square_footage'] = -1
    # Date Attempt 1
    if not listing_data.get('date_available'):
        date_available_element = soup.find("div", string=lambda s: s and "available" in s.lower())
    # Date Attempt 2
    if not listing_data.get('date_available'):
        date_available_element = soup.find("span", class_="Text-c11n-8-109-3__sc-aiai24-0 hdp__sc-1hoxd7t-2 cEHZrB iWQNvU")
        listing_data['date_available'] = date_available_element.text.strip() if date_available_element else "Not Listed"

    if not listing_data.get('image_url_for_fetch'):
        gallery = soup.find("div", {"data-testid": "hollywood-gallery-images-tile-list"})
        first_li = None
        if gallery:
            first_li = gallery.find("li")
        image_tag = first_li.find("img") if first_li else None
        image_url = image_tag["src"] if image_tag and "src" in image_tag.attrs else None
        listing_data['image_url_for_fetch'] = image_url

    # Fetch and encode image
    encoded_images = []
    image_url_to_fetch = listing_data.get('image_url_for_fetch')
    if image_url_to_fetch:
        try:
            img_response = session.get(image_url_to_fetch, timeout=10, headers=config.REQUEST_HEADERS)
            img_response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            
            content_type = img_response.headers.get('Content-Type', 'application/octet-stream').split(';')[0].strip()
            base64_content = base64.b64encode(img_response.content).decode("utf-8")
            full_data_uri = f"data:{content_type};base64,{base64_content}"
            
            if full_data_uri and len(full_data_uri) > 50: # Basic validation of data URI length
                encoded_images.append(full_data_uri)
                print(f"Scraped image converted to Data URI: {full_data_uri[:50]}... (Length: {len(full_data_uri)})")
            else:
                print(f"Warning: Scraped image from {image_url_to_fetch} was too short or invalid. Not added.")

        except requests.exceptions.RequestException as e:
            print(f"Error fetching image {image_url_to_fetch}: {e}")
    
    listing_data['image'] = encoded_images

    # Get distance
    listing_data['distance'] = get_distance(listing_data['address']) # Calls another utility function

    # Return a structured dictionary
    return {
        "image": listing_data.get('image', []),
        "price": listing_data.get('price'),
        "address": listing_data.get('address', "Address not found"),
        "bedrooms": listing_data.get('bedrooms', -1),
        "bathrooms": listing_data.get('bathrooms', -1.0),
        "square_footage": listing_data.get('square_footage', -1),
        "date_available": listing_data.get('date_available', "Not Listed"),
        "distance": listing_data.get('distance', "N/A"),
        "url": url
    }


def _get_distance(origin: str, destination: str) -> Optional[float]:
    """
    Placeholder for distance calculation. Requires a real API (e.g., Google Maps).
    Returns distance in miles or None if calculation fails.
    """
    logging.warning(f"Distance calculation is a placeholder. Manual entry or API integration needed for '{destination}'.")
    return None # Return None as distance cannot be reliably calculated without an API

def scrape_zillow(url, headless=True):
    """
    Scrapes a Zillow listing URL using Playwright for full JavaScript rendering.
    Handles CAPTCHA detection and provides options for manual solving.
    """
    print(f"Attempting to scrape Zillow URL: {url} using Playwright.")
    
    stealth_instance = Stealth() # For Playwright stealth mode

    temp_dir = None
    browser_context = None
    scraped_data_result = {}

    try:
        temp_dir = tempfile.mkdtemp() # Create a temporary directory for browser profile
        print(f"Using temporary browser profile: {temp_dir}")

        with sync_playwright() as p:
            try: 
                # Launch persistent context to reuse the profile if needed for CAPTCHA
                browser_context = p.chromium.launch_persistent_context(
                    user_data_dir=temp_dir,
                    headless=headless,
                    channel='chrome' # Use Chrome channel for better compatibility
                ) 
                page = browser_context.new_page()

                stealth_instance.apply_stealth_sync(page) # Apply stealth settings
                page.set_extra_http_headers(config.REQUEST_HEADERS) # Set custom headers

                # Simulate human-like delay before navigating
                delay_before_goto = random.uniform(2.0, 4.0)
                print(f"Waiting for {delay_before_goto:.2f} seconds before navigating...")
                time.sleep(delay_before_goto) 

                print(f"Navigating to {url}...")
                page.goto(url, wait_until="domcontentloaded", timeout=60000) # Wait up to 60 seconds
                print("Page loaded (domcontentloaded).")

                # Simulate human-like delay after navigation
                delay_after_goto = random.uniform(3.0, 7.0)
                print(f"Waiting for {delay_after_goto:.2f} seconds after navigation...")
                time.sleep(delay_after_goto)

                # Check for CAPTCHA
                if page.locator('text=Verify you\'re not a robot').is_visible() or \
                   page.locator('text=Please verify you are a human').is_visible() or \
                   page.locator('input[name="h_captcha_response"]').is_visible():
                    print("\n=========================================================================")
                    print("  CAPTCHA DETECTED! Browser is open for manual solving.")
                    print("=========================================================================")
                    if not headless:
                        # If not headless, prompt user to solve in the visible browser
                        input("Press Enter to continue scraping after solving CAPTCHA...\n")
                    else:
                        # If headless, re-launch in non-headless mode to allow solving
                        browser_context.close()
                        browser_context = p.chromium.launch_persistent_context(
                            user_data_dir=temp_dir,
                            headless=False,
                            channel='chrome'
                        )
                        page = browser_context.new_page()
                        stealth_instance.apply_stealth_sync(page)
                        page.set_extra_http_headers(config.REQUEST_HEADERS)
                        page.goto(url, wait_until="domcontentloaded", timeout=60000)
                        input("CAPTCHA window opened. Press Enter after solving and closing it...\n")

                # Get the fully rendered HTML content
                html = page.content()
                soup = BeautifulSoup(html, "html.parser")
                print(f"Successfully retrieved rendered HTML from {url}")

                # Parse the HTML using the internal helper
                scraped_data_result = _parse_zillow_html(soup, url)

            except PlaywrightTimeoutError as e:
                print(f"Playwright operation timed out: {e}")
                scraped_data_result = {"error": f"Playwright timeout: {e}"}
            except Exception as e: # Catch any other Playwright-related errors
                print(f"An unexpected error occurred during Playwright operations: {e}")
                print(f"Error details: {e.__class__.__name__}: {e}")
                scraped_data_result = {"error": f"Playwright error: {e}"}
            finally:
                if browser_context:
                    browser_context.close() # Always close the browser context
                    print("Browser context closed.")
        
    except Exception as outer_e: # Catch errors during Playwright setup
        print(f"An outer error occurred during setup or Playwright context creation: {outer_e}")
        print(f"Error details: {outer_e.__class__.__name__}: {outer_e}")
        scraped_data_result = {"error": f"Scraper setup error: {outer_e}"}
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir) # Clean up the temporary browser profile
            print(f"Cleaned up temporary browser profile at {temp_dir}")
        print("Scrape function finished and cleanup performed.")
    
    return scraped_data_result
def calculate_cost_per_occupant(rent: Optional[float], num_occupants: int, utility_estimate: Optional[float] = None) -> Optional[float]:
    """
    Calculates the cost per occupant, including an optional utility estimate.
    """
    rent_val = currency_to_float(rent)
    
    if rent_val is None:
        return None
    
    total_cost = rent_val
    # Safely add utility_estimate if it's a number
    if utility_estimate is not None and isinstance(utility_estimate, (int, float)):
        total_cost += float(utility_estimate)
    
    if num_occupants is None or num_occupants <= 0:
        # If no occupants specified or 0, cost is just rent + utility (for single person or total cost display)
        return total_cost 
    
    return total_cost / num_occupants

def assign_scores(listings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Assigns a recommended score to each listing based on configurable weights."""
    if not listings:
        return []

    # Make a copy to avoid modifying the original list during iteration if needed elsewhere
    scored_listings = [l.copy() for l in listings]

    weights = config.SCORE_WEIGHTS # Get weights from config

    def distance_to_float(dist_val: Optional[Any]) -> Optional[float]:
        """Converts distance string (e.g., '5.2 miles') or None to float."""
        if dist_val is None:
            return None
        if isinstance(dist_val, (int, float)):
            return float(dist_val)
        try:
            # Extract numeric part from "X miles" or similar
            match = re.search(r'(\d+(\.\d+)?)', str(dist_val))
            if match:
                return float(match.group(1))
        except (ValueError, TypeError):
            pass # Fall through to return None
        return None

    # Filter out listings that don't have enough data to calculate scores for normalization
    # These listings will get a score of 0.0 or similar.
    calculable_listings = [
        l for l in scored_listings
        if l.get("price") is not None and currency_to_float(l["price"]) is not None and
           l.get("square_footage") is not None and l["square_footage"] > 0 and
           l.get("bedrooms") is not None and l["bedrooms"] > 0 and
           l.get("bathrooms") is not None and l["bathrooms"] > 0 and
           distance_to_float(l.get("distance")) is not None and distance_to_float(l.get("distance")) >= 0 and
           l.get("overall_rating") is not None and l["overall_rating"] >= 1 and l["overall_rating"] <= 10 and
           l.get("roommates") is not None and l["roommates"] >= 0 # 0 means living alone
    ]

    if not calculable_listings:
        # If no listings are calculable, set default scores and derived fields for all
        for listing in scored_listings:
            listing["score"] = 0.0
            listing["cost_per_sqft"] = "N/A"
            listing["cost_per_occupant"] = "N/A"
        return scored_listings

    # Prepare data for normalization by converting to floats where necessary
    prices = [currency_to_float(l["price"]) for l in calculable_listings if currency_to_float(l["price"]) is not None]
    sqfts = [l["square_footage"] for l in calculable_listings]
    beds = [l["bedrooms"] for l in calculable_listings]
    baths = [l["bathrooms"] for l in calculable_listings]
    distances = [distance_to_float(l["distance"]) for l in calculable_listings if distance_to_float(l["distance"]) is not None]


    # Calculate min/max for normalization, avoiding errors for single-item lists
    min_price = min(prices) if prices else 0
    max_price = max(prices) if prices else 1
    min_sqft = min(sqfts) if sqfts else 0
    max_sqft = max(sqfts) if sqfts else 1
    min_beds = min(beds) if beds else 0
    max_beds = max(beds) if beds else 1
    min_baths = min(baths) if baths else 0
    max_baths = max(baths) if baths else 1
    min_distance = min(distances) if distances else 0
    max_distance = max(distances) if distances else 1

    # Prevent division by zero if all values are the same
    price_range = max_price - min_price if (max_price - min_price) != 0 else 1
    sqft_range = max_sqft - min_sqft if (max_sqft - min_sqft) != 0 else 1
    beds_range = max_beds - min_beds if (max_beds - min_beds) != 0 else 1
    baths_range = max_baths - min_baths if (max_baths - min_baths) != 0 else 1
    distance_range = max_distance - min_distance if (max_distance - min_distance) != 0 else 1

    for listing in scored_listings:
        raw_price = currency_to_float(listing.get("price"))
        sqft = listing.get("square_footage")
        bedrooms = listing.get("bedrooms")
        bathrooms = listing.get("bathrooms")
        distance = distance_to_float(listing.get("distance")) # Use the converted distance
        overall_rating = listing.get("overall_rating")
        roommates = listing.get("roommates", 0)
        
        # Safely get utility_estimate, default to 0.0 if None or missing
        utility_estimate_val = listing.get("utility_estimate")
        if utility_estimate_val is None:
            utility_estimate = 0.0
        else:
            try:
                utility_estimate = float(utility_estimate_val)
            except (ValueError, TypeError):
                utility_estimate = 0.0 # Default to 0.0 if it's not a valid number (e.g., "N/A")

        # Calculate derived fields (even if not used in score calculation, display on card)
        if raw_price is not None and sqft is not None and sqft > 0:
            listing["cost_per_sqft"] = round((raw_price + utility_estimate) / sqft, 2)
        else:
            listing["cost_per_sqft"] = "N/A"
        
        listing["cost_per_occupant"] = calculate_cost_per_occupant(raw_price, roommates, utility_estimate)
        if listing["cost_per_occupant"] is not None:
             listing["cost_per_occupant"] = round(listing["cost_per_occupant"], 2)
        else:
             listing["cost_per_occupant"] = "N/A"

        # Check if current listing has enough data to be scored
        if raw_price is None or sqft is None or sqft <= 0 or \
           bedrooms is None or bedrooms <= 0 or \
           bathrooms is None or bathrooms <= 0 or \
           distance is None or distance < 0 or \
           overall_rating is None or overall_rating < 1 or overall_rating > 10:
            listing["score"] = 0.0
            continue # Skip to next listing if data is incomplete

        # Normalize values (0-1 range)
        # Price (lower is better): 1 - (value - min) / (max - min)
        price_normalized = 1 - ((raw_price - min_price) / price_range) if price_range != 0 else 0.5
        # Square Footage (higher is better): (value - min) / (max - min)
        sqft_normalized = (sqft - min_sqft) / sqft_range if sqft_range != 0 else 0.5
        # Bedrooms (higher is better): (value - min) / (max - min)
        beds_normalized = (bedrooms - min_beds) / beds_range if beds_range != 0 else 0.5
        # Bathrooms (higher is better): (value - min) / (max - min)
        baths_normalized = (bathrooms - min_baths) / baths_range if baths_range != 0 else 0.5
        # Distance (lower is better): 1 - (value - min) / (max - min)
        distance_normalized = 1 - ((distance - min_distance) / distance_range) if distance_range != 0 else 0.5
        # Overall Rating (higher is better, scale 1-10 to 0-1)
        rating_normalized = (overall_rating - 1) / 9.0

        # Calculate score using weights
        score = (
            (price_normalized * weights.get("rent", 0)) +
            (sqft_normalized * weights.get("sqft", 0)) +
            (beds_normalized * weights.get("bedrooms", 0)) +
            (baths_normalized * weights.get("bathrooms", 0)) +
            (distance_normalized * weights.get("distance", 0)) +
            (rating_normalized * (1 - sum(weights.values()))) # Remaining weight for overall rating
        )
        listing["score"] = round(score, 2)

    return scored_listings

# Example usage (for testing purposes only)
if __name__ == '__main__':
    print("--- utils.py Test Run ---")

    # Ensure config.py is present or defaults are used for testing
    if not os.path.exists('config.py'):
        print("Warning: 'config.py' not found. Using fallback defaults for testing.")
        # Create a dummy config file for the test run
        with open('config.py', 'w') as f:
            f.write("LISTINGS_FILE = 'listings_test.json'\n")
            f.write("ORIGIN_ADDRESS = '120 1/2 W Laurel St A, Fort Collins, CO 80524'\n")
            f.write("SCORE_WEIGHTS = {'rent': 0.3, 'sqft': 0.2, 'bedrooms': 0.2, 'bathrooms': 0.2, 'distance': 0.1}\n")
        # Reload config module to pick up the new file
        import importlib
        import sys
        if 'config' in sys.modules:
            importlib.reload(config)
        else:
            import config
    
    # Clean up test listings file if it exists
    if os.path.exists(config.LISTINGS_FILE):
        os.remove(config.LISTINGS_FILE)
        print(f"Cleaned up old {config.LISTINGS_FILE}")

    # Test load/save
    initial_listings = load_listings()
    print(f"Initial listings loaded: {len(initial_listings)}")

    test_listing_1 = {
        "id": 1,
        "url": "http://example.com/test1",
        "address": "123 Main St",
        "price": "$2,000",
        "square_footage": 1200,
        "bedrooms": 3,
        "bathrooms": 2.5,
        "date_available": "August 1, 2025",
        "distance": "2.5 miles", # Now a string, to test conversion
        "contacted": False,
        "applied": False,
        "group": "none",
        "overall_rating": 7,
        "roommates": 2,
        "image": [],
        "comments": "Good location",
        "utility_estimate": 150.0
    }
    
    test_listing_2 = {
        "id": 2,
        "url": "http://example.com/test2",
        "address": "456 Oak Ave",
        "price": "$1,500",
        "square_footage": 900,
        "bedrooms": 2,
        "bathrooms": 1.0,
        "date_available": "Immediately",
        "distance": 0.8, # Still a float
        "contacted": True,
        "applied": False,
        "group": "red",
        "overall_rating": 9,
        "roommates": 1,
        "image": [],
        "comments": "Small but cheap",
        "utility_estimate": 50.0
    }

    test_listing_3 = { # Incomplete data for scoring, distance as "N/A"
        "id": 3,
        "url": "http://example.com/test3",
        "address": "789 Pine Ln",
        "price": "$2,500",
        "square_footage": None, # Missing data
        "bedrooms": 4,
        "bathrooms": 3.0,
        "date_available": "September 1, 2025",
        "distance": "N/A", # String "N/A"
        "contacted": False,
        "applied": False,
        "group": "none",
        "overall_rating": 6,
        "roommates": 3,
        "image": [],
        "comments": "Big but far",
        "utility_estimate": 200.0
    }
    
    test_listing_4 = { # Distance as 0.0, utility_estimate as None
        "id": 4,
        "url": "http://example.com/test4",
        "address": "100 Close St",
        "price": "$1200",
        "square_footage": 700,
        "bedrooms": 1,
        "bathrooms": 1.0,
        "date_available": "July 10, 2025",
        "distance": 0.0, # Distance as 0.0
        "contacted": False,
        "applied": False,
        "group": "none",
        "overall_rating": 8,
        "roommates": 1,
        "image": [],
        "comments": "Very close",
        "utility_estimate": None # Test with None utility estimate
    }
    
    test_listing_5 = { # Price as None, utility_estimate as "100" (string)
        "id": 5,
        "url": "http://example.com/test5",
        "address": "200 Missing Price",
        "price": None, # Test with None price
        "square_footage": 800,
        "bedrooms": 2,
        "bathrooms": 1.0,
        "date_available": "August 15, 2025",
        "distance": 3.0,
        "contacted": False,
        "applied": False,
        "group": "none",
        "overall_rating": 7,
        "roommates": 2,
        "image": [],
        "comments": "Missing price test",
        "utility_estimate": "100" # Test with string utility estimate
    }


    test_listings = [test_listing_1, test_listing_2, test_listing_3, test_listing_4, test_listing_5]
    save_listings(test_listings)
    print(f"Saved {len(test_listings)} test listings.")

    loaded_listings = load_listings()
    print(f"Loaded {len(loaded_listings)} listings after saving.")

    # Test assign_scores
    print("\nAssigning scores to listings:")
    scored_listings = assign_scores(loaded_listings)
    for listing in scored_listings:
        print(f"ID: {listing.get('id')}, "
              f"Address: {listing.get('address')}, "
              f"Price: {listing.get('price')}, "
              f"Utilities: {listing.get('utility_estimate')}, "
              f"SqFt: {listing.get('square_footage')}, "
              f"Beds: {listing.get('bedrooms')}, "
              f"Baths: {listing.get('bathrooms')}, "
              f"Distance: {listing.get('distance')}, "
              f"Rating: {listing.get('overall_rating')}, "
              f"Occupants: {listing.get('roommates')}, "
              f"Cost/SqFt: {listing.get('cost_per_sqft')}, "
              f"Cost/Occupant: {listing.get('cost_per_occupant')}, "
              f"Score: {listing.get('score')}")
    
    # Test `calculate_cost_per_occupant`
    print(f"\nTesting calculate_cost_per_occupant:")
    print(f"Rent $950, 1 occupant, $50 utility: ${calculate_cost_per_occupant(950, 1, 50):.2f}")
    print(f"Rent $1800, 3 occupants, $120 utility: ${calculate_cost_per_occupant(1800, 3, 120):.2f}")
    print(f"Rent $1000, 0 occupants, $80 utility (should just be total cost): ${calculate_cost_per_occupant(1000, 0, 80):.2f}")
    print(f"Rent $700, 1 occupant, no utility: ${calculate_cost_per_occupant(700, 1):.2f}")
    print(f"Rent $700, 1 occupant, None utility: ${calculate_cost_per_occupant(700, 1, None):.2f}")
    print(f"Rent $700, 1 occupant, 'N/A' utility: ${calculate_cost_per_occupant(700, 1, 'N/A')}") # Should be 700 / 1

    # Test scraping (this part requires a functional chromedriver setup)
    print("\nAttempting to scrape a Zillow URL (requires chromedriver and internet)...")
    sample_zillow_url = "https://www.zillow.com/homedetails/433-W-Locust-St-Fort-Collins-CO-80521/13374246_zpid/"
    # If headless=True, you won't see a browser. Set to False for debugging browser issues.
    # scraped_data_live = scrape_zillow(sample_zillow_url, headless=True, utility_estimate=100.0)
    # if "error" in scraped_data_live:
    #     print(f"Scraping failed: {scraped_data_live['error']}")
    # else:
    #     print("Scraped data:")
    #     for k, v in scraped_data_live.items():
    #         print(f"  {k}: {v}")

    # Clean up dummy config file after test
    if os.path.exists('config.py'):
        os.remove('config.py')
    if os.path.exists(config.LISTINGS_FILE):
        os.remove(config.LISTINGS_FILE)
    print("\n--- utils.py Test Run Complete ---")