from backend.content_class import ContentClassification, classify_content, classify_content_evidence


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

def test_no_signal_reports_none_source() -> None:
    assert classify_content_evidence(tags=["hd"], studio=None) == ContentClassification("unknown", "none")


def test_amateur_tag_reports_tag_amateur() -> None:
    assert classify_content_evidence(tags=[" User-Generated "], studio=None) == ContentClassification("amateur", "tag_amateur")


def test_studio_tag_reports_tag_studio() -> None:
    assert classify_content_evidence(tags=["production"], studio=None) == ContentClassification("studio", "tag_studio")


def test_explicit_studio_label_has_source_priority() -> None:
    assert classify_content_evidence(tags=["hd"], studio="Example Studio") == ContentClassification("studio", "studio_label")


def test_conflict_reports_conflict_source() -> None:
    assert classify_content_evidence(tags=["homemade", "professional"], studio="Example Studio") == ContentClassification("unknown", "conflict")


def test_title_is_not_an_input_to_classifier() -> None:
    result = classify_content_evidence(tags=["stepmom", "hd"], studio=None)
    assert result == ContentClassification("unknown", "none")
