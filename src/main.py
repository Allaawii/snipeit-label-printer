import threading
from pathlib import Path
from tkinter import END, Button, Entry, Frame, Label, StringVar, Tk, messagebox
from urllib.parse import urlparse

from browser import (
    BrowserRenderError,
    render_accessory_label_to_pdf,
    render_label_to_pdf,
)
from printer import (
    PrinterError,
    ensure_printer_exists,
    list_printers,
    print_pdf_to_printer,
)
from utils import ConfigError, UrlParseError, build_label_url, detect_item_type, extract_asset_id, load_config


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "config.json"
TEMP_DIR = PROJECT_ROOT / "temp"


class LabelPrinterApp:
    def __init__(self, root: Tk):
        self.root = root
        self.root.title("Snipe-IT Label Printer")
        self.root.geometry("560x220")
        self.root.resizable(False, False)

        self.status_var = StringVar(value="Ready")

        container = Frame(root, padx=12, pady=12)
        container.pack(fill="both", expand=True)

        Label(container, text="Snipe-IT Asset / Accessory URL:").pack(anchor="w")

        self.url_entry = Entry(container, width=72)
        self.url_entry.pack(fill="x", pady=(4, 10))

        controls = Frame(container)
        controls.pack(fill="x")

        self.print_btn = Button(
            controls,
            text="Print Label",
            command=self.on_print_clicked,
            width=16,
        )
        self.print_btn.pack(side="left")

        self.clipboard_btn = Button(
            controls,
            text="Use Clipboard",
            command=self.use_clipboard,
            width=16,
        )
        self.clipboard_btn.pack(side="left", padx=(8, 0))

        self.diagnostics_btn = Button(
            controls,
            text="Run Diagnostics",
            command=self.on_diagnostics_clicked,
            width=16,
        )
        self.diagnostics_btn.pack(side="left", padx=(8, 0))

        self.status_label = Label(
            container,
            textvariable=self.status_var,
            fg="blue",
            wraplength=520,
            justify="left",
            anchor="w",
        )
        self.status_label.pack(fill="x", pady=(16, 0))

    def set_status(self, message: str, is_error: bool = False) -> None:
        self.status_var.set(message)
        self.status_label.config(fg="red" if is_error else "green")

    def use_clipboard(self) -> None:
        try:
            text = self.root.clipboard_get().strip()
            self.url_entry.delete(0, END)
            self.url_entry.insert(0, text)
            self.set_status("Loaded URL from clipboard")
        except Exception:
            self.set_status("Clipboard is empty or unavailable", is_error=True)

    def on_print_clicked(self) -> None:
        url = self.url_entry.get().strip()
        self._set_controls_state("disabled")
        self.set_status("Preparing print job...")

        worker = threading.Thread(target=self._run_print_flow, args=(url,), daemon=True)
        worker.start()

    def on_diagnostics_clicked(self) -> None:
        url = self.url_entry.get().strip()
        self._set_controls_state("disabled")
        self.set_status("Running diagnostics...")

        worker = threading.Thread(target=self._run_diagnostics_flow, args=(url,), daemon=True)
        worker.start()

    def _build_asset_context(self, input_url: str, config: dict) -> tuple[str, str, str]:
        """Return (item_type, item_id, target_url).

        For hardware, target_url is the Snipe-IT label page. For accessories
        (which have no label page), target_url is the accessory page itself,
        used both to read its name and as the QR destination.
        """
        asset_id_regex = config.get("asset_id_regex")
        item_id = extract_asset_id(input_url, asset_id_regex=asset_id_regex)

        configured_base = str(config.get("base_url", "")).strip()
        if not configured_base or "your-snipeit.com" in configured_base:
            parsed_input = urlparse(input_url)
            configured_base = f"{parsed_input.scheme}://{parsed_input.netloc}"

        item_type = detect_item_type(input_url)
        if item_type == "accessories":
            target_url = build_label_url(
                base_url=configured_base,
                asset_id=item_id,
                label_path_template="/accessories/{id}",
            )
        else:
            target_url = build_label_url(
                base_url=configured_base,
                asset_id=item_id,
                label_path_template=config["label_path_template"],
            )
        return item_type, item_id, target_url

    def _render_pdf_for_item(
        self, item_type: str, item_id: str, target_url: str, output_dir: Path, config: dict
    ) -> Path:
        if item_type == "accessories":
            return render_accessory_label_to_pdf(
                accessory_url=target_url,
                accessory_id=item_id,
                output_dir=output_dir,
                config=config,
            )
        return render_label_to_pdf(label_url=target_url, output_dir=output_dir, config=config)

    def _run_print_flow(self, input_url: str) -> None:
        temp_pdf_path: Path | None = None

        try:
            config = load_config(CONFIG_PATH)
            item_type, item_id, target_url = self._build_asset_context(input_url, config)

            printer_name = str(config["printer_name"])
            ensure_printer_exists(printer_name)

            print_method = str(config.get("print_method", "pdf_fallback")).lower()
            if print_method != "pdf_fallback":
                # Browser-level silent printing cannot reliably target a specific Windows printer.
                raise PrinterError(
                    "Unsupported print_method. Use 'pdf_fallback' to print reliably on Windows."
                )

            temp_pdf_path = self._render_pdf_for_item(
                item_type, item_id, target_url, TEMP_DIR, config
            )

            timeout_sec = int(config.get("print_job_timeout_sec", 30))
            print_pdf_to_printer(
                pdf_path=temp_pdf_path,
                printer_name=printer_name,
                timeout_sec=timeout_sec,
            )

            label_kind = "accessory" if item_type == "accessories" else "asset"
            self.root.after(0, lambda: self.set_status(f"Printed {label_kind} {item_id}"))
        except (ConfigError, UrlParseError, BrowserRenderError, PrinterError) as exc:
            error_message = str(exc)
            self.root.after(0, lambda msg=error_message: self.set_status(msg, is_error=True))
        except Exception as exc:
            error_message = f"Unexpected error: {exc}"
            self.root.after(0, lambda msg=error_message: self.set_status(msg, is_error=True))
        finally:
            if temp_pdf_path and temp_pdf_path.exists():
                try:
                    temp_pdf_path.unlink(missing_ok=True)
                except Exception:
                    pass
            self.root.after(0, lambda: self._set_controls_state("normal"))

    def _run_diagnostics_flow(self, input_url: str) -> None:
        try:
            config = load_config(CONFIG_PATH)
            item_type, item_id, target_url = self._build_asset_context(input_url, config)

            printers = list_printers()
            printer_name = str(config["printer_name"])
            printer_ok = printer_name in printers

            diag_dir = TEMP_DIR / "diagnostics"
            test_pdf_path = self._render_pdf_for_item(
                item_type, item_id, target_url, diag_dir, config
            )

            label_kind = "Accessory" if item_type == "accessories" else "Asset"
            report = "\n".join(
                [
                    f"{label_kind} ID: {item_id}",
                    f"Target URL: {target_url}",
                    f"Configured printer: {printer_name}",
                    f"Printer available: {'Yes' if printer_ok else 'No'}",
                    f"Detected printers ({len(printers)}):",
                    ", ".join(printers) if printers else "none",
                    f"Test PDF rendered: {test_pdf_path}",
                ]
            )

            self.root.after(0, lambda: self.set_status("Diagnostics completed"))
            self.root.after(0, lambda: messagebox.showinfo("Diagnostics", report))
        except (ConfigError, UrlParseError, BrowserRenderError, PrinterError) as exc:
            error_message = str(exc)
            self.root.after(0, lambda msg=error_message: self.set_status(msg, is_error=True))
            self.root.after(0, lambda msg=error_message: messagebox.showerror("Diagnostics Error", msg))
        except Exception as exc:
            message = f"Unexpected error: {exc}"
            self.root.after(0, lambda: self.set_status(message, is_error=True))
            self.root.after(0, lambda: messagebox.showerror("Diagnostics Error", message))
        finally:
            self.root.after(0, lambda: self._set_controls_state("normal"))

    def _set_controls_state(self, state: str) -> None:
        self.print_btn.config(state="normal")
        self.clipboard_btn.config(state="normal")
        self.diagnostics_btn.config(state="normal")

        if state != "normal":
            self.print_btn.config(state=state)
            self.clipboard_btn.config(state=state)
            self.diagnostics_btn.config(state=state)


def main() -> None:
    root = Tk()
    app = LabelPrinterApp(root)
    app.url_entry.focus_set()
    root.mainloop()


if __name__ == "__main__":
    main()
