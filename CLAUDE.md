# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

A Windows-only Tkinter GUI that prints Snipe-IT hardware asset labels to a Brother QL-800 (or compatible) label printer. The pipeline is:

1. User pastes a Snipe-IT asset URL → asset ID extracted → label page URL constructed
2. Playwright renders the label page headlessly and saves it as a PDF
3. PyMuPDF rasterizes the PDF at 3× DPI for sharp QR codes and small text
4. Pillow/win32 GDI sends the rasterized image directly to the Windows printer

There is no Snipe-IT API usage — it's entirely browser-rendered.

## Setup (Windows)

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
playwright install

copy config\config.example.json config\config.json
# Edit config\config.json for your environment
```

## Running

```powershell
python src\main.py
# or double-click run.bat
```

## Authentication Setup

Required once when Snipe-IT needs login. Creates `auth.json` (gitignored) via interactive browser:

```powershell
python create_auth.py https://your-snipeit-url/login
# or via env var:
$env:SNIPEIT_LOGIN_URL = "https://your-snipeit-url/login"
python create_auth.py
```

Regenerate `auth.json` whenever sessions expire.

## Architecture

| File | Responsibility |
|------|---------------|
| `src/main.py` | Tkinter GUI (`LabelPrinterApp`); orchestrates print and diagnostics flows on daemon threads; all UI updates go through `root.after()` |
| `src/browser.py` | Playwright headless rendering; `render_label_to_pdf()` returns a temp PDF path |
| `src/printer.py` | Win32 printing; `print_pdf_to_printer()` rasterizes PDF → trims whitespace → draws via GDI |
| `src/utils.py` | Config loading, URL parsing, asset ID extraction, label URL building |
| `create_auth.py` | One-time interactive Playwright login to capture session cookies into `auth.json` |

## Key Constraints and Behaviors

- **Windows-only**: depends on `pywin32` (`win32print`, `win32ui`, `win32con`, `ImageWin`)
- **Only `pdf_fallback` print method is supported**: browser-level silent printing cannot reliably target a specific Windows printer
- `base_url` in config: if it contains `"your-snipeit.com"`, the app silently falls back to the origin of the input URL
- `label_path_template` must contain `{id}` placeholder; `asset_id_regex` is optional (defaults to `/hardware/(\d+)`)
- `pre_print_delay_sec` is clamped to `[0.5, 1.0]` to let dynamic content (QR codes) settle before PDF capture
- `pdf_scale` is clamped to `[0.8, 1.5]`
- Temp PDFs are written to `temp/` and deleted after printing; diagnostics saves to `temp/diagnostics/` and keeps them

## Config Keys

Required: `base_url`, `printer_name`, `label_path_template`, `browser`, `print_method`

Notable optional keys: `auth_mode` (`none` or `storage_state`), `storage_state_path` (default `auth.json`), `label_width_mm` (default `102.0`), `label_height_mm` (default `35.0`), `pre_print_delay_sec`, `pdf_scale`, `page_load_timeout_ms`, `print_job_timeout_sec`, `asset_id_regex`

## Gitignored Files

`auth.json` and `config/config.json` are gitignored — never commit them.
