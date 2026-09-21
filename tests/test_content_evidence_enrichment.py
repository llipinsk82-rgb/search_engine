import asyncio
from pathlib import Path

from backend.models import SearchItem
from backend.providers.sitemap import SitemapProvider

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "content_evidence_pages"


def provider(name: str) -> SitemapProvider:
    return SitemapProvider(
        name=name,
        sitemap_url=f"https://{name}.example/sitemap.xml",
        delay_seconds=0,
        obey_robots=False,
        content_class_enrichment=False,
    )


def test_existing_studio_is_never_overwritten_by_rule(monkeypatch):
    p = provider("xcafe")
    html = (FIXTURES / "xcafe-positive.html").read_text(encoding="utf-8")
    monkeypatch.setattr(p, "_fetch_text", lambda _url: html)
    base = SearchItem(
        id="1",
        provider="xcafe",
        title="Sample",
        url="https://xcafe.com/366143/",
        studio="Existing Studio",
    )
    enriched = asyncio.run(p.enrich_content_evidence(base))
    assert enriched.studio == "Existing Studio"


def test_rule_fills_missing_studio_when_generic_parser_has_none(monkeypatch):
    p = provider("xcafe")
    html = (FIXTURES / "xcafe-positive.html").read_text(encoding="utf-8")
    monkeypatch.setattr(p, "_fetch_text", lambda _url: html)
    base = SearchItem(
        id="2",
        provider="xcafe",
        title="Sample",
        url="https://xcafe.com/366143/",
    )
    enriched = asyncio.run(p.enrich_content_evidence(base))
    assert enriched.studio == "Blacked"


def test_rule_backed_provider_is_enrichment_eligible_without_config_flag():
    assert provider("porndoe").content_class_enrichment is True
    assert provider("sunporno").content_class_enrichment is False
