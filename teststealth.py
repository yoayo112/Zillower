# teststealth.py
import sys
from playwright.sync_api import sync_playwright
from playwright_stealth.stealth import Stealth # Keep this import

print("--- Diagnostics for playwright_stealth usage ---")
stealth_instance = None # Will hold our instantiated Stealth object

try:
    # 1. Import the Stealth class from the stealth.py file
    # from playwright_stealth.stealth import Stealth # Already imported at the top
    
    print(f"Successfully imported 'Stealth' class. Type: {type(Stealth)}")

    # 2. Instantiate the Stealth class
    stealth_instance = Stealth()
    print(f"Successfully instantiated 'Stealth' object. Type: {type(stealth_instance)}")
    
    # 3. Confirm the 'apply_stealth_sync' method exists and is callable
    if hasattr(stealth_instance, 'apply_stealth_sync') and callable(stealth_instance.apply_stealth_sync):
        print("Found and confirmed 'apply_stealth_sync' method is callable.")
    else:
        print("Error: 'apply_stealth_sync' method not found or not callable on Stealth instance.")
        raise AttributeError("Required 'apply_stealth_sync' method is missing.")

except ImportError as e:
    print(f"ImportError: Could not import Stealth class. Details: {e}")
    sys.exit(1)
except Exception as e:
    print(f"An unexpected error occurred during stealth setup: {e}")
    print(f"Error type: {type(e)}")
    sys.exit(1)


print("\n--- Attempting to run Playwright ---")
# 'browser' variable no longer needs to be initialized here as it's within the 'with' scope
try:
    if stealth_instance:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True) # Keep headless for now for quick testing
            page = browser.new_page()
            
            # Call the apply_stealth_sync method on the instantiated object
            print("Calling stealth_instance.apply_stealth_sync(page)...")
            stealth_instance.apply_stealth_sync(page) 
            print("Stealth applied successfully.")
            
            page.goto("https://www.google.com")
            page.wait_for_timeout(3000) 
            print("Test successful: Browser opened with stealth enabled.")
            
    else:
        print("Cannot proceed: Stealth instance could not be created.")

except Exception as e:
    print(f"Test failed: {e}")
    print(f"Error type: {type(e)}")
finally:
    # REMOVED: browser.close()
    # The 'with sync_playwright() as p:' context manager handles browser cleanup automatically.
    print("Browser cleanup handled by sync_playwright context manager.")