# This is a test script to check if the playwright browsers are installed correctly
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    try:
        browser = p.chromium.launch()
        print("Chromium launched successfully!")
        browser.close()
    except Exception as e:
        print(f"Error launching Chromium: {e}")
