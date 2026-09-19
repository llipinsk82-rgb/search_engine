from backend.content_class import classify_content


def test_explicit_amateur_tag() -> None:
    assert classify_content(tags=["Amateur"], studio=None) == "amateur"


def test_explicit_homemade_tag() -> None:
    assert classify_content(tags=["homemade"], studio=None) == "amateur"


def test_user_generated_hyphen_normalizes_as_exact_token() -> None:
    assert classify_content(tags=[" User-Generated "], studio=None) == "amateur"


def test_explicit_studio_label() -> None:
    assert classify_content(tags=[], studio="Example Studio") == "studio"


def test_explicit_studio_metadata_tag() -> None:
    assert classify_content(tags=["professional"], studio=None) == "studio"


def test_unrelated_tags_stay_unknown() -> None:
    assert classify_content(tags=["stepmom", "hd"], studio=None) == "unknown"


def test_conflicting_signals_are_unknown() -> None:
    assert classify_content(tags=["amateur", "professional"], studio="Example Studio") == "unknown"


def test_substrings_do_not_classify() -> None:
    assert classify_content(tags=["amateur teen", "professional model"], studio=None) == "unknown"


def test_empty_studio_is_not_a_signal() -> None:
    assert classify_content(tags=[], studio="   ") == "unknown"
