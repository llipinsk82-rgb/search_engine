from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from backend import cli
from backend.ingest import BackfillRun


class PagedProvider:
    name = "paged"
    sync_mode = "incremental"

    async def collect_page(self, *, offset, limit):
        return [], offset


def _report(*, failures=0):
    return SimpleNamespace(
        attempted=2,
        enriched=1,
        classified_amateur=1,
        classified_studio=0,
        conflicts=0,
        no_signal=0,
        failures=failures,
    )


def test_successful_backfill_hands_off_to_enrichment(monkeypatch, capsys) -> None:
    provider = PagedProvider()
    seen = {}

    async def fake_backfill(*args, **kwargs):
        return [BackfillRun("paged", 1, 10, False, None)]

    async def fake_enrich(providers, *, batch_size, max_seconds):
        seen["providers"] = providers
        seen["batch_size"] = batch_size
        seen["max_seconds"] = max_seconds
        return _report()

    monkeypatch.setattr(cli, "PROVIDERS", [provider])
    monkeypatch.setattr(cli, "backfill_many", fake_backfill)
    monkeypatch.setattr(cli, "enrich_unknown_content", fake_enrich)

    asyncio.run(
        cli._backfill_all(
            500,
            1,
            180,
            enrich_unknown_batch_size=25,
            enrich_unknown_seconds=45,
        )
    )

    assert seen == {
        "providers": [provider],
        "batch_size": 25,
        "max_seconds": 45,
    }
    assert "content-enrichment: attempted=2 enriched=1" in capsys.readouterr().out


def test_backfill_error_skips_enrichment_and_preserves_failure(monkeypatch) -> None:
    provider = PagedProvider()
    called = False

    async def fake_backfill(*args, **kwargs):
        return [BackfillRun("paged", 0, 0, False, "boom")]

    async def fake_enrich(*args, **kwargs):
        nonlocal called
        called = True
        return _report()

    monkeypatch.setattr(cli, "PROVIDERS", [provider])
    monkeypatch.setattr(cli, "backfill_many", fake_backfill)
    monkeypatch.setattr(cli, "enrich_unknown_content", fake_enrich)

    with pytest.raises(SystemExit) as exc:
        asyncio.run(
            cli._backfill_all(
                500,
                1,
                180,
                enrich_unknown_batch_size=25,
                enrich_unknown_seconds=45,
            )
        )
    assert exc.value.code == 1
    assert called is False


def test_zero_enrichment_seconds_skips_handoff(monkeypatch) -> None:
    provider = PagedProvider()
    called = False

    async def fake_backfill(*args, **kwargs):
        return [BackfillRun("paged", 1, 10, False, None)]

    async def fake_enrich(*args, **kwargs):
        nonlocal called
        called = True
        return _report()

    monkeypatch.setattr(cli, "PROVIDERS", [provider])
    monkeypatch.setattr(cli, "backfill_many", fake_backfill)
    monkeypatch.setattr(cli, "enrich_unknown_content", fake_enrich)

    asyncio.run(
        cli._backfill_all(
            500,
            1,
            180,
            enrich_unknown_batch_size=25,
            enrich_unknown_seconds=0,
        )
    )
    assert called is False


def test_isolated_enrichment_failures_do_not_fail_maintenance(monkeypatch, capsys) -> None:
    provider = PagedProvider()

    async def fake_backfill(*args, **kwargs):
        return [BackfillRun("paged", 1, 10, True, None)]

    async def fake_enrich(*args, **kwargs):
        return _report(failures=2)

    monkeypatch.setattr(cli, "PROVIDERS", [provider])
    monkeypatch.setattr(cli, "backfill_many", fake_backfill)
    monkeypatch.setattr(cli, "enrich_unknown_content", fake_enrich)

    asyncio.run(
        cli._backfill_all(
            500,
            1,
            180,
            enrich_unknown_batch_size=25,
            enrich_unknown_seconds=45,
        )
    )
    assert "failures=2" in capsys.readouterr().out
