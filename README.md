# Snipe-IT Label Printer (Brother QL-800)

This app prints Snipe-IT hardware labels on Windows using a browser-rendered PDF flow:

URL -> render label page with Playwright -> save PDF -> rasterize PDF -> send directly to the Brother printer.

It does not use the Snipe-IT API.

## Full Setup Guide (Step-by-Step)

### Step 1: Install Python
1. Go to https://www.python.org/downloads/
2. Install Python 3.10 or newer.
3. During installation, enable Add Python to PATH.
4. Open Command Prompt and verify:

```powershell
python --version
```

### Step 2: Clone repo
Run these commands:

```powershell
git clone <repo_url>
cd snipeit-label-printer
```

### Step 3: Create virtual environment

```powershell
python -m venv venv
```

### Step 4: Activate virtual environment
Windows command:

```powershell
venv\Scripts\activate
```

### Step 5: Install dependencies

```powershell
pip install -r requirements.txt
```

### Step 6: Install Playwright browsers

```powershell
playwright install
```

### Step 7: Configure app
1. Copy config file:

```powershell
copy config\config.example.json config\config.json
```

2. Open config\config.json and set:
- base_url: your Snipe-IT base URL, for example https://snipeit.company.local
- printer_name: must exactly match the printer name in Windows Printers
- auth_mode: use storage_state for private Snipe-IT
- storage_state_path: default is auth.json

### Step 8: Setup authentication (VERY IMPORTANT)
If your Snipe-IT requires login, you must generate auth.json.

If auth.json is missing or expired, printing will fail.

Create a temporary file named create_auth.py in the project root with this code:

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://your-snipeit-url/login")
    print("Log in to Snipe-IT in the opened browser, then press Enter here.")
    input()
    context.storage_state(path="auth.json")
    browser.close()
```

Run it:

```powershell
python create_auth.py
```

This creates auth.json in the project root. Keep config storage_state_path aligned with this file path.

### Step 9: Run the app

```powershell
python src\main.py
```

Or run by double-clicking run.bat.

## How To Use
1. Open a hardware asset page in Snipe-IT.
2. Copy the full asset URL.
3. Paste URL into the app.
4. Click Print Label.
5. Wait for rendering and printing to complete.
6. Label should print on the configured Brother printer.

Use Run Diagnostics first when testing on a new laptop.

## Troubleshooting (Practical)

### Problem: Nothing prints
- Confirm printer_name exactly matches Windows printer name.
- Print a normal test page to that printer from Windows.
- Make sure the Brother printer driver is installed and selected correctly in Windows.

### Problem: Authentication required
- auth.json is missing, expired, or not valid for current Snipe-IT session.
- Regenerate auth.json and retry.

### Problem: Blank or incomplete label
- Increase pre_print_delay_sec in config\config.json (allowed range is 0.5 to 1.0).
- Verify the Snipe-IT label page fully loads in a normal browser.

### Problem: Playwright errors
Run:

```powershell
playwright install
```

Then retry.

## Important Notes
- Printer must be installed and working in Windows before running the app.
- Label dimensions in config must match Brother QL-800 media settings.
- Works only when the Snipe-IT site is reachable from the laptop.
- Uses browser rendering flow, not API.
- Does not depend on a PDF viewer association for printing.
