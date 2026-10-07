from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from backend import cli


@pytest.fixture(autouse=True)
def _avoid_default_db(monkeypatch) -> None:
    monkeypatch.setattr(cli, "deactivate_provider", lambda name: 0)


def _provider(name: str = "xgroovy"):
    return SimpleNamespace(name=name)


def _result(name: str = "xgroovy"):
    return SimpleNamespace(
        provider=name,
        fetched=100,
        active_before=1000,
        active_after=1000,
        deactivated=0,
    )


def test_sync_all_retries_one_transient_timeout_then_succeeds(monkeypatch, capsys) -> None:
    provider = _provider()
    sync = AsyncMock(side_effect=[TimeoutError("The read operation timed out"), _result()])
    sleep = AsyncMock()
    monkeypatch.setattr(cli, "PROVIDERS", [provider])
    monkeypatch.setattr(cli, "sync_provider", sync)
    monkeypatch.setattr(cli.asyncio, "sleep", sleep)

    asyncio.run(cli._sync_all(100, False))

    assert sync.await_count == 2
    sleep.assert_awaited_once()
    out = capsys.readouterr().out
    assert "xgroovy: RETRY transient timeout" in out
    assert "xgroovy: fetched=100" in out
    assert "xgroovy: ERROR" not in out


def test_sync_all_persistent_timeout_retries_once_then_fails(monkeypatch, capsys) -> None:
    provider = _provider()
    sync = AsyncMock(side_effect=[TimeoutError("timed out"), TimeoutError("timed out again")])
    monkeypatch.setattr(cli, "PROVIDERS", [provider])
    monkeypatch.setattr(cli, "sync_provider", sync)
    monkeypatch.setattr(cli.asyncio, "sleep", AsyncMock())

    with pytest.raises(SystemExit) as exc:
        asyncio.run(cli._sync_all(100, False))

    assert exc.value.code == 1
    assert sync.await_count == 2
    out = capsys.readouterr().out
    assert "xgroovy: RETRY transient timeout" in out
    assert "xgroovy: ERROR timed out again" in out


def test_sync_all_non_timeout_failure_is_not_retried(monkeypatch, capsys) -> None:
    provider = _provider()
    sync = AsyncMock(side_effect=ValueError("bad provider data"))
    monkeypatch.setattr(cli, "PROVIDERS", [provider])
    monkeypatch.setattr(cli, "sync_provider", sync)

    with pytest.raises(SystemExit) as exc:
        asyncio.run(cli._sync_all(100, False))

    assert exc.value.code == 1
    assert sync.await_count == 1
    out = capsys.readouterr().out
    assert "RETRY" not in out
    assert "xgroovy: ERROR bad provider data" in out
