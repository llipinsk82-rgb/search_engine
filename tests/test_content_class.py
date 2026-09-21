from backend.content_class import ContentClassification, classify_content, classify_content_evidence


def test_explicit_amateur_tag_on_audited_provider() -> None:
    assert classify_content(provider="xvideos", tags=["Amateur"], studio=None) == "amateur"


def test_explicit_homemade_tag_on_audited_provider() -> None:
    assert classify_content(provider="xvideos", tags=["homemade"], studio=None) == "amateur"


def test_user_generated_hyphen_normalizes_as_exact_token() -> None:
    assert classify_content(provider="xvideos", tags=[" User-Generated "], studio=None) == "amateur"


def test_explicit_studio_label_on_audited_provider() -> None:
    assert classify_content(provider="xcafe", tags=[], studio="Blacked") == "studio"


def test_generic_professional_tag_is_not_studio_evidence() -> None:
    assert classify_content(provider="xvideos", tags=["professional"], studio=None) == "unknown"


def test_bare_studio_tag_is_ambiguous_and_stays_unknown() -> None:
    assert classify_content(provider="xvideos", tags=["studio"], studio=None) == "unknown"


def test_unrelated_tags_stay_unknown() -> None:
    assert classify_content(provider="xvideos", tags=["stepmom", "hd"], studio=None) == "unknown"


def test_conflicting_audited_signals_are_unknown() -> None:
    assert classify_content(provider="xcafe", tags=["amateur"], studio="Blacked") == "unknown"


def test_substrings_do_not_classify() -> None:
    assert classify_content(provider="xvideos", tags=["amateur teen", "professional model"], studio=None) == "unknown"


def test_empty_studio_is_not_a_signal() -> None:
    assert classify_content(provider="xcafe", tags=[], studio="   ") == "unknown"


def test_no_signal_reports_none_source() -> None:
    assert classify_content_evidence(provider="xvideos", tags=["hd"], studio=None) == ContentClassification("unknown", "none")


def test_amateur_tag_reports_tag_amateur() -> None:
    assert classify_content_evidence(provider="xvideos", tags=[" User-Generated "], studio=None) == ContentClassification("amateur", "tag_amateur")


def test_generic_production_tag_reports_no_signal() -> None:
    assert classify_content_evidence(provider="xvideos", tags=["production"], studio=None) == ContentClassification("unknown", "none")


def test_explicit_studio_label_has_source_priority() -> None:
    assert classify_content_evidence(provider="xcafe", tags=["hd"], studio="Blacked") == ContentClassification("studio", "studio_label")


def test_conflict_reports_conflict_source() -> None:
    assert classify_content_evidence(provider="xcafe", tags=["homemade"], studio="Blacked") == ContentClassification("unknown", "conflict")


def test_title_is_not_an_input_to_classifier() -> None:
    result = classify_content_evidence(provider="xvideos", tags=["stepmom", "hd"], studio=None)
    assert result == ContentClassification("unknown", "none")
