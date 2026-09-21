from backend.media_policy import media_policy_rows, media_url_allowed, provider_media_policy


def test_unknown_provider_defaults_to_safe_media_modes():
    p = provider_media_policy("unknown")
    assert p.thumbnail_mode == "direct"
    assert p.preview_mode == "disabled"


def test_thumbzilla_policy_uses_proxy_thumbnail_and_preview():
    p = provider_media_policy("thumbzilla")
    assert p.thumbnail_mode == "proxy"
    assert p.preview_mode == "proxy"
    assert media_url_allowed("thumbzilla", "thumbnail", "https://pix-cdn77.ypncdn.com/a.jpg")
    assert not media_url_allowed("thumbzilla", "thumbnail", "https://evil.example/a.jpg")


def test_non_https_credentials_and_non_default_ports_are_rejected():
    assert not media_url_allowed("thumbzilla", "thumbnail", "http://pix-cdn77.ypncdn.com/a.jpg")
    assert not media_url_allowed("thumbzilla", "thumbnail", "https://u:p@pix-cdn77.ypncdn.com/a.jpg")
    assert not media_url_allowed("thumbzilla", "thumbnail", "https://pix-cdn77.ypncdn.com:8443/a.jpg")


def test_preview_host_allowlist_is_provider_specific():
    assert media_url_allowed("bigfuck", "preview", "https://icdn05.bigfuck.tv/x.mp4")
    assert not media_url_allowed("bigfuck", "preview", "https://evil.example/x.mp4")


def test_provider_rows_expose_modes_without_url_secrets():
    row = next(r for r in media_policy_rows({"tube8"}) if r["name"] == "tube8")
    assert row["name"] == "tube8"
    assert row["thumbnail_mode"] == "refresh"
    assert row["preview_mode"] == "direct"
    assert ".t8cdn.com" in row["preview_host_suffixes"]


def test_redirecting_preview_providers_are_disabled():
    for name in ("pornhat", "porndr", "anyporn"):
        assert provider_media_policy(name).preview_mode == "disabled"


def test_thumbzilla_preview_requires_strict_proxy():
    p = provider_media_policy("thumbzilla")
    assert p.preview_mode == "proxy"
    assert p.preview_referer == "https://www.thumbzilla.com/"
    assert media_url_allowed(
        "thumbzilla",
        "preview",
        "https://ev-ph.ypncdn.com/videos/example.mp4?token=x",
    )


def test_audited_preview_rules_match_media_policy_exactly():
    import json
    from pathlib import Path
    rules = json.loads((Path(__file__).resolve().parents[1] / "deploy" / "search-engine-preview-rules.json").read_text())
    for row in rules:
        name = row["provider"]
        policy = provider_media_policy(name)
        assert policy.preview_mode == row["playback_mode"]
        for host in row["preview_hosts"]:
            good = f"https://{host}/sample.mp4"
            assert media_url_allowed(name, "preview", good)
            assert not media_url_allowed(name, "preview", f"http://{host}/sample.mp4")
            assert not media_url_allowed(name, "preview", f"https://u:p@{host}/sample.mp4")
            assert not media_url_allowed(name, "preview", f"https://{host}:8443/sample.mp4")
        assert not media_url_allowed(name, "preview", "https://evil.example/sample.mp4")
