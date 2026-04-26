# Snipe-IT Label Printer (Brother QL-800)

## Description
Snipe-IT Label Printer is a small Windows desktop tool for IT teams that print hardware asset labels from Snipe-IT.

Instead of manually opening label pages, exporting files, and printing through multiple screens, this tool lets you paste a Snipe-IT hardware asset URL and print directly to a Brother QL-800.

It is designed for internal operations where speed and consistency matter.

## Features
- Print label from hardware asset URL
- Uses Snipe-IT built-in labels
- Works with Brother QL-800
- No modification to Snipe-IT required
- Simple GUI + clipboard support
- Diagnostics button to validate URL parsing, printer detection, and PDF rendering

## Requirements
- Windows 10 or Windows 11
- Python 3.10+
- Brother QL-800 installed and working in Windows
- Snipe-IT accessible from the laptop

## Project Structure
snipeit-label-printer/
- src/
  - main.py
  - browser.py
  - printer.py
  - utils.py
- config/
  - config.example.json
  - config.json (local file, not committed)
- logs/
- README.md
- requirements.txt
- .gitignore
- run.bat
- LICENSE

## Installation
1. Clone this repository.
2. Install Python 3.10 or newer.
3. Open Command Prompt or PowerShell in the project folder.
4. Install dependencies:
   - pip install -r requirements.txt
5. Install Playwright browser runtime:
   - playwright install
6. Copy configuration template:
   - copy config\config.example.json config\config.json
7. Edit config\config.json:
   - Set base_url to your Snipe-IT URL
   - Set printer_name to the exact Windows printer name for your Brother QL-800

## How to Run
- Command line:
  - python src/main.py
- Non-technical option:
  - Double-click run.bat

## How to Use
1. Open a hardware asset in Snipe-IT.
2. Copy the hardware asset URL.
3. Paste the URL into the app.
4. Click Print Label.
5. The label is rendered and sent to the configured printer automatically.

### Clipboard Button
- Click Use Clipboard to paste the current clipboard text into the URL field.

### Diagnostics Button
- Click Run Diagnostics to verify:
  - Asset ID extraction from URL
  - Final label URL generation
  - Printer detection on Windows
  - Render-only test PDF generation
- Diagnostics does not send a print job.

## Configuration
Configuration file: config/config.json

- base_url
  - Your Snipe-IT base address.
  - Example: https://snipeit.company.local
- printer_name
  - Exact printer name as shown in Windows Printers.
  - Example: Brother QL-800
- label_path_template
  - Label route format. {id} is replaced with the asset ID.
  - Default: /hardware/{id}/label
- label_width_mm
  - Label page width in millimeters for PDF render.
- label_height_mm
  - Label page height in millimeters for PDF render.

Additional keys in config are for timeout and parsing behavior, and normally do not need frequent changes.

Note: the default configuration and URL parsing are hardware-specific. Consumables, accessories, and other Snipe-IT object types are not supported unless you change the parser and label route to match your instance.

## Troubleshooting
- Printer not found
  - Confirm the exact printer name in Windows and match printer_name in config/config.json.

- Blank label or wrong scale
  - Verify label_width_mm and label_height_mm in config/config.json.
  - Confirm Brother driver media settings match your installed roll.

- Nothing prints
  - Ensure Windows has a PDF handler that supports print command integration.
  - Test printing a normal PDF to the same printer outside the app.

- Playwright error
  - Run playwright install again.
  - Confirm internet access if browser runtime must be downloaded.

## Notes
- Label dimensions in config must match Brother printer media settings.
- Best results come from correctly configured QL-800 roll/media settings.
- Print method uses robust PDF fallback for consistent Windows behavior.
