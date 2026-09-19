from unittest.mock import MagicMock, patch

import pytest

from backend.app import _preview_proxy_fetch, app


def test_preview_proxy_route_is_registered():
    paths = {route.path for route in app.routes}
    assert "/api/preview-proxy" in paths


def test_preview_proxy_rejects_non_proxy_provider():
    with pytest.raises(ValueError, match="preview proxy is not enabled"):
        _preview_proxy_fetch("bigfuck", "https://icdn05.bigfuck.tv/x.mp4", None)


def test_preview_proxy_rejects_wrong_thumbzilla_host():
    with pytest.raises(ValueError, match="preview host is not allowed"):
        _preview_proxy_fetch("thumbzilla", "https://evil.example/x.mp4", None)


def test_thumbzilla_preview_proxy_adds_referer_and_bounded_range():
    with patch("backend.app._thumbnail_proxy_open") as opened:
        response = MagicMock()
        response.__enter__.return_value = response
        response.__exit__.return_value = False
        response.status = 206
        response.headers.get_content_type.return_value = "video/mp4"
        response.headers.get.return_value = None
        response.read.return_value = b"video"
        opened.return_value = response

        body, content_type, status, headers = _preview_proxy_fetch(
            "thumbzilla",
            "https://ev-ph.ypncdn.com/videos/example.mp4?token=x",
            "bytes=0-",
        )

        request = opened.call_args.args[0]
        assert request.headers["Referer"] == "https://www.thumbzilla.com/"
        assert request.headers["Range"] == "bytes=0-1048575"
        assert body == b"video"
        assert content_type == "video/mp4"
        assert status == 206
        assert isinstance(headers, dict)


def test_preview_proxy_rejects_non_video_content():
    with patch("backend.app._thumbnail_proxy_open") as opened:
        response = MagicMock()
        response.__enter__.return_value = response
        response.__exit__.return_value = False
        response.status = 200
        response.headers.get_content_type.return_value = "text/html"
        response.read.return_value = b"nope"
        opened.return_value = response
        with pytest.raises(ValueError, match="video"):
            _preview_proxy_fetch(
                "thumbzilla",
                "https://ev-ph.ypncdn.com/videos/example.mp4",
                None,
            )
