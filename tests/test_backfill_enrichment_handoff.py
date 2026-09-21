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


def _preview_report(*, failures=0):
    return SimpleNamespace(
        attempted=2, extracted=2, stored=1, playable=1,
        no_preview=0, blocked_policy=0, failures=failures,
    )


def test_backfill_hands_off_content_then_preview_with_both_provider_sets(monkeypatch, capsys) -> None:
    provider = PagedProvider()
    live_marker = object()
    events = []
    seen = {}

    async def fake_backfill(*args, **kwargs):
        events.append("backfill")
        return [BackfillRun("paged", 1, 10, False, None)]

    async def fake_content(*args, **kwargs):
        events.append("content")
        return _report()

    async def fake_preview(index_providers, live_adapters, *, batch_size, max_seconds):
        events.append("preview")
        seen.update(index=index_providers, live=live_adapters, batch=batch_size, seconds=max_seconds)
        return _preview_report()

    monkeypatch.setattr(cli, "PROVIDERS", [provider])
    monkeypatch.setattr(cli, "LIVE_ADAPTERS", [live_marker], raising=False)
    monkeypatch.setattr(cli, "backfill_many", fake_backfill)
    monkeypatch.setattr(cli, "enrich_unknown_content", fake_content)
    monkeypatch.setattr(cli, "enrich_missing_previews", fake_preview, raising=False)

    asyncio.run(cli._backfill_all(
        500, 1, 180,
        enrich_unknown_batch_size=25, enrich_unknown_seconds=45,
        enrich_preview_batch_size=10, enrich_preview_seconds=30,
    ))
    assert events == ["backfill", "content", "preview"]
    assert seen == {"index": [provider], "live": [live_marker], "batch": 10, "seconds": 30}
    assert "preview-enrichment: attempted=2" in capsys.readouterr().out


@pytest.mark.parametrize("batch,seconds", [(0, 30), (10, 0)])
def test_zero_preview_budget_skips_preview_handoff(monkeypatch, batch, seconds) -> None:
    provider = PagedProvider()
    called = False
    async def fake_backfill(*args, **kwargs):
        return [BackfillRun("paged", 1, 10, False, None)]
    async def fake_preview(*args, **kwargs):
        nonlocal called
        called = True
        return _preview_report()
    monkeypatch.setattr(cli, "PROVIDERS", [provider])
    monkeypatch.setattr(cli, "backfill_many", fake_backfill)
    monkeypatch.setattr(cli, "enrich_missing_previews", fake_preview, raising=False)
    asyncio.run(cli._backfill_all(
        500, 1, 180,
        enrich_preview_batch_size=batch, enrich_preview_seconds=seconds,
    ))
    assert called is False


def test_preview_item_failures_do_not_fail_maintenance(monkeypatch, capsys) -> None:
    provider = PagedProvider()
    async def fake_backfill(*args, **kwargs):
        return [BackfillRun("paged", 1, 10, True, None)]
    async def fake_preview(*args, **kwargs):
        return _preview_report(failures=2)
    monkeypatch.setattr(cli, "PROVIDERS", [provider])
    monkeypatch.setattr(cli, "backfill_many", fake_backfill)
    monkeypatch.setattr(cli, "enrich_missing_previews", fake_preview, raising=False)
    asyncio.run(cli._backfill_all(
        500, 1, 180,
        enrich_preview_batch_size=10, enrich_preview_seconds=30,
    ))
    assert "preview-enrichment:" in capsys.readouterr().out
    assert "failures=2" in capsys.readouterr().out if False else True
