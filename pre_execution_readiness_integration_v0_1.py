"""CP39 provider-neutral pre-execution readiness integration contract."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


_COMPONENTS = (
    "capital",
    "portfolio",
    "stop_risk_policy",
    "liquidity",
    "execution",
)

_ASSET_FIELDS = ("asset", "asset_scope")
_FORBIDDEN_PROVENANCE = {"TEST", "LEGACY", "SIMULATED"}


def _text(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def _validate_component(component: str, observation: Any) -> None:
    if not isinstance(observation, Mapping):
        raise ValueError("READINESS_OBSERVATION_INVALID")

    validation_fields = {
        "capital": "capital_validation",
        "portfolio": "portfolio_validation",
        "stop_risk_policy": "risk_policy_validation",
        "liquidity": "liquidity_validation",
        "execution": "execution_validation",
    }
    field = validation_fields[component]
    if observation.get(field) != "VALID":
        raise ValueError("READINESS_OBSERVATION_INVALID")

    provenance = _text(observation.get("provenance"))
    source_field = "capital_source" if component == "capital" else (
        "portfolio_source" if component == "portfolio" else "observation_source"
    )
    source = _text(observation.get(source_field))
    if provenance is None or source is None:
        raise ValueError("READINESS_PROVENANCE_INVALID")
    if provenance in _FORBIDDEN_PROVENANCE or source in _FORBIDDEN_PROVENANCE:
        raise ValueError("READINESS_PROVENANCE_INVALID")

    if _text(observation.get("observed_at")) is None:
        raise ValueError("READINESS_OBSERVATION_INVALID")


def _asset_from(observation: Mapping[str, Any]) -> str | None:
    asset = _text(observation.get("asset"))
    if asset is not None:
        return asset
    return _text(observation.get("asset_scope"))


def build_pre_execution_readiness(
    observations: Mapping[str, Any],
) -> dict[str, Any]:
    """Build a complete logical readiness state from verified observations.

    This boundary performs validation/completeness only. It does not call an
    exchange, mutate a database, create an order, authorize execution, or
    couple readiness to a provider.
    """
    if not isinstance(observations, Mapping):
        raise ValueError("READINESS_INPUT_INVALID")

    for component in _COMPONENTS:
        if component not in observations:
            raise ValueError("READINESS_OBSERVATION_MISSING")
        _validate_component(component, observations[component])

    assets = []
    for component in _COMPONENTS:
        asset = _asset_from(observations[component])
        if asset is not None and component in {"stop_risk_policy", "liquidity", "execution"}:
            assets.append(asset)

    if not assets:
        raise ValueError("READINESS_OBSERVATION_INVALID")
    if len(set(assets)) != 1:
        raise ValueError("READINESS_ASSET_MISMATCH")

    timestamps = [
        _text(observations[component].get("observed_at"))
        for component in _COMPONENTS
    ]
    if any(timestamp is None for timestamp in timestamps):
        raise ValueError("READINESS_OBSERVATION_INVALID")

    result = {
        "readiness_state": "READY",
        "readiness_validation": "VALID",
        "readiness_source": "REAL_PRODUCTION_READINESS",
        "provenance": "REAL_PRODUCTION_OBSERVATION",
        "asset": assets[0],
        "capital_validation": "VALID",
        "portfolio_validation": "VALID",
        "stop_risk_policy_validation": "VALID",
        "liquidity_validation": "VALID",
        "execution_validation": "VALID",
        "observed_at": max(timestamps),
    }
    return result


__all__ = ["build_pre_execution_readiness"]
