"""CP49 canonical decision-birth identity boundary.

A decision_id is never generated here. It must already exist at the real
decision-birth boundary and is propagated unchanged.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def require_canonical_decision_id(
    decision_record: Mapping[str, Any],
) -> str:
    if not isinstance(decision_record, Mapping):
        raise ValueError("CANONICAL_DECISION_ID_INPUT_INVALID")

    value = decision_record.get("decision_id")

    if not isinstance(value, str) or not value.strip():
        raise ValueError("CANONICAL_DECISION_ID_MISSING")

    return value.strip()


def bind_canonical_decision_identity(
    decision_record: Mapping[str, Any],
) -> dict[str, Any]:
    decision_id = require_canonical_decision_id(decision_record)
    bound = dict(decision_record)
    bound["decision_id"] = decision_id
    return bound
