"""ARUNDA TRADER — CP46-D PRODUCTION PROVIDER PREFLIGHT ORCHESTRATOR v0.1

Production wiring boundary only.

Canonical -> CP46-C translation -> Toobit authoritative evidence -> CP46-D -> CP46-A6.
No execution, order submission, exchange write, DB write, retry, quantity mutation,
rounding, estimation, or synthetic provider state.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from cp46_d_provider_execution_handoff_v0_1 import (
    ProviderExecutionHandoffResult,
    handoff_to_provider_preflight,
)

from execution_venue_routing_policy_v0_1 import (
    RoutingReason,
    Venue,
    VenueRoutingRequest,
    route_venue,
)
from provider_order_translation_v0_1 import (
    ProviderOrderRequest,
    ProviderTranslationEvidence,
    ProviderTranslationResult,
    TranslationStatus,
    translate_order_request,
)
from provider_preflight_v0_1 import ProviderPreflightEvidence
from toobit_provider_preflight_evidence_v0_1 import (
    build_toobit_provider_preflight_evidence,
)


@dataclass(frozen=True)
class ProductionProviderPreflightResult:
    status: str
    reason: str
    message: str
    translation: Optional[ProviderTranslationResult] = None
    handoff: Optional[ProviderExecutionHandoffResult] = None


def _block(
    reason: str,
    message: str,
    *,
    translation: Optional[ProviderTranslationResult] = None,
    handoff: Optional[ProviderExecutionHandoffResult] = None,
) -> ProductionProviderPreflightResult:
    return ProductionProviderPreflightResult(
        status="BLOCK",
        reason=reason,
        message=message,
        translation=translation,
        handoff=handoff,
    )


def _provider_symbol(
    adapter: Any,
    asset: str,
    *,
    venue: str = "SPOT",
) -> str:
    if venue == "FUTURES":
        result = adapter.futures_trading_constraints(asset)
    else:
        result = adapter.trading_constraints(asset)
    if getattr(result, "allowed", False) is not True:
        raise RuntimeError(
            "AUTHORITATIVE_PROVIDER_SYMBOL_UNAVAILABLE:"
            f"{getattr(result, 'reason', 'unknown')}"
        )

    data = getattr(result, "data", None)
    symbol = data.get("symbol") if isinstance(data, dict) else None
    if not isinstance(symbol, str) or not symbol.strip():
        raise RuntimeError("AUTHORITATIVE_PROVIDER_SYMBOL_INVALID")

    return symbol.strip().upper()


def _authoritative_provider_request_timestamp(adapter: Any) -> str:
    """Capture provider time immediately before provider translation."""
    result = adapter.get_server_time()
    if getattr(result, "allowed", False) is not True:
        raise RuntimeError(
            "AUTHORITATIVE_PROVIDER_REQUEST_TIME_UNAVAILABLE:"
            f"{getattr(result, 'reason', 'unknown')}"
        )

    data = getattr(result, "data", None)
    if not isinstance(data, dict):
        raise RuntimeError(
            "AUTHORITATIVE_PROVIDER_REQUEST_TIME_INVALID"
        )

    raw = data.get("serverTime")
    if raw is None:
        raw = data.get("timestamp")

    try:
        timestamp_ms = int(raw)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(
            "AUTHORITATIVE_PROVIDER_REQUEST_TIME_INVALID"
        ) from exc

    if timestamp_ms <= 0:
        raise RuntimeError(
            "AUTHORITATIVE_PROVIDER_REQUEST_TIME_INVALID"
        )

    return str(timestamp_ms)


def build_toobit_translation_evidence(
    *,
    adapter: Any,
    canonical_request: Any,
    quote_quantity: Any = None,
    venue: str = "SPOT",
) -> ProviderTranslationEvidence:
    if adapter is None:
        raise RuntimeError("Toobit adapter is required")

    asset = str(canonical_request.asset).strip().upper()
    if not asset:
        raise RuntimeError("Canonical asset is required")

    # Provider symbol is authoritative exchange metadata. It is never
    # reconstructed from a hardcoded suffix or inferred mapping.
    symbol = _provider_symbol(adapter, asset, venue=venue)

    contract_multiplier = None
    contract_quantity_step = None
    if venue == "FUTURES":
        constraints = adapter.futures_trading_constraints(asset)
        if getattr(constraints, "allowed", False) is not True:
            raise RuntimeError(
                "AUTHORITATIVE_FUTURES_CONTRACT_STATE_UNAVAILABLE:"
                f"{getattr(constraints, 'reason', 'unknown')}"
            )
        data = getattr(constraints, "data", None)
        if not isinstance(data, dict):
            raise RuntimeError("AUTHORITATIVE_FUTURES_CONTRACT_STATE_INVALID")
        contract_multiplier = data.get("contract_multiplier")
        filters = data.get("filters")
        if not isinstance(filters, dict):
            raise RuntimeError("AUTHORITATIVE_FUTURES_CONTRACT_FILTERS_INVALID")
        lot = filters.get("LOT_SIZE") or filters.get("MARKET_LOT_SIZE")
        if not isinstance(lot, dict):
            raise RuntimeError("AUTHORITATIVE_FUTURES_QUANTITY_FILTER_UNAVAILABLE")
        raw_step = lot.get("stepSize")
        if raw_step is None:
            raise RuntimeError("AUTHORITATIVE_FUTURES_QUANTITY_STEP_UNAVAILABLE")
        from decimal import Decimal, InvalidOperation
        try:
            multiplier = Decimal(str(contract_multiplier))
            step = Decimal(str(raw_step))
        except (InvalidOperation, ValueError) as exc:
            raise RuntimeError("AUTHORITATIVE_FUTURES_QUANTITY_STATE_INVALID") from exc
        if multiplier <= 0 or step <= 0:
            raise RuntimeError("AUTHORITATIVE_FUTURES_QUANTITY_STATE_INVALID")
        contract_quantity_step = str(step / multiplier)

    # For Spot MARKET BUY, quote_quantity is supplied by the already-
    # authoritative Risk.position exposure output. The provider boundary
    # transports that value; it never derives it from price.
    #
    # Decision-Birth timestamp is preserved upstream as identity/history.
    # Provider preflight instead receives a fresh authoritative provider
    # timestamp so a long-running pipeline cannot fail the 5s drift guard
    # merely because Decision Birth occurred several seconds earlier.
    provider_request_timestamp = _authoritative_provider_request_timestamp(
        adapter
    )
    return ProviderTranslationEvidence(
        provider_symbol=symbol,
        quote_quantity=quote_quantity,
        contract_multiplier=contract_multiplier,
        contract_quantity_step=contract_quantity_step,
        provider_request_timestamp=provider_request_timestamp,
    )


def translate_and_preflight_toobit(
    *,
    canonical_request: Any,
    adapter: Any,
    quote_quantity: Any = None,
) -> ProductionProviderPreflightResult:
    if adapter is None:
        return _block(
            "TOOBIT_ADAPTER_MISSING",
            "Toobit adapter is required.",
        )

    # CP46-A3 is the authoritative venue-routing boundary.
    # SHORT is Futures-only; never reinterpret it as Spot SELL.
    # Futures readiness is established only when the adapter exposes both
    # authoritative Futures contract and account read boundaries.
    direction = str(
        getattr(canonical_request, "direction", "")
    ).strip().upper()
    futures_ready = False

    if (
        callable(getattr(adapter, "futures_trading_constraints", None))
        and callable(getattr(adapter, "futures_account_state", None))
    ):
        try:
            futures_constraints = adapter.futures_trading_constraints(
                canonical_request.asset
            )

            if getattr(futures_constraints, "allowed", False) is True:
                futures_account = adapter.futures_account_state(
                    canonical_request.asset
                )

                if getattr(futures_account, "allowed", False) is not True:
                    return _block(
                        "AUTHORITATIVE_PROVIDER_STATE_UNAVAILABLE",
                        str(
                            getattr(
                                futures_account,
                                "reason",
                                "FUTURES_ACCOUNT_UNAVAILABLE",
                            )
                        ),
                    )

                futures_ready = True

        except Exception as exc:
            return _block(
                "AUTHORITATIVE_PROVIDER_STATE_UNAVAILABLE",
                str(exc),
            )

    routing = route_venue(
        VenueRoutingRequest(
            direction=direction,
            spot_ready=True,
            futures_ready=futures_ready,
        )
    )
    if routing.venue is Venue.NONE:
        return _block(
            routing.reason.value,
            (
                "CP46-A3 venue routing blocked the canonical request. "
                f"routing_reason={routing.reason.value}"
            ),
        )
    try:
        venue = routing.venue.value
        evidence = build_toobit_translation_evidence(
            adapter=adapter,
            canonical_request=canonical_request,
            quote_quantity=quote_quantity,
            venue=venue,
        )

        translation = translate_order_request(
            canonical_request,
            evidence,
            venue=venue,
        )
    except Exception as exc:
        return _block(
            "AUTHORITATIVE_PROVIDER_STATE_UNAVAILABLE",
            str(exc),
        )

    if translation.status != TranslationStatus.PASS:
        return _block(
            "CP46_C_TRANSLATION_BLOCKED",
            translation.message,
            translation=translation,
        )

    # CP46-D remains the sole owner of ProviderOrderRequest -> A6 adaptation.
    try:
        provider_evidence: ProviderPreflightEvidence = (
            build_toobit_provider_preflight_evidence(
                adapter=adapter,
                asset=canonical_request.asset,
                venue=venue,
            )
        )

        handoff = handoff_to_provider_preflight(
            translation,
            provider_evidence,
        )
    except Exception as exc:
        return _block(
            "AUTHORITATIVE_PROVIDER_STATE_UNAVAILABLE",
            str(exc),
            translation=translation,
        )

    if handoff.status != "PASS":
        return _block(
            "CP46_D_PREFLIGHT_BLOCKED",
            handoff.message,
            translation=translation,
            handoff=handoff,
        )

    return ProductionProviderPreflightResult(
        status="PASS",
        reason="CP46_D_PROVIDER_PREFLIGHT_PASS",
        message="CP46-C translation and CP46-D provider preflight passed.",
        translation=translation,
        handoff=handoff,
    )


__all__ = [
    "ProductionProviderPreflightResult",
    "build_toobit_translation_evidence",
    "translate_and_preflight_toobit",
]