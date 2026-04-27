from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://snipeit.iesci.tech:8085/login")
    print("Log in to Snipe-IT in the opened browser, then press Enter here.")
    input()
    context.storage_state(path="auth.json")
    browser.close()