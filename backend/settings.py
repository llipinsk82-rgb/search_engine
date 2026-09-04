from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.environ.get("SEARCH_DB_PATH", "search_engine.db"))


def get_build_id() -> str:
    value = os.environ.get("SEARCH_BUILD_ID", "").strip()
    if value:
        return value
    marker = ROOT / ".build-id"
    try:
        return marker.read_text(encoding="utf-8").strip() or "dev"
    except OSError:
        return "dev"
