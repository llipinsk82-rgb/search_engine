from backend.live import parse_drtuber_listing


def test_parse_drtuber_listing_core_metadata():
    raw = '''<a href="/video/9650666/sample-video" class="th ch-video wrap-better-content">
      <img src="https://g1.drtst.com/media/videos/tmb/9650666/240_180/5.jpg?1" alt="Sample &amp; Title" data-webm="https://g3.drtst.com/media/videos/tmb/9650666/9650666.mp4" />
      <strong class="toolbar"><em class="time_thumb"><i class="quality"><i class="ico_hd"></i></i><em>22:40</em></em></strong>
    </a>'''
    rows = parse_drtuber_listing(raw, limit=5)
    assert len(rows) == 1
    item = rows[0]
    assert item.provider == "drtuber"
    assert str(item.url) == "https://www.drtuber.com/video/9650666/sample-video"
    assert item.title == "Sample & Title"
    assert str(item.thumbnail).startswith("https://g1.drtst.com/")
    assert str(item.preview_url).endswith("9650666.mp4")
    assert item.duration_seconds == 1360
    assert item.quality == "HD"
