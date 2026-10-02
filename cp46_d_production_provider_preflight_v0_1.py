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


def _provider_symbol(adapter: Any, asset: str) -> str:
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


def build_toobit_translation_evidence(
    *,
    adapter: Any,
    canonical_request: Any,
) -> ProviderTranslationEvidence:
    if adapter is None:
        raise RuntimeError("Toobit adapter is required")

    asset = str(canonical_request.asset).strip().upper()
    if not asset:
        raise RuntimeError("Canonical asset is required")

    # Provider symbol is authoritative exchange metadata. It is never
    # reconstructed from a hardcoded suffix or inferred mapping.
    symbol = _provider_symbol(adapter, asset)

    # Spot MARKET BUY requires an already-authoritative quote quantity.
    # No producer currently exists for this value; therefore None is
    # intentional and CP46-C fails closed rather than estimating it.
    return ProviderTranslationEvidence(
        provider_symbol=symbol,
        quote_quantity=None,
    )


def translate_and_preflight_toobit(
    *,
    canonical_request: Any,
    adapter: Any,
) -> ProductionProviderPreflightResult:
    if adapter is None:
        return _block(
            "TOOBIT_ADAPTER_MISSING",
            "Toobit adapter is required.",
        )

    evidence = build_toobit_translation_evidence(
        adapter=adapter,
        canonical_request=canonical_request,
    )

    translation = translate_order_request(
        canonical_request,
        evidence,
        venue="SPOT",
    )

    if translation.status != TranslationStatus.PASS:
        return _block(
            "CP46_C_TRANSLATION_BLOCKED",
            translation.message,
            translation=translation,
        )

    # CP46-D remains the sole owner of ProviderOrderRequest -> A6 adaptation.
    provider_evidence: ProviderPreflightEvidence = (
        build_toobit_provider_preflight_evidence(
            adapter=adapter,
            asset=canonical_request.asset,
        )
    )

    handoff = handoff_to_provider_preflight(
        translation,
        provider_evidence,
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
