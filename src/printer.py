import time
from pathlib import Path

import win32api
import win32print


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


def print_pdf_to_printer(pdf_path: str | Path, printer_name: str, timeout_sec: int = 30) -> None:
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        raise PrinterError(f"PDF file does not exist: {pdf_file}")

    ensure_printer_exists(printer_name)

    initial_jobs = _get_printer_job_count(printer_name)

    try:
        # Uses the registered PDF handler and sends directly to the target printer.
        win32api.ShellExecute(
            0,
            "printto",
            str(pdf_file),
            f'"{printer_name}"',
            ".",
            0,
        )
    except Exception as exc:
        raise PrinterError(f"Windows print command failed: {exc}") from exc

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
        raise PrinterError(
            "Print job did not appear in printer queue. Ensure a PDF viewer with print-to support is installed (Edge or Adobe Reader)."
        )

    raise PrinterError("Print job did not complete within timeout")
