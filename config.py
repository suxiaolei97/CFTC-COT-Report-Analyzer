import json
import os

REPORT_TYPES = {
    "legacy_fut": "Legacy -\u4ec5\u671f\u8d27",
    "legacy_futopt": "Legacy -\u671f\u8d27+\u671f\u6743",
    "supplemental_futopt": "\u8865\u5145\u62a5\u544a -\u671f\u8d27+\u671f\u6743",
    "disaggregated_fut": "\u7ec6\u5206\u7c7b -\u4ec5\u671f\u8d27",
    "disaggregated_futopt": "\u7ec6\u5206\u7c7b -\u671f\u8d27+\u671f\u6743",
    "traders_in_financial_futures_fut": "TFF -\u4ec5\u671f\u8d27",
    "traders_in_financial_futures_futopt": "TFF -\u671f\u8d27+\u671f\u6743",
}

DEFAULT_REPORT_TYPE = "legacy_futopt"
DEFAULT_YEAR = 2026
DEFAULT_START_YEAR = 2020
DEFAULT_LANG = "zh"
DEFAULT_TOP_N = 5

COLORS = {
    "bg": "#0f0f1a",
    "panel_bg": "#16162a",
    "border": "#2a2a5a",
    "header": "#3a3a6a",
    "text": "#c0c0e0",
    "text_dim": "#606080",
    "accent": "#5a8ad4",
    "accent_bright": "#7aafff",
    "green": "#4ee04e",
    "red": "#e05050",
    "yellow": "#e0c040",
    "cyan": "#40c0c0",
    "orange": "#e08040",
}

_CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".cot_tui_config.json")

_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(_PROJECT_ROOT, "data")


def data_path(filename: str) -> str:
    return os.path.join(DATA_DIR, filename)


def ensure_data_dir() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)


def load_app_config() -> dict:
    try:
        if os.path.exists(_CONFIG_PATH):
            with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def save_app_config(data: dict) -> None:
    try:
        with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass
