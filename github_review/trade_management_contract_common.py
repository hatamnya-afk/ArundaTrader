"""Shared primitives for Arunda Trade Management contracts.

Contract-only layer: no database, execution, calculations, or provider bindings.
"""
from dataclasses import asdict, dataclass
from enum import Enum
from math import isfinite
from typing import Any, Mapping


class CapitalState(str, Enum):
    REAL_CAPITAL = "REAL_CAPITAL"
    TEST_CAPITAL = "TEST_CAPITAL"
    UNAVAILABLE_CAPITAL = "UNAVAILABLE_CAPITAL"


class ValidationStatus(str, Enum):
    VALID = "VALID"
    RUNTIME_VALIDATION_REQUIRED = "RUNTIME_VALIDATION_REQUIRED"
    NOT_YET_AVAILABLE = "NOT_YET_AVAILABLE"
    UNVALIDATED = "UNVALIDATED"


def _require_nonempty_text(value: Any, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty text")


def _validate_optional_number(value: Any, name: str, *, positive: bool = False) -> None:
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(float(value)):
        raise TypeError(f"{name} must be a finite number or None")
    if positive and float(value) <= 0:
        raise ValueError(f"{name} must be > 0")


def _validate_text_or_none(value: Any, name: str) -> None:
    if value is not None and not isinstance(value, str):
        raise TypeError(f"{name} must be text or None")


@dataclass(frozen=True)
class ContractBase:
    """Immutable contract value object base."""

    def to_dict(self) -> dict:
        return asdict(self)
