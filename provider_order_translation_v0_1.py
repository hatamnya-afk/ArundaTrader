"""
ARUNDA TRADER
PROVIDER ORDER TRANSLATION CONTRACT v0.1

CP46-C

Provider-specific translation only.

NO NETWORK.
NO DATABASE WRITE.
NO EXCHANGE WRITE.
NO ORDER SUBMISSION.
NO EXECUTION.

Rules:
- CanonicalOrderRequest is never mutated.
- Canonical quantity remains BASE_ASSET.
- Spot LIMIT LONG may translate directly to BASE_ASSET.
- Spot MARKET LONG requires QUOTE_ASSET and therefore blocks unless
  an already-authoritative quote quantity exists.
- SHORT routes only to Futures.
- Futures BASE_ASSET -> CONTRACTS requires an authoritative
  contract_multiplier.
- No estimation.
- No forced rounding.
- No symbol reconstruction.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, Optional

from exchange_execution_contract import CanonicalOrderRequest


class TranslationStatus(str, Enum):
    PASS = "PASS"
    BLOCK = "BLOCK"


class TranslationReason(str, Enum):
    PASS = "PASS"
    INVALID_REQUEST = "INVALID_REQUEST"
    UNSUPPORTED_ROUTE = "UNSUPPORTED_ROUTE"
    SYMBOL_MAPPING_REQUIRED = "SYMBOL_MAPPING_REQUIRED"
    SYMBOL_MAPPING_INVALID = "SYMBOL_MAPPING_INVALID"
    QUANTITY_INVALID = "QUANTITY_INVALID"
    QUANTITY_TRANSLATION_REQUIRED = "QUANTITY_TRANSLATION_REQUIRED"
    CONTRACT_MULTIPLIER_REQUIRED = "CONTRACT_MULTIPLIER_REQUIRED"
    CONTRACT_MULTIPLIER_INVALID = "CONTRACT_MULTIPLIER_INVALID"
    CONTRACT_QUANTITY_INVALID = "CONTRACT_QUANTITY_INVALID"
    CONTRACT_QUANTITY_PRECISION_INVALID = (
        "CONTRACT_QUANTITY_PRECISION_INVALID"
    )
    MARKET_BUY_QUOTE_QUANTITY_REQUIRED = (
        "MARKET_BUY_QUOTE_QUANTITY_REQUIRED"
    )
    PRICE_REQUIRED = "PRICE_REQUIRED"


@dataclass(frozen=True)
class ProviderTranslationEvidence:
    provider_symbol: Optional[str]

    # Required only for Futures BASE_ASSET -> CONTRACTS.
    #
    # Meaning:
    #   base-asset quantity represented by one provider contract.
    contract_multiplier: Optional[Any] = None

    # Authoritative provider quantity step for Futures contracts.
    contract_quantity_step: Optional[Any] = None

    # Already-authoritative provider quote quantity.
    #
    # This is deliberately optional. The translator never derives
    # quote quantity from an estimated/reference market price.
    quote_quantity: Optional[Any] = None


@dataclass(frozen=True)
class ProviderOrderRequest:
    venue: str
    symbol: str
    side: str
    position_side: Optional[str]
    order_type: str
    quantity: Any
    quantity_unit: str
    entry_price: Optional[Any]
    intent_id: str
    snapshot_id: str
    timestamp: str


@dataclass(frozen=True)
class ProviderTranslationResult:
    status: TranslationStatus
    reason: TranslationReason
    message: str
    request: Optional[ProviderOrderRequest] = None


def _decimal(value: Any) -> Optional[Decimal]:
    if value is None or isinstance(value, bool):
        return None

    try:
        value = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None

    if not value.is_finite():
        return None

    return value


def _positive(value: Any) -> Optional[Decimal]:
    number = _decimal(value)

    if number is None or number <= 0:
        return None

    return number


def _step_valid(
    quantity: Decimal,
    step: Decimal,
) -> bool:
    if step <= 0:
        return False

    units = quantity / step
    return units == units.to_integral_value()


def _block(
    reason: TranslationReason,
    message: str,
) -> ProviderTranslationResult:
    return ProviderTranslationResult(
        status=TranslationStatus.BLOCK,
        reason=reason,
        message=message,
        request=None,
    )


def translate_order_request(
    canonical: CanonicalOrderRequest,
    evidence: ProviderTranslationEvidence,
    *,
    venue: str,
) -> ProviderTranslationResult:
    """
    Translate a canonical request into an explicit provider request.

    The canonical request is never modified.

    No provider I/O occurs.
    """

    if not isinstance(canonical, CanonicalOrderRequest):
        return _block(
            TranslationReason.INVALID_REQUEST,
            "CanonicalOrderRequest is required.",
        )

    if not isinstance(evidence, ProviderTranslationEvidence):
        return _block(
            TranslationReason.INVALID_REQUEST,
            "ProviderTranslationEvidence is required.",
        )

    if venue not in {"SPOT", "FUTURES"}:
        return _block(
            TranslationReason.UNSUPPORTED_ROUTE,
            "Unsupported provider venue.",
        )

    if not canonical.asset.strip():
        return _block(
            TranslationReason.INVALID_REQUEST,
            "Canonical asset is required.",
        )

    if canonical.direction not in {"LONG", "SHORT"}:
        return _block(
            TranslationReason.INVALID_REQUEST,
            "Canonical direction must be LONG or SHORT.",
        )

    if canonical.quantity_unit != "BASE_ASSET":
        return _block(
            TranslationReason.QUANTITY_TRANSLATION_REQUIRED,
            "Canonical quantity must originate as BASE_ASSET.",
        )

    quantity = _positive(canonical.quantity)

    if quantity is None:
        return _block(
            TranslationReason.QUANTITY_INVALID,
            "Canonical quantity must be finite and positive.",
        )

    provider_symbol = evidence.provider_symbol

    if not isinstance(provider_symbol, str):
        return _block(
            TranslationReason.SYMBOL_MAPPING_REQUIRED,
            "Authoritative provider symbol mapping is required.",
        )

    provider_symbol = provider_symbol.strip().upper()

    if not provider_symbol:
        return _block(
            TranslationReason.SYMBOL_MAPPING_INVALID,
            "Provider symbol mapping is empty.",
        )

    # ---------------------------------------------------------
    # SPOT
    # ---------------------------------------------------------

    if venue == "SPOT":
        # SHORT is never represented as Spot SELL.
        if canonical.direction != "LONG":
            return _block(
                TranslationReason.UNSUPPORTED_ROUTE,
                "SHORT cannot be translated to Spot.",
            )

        if canonical.order_type == "MARKET":
            # Toobit Spot MARKET BUY requires quote-asset quantity.
            #
            # Never derive quote quantity from reference_price:
            # that would be an estimation of executable value.
            quote_quantity = _positive(
                evidence.quote_quantity
            )

            if quote_quantity is None:
                return _block(
                    TranslationReason.MARKET_BUY_QUOTE_QUANTITY_REQUIRED,
                    (
                        "Spot MARKET BUY requires authoritative "
                        "QUOTE_ASSET quantity; no price-based "
                        "conversion is permitted."
                    ),
                )

            request = ProviderOrderRequest(
                venue="SPOT",
                symbol=provider_symbol,
                side="BUY",
                position_side=None,
                order_type="MARKET",
                quantity=quote_quantity,
                quantity_unit="QUOTE_ASSET",
                entry_price=None,
                intent_id=canonical.intent_id,
                snapshot_id=canonical.snapshot_id,
                timestamp=canonical.timestamp,
            )

            return ProviderTranslationResult(
                status=TranslationStatus.PASS,
                reason=TranslationReason.PASS,
                message="Spot MARKET BUY translated from authoritative quote quantity.",
                request=request,
            )

        if canonical.order_type != "LIMIT":
            return _block(
                TranslationReason.UNSUPPORTED_ROUTE,
                "Unsupported Spot order type.",
            )

        if canonical.entry_price is None:
            return _block(
                TranslationReason.PRICE_REQUIRED,
                "Spot LIMIT requires canonical entry price.",
            )

        request = ProviderOrderRequest(
            venue="SPOT",
            symbol=provider_symbol,
            side="BUY",
            position_side=None,
            order_type="LIMIT",
            quantity=canonical.quantity,
            quantity_unit="BASE_ASSET",
            entry_price=canonical.entry_price,
            intent_id=canonical.intent_id,
            snapshot_id=canonical.snapshot_id,
            timestamp=canonical.timestamp,
        )

        return ProviderTranslationResult(
            status=TranslationStatus.PASS,
            reason=TranslationReason.PASS,
            message="Spot LIMIT LONG translated without quantity mutation.",
            request=request,
        )

    # ---------------------------------------------------------
    # FUTURES
    # ---------------------------------------------------------

    if canonical.order_type not in {"LIMIT", "MARKET"}:
        return _block(
            TranslationReason.UNSUPPORTED_ROUTE,
            "Unsupported Futures order type.",
        )

    multiplier = _positive(evidence.contract_multiplier)

    if multiplier is None:
        return _block(
            TranslationReason.CONTRACT_MULTIPLIER_REQUIRED,
            (
                "Authoritative Futures contract multiplier is required "
                "for BASE_ASSET to CONTRACTS translation."
            ),
        )

    contracts = quantity / multiplier

    if contracts <= 0 or not contracts.is_finite():
        return _block(
            TranslationReason.CONTRACT_QUANTITY_INVALID,
            "Translated Futures contract quantity is invalid.",
        )

    step = _positive(evidence.contract_quantity_step)

    if step is None:
        return _block(
            TranslationReason.CONTRACT_QUANTITY_PRECISION_INVALID,
            "Authoritative Futures contract quantity step is required.",
        )

    if not _step_valid(contracts, step):
        return _block(
            TranslationReason.CONTRACT_QUANTITY_PRECISION_INVALID,
            (
                "Translated Futures quantity does not satisfy the "
                "authoritative provider contract step."
            ),
        )

    if canonical.direction == "LONG":
        side = "BUY"
        position_side = "LONG"
    else:
        side = "SELL"
        position_side = "SHORT"

    request = ProviderOrderRequest(
        venue="FUTURES",
        symbol=provider_symbol,
        side=side,
        position_side=position_side,
        order_type=canonical.order_type,
        quantity=contracts,
        quantity_unit="CONTRACTS",
        entry_price=canonical.entry_price,
        intent_id=canonical.intent_id,
        snapshot_id=canonical.snapshot_id,
        timestamp=canonical.timestamp,
    )

    return ProviderTranslationResult(
        status=TranslationStatus.PASS,
        reason=TranslationReason.PASS,
        message=(
            "Futures request translated using authoritative "
            "contract multiplier."
        ),
        request=request,
    )


__all__ = [
    "TranslationStatus",
    "TranslationReason",
    "ProviderTranslationEvidence",
    "ProviderOrderRequest",
    "ProviderTranslationResult",
    "translate_order_request",
]