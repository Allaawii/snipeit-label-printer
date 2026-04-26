import json
import re
from pathlib import Path
from typing import Any, Dict
from urllib.parse import urlparse


class ConfigError(Exception):
    pass


class UrlParseError(Exception):
    pass


def load_config(config_path: str | Path = Path("config") / "config.json") -> Dict[str, Any]:
    path = Path(config_path)
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid JSON in config file: {exc}") from exc

    required = [
        "base_url",
        "printer_name",
        "label_path_template",
        "browser",
        "print_method",
    ]
    missing = [key for key in required if key not in data]
    if missing:
        raise ConfigError(f"Missing config keys: {', '.join(missing)}")

    return data


def normalize_base_url(base_url: str) -> str:
    base = base_url.strip().rstrip("/")
    parsed = urlparse(base)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise UrlParseError("base_url in config must be a valid http(s) URL")
    return base


def extract_asset_id(asset_url: str, asset_id_regex: str | None = None) -> str:
    if not asset_url or not asset_url.strip():
        raise UrlParseError("Asset URL is empty")

    url = asset_url.strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise UrlParseError("Invalid URL format. Expected http(s)://...")

    regex_pattern = asset_id_regex or r"/hardware/(\d+)(?:/|$)"
    match = re.search(regex_pattern, parsed.path)
    if not match:
        raise UrlParseError(
            "Cannot extract asset ID from URL. Expected path like /hardware/123"
        )

    asset_id = match.group(1)
    if not asset_id.isdigit():
        raise UrlParseError("Extracted asset ID is not numeric")

    return asset_id


def build_label_url(base_url: str, asset_id: str, label_path_template: str) -> str:
    normalized_base = normalize_base_url(base_url)

    template = label_path_template.strip()
    if "{id}" not in template:
        raise UrlParseError("label_path_template must include '{id}' placeholder")

    if not template.startswith("/"):
        template = "/" + template

    label_path = template.format(id=asset_id)
    return f"{normalized_base}{label_path}"
