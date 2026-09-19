from backend.media_policy import media_policy_rows, media_url_allowed, provider_media_policy


def test_unknown_provider_defaults_to_safe_media_modes():
    p = provider_media_policy("unknown")
    assert p.thumbnail_mode == "direct"
    assert p.preview_mode == "disabled"


def test_thumbzilla_policy_uses_proxy_thumbnail_and_direct_preview():
    p = provider_media_policy("thumbzilla")
    assert p.thumbnail_mode == "proxy"
    assert p.preview_mode == "direct"
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
