from opportunity_engine import (
    MIN_OPPORTUNITY_SCORE,
    calculate_confidence,
    determine_status,
)


def test_confidence_score_normalizes_to_opportunity_floor():
    confidence = calculate_confidence(
        MIN_OPPORTUNITY_SCORE,
        1.25,
        0.0,
        50.0,
    )

    assert confidence >= 0.55


def test_opportunity_floor_and_confidence_can_reach_eligible():
    score = MIN_OPPORTUNITY_SCORE
    confidence = calculate_confidence(
        score,
        1.25,
        0.0,
        50.0,
    )

    assert determine_status(
        score,
        confidence,
        "LONG",
    ) == "ELIGIBLE"


def test_confidence_remains_bounded():
    confidence = calculate_confidence(
        100.0,
        10.0,
        100.0,
        100.0,
    )

    assert 0.0 <= confidence <= 1.0
