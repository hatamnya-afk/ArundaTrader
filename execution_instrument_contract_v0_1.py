"""ARUNDA TRADER — PROVIDER-NEUTRAL EXECUTION INSTRUMENT CONTRACT v0.1.

This contract defines the execution instrument specification before any
provider-specific symbol is selected.

NO NETWORK.
NO DATABASE WRITE.
NO EXCHANGE WRITE.
NO ORDER SUBMISSION.
NO EXECUTION.

The Core never carries a provider symbol. A provider adapter receives this
neutral specification and resolves it against authoritative provider
metadata. Zero or multiple valid matches fail closed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional


_VALID_VENUES = frozenset({"SPOT", "FUTURES"})
_VALID_INSTRUMENT_TYPES = frozenset({"PERPETUAL", "DELIVERY"})
_FORBIDDEN_SOURCES = frozenset({"TEST", "SIMULATED", "LEGACY"})


class InstrumentResolutionStatus:
    RESOLVED = "RESOLVED"
    BLOCK = "BLOCK"


class InstrumentResolutionReason:
    RESOLVED = "RESOLVED"
    SPEC_INVALID = "EXECUTION_INSTRUMENT_SPEC_INVALID"
    CANDIDATES_INVALID = "PROVIDER_INSTRUMENT_CANDIDATES_INVALID"
    NOT_FOUND = "AUTHORITATIVE_PROVIDER_INSTRUMENT_NOT_FOUND"
    AMBIGUOUS = "AUTHORITATIVE_PROVIDER_INSTRUMENT_AMBIGUOUS"


@dataclass(frozen=True)
class ExecutionInstrumentSpecification:
    """Provider-neutral execution instrument selection.

    settlement_asset is the neutral settlement/margin asset requested by an
    already-authoritative execution policy. It is NOT a provider symbol.
    """

    asset: str
    venue: str
    settlement_asset: Optional[str]
    instrument_type: Optional[str]
    selection_source: str
    policy_version: str


@dataclass(frozen=True)
class InstrumentResolutionResult:
    status: str
    reason: str
    provider_symbol: Optional[str] = None
    observation: Optional[Mapping[str, Any]] = None


def validate_execution_instrument(
    specification: ExecutionInstrumentSpecification,
) -> tuple[bool, str]:
    if not isinstance(
        specification,
        ExecutionInstrumentSpecification,
    ):
        return False, InstrumentResolutionReason.SPEC_INVALID

    asset = specification.asset.strip().upper()
    if not asset:
        return False, "EXECUTION_INSTRUMENT_ASSET_INVALID"

    venue = specification.venue.strip().upper()
    if venue not in _VALID_VENUES:
        return False, "EXECUTION_INSTRUMENT_VENUE_INVALID"

    settlement = specification.settlement_asset
    if venue == "FUTURES":
        if not isinstance(settlement, str) or not settlement.strip():
            return False, "EXECUTION_INSTRUMENT_SETTLEMENT_ASSET_REQUIRED"

    if settlement is not None:
        if not isinstance(settlement, str) or not settlement.strip():
            return False, "EXECUTION_INSTRUMENT_SETTLEMENT_ASSET_INVALID"

    instrument_type = specification.instrument_type
    if instrument_type is not None:
        if (
            not isinstance(instrument_type, str)
            or instrument_type.strip().upper() not in _VALID_INSTRUMENT_TYPES
        ):
            return False, "EXECUTION_INSTRUMENT_TYPE_INVALID"

    source = specification.selection_source
    if not isinstance(source, str) or not source.strip():
        return False, "EXECUTION_INSTRUMENT_SOURCE_INVALID"
    if source.strip().upper() in _FORBIDDEN_SOURCES:
        return False, "EXECUTION_INSTRUMENT_SOURCE_INVALID"

    version = specification.policy_version
    if not isinstance(version, str) or not version.strip():
        return False, "EXECUTION_INSTRUMENT_POLICY_VERSION_INVALID"

    return True, "VALID"


def resolve_provider_instrument(
    specification: ExecutionInstrumentSpecification,
    candidates: list[Mapping[str, Any]],
) -> InstrumentResolutionResult:
    """Resolve a neutral specification against normalized provider metadata.

    Each candidate must expose:
        asset
        venue
        settlement_asset
        provider_symbol
        status

    Optional:
        instrument_type

    Provider-specific parsing belongs exclusively in the adapter that
    constructs these normalized observations.
    """

    valid, reason = validate_execution_instrument(specification)
    if not valid:
        return InstrumentResolutionResult(
            status=InstrumentResolutionStatus.BLOCK,
            reason=reason,
        )

    if not isinstance(candidates, list):
        return InstrumentResolutionResult(
            status=InstrumentResolutionStatus.BLOCK,
            reason=InstrumentResolutionReason.CANDIDATES_INVALID,
        )

    target_asset = specification.asset.strip().upper()
    target_venue = specification.venue.strip().upper()
    target_settlement = (
        specification.settlement_asset.strip().upper()
        if specification.settlement_asset is not None
        else None
    )
    target_type = (
        specification.instrument_type.strip().upper()
        if specification.instrument_type is not None
        else None
    )

    matches: list[Mapping[str, Any]] = []

    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            return InstrumentResolutionResult(
                status=InstrumentResolutionStatus.BLOCK,
                reason=InstrumentResolutionReason.CANDIDATES_INVALID,
            )

        symbol = candidate.get("provider_symbol")
        asset = candidate.get("asset")
        venue = candidate.get("venue")
        settlement = candidate.get("settlement_asset")
        status = candidate.get("status")

        if not all(
            isinstance(value, str) and value.strip()
            for value in (symbol, asset, venue, settlement, status)
        ):
            return InstrumentResolutionResult(
                status=InstrumentResolutionStatus.BLOCK,
                reason=InstrumentResolutionReason.CANDIDATES_INVALID,
            )

        if status.strip().upper() != "TRADING":
            continue

        if asset.strip().upper() != target_asset:
            continue

        if venue.strip().upper() != target_venue:
            continue

        if target_settlement is not None:
            if settlement.strip().upper() != target_settlement:
                continue

        if target_type is not None:
            candidate_type = candidate.get("instrument_type")
            if (
                not isinstance(candidate_type, str)
                or candidate_type.strip().upper() != target_type
            ):
                continue

        matches.append(candidate)

    if len(matches) == 0:
        return InstrumentResolutionResult(
            status=InstrumentResolutionStatus.BLOCK,
            reason=InstrumentResolutionReason.NOT_FOUND,
        )

    if len(matches) != 1:
        return InstrumentResolutionResult(
            status=InstrumentResolutionStatus.BLOCK,
            reason=InstrumentResolutionReason.AMBIGUOUS,
        )

    winner = matches[0]
    return InstrumentResolutionResult(
        status=InstrumentResolutionStatus.RESOLVED,
        reason=InstrumentResolutionReason.RESOLVED,
        provider_symbol=str(winner["provider_symbol"]).strip().upper(),
        observation=winner,
    )


__all__ = [
    "ExecutionInstrumentSpecification",
    "InstrumentResolutionResult",
    "InstrumentResolutionStatus",
    "InstrumentResolutionReason",
    "validate_execution_instrument",
    "resolve_provider_instrument",
]
