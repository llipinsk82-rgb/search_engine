from __future__ import annotations

import sys

from backend import cli


def test_reclassify_content_defaults_to_dry_run(monkeypatch, capsys) -> None:
    seen = {}

    class Report:
        scanned = 3
        changed = 2
        conflicts = 1
        before = {"amateur": 0, "studio": 0, "unknown": 3}
        after = {"amateur": 1, "studio": 1, "unknown": 1}
        sources = {"tag_amateur": 1, "tag_studio": 1, "conflict": 1}
        next_after_id = None
        complete = True

    def fake(**kwargs):
        seen.update(kwargs)
        return Report()

    monkeypatch.setattr(cli, "reclassify_content", fake)
    monkeypatch.setattr(sys, "argv", ["search-engine", "reclassify-content"])
    cli.main()

    assert seen["apply"] is False
    assert seen["batch_size"] == 5000
    assert seen["after_id"] is None
    assert seen["max_rows"] is None
    out = capsys.readouterr().out
    assert "scanned=3" in out
    assert "changed=2" in out
    assert "conflicts=1" in out
    assert "complete=true" in out


def test_reclassify_content_apply_is_explicit(monkeypatch) -> None:
    seen = {}

    class Report:
        scanned = 0
        changed = 0
        conflicts = 0
        before = {}
        after = {}
        sources = {}
        next_after_id = "abc"
        complete = False

    def fake(**kwargs):
        seen.update(kwargs)
        return Report()

    monkeypatch.setattr(cli, "reclassify_content", fake)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "search-engine",
            "reclassify-content",
            "--apply",
            "--batch-size",
            "25",
            "--after-id",
            "abc",
            "--max-rows",
            "100",
        ],
    )
    cli.main()

    assert seen == {
        "apply": True,
        "batch_size": 25,
        "after_id": "abc",
        "max_rows": 100,
    }


def test_content_class_stats_command(monkeypatch, capsys) -> None:
    class Stats:
        total = 9
        class_counts = {"amateur": 2, "studio": 3, "unknown": 4}
        percentages = {"amateur": 22.2, "studio": 33.3, "unknown": 44.4}
        source_counts = {"none": 4}
        conflicts = 0
        providers = {"demo": {"total": 9, "amateur": 2, "studio": 3, "unknown": 4, "none_source": 4}}

    monkeypatch.setattr(cli, "content_class_stats", lambda: Stats())
    monkeypatch.setattr(sys, "argv", ["search-engine", "content-class-stats"])
    cli.main()

    out = capsys.readouterr().out
    assert "total=9" in out
    assert "unknown=4" in out
    assert "demo" in out
