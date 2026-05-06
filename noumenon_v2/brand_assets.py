from __future__ import annotations

import base64
from pathlib import Path


ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"


def load_brand_svg(name: str) -> str:
    path = ASSETS_DIR / name
    return path.read_text(encoding="utf-8")


def load_brand_bytes(name: str) -> bytes:
    path = ASSETS_DIR / name
    return path.read_bytes()


def load_brand_svg_data_uri(name: str) -> str:
    path = ASSETS_DIR / name
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"
