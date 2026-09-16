import math
from collections.abc import Mapping


_FORBIDDEN_SOURCES = {"TEST", "LEGACY", "SIMULATED"}


def _require_nonempty_string(observation, field, error):
    value = observation.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(error)
    return value


def _require_positive_finite(value, error):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(error)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(error)
    return float(value)


def validate_real_capital_source(observation):
    if not isinstance(observation, Mapping):
        raise ValueError("CAPITAL_INPUT_INVALID")

    if observation.get("capital_state") != "AVAILABLE":
        raise ValueError("CAPITAL_STATE_INVALID")

    if observation.get("capital_validation") != "VALID":
        raise ValueError("CAPITAL_VALIDATION_INVALID")

    capital_source = _require_nonempty_string(
        observation, "capital_source", "CAPITAL_SOURCE_INVALID"
    )
    if capital_source in _FORBIDDEN_SOURCES:
        raise ValueError("CAPITAL_SOURCE_INVALID")

    provenance = _require_nonempty_string(
        observation, "provenance", "CAPITAL_PROVENANCE_INVALID"
    )
    asset_scope = _require_nonempty_string(
        observation, "asset_scope", "CAPITAL_ASSET_SCOPE_INVALID"
    )
    observed_at = _require_nonempty_string(
        observation, "observed_at", "CAPITAL_OBSERVED_AT_INVALID"
    )

    available_capital = _require_positive_finite(
        observation.get("available_capital"), "AVAILABLE_CAPITAL_INVALID"
    )
    usable_capital = _require_positive_finite(
        observation.get("usable_capital"), "USABLE_CAPITAL_INVALID"
    )
    if usable_capital > available_capital:
        raise ValueError("USABLE_CAPITAL_INVALID")

    return {
        "capital_state": "AVAILABLE",
        "capital_source": capital_source,
        "provenance": provenance,
        "asset_scope": asset_scope,
        "available_capital": available_capital,
        "usable_capital": usable_capital,
        "observed_at": observed_at,
    }
