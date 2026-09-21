from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from backend.index import initialize
from backend.media_policy import media_url_allowed
from backend.settings import DB_PATH


@dataclass(frozen=True)
class ProviderPreviewStats:
    total: int
    stored: int
    playable: int


@dataclass(frozen=True)
class PreviewCoverageStats:
    total: int
    stored: int
    playable: int
    stored_percent: float
    playable_percent: float
    providers: dict[str, ProviderPreviewStats]
    states: dict[str, int]


def preview_coverage_stats(path: Path = DB_PATH) -> PreviewCoverageStats:
    initialize(path)
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT provider, preview_url FROM items WHERE active = 1 ORDER BY provider"
        ).fetchall()
        state_rows = conn.execute(
            "SELECT status, COUNT(*) AS n FROM preview_enrichment_state GROUP BY status ORDER BY status"
        ).fetchall()

    per: dict[str, list[int]] = {}
    stored = 0
    playable = 0
    for row in rows:
        provider = str(row["provider"])
        values = per.setdefault(provider, [0, 0, 0])
        values[0] += 1
        preview = str(row["preview_url"] or "").strip()
        if not preview:
            continue
        stored += 1
        values[1] += 1
        if media_url_allowed(provider, "preview", preview):
            playable += 1
            values[2] += 1

    total = len(rows)
    providers = {
        name: ProviderPreviewStats(total=v[0], stored=v[1], playable=v[2])
        for name, v in sorted(per.items())
    }
    states = {str(row["status"]): int(row["n"]) for row in state_rows}
    return PreviewCoverageStats(
        total=total,
        stored=stored,
        playable=playable,
        stored_percent=round((stored / total * 100.0) if total else 0.0, 2),
        playable_percent=round((playable / total * 100.0) if total else 0.0, 2),
        providers=providers,
        states=states,
    )
