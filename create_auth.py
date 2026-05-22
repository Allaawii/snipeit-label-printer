import os
import sys

from playwright.sync_api import sync_playwright


def _prompt_for_login_url() -> str:
    env_url = os.environ.get("SNIPEIT_LOGIN_URL", "").strip()
    if env_url:
        return env_url

    if len(sys.argv) > 1:
        return sys.argv[1].strip()

    entered_url = input("Enter your Snipe-IT login URL: ").strip()
    if not entered_url:
        raise SystemExit("A login URL is required.")
    return entered_url


def main() -> None:
    login_url = _prompt_for_login_url()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto(login_url)
        print("Log in to Snipe-IT in the opened browser, then press Enter here.")
        input()
        context.storage_state(path="auth.json")
        browser.close()


if __name__ == "__main__":
    main()