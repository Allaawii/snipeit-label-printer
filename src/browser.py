import time
import uuid
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


class BrowserRenderError(Exception):
    pass


def _resolve_storage_state_path(raw_path: str) -> Path:
    path = Path(raw_path).expanduser()
    if path.is_absolute():
        return path
    return (Path(__file__).resolve().parent.parent / path).resolve()


def _ensure_not_login_page(page) -> None:
    current_url = page.url.lower()
    if "/login" in current_url or "signin" in current_url:
        raise BrowserRenderError(
            "Authentication required. Your session (auth.json) is missing or expired."
        )

    if page.locator("input[type='password']").count() > 0:
        raise BrowserRenderError(
            "Authentication required. Your session (auth.json) is missing or expired."
        )

    if page.locator("form[action*='login']").count() > 0:
        raise BrowserRenderError(
            "Authentication required. Your session (auth.json) is missing or expired."
        )


def render_label_to_pdf(label_url: str, output_dir: Path, config: dict) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = output_dir / f"snipeit_label_{uuid.uuid4().hex}.pdf"

    browser_name = str(config.get("browser", "chromium")).lower()
    auth_mode = str(config.get("auth_mode", "none")).strip().lower()
    storage_state_path = str(config.get("storage_state_path", "auth.json")).strip()
    timeout_ms = int(config.get("page_load_timeout_ms", 30000))
    pre_print_delay_sec = float(config.get("pre_print_delay_sec", 0.8))
    pre_print_delay_sec = max(0.5, min(1.0, pre_print_delay_sec))
    pdf_scale = float(config.get("pdf_scale", 1.12))
    pdf_scale = max(0.8, min(1.5, pdf_scale))

    # Default to a common Brother DK label size if not explicitly configured.
    label_width_mm = float(config.get("label_width_mm", 102.0))
    label_height_mm = float(config.get("label_height_mm", 35.0))

    if browser_name not in {"chromium", "firefox", "webkit"}:
        raise BrowserRenderError(
            f"Unsupported browser '{browser_name}'. Use chromium, firefox, or webkit."
        )

    if auth_mode not in {"none", "storage_state"}:
        raise BrowserRenderError(
            f"Unsupported auth_mode '{auth_mode}'. Use 'none' or 'storage_state'."
        )

    context_kwargs = {}
    if auth_mode == "storage_state":
        resolved_state_path = _resolve_storage_state_path(storage_state_path)
        if not resolved_state_path.exists():
            raise BrowserRenderError(
                f"storage_state file not found: {resolved_state_path}. Generate it first."
            )
        context_kwargs["storage_state"] = str(resolved_state_path)

    try:
        with sync_playwright() as p:
            browser_factory = getattr(p, browser_name)
            browser = browser_factory.launch(headless=True)
            try:
                context = browser.new_context(**context_kwargs)
                page = context.new_page()
                page.goto(label_url, wait_until="networkidle", timeout=timeout_ms)
                _ensure_not_login_page(page)
                page.emulate_media(media="print")
                # Allow dynamic label elements (such as QR codes) to settle before PDF capture.
                page.wait_for_timeout(int(pre_print_delay_sec * 1000))

                page.pdf(
                    path=str(pdf_path),
                    print_background=True,
                    margin={"top": "0mm", "right": "0mm", "bottom": "0mm", "left": "0mm"},
                    width=f"{label_width_mm}mm",
                    height=f"{label_height_mm}mm",
                    scale=pdf_scale,
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
