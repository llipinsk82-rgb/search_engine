from __future__ import annotations

import importlib

from backend.media_policy import media_url_allowed
from backend.models import SearchItem


def derive(provider: str, row: SearchItem) -> str | None:
    module = importlib.import_module("backend.preview_rules")
    fn = getattr(module, "derive_custom_preview", None)
    assert callable(fn), "derive_custom_preview must exist"
    return fn(provider, row)


def item(provider: str, *, url: str, thumbnail: str) -> SearchItem:
    return SearchItem(id=f"{provider}-1", provider=provider, title="Sample", url=url, thumbnail=thumbnail, tags=[])


def test_item_bound_custom_preview_derivation_for_promoted_providers() -> None:
    rows = [
        ("xvideos", item("xvideos", url="https://www.xvideos.com/video.abc/sample", thumbnail="https://thumb-cdn77.xvideos-cdn.com/u/0/xv_4_t.jpg"), "https://thumb-cdn77.xvideos-cdn.com/u/0/preview.mp4"),
        ("xnxx", item("xnxx", url="https://www.xnxx.com/video-a/sample", thumbnail="https://thumb-cdn77.xnxx-cdn.com/u/0/xn_4_t.jpg"), "https://thumb-cdn77.xnxx-cdn.com/u/0/preview.mp4"),
        ("mypornhere", item("mypornhere", url="https://www.mypornhere.com/videos/153917/sample/", thumbnail="https://www.mypornhere.com/contents/videos_screenshots/153000/153917/preview.jpg"), "https://www.mypornhere.com/contents/videos/153000/153917/153917_preview.mp4"),
        ("pussyspace", item("pussyspace", url="https://www.pussyspace.com/vid-1-sample/", thumbnail="https://thumbs-gcore.xvideos-cdn.com/u/3/xv_30_p.avif"), "https://thumbs-gcore.xvideos-cdn.com/u/3/preview.mp4"),
        ("porndig", item("porndig", url="https://www.porndig.com/videos/123704/sample.html", thumbnail="https://image-cdn.porndig.com/thumbs/2018/11/285922/400x225/clips/13.jpg"), "https://image-cdn.porndig.com/previewclips/2018/11/285922/285922_1.mp4"),
        ("sexvid", item("sexvid", url="https://www.sexvid.xxx/sample.html", thumbnail="https://cdn1.sexvid.xxx/contents/videos_screenshots/119000/119680/preview.jpg"), "https://pr1.sexvid.xxx/contents/videos/119000/119680/119680_short_preview.mp4"),
        ("pornid", item("pornid", url="https://www.pornid.xxx/sample.html", thumbnail="https://cdn.pornid.xxx/contents/videos_screenshots/84000/84633/preview.jpg"), "https://pr1.pornid.xxx/contents/videos/84000/84633/84633_short_preview_480x270.mp4"),
        ("zbporn", item("zbporn", url="https://zbporn.com/videos/665433/sample/", thumbnail="https://cdnth.zbporn.com/contents/videos_screenshots/665000/665433/preview.mp4.jpg"), "https://pr1.zbporn.com/contents/videos/665000/665433/665433_short_preview.mp4"),
    ]
    for provider, row, expected in rows:
        assert derive(provider, row) == expected


def test_pussyspace_only_derives_from_xvideos_cdn_thumbnail() -> None:
    row = item("pussyspace", url="https://www.pussyspace.com/vid-6089074-sample/", thumbnail="https://cdne-pics.youjizz.com/e/5/1/5/9/sample.jpg")
    assert derive("pussyspace", row) is None


def test_promoted_preview_media_hosts_are_strictly_allowlisted() -> None:
    allowed = {
        "xvideos": "https://thumb-cdn77.xvideos-cdn.com/u/0/preview.mp4",
        "xnxx": "https://thumb-cdn77.xnxx-cdn.com/u/0/preview.mp4",
        "mypornhere": "https://www.mypornhere.com/contents/videos/1/1/1_preview.mp4",
        "pussyspace": "https://thumbs-gcore.xvideos-cdn.com/u/3/preview.mp4",
        "porndig": "https://image-cdn.porndig.com/previewclips/2018/11/1/1_1.mp4",
        "sexvid": "https://pr1.sexvid.xxx/contents/videos/1/1/1_short_preview.mp4",
        "pornid": "https://pr1.pornid.xxx/contents/videos/1/1/1_short_preview_480x270.mp4",
        "zbporn": "https://pr1.zbporn.com/contents/videos/1/1/1_short_preview.mp4",
    }
    for provider, url in allowed.items():
        assert media_url_allowed(provider, "preview", url)
        assert not media_url_allowed(provider, "preview", "https://evil.example/preview.mp4")

import asyncio


def test_custom_sitemap_preview_is_derived_without_fetching_page(monkeypatch) -> None:
    import backend.providers.sitemap as sitemap_module
    from backend.preview_rules import PreviewRule
    from backend.providers.sitemap import SitemapProvider

    rule = PreviewRule(
        provider="xvideos",
        kind="custom",
        preview_host_suffixes=(".xvideos-cdn.com",),
    )
    provider = SitemapProvider(
        name="xvideos",
        sitemap_url="https://www.xvideos.com/sitemap.xml",
        obey_robots=False,
    )
    row = item(
        "xvideos",
        url="https://www.xvideos.com/video.abc/sample",
        thumbnail="https://thumb-cdn77.xvideos-cdn.com/u/0/xv_4_t.jpg",
    )
    monkeypatch.setattr(sitemap_module, "PREVIEW_RULES", {"xvideos": rule})
    monkeypatch.setattr(sitemap_module, "media_url_allowed", lambda *args: True)
    monkeypatch.setattr(provider, "_fetch_text", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not fetch")))

    assert provider.preview_resolution is True
    assert asyncio.run(provider.extract_preview(row)) == "https://thumb-cdn77.xvideos-cdn.com/u/0/preview.mp4"


def test_promoted_providers_are_registered_as_stable_custom_rules() -> None:
    rules = importlib.import_module("backend.preview_rules").PREVIEW_RULES
    expected = {"xvideos", "xnxx", "mypornhere", "pussyspace", "porndig", "sexvid", "pornid", "zbporn"}
    assert expected <= set(rules)
    for name in expected:
        assert rules[name].kind == "custom"
        assert rules[name].storage_mode == "stable"


def test_custom_manifest_fixtures_match_derivation() -> None:
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "tests/fixtures/preview_audit_manifest.json").read_text())
    custom = [row for row in manifest if row.get("status") == "PLAYBACK_CONFIRMED" and row.get("rule_kind") == "custom"]
    assert {row["provider"] for row in custom} == {"xvideos", "xnxx", "mypornhere", "pussyspace", "porndig", "sexvid", "pornid", "zbporn"}
    for row in custom:
        positive = json.loads((root / row["fixture"]).read_text())
        negative = json.loads((root / row["negative_fixture"]).read_text())
        pitem = SearchItem(id=f'{row["provider"]}-positive', tags=[], **positive["item"])
        nitem = SearchItem(id=f'{row["provider"]}-negative', tags=[], **negative["item"])
        assert derive(row["provider"], pitem) == positive["expected_preview"]
        assert derive(row["provider"], nitem) is None


def test_preview_endpoint_resolves_custom_rule_without_upstream_fetch(monkeypatch) -> None:
    import asyncio
    import backend.app as app_module
    from backend.providers.sitemap import SitemapProvider

    provider = SitemapProvider(
        name="xvideos",
        sitemap_url="https://www.xvideos.com/sitemap.xml",
        obey_robots=False,
    )
    row = item(
        "xvideos",
        url="https://www.xvideos.com/video.abc/sample",
        thumbnail="https://thumb-cdn77.xvideos-cdn.com/u/0/xv_4_t.jpg",
    )
    monkeypatch.setattr(app_module, "get_item", lambda _item_id: row)
    monkeypatch.setattr(app_module, "PROVIDERS", [provider])
    monkeypatch.setattr(app_module, "LIVE_ADAPTERS", [])
    monkeypatch.setattr(provider, "_fetch_text", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not fetch")))
    assert asyncio.run(app_module.resolve_preview(row.id)) == {
        "preview_url": "https://thumb-cdn77.xvideos-cdn.com/u/0/preview.mp4"
    }
