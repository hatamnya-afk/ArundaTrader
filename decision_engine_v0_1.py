"""CP40 provider-neutral deterministic Decision engine."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from decision_contract_v0_1 import validate_sealed_decision_input


def _parse_aware_timestamp(value: str, error_code: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(error_code) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(error_code)
    return parsed


def build_decision(
    decision_input: Mapping[str, Any],
    *,
    evaluation_time: str | None = None,
    max_age_seconds: int | float | None = None,
) -> dict[str, Any]:
    """Produce a decision status from sealed input only.

    The engine does not calculate price, entry, stop, capital, quantity,
    portfolio state, risk, order intent, or execution authorization.
    """
    sealed = validate_sealed_decision_input(decision_input)

    if evaluation_time is None:
        raise ValueError("DECISION_EVALUATION_TIME_REQUIRED")
    if max_age_seconds is None or isinstance(max_age_seconds, bool) or max_age_seconds <= 0:
        raise ValueError("DECISION_MAX_AGE_INVALID")

    evaluation = _parse_aware_timestamp(
        evaluation_time,
        "DECISION_EVALUATION_TIME_INVALID",
    )
    observed = _parse_aware_timestamp(
        sealed["observed_at"],
        "DECISION_INPUT_INVALID",
    )

    age_seconds = (evaluation - observed).total_seconds()
    if age_seconds < 0 or age_seconds > float(max_age_seconds):
        raise ValueError("DECISION_INPUT_STALE")

    return {
        "decision_state": "READY",
        "decision_validation": "VALID",
        "decision_reason": "SEALED_INPUT_VALID",
        "asset": sealed["asset"],
        "provenance": sealed["provenance"],
        "observed_at": sealed["observed_at"],
    }


__all__ = ["build_decision"]
