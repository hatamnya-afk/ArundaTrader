"""ARUNDA TRADER — EXECUTION INSTRUMENT POLICY v0.1.

This is the explicit execution-environment policy that produces the
provider-neutral ExecutionInstrumentSpecification.

The policy does not contain provider symbols and does not call a provider.
It states the intended execution instrument semantics for the configured
real execution environment. Provider adapters resolve those semantics
against authoritative exchange metadata.

NO NETWORK.
NO DATABASE WRITE.
NO EXCHANGE WRITE.
NO ORDER SUBMISSION.
NO EXECUTION.
"""

from __future__ import annotations

from execution_instrument_contract_v0_1 import (
    ExecutionInstrumentSpecification,
)


POLICY_VERSION = "EXECUTION_INSTRUMENT_POLICY_V0_1"
SELECTION_SOURCE = "REAL_EXECUTION_ENVIRONMENT_POLICY"

# Explicit environment policy:
# Futures execution is USDT-settled perpetual.
# This is a neutral execution semantic, NOT a provider symbol.
FUTURES_SETTLEMENT_ASSET = "USDT"
FUTURES_INSTRUMENT_TYPE = "PERPETUAL"


def build_execution_instrument_specification(
    *,
    asset: str,
    venue: str,
) -> ExecutionInstrumentSpecification:
    """Build the authoritative provider-neutral execution specification."""

    normalized_asset = str(asset).strip().upper()
    normalized_venue = str(venue).strip().upper()

    if not normalized_asset:
        raise ValueError("EXECUTION_INSTRUMENT_ASSET_INVALID")

    if normalized_venue == "FUTURES":
        return ExecutionInstrumentSpecification(
            asset=normalized_asset,
            venue="FUTURES",
            settlement_asset=FUTURES_SETTLEMENT_ASSET,
            instrument_type=FUTURES_INSTRUMENT_TYPE,
            selection_source=SELECTION_SOURCE,
            policy_version=POLICY_VERSION,
        )

    if normalized_venue == "SPOT":
        return ExecutionInstrumentSpecification(
            asset=normalized_asset,
            venue="SPOT",
            settlement_asset=None,
            instrument_type=None,
            selection_source=SELECTION_SOURCE,
            policy_version=POLICY_VERSION,
        )

    raise ValueError("EXECUTION_INSTRUMENT_VENUE_INVALID")


__all__ = [
    "POLICY_VERSION",
    "SELECTION_SOURCE",
    "FUTURES_SETTLEMENT_ASSET",
    "FUTURES_INSTRUMENT_TYPE",
    "build_execution_instrument_specification",
]
