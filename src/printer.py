import time
from pathlib import Path

import fitz
from PIL import Image, ImageWin
import win32con
import win32print
import win32ui


class PrinterError(Exception):
    pass


def list_printers() -> list[str]:
    flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
    printers = win32print.EnumPrinters(flags)
    return [printer[2] for printer in printers]


def ensure_printer_exists(printer_name: str) -> None:
    printers = list_printers()
    if printer_name not in printers:
        raise PrinterError(
            f"Printer '{printer_name}' not found. Available printers: {', '.join(printers) or 'none'}"
        )


def _get_printer_job_count(printer_name: str) -> int:
    handle = win32print.OpenPrinter(printer_name)
    try:
        jobs = win32print.EnumJobs(handle, 0, 999, 1)
        return len(jobs)
    finally:
        win32print.ClosePrinter(handle)


def _load_pdf_first_page(pdf_file: Path) -> Image.Image:
    try:
        document = fitz.open(str(pdf_file))
    except Exception as exc:
        raise PrinterError(f"Failed to open PDF for printing: {exc}") from exc

    try:
        if document.page_count < 1:
            raise PrinterError("PDF contains no pages")

        page = document.load_page(0)
        # Render at higher DPI so QR codes and small text stay sharp on labels.
        pixmap = page.get_pixmap(matrix=fitz.Matrix(3, 3), alpha=False)
        return Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
    except PrinterError:
        raise
    except Exception as exc:
        raise PrinterError(f"Failed to rasterize PDF for printing: {exc}") from exc
    finally:
        document.close()


def _trim_whitespace(image: Image.Image, threshold: int = 245, padding: int = 12) -> Image.Image:
    grayscale = image.convert("L")
    content_mask = grayscale.point(lambda pixel: 255 if pixel < threshold else 0)
    bbox = content_mask.getbbox()

    if bbox is None:
        return image

    left = max(0, bbox[0] - padding)
    top = max(0, bbox[1] - padding)
    right = min(image.width, bbox[2] + padding)
    bottom = min(image.height, bbox[3] + padding)

    if right <= left or bottom <= top:
        return image

    return image.crop((left, top, right, bottom))


def _print_image_to_printer(image: Image.Image, printer_name: str) -> None:
    image = _trim_whitespace(image.convert("RGB"))

    dc = win32ui.CreateDC()
    try:
        dc.CreatePrinterDC(printer_name)

        printable_width = dc.GetDeviceCaps(win32con.HORZRES)
        printable_height = dc.GetDeviceCaps(win32con.VERTRES)

        if printable_width <= 0 or printable_height <= 0:
            raise PrinterError("Printer returned invalid printable dimensions")

        # Preserve aspect ratio and center the label while fitting it to the sticker.
        scale = min(printable_width / image.width, printable_height / image.height)
        draw_width = max(1, int(image.width * scale))
        draw_height = max(1, int(image.height * scale))
        left = max(0, (printable_width - draw_width) // 2)
        top = max(0, (printable_height - draw_height) // 2)
        right = left + draw_width
        bottom = top + draw_height

        image = image.resize((draw_width, draw_height), Image.LANCZOS)

        dc.StartDoc(f"Snipe-IT Label - {printer_name}")
        dc.StartPage()
        try:
            dib = ImageWin.Dib(image)
            dib.draw(dc.GetHandleOutput(), (left, top, right, bottom))
        finally:
            dc.EndPage()
            dc.EndDoc()
    except Exception as exc:
        raise PrinterError(f"Direct printer rendering failed: {exc}") from exc
    finally:
        try:
            dc.DeleteDC()
        except Exception:
            pass


def print_pdf_to_printer(pdf_path: str | Path, printer_name: str, timeout_sec: int = 30) -> None:
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        raise PrinterError(f"PDF file does not exist: {pdf_file}")

    ensure_printer_exists(printer_name)

    initial_jobs = _get_printer_job_count(printer_name)

    image = _load_pdf_first_page(pdf_file)
    _print_image_to_printer(image, printer_name)

    deadline = time.time() + timeout_sec
    saw_job = False

    while time.time() < deadline:
        current_jobs = _get_printer_job_count(printer_name)

        if current_jobs > initial_jobs:
            saw_job = True

        # Job appeared and queue returned to initial level, so spooling likely completed.
        if saw_job and current_jobs <= initial_jobs:
            return

        time.sleep(0.5)

    if not saw_job:
        raise PrinterError("Print job failed to reach printer. Check printer name and PDF handler.")

    raise PrinterError("Print job did not complete within timeout")
