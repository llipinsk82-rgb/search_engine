from tools.filter_lab import summarize_counts


def test_candidate_production_is_everything_not_explicit_amateur() -> None:
    result = summarize_counts(all_total=4363, amateur_total=652, current_production_total=5)
    assert result == {
        "all": 4363,
        "amateur": 652,
        "current_production": 5,
        "candidate_production": 3711,
        "unclassified_gap": 3706,
    }


def test_candidate_production_never_goes_negative() -> None:
    result = summarize_counts(all_total=3, amateur_total=5, current_production_total=0)
    assert result["candidate_production"] == 0
