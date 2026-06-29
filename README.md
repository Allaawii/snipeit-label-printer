# Snipe-IT Label Printer (Brother QL-800)

A Windows inventory-labeling tool for Snipe-IT. Paste a hardware asset or accessory URL, click Print Label, and a label prints on the Brother QL-800.

It does not use the Snipe-IT API. The print pipeline is:

URL → render page with Playwright → save PDF → rasterize PDF → send directly to the Brother printer via Win32 GDI.

For accessories (which have no native Snipe-IT label page), the app generates the label itself — same layout as hardware: QR code linking to the accessory page, name, IE logo, and cosmetic barcode.

## Full Setup Guide (Step-by-Step)

### Step 1: Install Python
1. Go to https://www.python.org/downloads/
2. Install Python 3.10 or newer.
3. During installation, enable **Add Python to PATH**.
4. Verify in Command Prompt:

```powershell
python --version
```

### Step 2: Clone repo

```powershell
git clone <repo_url>
cd snipeit-label-printer
```

### Step 3: Create and activate virtual environment

```powershell
python -m venv venv
venv\Scripts\activate
```

### Step 4: Install dependencies

```powershell
pip install -r requirements.txt
playwright install
```

### Step 5: Configure app

```powershell
copy config\config.example.json config\config.json
```

Open `config\config.json` and set:
- `base_url` — your Snipe-IT base URL including port, e.g. `https://snipeit.company.local:8085`
- `printer_name` — must exactly match the printer name shown in Windows Printers & Scanners
- `auth_mode` — use `storage_state` if your Snipe-IT requires login
- `storage_state_path` — default is `auth.json`

### Step 6: Set up authentication

Required if Snipe-IT requires login. Run this in a **native Windows PowerShell or CMD window** (not WSL):

```powershell
python create_auth.py https://your-snipeit-url/login
```

A Chromium window will open. Log in fully until you see the Snipe-IT dashboard, then press Enter in the terminal. This saves `auth.json`. Re-run whenever the session expires.

### Step 7: Run the app

```powershell
python src\main.py
```

Or double-click `run.bat`.

## How To Use

1. Open a hardware asset **or** accessory page in Snipe-IT.
2. Copy the full URL (e.g. `https://snipeit.example.com/hardware/91` or `/accessories/81`).
3. Paste it into the app.
4. Click **Print Label**.
5. The label prints on the configured Brother printer.

Use **Run Diagnostics** first when testing — it renders a preview PDF without printing.

## Troubleshooting

### Nothing prints
- Confirm `printer_name` exactly matches the Windows printer name.
- Print a test page to that printer from Windows to verify the driver works.

### Authentication required
- `auth.json` is missing, expired, or was generated inside WSL (invisible browser = incomplete login).
- Re-run `create_auth.py` in a native Windows PowerShell window, log in fully, then retry.

### Blank or incomplete label
- Increase `pre_print_delay_sec` in `config.json` (allowed range: 0.5–1.0).
- Verify the Snipe-IT label page fully loads in a normal browser.

### Playwright errors

```powershell
playwright install
```

## Notes
- Windows-only: depends on `pywin32` for Win32 GDI printing.
- Label dimensions in config must match the Brother QL-800 media loaded.
- Works only when the Snipe-IT site is reachable from the machine.
