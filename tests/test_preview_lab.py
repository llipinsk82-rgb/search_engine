from tools.preview_lab import extract_preview_candidates, preview_status


def test_stored_preview_wins_without_resolver() -> None:
    item = {"preview_url": "https://cdn.example/preview.mp4"}
    assert preview_status(item, None, None) == ("stored", "https://cdn.example/preview.mp4")


def test_resolved_preview_is_reported() -> None:
    assert preview_status({}, 200, {"preview_url": "https://cdn.example/r.mp4"}) == (
        "resolved",
        "https://cdn.example/r.mp4",
    )


def test_404_is_no_current_preview() -> None:
    assert preview_status({}, 404, {"detail": "preview not found"}) == ("none", None)


def test_deep_probe_accepts_only_preview_named_motion_candidates() -> None:
    html = """
    <div data-preview="/media/teaser.mp4"></div>
    <script>window.x={"trailerUrl":"https://cdn.example/t.webm", "contentUrl":"https://cdn.example/full.mp4"}</script>
    <video><source src="https://cdn.example/full2.mp4"></video>
    """
    rows = extract_preview_candidates(html, "https://example.com/video/1")
    urls = {row["url"] for row in rows}
    assert "https://example.com/media/teaser.mp4" in urls
    assert "https://cdn.example/t.webm" in urls
    assert "https://cdn.example/full.mp4" not in urls
    assert "https://cdn.example/full2.mp4" not in urls


def test_xvideos_and_xnxx_infer_preview_from_thumbnail_directory() -> None:
    from tools.preview_lab import infer_preview_candidate
    for provider, thumb in [
        ("xvideos", "https://thumb.example/uuid/0/xv_3_t.jpg"),
        ("xnxx", "https://thumb.example/uuid/0/xv_13_t.jpg"),
    ]:
        row = {"thumbnail": thumb, "url": "https://example.com/v"}
        assert infer_preview_candidate(provider, row) == "https://thumb.example/uuid/0/preview.mp4"


def test_xgroovy_infers_bucketed_item_preview() -> None:
    from tools.preview_lab import infer_preview_candidate
    assert infer_preview_candidate(
        "xgroovy",
        {"thumbnail": "https://i.example/preview.jpg", "url": "https://xgroovy.com/videos/1869/example/"},
    ) == "https://preview.xgroovy.com/videos/1000/1869/1869_pr640.mp4"


def test_unknown_provider_has_no_inferred_preview() -> None:
    from tools.preview_lab import infer_preview_candidate
    assert infer_preview_candidate("xcafe", {"thumbnail": "https://i.example/a.jpg", "url": "https://example.com/1"}) is None


def test_pussyspace_uses_thumbnail_directory_preview() -> None:
    from tools.preview_lab import infer_preview_candidate
    row = {"thumbnail": "https://thumb-cdn.example/uuid/6/xv_15_p.avif", "url": "https://www.pussyspace.com/vid-6162641-example/"}
    assert infer_preview_candidate("pussyspace", row) == "https://thumb-cdn.example/uuid/6/preview.mp4"


def test_mypornhere_uses_bucketed_preview_file() -> None:
    from tools.preview_lab import infer_preview_candidate
    row = {"thumbnail": "https://www.mypornhere.com/contents/videos_screenshots/354000/354893/preview.jpg", "url": "https://www.mypornhere.com/videos/354893/example/"}
    assert infer_preview_candidate("mypornhere", row) == "https://www.mypornhere.com/contents/videos/354000/354893/354893_preview.mp4"


def test_porndig_infers_previewclip_from_thumbnail_path() -> None:
    from tools.preview_lab import infer_preview_candidate
    row = {"thumbnail": "https://image-cdn.porndig.com/thumbs/2014/08/59523/400x225/18.jpg", "url": "https://www.porndig.com/videos/26321/example.html"}
    assert infer_preview_candidate("porndig", row) == "https://image-cdn.porndig.com/previewclips/2014/08/59523/59523_1.mp4"


def test_sexvid_infers_short_preview_from_thumbnail_path() -> None:
    from tools.preview_lab import infer_preview_candidate
    row = {"thumbnail": "https://cdn1.sexvid.xxx/contents/videos_screenshots/98000/98793/preview.jpg", "url": "https://www.sexvid.xxx/example.html"}
    assert infer_preview_candidate("sexvid", row) == "https://pr1.sexvid.xxx/contents/videos/98000/98793/98793_short_preview.mp4"


def test_pornid_infers_short_preview_from_thumbnail_path() -> None:
    from tools.preview_lab import infer_preview_candidate
    row = {"thumbnail": "https://cdn.pornid.xxx/contents/videos_screenshots/87000/87864/preview.jpg", "url": "https://www.pornid.xxx/example.html"}
    assert infer_preview_candidate("pornid", row) == "https://pr1.pornid.xxx/contents/videos/87000/87864/87864_short_preview_480x270.mp4"


def test_zbporn_infers_short_preview_from_thumbnail_path() -> None:
    from tools.preview_lab import infer_preview_candidate
    row = {"thumbnail": "https://cdnth.zbporn.com/contents/videos_screenshots/682000/682348/preview.mp4.jpg", "url": "https://zbporn.com/videos/682348/example/"}
    assert infer_preview_candidate("zbporn", row) == "https://pr1.zbporn.com/contents/videos/682000/682348/682348_short_preview.mp4"
