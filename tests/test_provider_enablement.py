from backend.live import LIVE_ADAPTERS
from backend.source_policy import is_searchable_provider


def test_reaudited_live_providers_are_enabled():
    names={adapter.name for adapter in LIVE_ADAPTERS}
    for name in ("spankbang", "thumbzilla"):
        assert name in names
        assert is_searchable_provider(name)


def test_sunporno_is_searchable_index_provider_not_live_adapter():
    names={adapter.name for adapter in LIVE_ADAPTERS}
    assert "sunporno" not in names
    assert is_searchable_provider("sunporno")


def test_pending_candidates_remain_disabled():
    for name in ("tube8", "xhamster"):
        assert not is_searchable_provider(name)
