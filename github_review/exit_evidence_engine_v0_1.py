"""ARUNDA EXIT EVIDENCE ENGINE v0.1 — evidence observation boundary only."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Optional

from exit_evidence_contract_v0_1 import ExitEvidence, ExitEvidenceLevel


def _optional_number(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and value >= 0:
        return float(value)
    return None


def _level(value: Any) -> tuple[ExitEvidenceLevel, tuple[str, ...]]:
    if isinstance(value, ExitEvidenceLevel):
        return value, ()
    if isinstance(value, str):
        try:
            return ExitEvidenceLevel(value), ()
        except ValueError:
            pass
    if value is None:
        return ExitEvidenceLevel.NONE, ()
    return ExitEvidenceLevel.NONE, ("UNKNOWN_EVIDENCE_LEVEL",)


def build_exit_evidence(
    observations: Mapping[str, Any],
    *,
    evidence_level: Any = None,
) -> ExitEvidence:
    """Copy explicitly supplied observations into ExitEvidence.

    The engine does not derive thresholds, detect structure breaks, calculate
    exits, size positions, access capital, call providers, or write storage.
    Evidence strength is accepted only as an explicit observation.
    """
    if not isinstance(observations, Mapping):
        observations = {}

    level, level_reasons = _level(evidence_level)

    def text(name: str) -> Optional[str]:
        value = observations.get(name)
        return value if isinstance(value, str) else None

    result = ExitEvidence(
        signal_health=text("signal_health"),
        structure_health=text("structure_health"),
        momentum_state=text("momentum_state"),
        volatility_state=text("volatility_state"),
        mfe=_optional_number(observations.get("mfe")),
        mae=_optional_number(observations.get("mae")),
        giveback=_optional_number(observations.get("giveback")),
        holding_time=_optional_number(observations.get("holding_time")),
        liquidity=observations.get("liquidity"),
        market_regime=text("market_regime"),
        trend_state=text("trend_state"),
        exit_evidence_level=level,
        evidence_reasons=level_reasons,
    )
    result.validate()
    return result
