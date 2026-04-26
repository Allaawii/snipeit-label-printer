import time
import uuid
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


class BrowserRenderError(Exception):
    pass


def render_label_to_pdf(label_url: str, output_dir: Path, config: dict) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = output_dir / f"snipeit_label_{uuid.uuid4().hex}.pdf"

    browser_name = str(config.get("browser", "chromium")).lower()
    timeout_ms = int(config.get("page_load_timeout_ms", 30000))
    pre_print_delay_sec = float(config.get("pre_print_delay_sec", 0.5))

    # Default to a common Brother DK label size if not explicitly configured.
    label_width_mm = float(config.get("label_width_mm", 62.0))
    label_height_mm = float(config.get("label_height_mm", 29.0))

    if browser_name not in {"chromium", "firefox", "webkit"}:
        raise BrowserRenderError(
            f"Unsupported browser '{browser_name}'. Use chromium, firefox, or webkit."
        )

    try:
        with sync_playwright() as p:
            browser_factory = getattr(p, browser_name)
            browser = browser_factory.launch(headless=True)
            try:
                context = browser.new_context()
                page = context.new_page()
                page.goto(label_url, wait_until="networkidle", timeout=timeout_ms)
                page.emulate_media(media="print")
                page.wait_for_timeout(int(pre_print_delay_sec * 1000))

                page.pdf(
                    path=str(pdf_path),
                    print_background=True,
                    margin={"top": "0mm", "right": "0mm", "bottom": "0mm", "left": "0mm"},
                    width=f"{label_width_mm}mm",
                    height=f"{label_height_mm}mm",
                    scale=1.0,
                    prefer_css_page_size=True,
                    page_ranges="1",
                )
            finally:
                browser.close()
    except PlaywrightTimeoutError as exc:
        raise BrowserRenderError(
            f"Page load timeout while opening label URL: {label_url}"
        ) from exc
    except Exception as exc:
        raise BrowserRenderError(f"Failed to render label PDF: {exc}") from exc

    if not pdf_path.exists() or pdf_path.stat().st_size == 0:
        raise BrowserRenderError("Generated PDF is missing or empty")

    return pdf_path
