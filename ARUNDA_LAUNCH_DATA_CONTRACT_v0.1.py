"""
ARUNDA TRADER — LAUNCH DATA CONTRACT v0.1

Purpose:
    Formal production data boundary + rolling historical context contract.

Properties:
    - Pure
    - Deterministic
    - Side-effect free
    - No SQLite
    - No network
    - No exchange access
    - No filesystem access
    - No INSERT / UPDATE / DELETE / ALTER / CREATE
    - No legacy-data modification
    - No synthetic data
    - No interpolation
    - No forward-fill
    - No back-fill
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Mapping, Optional


# ============================================================================
# CONTRACT IDENTITY
# ============================================================================

CONTRACT_NAME = "ARUNDA_LAUNCH_DATA_CONTRACT"
CONTRACT_VERSION = "v0.1"


# ============================================================================
# LAUNCH BOUNDARY
# ============================================================================

# IMPORTANT:
# This is the formal production boundary.
# It is timezone-aware and immutable at runtime.
#
# Replace ONLY this value when the real production launch timestamp is
# formally frozen. Do not infer launch from row IDs, file dates, or history.

LAUNCH_TIMESTAMP = datetime.fromisoformat(
    "2026-08-31T00:00:00+00:00"
)


# ============================================================================
# ENUMS
# ============================================================================

class DataProvenance(str, Enum):
    LEGACY = "LEGACY"
    TEST = "TEST"
    PRODUCTION = "PRODUCTION"
    INVALID = "INVALID"


class ProductionDataDecision(str, Enum):
    PRODUCTION_ELIGIBLE = "PRODUCTION_ELIGIBLE"
    BLOCKED = "BLOCKED"


class HistoricalHorizon(str, Enum):
    IMMEDIATE = "IMMEDIATE"
    SHORT_TERM = "SHORT_TERM"
    MEDIUM_TERM = "MEDIUM_TERM"
    LONG_TERM = "LONG_TERM"


class RetentionStatus(str, Enum):
    BOUNDED = "BOUNDED"
    CONFIG_REQUIRED = "CONFIG_REQUIRED"
    INVALID = "INVALID"


# ============================================================================
# CONTRACT ERRORS
# ============================================================================

class LaunchDataContractError(ValueError):
    pass


class TimestampValidationError(LaunchDataContractError):
    pass


class ProvenanceValidationError(LaunchDataContractError):
    pass


class ContextWindowValidationError(LaunchDataContractError):
    pass


class RetentionPolicyError(LaunchDataContractError):
    pass


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass(frozen=True)
class LaunchDataBoundary:
    """
    Immutable production launch boundary.
    """

    launch_timestamp: datetime

    def __post_init__(self) -> None:
        validate_timestamp(self.launch_timestamp)


@dataclass(frozen=True)
class RetentionPolicy:
    """
    Bounded retention contract.

    If no numeric retention value has been formally decided yet,
    CONFIG_REQUIRED is represented by both values being None.

    This does NOT mean unlimited retention is allowed.
    """

    max_observations: Optional[int] = None
    max_age_seconds: Optional[int] = None

    def status(self) -> RetentionStatus:

        if (
            self.max_observations is None
            and self.max_age_seconds is None
        ):
            return RetentionStatus.CONFIG_REQUIRED

        if self.max_observations is not None:
            if (
                not isinstance(self.max_observations, int)
                or isinstance(self.max_observations, bool)
                or self.max_observations <= 0
            ):
                return RetentionStatus.INVALID

        if self.max_age_seconds is not None:
            if (
                not isinstance(self.max_age_seconds, int)
                or isinstance(self.max_age_seconds, bool)
                or self.max_age_seconds <= 0
            ):
                return RetentionStatus.INVALID

        return RetentionStatus.BOUNDED


@dataclass(frozen=True)
class HistoricalContextPolicy:
    """
    Four conceptual historical horizons.

    Numeric window sizes remain unspecified until formally configured.
    """

    immediate: Any = None
    short_term: Any = None
    medium_term: Any = None
    long_term: Any = None

    def horizons(self) -> tuple[HistoricalHorizon, ...]:
        return (
            HistoricalHorizon.IMMEDIATE,
            HistoricalHorizon.SHORT_TERM,
            HistoricalHorizon.MEDIUM_TERM,
            HistoricalHorizon.LONG_TERM,
        )

    def configuration_required(self) -> bool:
        return not self.has_complete_configuration()

    def has_complete_configuration(self) -> bool:
        return all(
            value is not None
            for value in (
                self.immediate,
                self.short_term,
                self.medium_term,
                self.long_term,
            )
        )


@dataclass(frozen=True)
class ContextMetadata:
    """
    Metadata contract for bounded/compressed historical state.
    """

    source: str
    window_start: datetime
    window_end: datetime
    observation_count: int
    last_update: datetime
    state_version: str
    data_boundary: datetime

    def __post_init__(self) -> None:

        if not isinstance(self.source, str):
            raise ContextWindowValidationError(
                "source must be a string"
            )

        if not self.source.strip():
            raise ContextWindowValidationError(
                "source is required"
            )

        validate_timestamp(self.window_start)
        validate_timestamp(self.window_end)
        validate_timestamp(self.last_update)
        validate_timestamp(self.data_boundary)

        if self.window_end < self.window_start:
            raise ContextWindowValidationError(
                "window_end must be >= window_start"
            )

        if (
            not isinstance(self.observation_count, int)
            or isinstance(self.observation_count, bool)
            or self.observation_count < 0
        ):
            raise ContextWindowValidationError(
                "observation_count must be a non-negative integer"
            )

        if (
            not isinstance(self.state_version, str)
            or not self.state_version.strip()
        ):
            raise ContextWindowValidationError(
                "state_version is required"
            )

        if self.window_start < self.data_boundary:
            raise ContextWindowValidationError(
                "context window contains pre-launch data"
            )


# ============================================================================
# TIMESTAMP CONTRACT
# ============================================================================

def validate_timestamp(value: Any) -> datetime:
    """
    Accept timezone-aware datetime only.

    Naive datetime is always rejected.
    """

    if not isinstance(value, datetime):
        raise TimestampValidationError(
            "timestamp must be datetime"
        )

    if value.tzinfo is None or value.utcoffset() is None:
        raise TimestampValidationError(
            "timezone-naive timestamp rejected"
        )

    return value


# ============================================================================
# PROVENANCE CONTRACT
# ============================================================================

def classify_provenance(
    value: Any,
) -> DataProvenance:
    """
    Explicit provenance classification.

    No inference is allowed from:
        - row ID
        - file name
        - file modification time
        - symbol
        - ordering
        - database position
        - timestamp alone
    """

    if isinstance(value, DataProvenance):
        return value

    if value is None:
        return DataProvenance.INVALID

    if not isinstance(value, str):
        return DataProvenance.INVALID

    normalized = value.strip().upper()

    try:
        return DataProvenance(normalized)
    except ValueError:
        return DataProvenance.INVALID


def classify_record_provenance(
    record: Mapping[str, Any],
) -> DataProvenance:
    """
    Read explicit provenance from a record.

    Accepted keys:
        provenance
        source_provenance
    """

    if not isinstance(record, Mapping):
        return DataProvenance.INVALID

    if "provenance" in record:
        return classify_provenance(
            record.get("provenance")
        )

    if "source_provenance" in record:
        return classify_provenance(
            record.get("source_provenance")
        )

    return DataProvenance.INVALID


# ============================================================================
# PRODUCTION VALIDITY CONTRACT
# ============================================================================

def is_production_valid(
    record: Mapping[str, Any],
    launch_timestamp: datetime = LAUNCH_TIMESTAMP,
) -> bool:
    """
    Production validity requires BOTH:

        1. Explicit PRODUCTION provenance
        2. timestamp >= LAUNCH_TIMESTAMP

    Therefore:

        pre-launch + PRODUCTION
            -> BLOCKED

        post-launch + LEGACY
            -> BLOCKED

        post-launch + TEST
            -> BLOCKED

        post-launch + INVALID
            -> BLOCKED

        post-launch + PRODUCTION
            -> ALLOWED
    """

    if not isinstance(record, Mapping):
        return False

    try:
        validate_timestamp(launch_timestamp)
        timestamp = validate_timestamp(
            record.get("timestamp")
        )
    except TimestampValidationError:
        return False

    provenance = classify_record_provenance(record)

    if provenance != DataProvenance.PRODUCTION:
        return False

    return timestamp >= launch_timestamp


def production_data_decision(
    record: Mapping[str, Any],
    launch_timestamp: datetime = LAUNCH_TIMESTAMP,
) -> ProductionDataDecision:
    """
    Return explicit production-path decision.
    """

    if is_production_valid(
        record,
        launch_timestamp,
    ):
        return ProductionDataDecision.PRODUCTION_ELIGIBLE

    return ProductionDataDecision.BLOCKED


# ============================================================================
# CONTEXT WINDOW CONTRACT
# ============================================================================

def validate_context_window(
    window_start: datetime,
    window_end: datetime,
    launch_timestamp: datetime = LAUNCH_TIMESTAMP,
) -> bool:
    """
    Historical context may contain ONLY post-launch observations.

    Required:

        window_start >= launch_timestamp
        window_end >= window_start
        all timestamps timezone-aware
    """

    validate_timestamp(window_start)
    validate_timestamp(window_end)
    validate_timestamp(launch_timestamp)

    if window_end < window_start:
        raise ContextWindowValidationError(
            "window_end must be >= window_start"
        )

    if window_start < launch_timestamp:
        raise ContextWindowValidationError(
            "context window contains pre-launch data"
        )

    return True


# ============================================================================
# RETENTION CONTRACT
# ============================================================================

def validate_retention_policy(
    policy: RetentionPolicy,
) -> RetentionStatus:
    """
    Unlimited raw retention is never an accepted state.

    If retention number has not been formally decided:

        CONFIG_REQUIRED

    If a positive numeric bound exists:

        BOUNDED

    Invalid values:

        INVALID
    """

    if not isinstance(policy, RetentionPolicy):
        raise RetentionPolicyError(
            "policy must be RetentionPolicy"
        )

    status = policy.status()

    if status == RetentionStatus.INVALID:
        raise RetentionPolicyError(
            "retention policy contains invalid values"
        )

    return status


# ============================================================================
# CONTEXT METADATA CONTRACT
# ============================================================================

def validate_context_metadata(
    *,
    source: str,
    window_start: datetime,
    window_end: datetime,
    observation_count: int,
    last_update: datetime,
    state_version: str,
    launch_timestamp: datetime = LAUNCH_TIMESTAMP,
) -> bool:
    """
    Validate metadata required for rolling/compressed context state.
    """

    ContextMetadata(
        source=source,
        window_start=window_start,
        window_end=window_end,
        observation_count=observation_count,
        last_update=last_update,
        state_version=state_version,
        data_boundary=launch_timestamp,
    )

    return True


# ============================================================================
# DEFAULT POLICIES
# ============================================================================

def default_retention_policy() -> RetentionPolicy:
    """
    Numeric retention is intentionally not invented yet.
    """

    return RetentionPolicy(
        max_observations=None,
        max_age_seconds=None,
    )


def default_historical_context_policy() -> HistoricalContextPolicy:
    """
    Four required conceptual horizons.
    """

    return HistoricalContextPolicy()


# ============================================================================
# ARCHITECTURAL INVARIANTS
# ============================================================================

MARKET_TECHNICAL_IS_PERMANENT_HISTORY = False

LEGACY_DATA_MUST_REMAIN_IN_DB = True

LEGACY_DATA_MUST_NOT_ENTER_PRODUCTION_ANALYSIS = True

TEST_DATA_MUST_NOT_ENTER_PRODUCTION_ANALYSIS = True

PRODUCTION_REQUIRES_EXPLICIT_PROVENANCE = True

PRODUCTION_REQUIRES_POST_LAUNCH_TIMESTAMP = True

UNLIMITED_RAW_TECHNICAL_RETENTION_ALLOWED = False

SYNTHETIC_DATA_ALLOWED = False

INTERPOLATION_ALLOWED = False

FORWARD_FILL_ALLOWED = False

BACK_FILL_ALLOWED = False


# ============================================================================
# DETERMINISTIC TESTS
# ============================================================================

def run_contract_tests() -> None:
    """
    Deterministic tests.

    No:
        SQLite
        network
        filesystem
        exchange
        mutation
    """

    launch = LAUNCH_TIMESTAMP

    # ------------------------------------------------------------------------
    # TEST A
    # timestamp < launch
    # ------------------------------------------------------------------------

    pre_launch_record = {
        "timestamp": datetime.fromisoformat(
            "2026-08-30T23:59:59+00:00"
        ),
        "provenance": "PRODUCTION",
    }

    assert (
        is_production_valid(
            pre_launch_record,
            launch,
        )
        is False
    )

    assert (
        production_data_decision(
            pre_launch_record,
            launch,
        )
        == ProductionDataDecision.BLOCKED
    )

    # ------------------------------------------------------------------------
    # TEST B
    # timestamp == launch
    # ------------------------------------------------------------------------

    exact_launch_record = {
        "timestamp": launch,
        "provenance": "PRODUCTION",
    }

    assert (
        is_production_valid(
            exact_launch_record,
            launch,
        )
        is True
    )

    assert (
        production_data_decision(
            exact_launch_record,
            launch,
        )
        == ProductionDataDecision.PRODUCTION_ELIGIBLE
    )

    # ------------------------------------------------------------------------
    # TEST C
    # timestamp > launch
    # ------------------------------------------------------------------------

    post_launch_record = {
        "timestamp": datetime.fromisoformat(
            "2026-08-31T00:00:01+00:00"
        ),
        "provenance": "PRODUCTION",
    }

    assert (
        is_production_valid(
            post_launch_record,
            launch,
        )
        is True
    )

    # ------------------------------------------------------------------------
    # TEST D
    # legacy provenance + post-launch
    # ------------------------------------------------------------------------

    legacy_post_launch = {
        "timestamp": datetime.fromisoformat(
            "2026-08-31T00:01:00+00:00"
        ),
        "provenance": "LEGACY",
    }

    assert (
        is_production_valid(
            legacy_post_launch,
            launch,
        )
        is False
    )

    # ------------------------------------------------------------------------
    # TEST E
    # production provenance + pre-launch
    # ------------------------------------------------------------------------

    production_pre_launch = {
        "timestamp": datetime.fromisoformat(
            "2026-08-30T12:00:00+00:00"
        ),
        "provenance": "PRODUCTION",
    }

    assert (
        is_production_valid(
            production_pre_launch,
            launch,
        )
        is False
    )

    # ------------------------------------------------------------------------
    # TEST F
    # timezone-naive timestamp
    # ------------------------------------------------------------------------

    try:
        validate_timestamp(
            datetime(
                2026,
                8,
                31,
                0,
                0,
            )
        )
    except TimestampValidationError:
        pass
    else:
        raise AssertionError(
            "timezone-naive timestamp was accepted"
        )

    # ------------------------------------------------------------------------
    # TEST G
    # invalid context window
    # ------------------------------------------------------------------------

    try:
        validate_context_window(
            datetime.fromisoformat(
                "2026-08-30T23:59:00+00:00"
            ),
            datetime.fromisoformat(
                "2026-08-31T00:01:00+00:00"
            ),
            launch,
        )
    except ContextWindowValidationError:
        pass
    else:
        raise AssertionError(
            "pre-launch context window was accepted"
        )

    try:
        validate_context_window(
            datetime.fromisoformat(
                "2026-08-31T00:02:00+00:00"
            ),
            datetime.fromisoformat(
                "2026-08-31T00:01:00+00:00"
            ),
            launch,
        )
    except ContextWindowValidationError:
        pass
    else:
        raise AssertionError(
            "reversed context window was accepted"
        )

    # ------------------------------------------------------------------------
    # TEST H
    # unbounded retention
    # ------------------------------------------------------------------------

    policy = RetentionPolicy()

    assert (
        validate_retention_policy(policy)
        == RetentionStatus.CONFIG_REQUIRED
    )

    # Explicitly invalid bounds must reject.
    try:
        validate_retention_policy(
            RetentionPolicy(max_observations=0)
        )
    except RetentionPolicyError:
        pass
    else:
        raise AssertionError(
            "invalid retention bound was accepted"
        )

    # ------------------------------------------------------------------------
    # ADDITIONAL SAFETY TESTS
    # ------------------------------------------------------------------------

    # Missing provenance must never become production.
    missing_provenance = {
        "timestamp": datetime.fromisoformat(
            "2026-08-31T00:10:00+00:00"
        ),
    }

    assert (
        is_production_valid(
            missing_provenance,
            launch,
        )
        is False
    )

    # TEST provenance must never become production.
    test_record = {
        "timestamp": datetime.fromisoformat(
            "2026-08-31T00:10:00+00:00"
        ),
        "provenance": "TEST",
    }

    assert (
        is_production_valid(
            test_record,
            launch,
        )
        is False
    )

    # Unknown provenance must be INVALID.
    assert (
        classify_provenance("something_unknown")
        == DataProvenance.INVALID
    )

    # Context exactly at launch is valid.
    assert (
        validate_context_window(
            launch,
            launch,
            launch,
        )
        is True
    )

    # Valid bounded retention.
    bounded_policy = RetentionPolicy(
        max_observations=1000
    )

    assert (
        validate_retention_policy(
            bounded_policy
        )
        == RetentionStatus.BOUNDED
    )

    # ------------------------------------------------------------------------
    # SUCCESS
    # ------------------------------------------------------------------------

    print("=" * 90)
    print("ARUNDA LAUNCH DATA CONTRACT v0.1")
    print("=" * 90)
    print("CONTRACT TEST RESULT : PASS")
    print("SIDE EFFECTS         : NONE")
    print("DATABASE ACCESS      : NONE")
    print("NETWORK ACCESS       : NONE")
    print("LEGACY MODIFICATION  : NONE")
    print("SYNTHETIC DATA       : FORBIDDEN")
    print("INTERPOLATION        : FORBIDDEN")
    print("FORWARD-FILL         : FORBIDDEN")
    print("BACK-FILL            : FORBIDDEN")
    print("LAUNCH BOUNDARY      : ENFORCED")
    print("PROVENANCE           : ENFORCED")
    print("CONTEXT WINDOW       : ENFORCED")
    print("RETENTION            : BOUNDED / CONFIG_REQUIRED")
    print("=" * 90)


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    run_contract_tests()