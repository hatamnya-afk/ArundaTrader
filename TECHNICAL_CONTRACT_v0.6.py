"""
ARUNDA TRADER
TECHNICAL CONTRACT v0.6

Purpose:
    Define the trusted Technical Contract scope.

Contract Scope:
    ONLY records belonging to the trusted 987-record contract epoch.

Out of Scope:
    All other historical / legacy / pre-arm / foreign-contract records.

Important:
    OUT_OF_SCOPE != INVALID

Mode:
    READ / VALIDATION ONLY

No database mutation.
No repair.
No migration.
No deletion.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional


# ============================================================================
# CONTRACT IDENTITY
# ============================================================================

CONTRACT_NAME = "TECHNICAL_CONTRACT"
CONTRACT_VERSION = "TECHNICAL_v0.6"

# The currently trusted contract population.
TRUSTED_RECORD_COUNT = 987

# Records outside this scope are ignored by this contract.
OUT_OF_SCOPE_POLICY = "IGNORE"


# ============================================================================
# TRUSTED CONTRACT FINGERPRINT
# ============================================================================

REQUIRED_FIELDS = (
    "symbol",
    "history_points",
    "price",
    "close",
    "volatility",
    "volatility_20",
    "regime",
    "technical_available",
    "technical_completeness",
    "technical_version",
    "engine_version",
    "source",
)

TRUSTED_SOURCE = "REAL_MARKET_HISTORY"
TRUSTED_TECHNICAL_VERSION = "TECHNICAL_v0.5"
TRUSTED_ENGINE_VERSION = "TECHNICAL_v0.5"


# ============================================================================
# RESULT STATES
# ============================================================================

STATUS_IN_SCOPE = "IN_SCOPE"
STATUS_OUT_OF_SCOPE = "OUT_OF_SCOPE"
STATUS_INVALID = "INVALID"


@dataclass(frozen=True)
class TechnicalContractResult:
    status: str
    valid: bool
    contract: str
    contract_version: str
    reason: str


# ============================================================================
# BASIC HELPERS
# ============================================================================

def _is_missing(value: Any) -> bool:
    return value is None


def _has_value(record: Mapping[str, Any], field: str) -> bool:
    return not _is_missing(record.get(field))


# ============================================================================
# SCOPE DEFINITION
# ============================================================================

def is_contract_scope(record: Mapping[str, Any]) -> bool:
    """
    Determine whether a record belongs to the trusted Technical Contract.

    This function intentionally uses the established trusted fingerprint.

    Anything that does not match the trusted fingerprint is OUT_OF_SCOPE.
    It is NOT automatically INVALID.
    """

    if not _has_value(record, "symbol"):
        return False

    if record.get("history_points") != 200:
        return False

    if not _has_value(record, "price"):
        return False

    if not _has_value(record, "close"):
        return False

    if not _has_value(record, "volatility"):
        return False

    if not _has_value(record, "volatility_20"):
        return False

    if not _has_value(record, "regime"):
        return False

    if not _has_value(record, "technical_available"):
        return False

    if not _has_value(record, "technical_completeness"):
        return False

    if record.get("technical_version") != TRUSTED_TECHNICAL_VERSION:
        return False

    if record.get("engine_version") != TRUSTED_ENGINE_VERSION:
        return False

    if record.get("source") != TRUSTED_SOURCE:
        return False

    return True


# ============================================================================
# CONTRACT VALIDATION
# ============================================================================

def validate_in_scope_record(
    record: Mapping[str, Any],
) -> TechnicalContractResult:
    """
    Validate ONLY records already identified as belonging to the contract.

    Out-of-scope records must be filtered before this function is called.
    """

    if not is_contract_scope(record):
        return TechnicalContractResult(
            status=STATUS_OUT_OF_SCOPE,
            valid=False,
            contract=CONTRACT_NAME,
            contract_version=CONTRACT_VERSION,
            reason="RECORD_OUTSIDE_TRUSTED_TECHNICAL_CONTRACT",
        )

    # ------------------------------------------------------------------------
    # Required-field validation
    # ------------------------------------------------------------------------

    missing = [
        field
        for field in REQUIRED_FIELDS
        if not _has_value(record, field)
    ]

    if missing:
        return TechnicalContractResult(
            status=STATUS_INVALID,
            valid=False,
            contract=CONTRACT_NAME,
            contract_version=CONTRACT_VERSION,
            reason="MISSING_REQUIRED_FIELDS:" + ",".join(missing),
        )

    # ------------------------------------------------------------------------
    # Canonical history contract
    # ------------------------------------------------------------------------

    if record["history_points"] < 200:
        return TechnicalContractResult(
            status=STATUS_INVALID,
            valid=False,
            contract=CONTRACT_NAME,
            contract_version=CONTRACT_VERSION,
            reason="INSUFFICIENT_HISTORY_POINTS",
        )

    # ------------------------------------------------------------------------
    # Canonical price contract
    # ------------------------------------------------------------------------

    if record["price"] <= 0:
        return TechnicalContractResult(
            status=STATUS_INVALID,
            valid=False,
            contract=CONTRACT_NAME,
            contract_version=CONTRACT_VERSION,
            reason="INVALID_PRICE",
        )

    if record["close"] <= 0:
        return TechnicalContractResult(
            status=STATUS_INVALID,
            valid=False,
            contract=CONTRACT_NAME,
            contract_version=CONTRACT_VERSION,
            reason="INVALID_CLOSE",
        )

    # ------------------------------------------------------------------------
    # Availability
    # ------------------------------------------------------------------------

    if record["technical_available"] not in (0, 1):
        return TechnicalContractResult(
            status=STATUS_INVALID,
            valid=False,
            contract=CONTRACT_NAME,
            contract_version=CONTRACT_VERSION,
            reason="INVALID_TECHNICAL_AVAILABILITY",
        )

    # ------------------------------------------------------------------------
    # Completeness
    # ------------------------------------------------------------------------

    completeness = record["technical_completeness"]

    if not isinstance(completeness, (int, float)):
        return TechnicalContractResult(
            status=STATUS_INVALID,
            valid=False,
            contract=CONTRACT_NAME,
            contract_version=CONTRACT_VERSION,
            reason="INVALID_TECHNICAL_COMPLETENESS",
        )

    if not 0 <= completeness <= 1:
        return TechnicalContractResult(
            status=STATUS_INVALID,
            valid=False,
            contract=CONTRACT_NAME,
            contract_version=CONTRACT_VERSION,
            reason="TECHNICAL_COMPLETENESS_OUT_OF_RANGE",
        )

    return TechnicalContractResult(
        status=STATUS_IN_SCOPE,
        valid=True,
        contract=CONTRACT_NAME,
        contract_version=CONTRACT_VERSION,
        reason="TRUSTED_TECHNICAL_CONTRACT",
    )


# ============================================================================
# PUBLIC ENTRY POINT
# ============================================================================

def evaluate_record(record: Mapping[str, Any]) -> TechnicalContractResult:
    """
    Single public contract boundary.

    OUT_OF_SCOPE records stop here and are ignored.

    Only trusted records proceed to validation.
    """

    if not is_contract_scope(record):
        return TechnicalContractResult(
            status=STATUS_OUT_OF_SCOPE,
            valid=False,
            contract=CONTRACT_NAME,
            contract_version=CONTRACT_VERSION,
            reason="IGNORED_OUTSIDE_CONTRACT_SCOPE",
        )

    return validate_in_scope_record(record)


# ============================================================================
# BATCH SCOPE FILTER
# ============================================================================

def filter_contract_records(
    records: list[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    """
    Return ONLY records belonging to the trusted Technical Contract.

    No mutation is performed.
    """

    return [
        record
        for record in records
        if is_contract_scope(record)
    ]


# ============================================================================
# CONTRACT METADATA
# ============================================================================

def contract_metadata() -> dict[str, Any]:
    return {
        "contract_name": CONTRACT_NAME,
        "contract_version": CONTRACT_VERSION,
        "trusted_record_count": TRUSTED_RECORD_COUNT,
        "out_of_scope_policy": OUT_OF_SCOPE_POLICY,
        "trusted_source": TRUSTED_SOURCE,
        "trusted_technical_version": TRUSTED_TECHNICAL_VERSION,
        "trusted_engine_version": TRUSTED_ENGINE_VERSION,
        "history_points": 200,
        "out_of_scope_is_invalid": False,
        "database_mutation": False,
    }


__all__ = [
    "CONTRACT_NAME",
    "CONTRACT_VERSION",
    "TRUSTED_RECORD_COUNT",
    "TechnicalContractResult",
    "is_contract_scope",
    "validate_in_scope_record",
    "evaluate_record",
    "filter_contract_records",
    "contract_metadata",
]