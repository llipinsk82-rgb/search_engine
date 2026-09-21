from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import patch

from backend.app import app


def test_app_lifespan_initializes_index_once() -> None:
    async def run() -> None:
        with patch("backend.app.initialize") as initialize:
            async with app.router.lifespan_context(app):
                initialize.assert_called_once_with()

    asyncio.run(run())


def test_app_source_does_not_use_deprecated_on_event() -> None:
    source = (Path(__file__).resolve().parents[1] / "backend" / "app.py").read_text(encoding="utf-8")
    assert '@app.on_event("startup")' not in source
