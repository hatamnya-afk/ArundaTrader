from __future__ import annotations

import pytest

from cp49_canonical_decision_birth_boundary_v0_1 import (
    bind_canonical_decision_identity,
    require_canonical_decision_id,
)


def test_requires_existing_canonical_decision_id() -> None:
    with pytest.raises(ValueError, match="CANONICAL_DECISION_ID_MISSING"):
        require_canonical_decision_id({"asset": "BTC"})


def test_rejects_blank_canonical_decision_id() -> None:
    with pytest.raises(ValueError, match="CANONICAL_DECISION_ID_MISSING"):
        require_canonical_decision_id({"decision_id": "   "})


def test_preserves_existing_identity_without_derivation() -> None:
    source = {
        "decision_id": "REAL-DECISION-001",
        "asset": "BTC",
        "direction": "LONG",
    }
    result = bind_canonical_decision_identity(source)
    assert result["decision_id"] == "REAL-DECISION-001"


def test_does_not_accept_non_mapping_input() -> None:
    with pytest.raises(ValueError, match="CANONICAL_DECISION_ID_INPUT_INVALID"):
        require_canonical_decision_id(None)  # type: ignore[arg-type]
