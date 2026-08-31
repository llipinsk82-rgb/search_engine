from __future__ import annotations

import os
from pathlib import Path

DB_PATH = Path(os.environ.get("SEARCH_DB_PATH", "search_engine.db"))
