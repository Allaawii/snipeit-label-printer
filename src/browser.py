import uuid
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from accessory_label import build_accessory_label_html


class BrowserRenderError(Exception):
    pass


# Snipe-IT's configured label logo. Overridable via the `label_logo_url` config
# key (absolute URL, or a path relative to the site origin).
DEFAULT_LABEL_LOGO_PATH = "/uploads/setting-label_logo-1-UFHdqqwtvy.png"


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


def _validate_render_config(config: dict) -> tuple[str, dict]:
    """Return (browser_name, context_kwargs) and validate shared render config."""
    browser_name = str(config.get("browser", "chromium")).lower()
    auth_mode = str(config.get("auth_mode", "none")).strip().lower()
    storage_state_path = str(config.get("storage_state_path", "auth.json")).strip()

    if browser_name not in {"chromium", "firefox", "webkit"}:
        raise BrowserRenderError(
            f"Unsupported browser '{browser_name}'. Use chromium, firefox, or webkit."
        )

    if auth_mode not in {"none", "storage_state"}:
        raise BrowserRenderError(
            f"Unsupported auth_mode '{auth_mode}'. Use 'none' or 'storage_state'."
        )

    context_kwargs: dict = {}
    if auth_mode == "storage_state":
        resolved_state_path = _resolve_storage_state_path(storage_state_path)
        if not resolved_state_path.exists():
            raise BrowserRenderError(
                f"storage_state file not found: {resolved_state_path}. Generate it first."
            )
        context_kwargs["storage_state"] = str(resolved_state_path)

    return browser_name, context_kwargs


def _capture_pdf(page, pdf_path: Path, config: dict) -> None:
    """Render the current page to a PDF using the shared label-print settings."""
    pre_print_delay_sec = float(config.get("pre_print_delay_sec", 0.8))
    pre_print_delay_sec = max(0.5, min(1.0, pre_print_delay_sec))
    pdf_scale = float(config.get("pdf_scale", 1.12))
    pdf_scale = max(0.8, min(1.5, pdf_scale))

    # Default to a common Brother DK label size if not explicitly configured.
    label_width_mm = float(config.get("label_width_mm", 102.0))
    label_height_mm = float(config.get("label_height_mm", 35.0))

    page.emulate_media(media="print")
    # Allow dynamic label elements (such as QR codes) to settle before capture.
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


def render_label_to_pdf(label_url: str, output_dir: Path, config: dict) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = output_dir / f"snipeit_label_{uuid.uuid4().hex}.pdf"

    browser_name, context_kwargs = _validate_render_config(config)
    timeout_ms = int(config.get("page_load_timeout_ms", 30000))

    try:
        with sync_playwright() as p:
            browser_factory = getattr(p, browser_name)
            browser = browser_factory.launch(headless=True)
            try:
                context = browser.new_context(**context_kwargs)
                page = context.new_page()
                page.goto(label_url, wait_until="networkidle", timeout=timeout_ms)
                _ensure_not_login_page(page)
                _capture_pdf(page, pdf_path, config)
            finally:
                browser.close()
    except PlaywrightTimeoutError as exc:
        raise BrowserRenderError(
            f"Page load timeout while opening label URL: {label_url}"
        ) from exc
    except BrowserRenderError:
        raise
    except Exception as exc:
        raise BrowserRenderError(f"Failed to render label PDF: {exc}") from exc

    if not pdf_path.exists() or pdf_path.stat().st_size == 0:
        raise BrowserRenderError("Generated PDF is missing or empty")

    return pdf_path


def _accessory_name_from_title(title: str) -> str:
    # Snipe-IT title format: "<name> Accessory :: <site name>"
    name = title.split("::", 1)[0].strip()
    if name.endswith("Accessory"):
        name = name[: -len("Accessory")].strip()
    return name


def _resolve_logo_url(accessory_url: str, config: dict) -> str:
    configured = str(config.get("label_logo_url", "")).strip()
    parsed = urlparse(accessory_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    if not configured:
        return f"{origin}{DEFAULT_LABEL_LOGO_PATH}"
    if configured.lower().startswith(("http://", "https://")):
        return configured
    if not configured.startswith("/"):
        configured = "/" + configured
    return f"{origin}{configured}"


def render_accessory_label_to_pdf(
    accessory_url: str,
    accessory_id: str,
    output_dir: Path,
    config: dict,
) -> Path:
    """Render a self-built accessory label (matching the hardware label) to PDF.

    Snipe-IT has no accessory label page, so we fetch the accessory name from its
    page, generate our own QR (linking to the accessory) and a cosmetic barcode,
    reuse the IE logo, and print through the same pipeline as hardware labels.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = output_dir / f"snipeit_label_{uuid.uuid4().hex}.pdf"

    browser_name, context_kwargs = _validate_render_config(config)
    timeout_ms = int(config.get("page_load_timeout_ms", 30000))
    logo_url = _resolve_logo_url(accessory_url, config)

    try:
        with sync_playwright() as p:
            browser_factory = getattr(p, browser_name)
            browser = browser_factory.launch(headless=True)
            try:
                context = browser.new_context(**context_kwargs)
                page = context.new_page()
                page.goto(accessory_url, wait_until="networkidle", timeout=timeout_ms)
                _ensure_not_login_page(page)

                accessory_name = _accessory_name_from_title(page.title())

                # Fetch the label logo with the authenticated session; embed it
                # so the label is self-contained. Omit gracefully if unavailable.
                logo_data_uri: str | None = None
                try:
                    resp = context.request.get(logo_url)
                    if resp.ok:
                        import base64

                        body = resp.body()
                        content_type = resp.headers.get("content-type", "image/png")
                        encoded = base64.b64encode(body).decode("ascii")
                        logo_data_uri = f"data:{content_type};base64,{encoded}"
                except Exception:
                    logo_data_uri = None

                html = build_accessory_label_html(
                    accessory_id=accessory_id,
                    accessory_name=accessory_name,
                    accessory_url=accessory_url,
                    logo_data_uri=logo_data_uri,
                )
                page.set_content(html, wait_until="networkidle", timeout=timeout_ms)
                _capture_pdf(page, pdf_path, config)
            finally:
                browser.close()
    except PlaywrightTimeoutError as exc:
        raise BrowserRenderError(
            f"Page load timeout while opening accessory URL: {accessory_url}"
        ) from exc
    except BrowserRenderError:
        raise
    except Exception as exc:
        raise BrowserRenderError(f"Failed to render accessory label PDF: {exc}") from exc

    if not pdf_path.exists() or pdf_path.stat().st_size == 0:
        raise BrowserRenderError("Generated PDF is missing or empty")

    return pdf_path
