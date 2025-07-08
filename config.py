## Sky Vercauteren
## Zillower
## Updated july 2025

import os

# --- File Paths ---
LISTINGS_FILE = "listings.json"
GOOGLE_API_KEY_FILE = "googleapi.txt"

# --- Scoring Weights ---
SCORE_WEIGHTS = {
    "rent": 0.3,
    "sqft": 0.2,
    "bedrooms": 0.2,
    "bathrooms": 0.2,
    "distance": 0.1
}

# --- Google Maps API Key ---
Maps_API_KEY = None
try:
    with open(GOOGLE_API_KEY_FILE, "r") as file:
        Maps_API_KEY = file.read().strip()
except FileNotFoundError:
    print(f"WARNING: {GOOGLE_API_KEY_FILE} not found. Google Maps API key is missing.")
    Maps_API_KEY = "YOUR_Maps_API_KEY_HERE"  # Fallback/placeholder

# --- Origin Address for Distance Calculation ---
ORIGIN_ADDRESS = "120 1/2 W Laurel St A, Fort Collins, CO 80524"

# --- Request Headers for Web Scraping (Crucial for bypassing detection) ---
REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image:apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "max-age=0",
    "DNT": "1",
    "Priority": "u=0, i",
    "Referer": "https://www.zillow.com/",
    "sec-ch-ua": '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
}