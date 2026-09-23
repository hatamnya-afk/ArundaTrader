"""
ARUNDA TRADER
PROVIDER PREFLIGHT / DUPLICATE PROTECTION v0.1

CP46-A6

READ-ONLY PREFLIGHT CONTRACT.

NO NETWORK.
NO DATABASE WRITE.
NO EXCHANGE WRITE.
NO ORDER SUBMISSION.
NO QUANTITY CONVERSION.
NO QUANTITY MUTATION.
NO LEVERAGE CALCULATION.
NO MARGIN CALCULATION.
NO ROUNDING.

Purpose:
    Validate provider/exchange readiness using already-authoritative
    provider state supplied by the caller.

Important:
    Canonical quantity remains untouched.

    Provider-specific quantity translation is OUTSIDE this module.

    Any unknown, ambiguous, conflicting, or unavailable provider state
    produces BLOCK.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, FrozenSet, Optional


class PreflightStatus(str, Enum):
    PASS = "PASS"
    BLOCK = "BLOCK"


class PreflightReason(str, Enum):
    PASS = "PASS"

    BLOCK_REQUEST_INVALID = "BLOCK_REQUEST_INVALID"
    BLOCK_SYMBOL_INVALID = "BLOCK_SYMBOL_INVALID"
    BLOCK_DIRECTION_INVALID = "BLOCK_DIRECTION_INVALID"
    BLOCK_ORDER_TYPE_INVALID = "BLOCK_ORDER_TYPE_INVALID"
    BLOCK_QUANTITY_INVALID = "BLOCK_QUANTITY_INVALID"
    BLOCK_QUANTITY_TRANSLATION_REQUIRED = (
        "BLOCK_QUANTITY_TRANSLATION_REQUIRED"
    )

    BLOCK_SYMBOL_NOT_SUPPORTED = "BLOCK_SYMBOL_NOT_SUPPORTED"
    BLOCK_CONTRACT_STATE_UNKNOWN = "BLOCK_CONTRACT_STATE_UNKNOWN"
    BLOCK_CONTRACT_INVALID = "BLOCK_CONTRACT_INVALID"

    BLOCK_POSITION_CONFLICT = "BLOCK_POSITION_CONFLICT"
    BLOCK_DUPLICATE_ORDER = "BLOCK_DUPLICATE_ORDER"
    BLOCK_OPEN_ORDER_CONFLICT = "BLOCK_OPEN_ORDER_CONFLICT"

    BLOCK_TIMESTAMP_INVALID = "BLOCK_TIMESTAMP_INVALID"
    BLOCK_TIMESTAMP_DRIFT = "BLOCK_TIMESTAMP_DRIFT"

    BLOCK_PRECISION_INVALID = "BLOCK_PRECISION_INVALID"
    BLOCK_MIN_QUANTITY = "BLOCK_MIN_QUANTITY"
    BLOCK_MAX_QUANTITY = "BLOCK_MAX_QUANTITY"
    BLOCK_NOTIONAL_INVALID = "BLOCK_NOTIONAL_INVALID"

    BLOCK_ACCOUNT_STATE_UNKNOWN = "BLOCK_ACCOUNT_STATE_UNKNOWN"
    BLOCK_BALANCE_INSUFFICIENT = "BLOCK_BALANCE_INSUFFICIENT"
    BLOCK_MARGIN_STATE_UNKNOWN = "BLOCK_MARGIN_STATE_UNKNOWN"
    BLOCK_LEVERAGE_STATE_UNKNOWN = "BLOCK_LEVERAGE_STATE_UNKNOWN"

    BLOCK_PORTFOLIO_EXPOSURE = "BLOCK_PORTFOLIO_EXPOSURE"
    BLOCK_PROVIDER_STATE_INCONSISTENT = (
        "BLOCK_PROVIDER_STATE_INCONSISTENT"
    )


@dataclass(frozen=True)
class ProviderOrderPreflightRequest:
    symbol: str
    direction: str
    order_type: str
    quantity: Any
    quantity_unit: str

    intent_id: str
    timestamp_ms: int

    # Provider-specific semantics already resolved upstream.
    venue: str

    # Optional because not every provider/order type needs a price.
    reference_price: Optional[Any] = None


@dataclass(frozen=True)
class ProviderContractState:
    """
    Authoritative provider contract metadata.

    None means UNKNOWN and therefore blocks.

    No conversion is performed from this metadata.
    """

    symbol_valid: Optional[bool]
    contract_valid: Optional[bool]

    min_quantity: Optional[Any]
    max_quantity: Optional[Any]

    quantity_step: Optional[Any]

    min_notional: Optional[Any]
    max_notional: Optional[Any]


@dataclass(frozen=True)
class ProviderAccountState:
    """
    Authoritative account state.

    Unknown state is represented by None and fails closed.
    """

    state_known: bool

    balance_sufficient: Optional[bool]

    margin_state_known: Optional[bool]
    leverage_state_known: Optional[bool]

    position_conflict: Optional[bool]


@dataclass(frozen=True)
class ProviderOrderState:
    """
    Authoritative current/recent order state.

    Client order IDs are used for deterministic duplicate detection.
    """

    state_known: bool

    open_order_client_ids: FrozenSet[str]
    recent_order_client_ids: FrozenSet[str]


@dataclass(frozen=True)
class ProviderTimestampState:
    """
    Provider timestamp evidence.

    exchange_timestamp_ms must be authoritative provider time.

    No local clock is read by this module.
    """

    state_known: bool
    exchange_timestamp_ms: Optional[int]

    max_drift_ms: int = 5000


@dataclass(frozen=True)
class ProviderPortfolioState:
    """
    Authoritative portfolio exposure state.

    No exposure calculation is performed here.
    """

    state_known: bool
    exposure_allowed: Optional[bool]


@dataclass(frozen=True)
class ProviderPreflightEvidence:
    contract: ProviderContractState
    account: ProviderAccountState
    orders: ProviderOrderState
    timestamp: ProviderTimestampState
    portfolio: ProviderPortfolioState


@dataclass(frozen=True)
class ProviderPreflightResult:
    status: PreflightStatus
    reason: PreflightReason
    message: str


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


def _positive_decimal(value: Any) -> Optional[Decimal]:
    number = _decimal(value)

    if number is None or number <= 0:
        return None

    return number


def _quantity_step_valid(
    quantity: Decimal,
    step: Decimal,
) -> bool:
    if step <= 0:
        return False

    units = quantity / step
    return units == units.to_integral_value()


def _block(
    reason: PreflightReason,
    message: str,
) -> ProviderPreflightResult:
    return ProviderPreflightResult(
        status=PreflightStatus.BLOCK,
        reason=reason,
        message=message,
    )


def _pass() -> ProviderPreflightResult:
    return ProviderPreflightResult(
        status=PreflightStatus.PASS,
        reason=PreflightReason.PASS,
        message="Provider preflight passed.",
    )


def run_provider_preflight(
    request: ProviderOrderPreflightRequest,
    evidence: ProviderPreflightEvidence,
) -> ProviderPreflightResult:
    """
    Deterministic fail-closed provider preflight.

    This function validates only.

    It does NOT:
        - call network
        - query exchange
        - write database
        - convert quantity
        - calculate margin
        - calculate leverage
        - calculate exposure
        - round quantity
        - modify request
    """

    if not isinstance(
        request,
        ProviderOrderPreflightRequest,
    ):
        return _block(
            PreflightReason.BLOCK_REQUEST_INVALID,
            "Provider preflight request type is invalid.",
        )

    if not isinstance(
        evidence,
        ProviderPreflightEvidence,
    ):
        return _block(
            PreflightReason.BLOCK_PROVIDER_STATE_INCONSISTENT,
            "Provider preflight evidence type is invalid.",
        )

    symbol = request.symbol.strip().upper()

    if not symbol:
        return _block(
            PreflightReason.BLOCK_SYMBOL_INVALID,
            "Symbol is empty.",
        )

    if request.direction not in {"LONG", "SHORT"}:
        return _block(
            PreflightReason.BLOCK_DIRECTION_INVALID,
            "Direction must be LONG or SHORT.",
        )

    if request.order_type not in {
        "MARKET",
        "LIMIT",
    }:
        return _block(
            PreflightReason.BLOCK_ORDER_TYPE_INVALID,
            "Unsupported canonical order type.",
        )

    quantity = _positive_decimal(request.quantity)

    if quantity is None:
        return _block(
            PreflightReason.BLOCK_QUANTITY_INVALID,
            "Quantity must be a finite positive value.",
        )

    if not request.intent_id.strip():
        return _block(
            PreflightReason.BLOCK_REQUEST_INVALID,
            "Intent ID is required.",
        )

    if request.timestamp_ms <= 0:
        return _block(
            PreflightReason.BLOCK_TIMESTAMP_INVALID,
            "Request timestamp is invalid.",
        )

    # ---------------------------------------------------------
    # Canonical quantity boundary.
    # ---------------------------------------------------------
    #
    # This module never translates quantity.
    #
    # Futures provider quantity is CONTRACTS while canonical
    # Arunda quantity is BASE_ASSET.
    #
    # Therefore Futures cannot pass until an explicit translation
    # contract exists upstream.
    #

    if request.venue == "FUTURES":
        if request.quantity_unit != "CONTRACTS":
            return _block(
                PreflightReason.BLOCK_QUANTITY_TRANSLATION_REQUIRED,
                (
                    "Futures provider requires CONTRACTS, but the "
                    "supplied quantity has not been translated by "
                    "an explicit provider translation contract."
                ),
            )

    elif request.venue == "SPOT":
        if request.quantity_unit not in {
            "BASE_ASSET",
            "QUOTE_ASSET",
        }:
            return _block(
                PreflightReason.BLOCK_QUANTITY_INVALID,
                "Unsupported Spot quantity unit.",
            )

        # Toobit Spot MARKET BUY requires quote-asset quantity.
        if (
            request.order_type == "MARKET"
            and request.direction == "LONG"
            and request.quantity_unit != "QUOTE_ASSET"
        ):
            return _block(
                PreflightReason.BLOCK_QUANTITY_TRANSLATION_REQUIRED,
                (
                    "Spot MARKET BUY requires QUOTE_ASSET quantity; "
                    "no quantity conversion is permitted in preflight."
                ),
            )

    else:
        return _block(
            PreflightReason.BLOCK_PROVIDER_STATE_INCONSISTENT,
            "Unsupported execution venue.",
        )

    # ---------------------------------------------------------
    # Contract / symbol state.
    # ---------------------------------------------------------

    contract = evidence.contract

    if contract.symbol_valid is not True:
        return _block(
            PreflightReason.BLOCK_SYMBOL_NOT_SUPPORTED,
            "Provider symbol validity is not confirmed.",
        )

    if contract.contract_valid is not True:
        return _block(
            PreflightReason.BLOCK_CONTRACT_STATE_UNKNOWN,
            "Provider contract validity is not confirmed.",
        )

    # ---------------------------------------------------------
    # Quantity constraints.
    # ---------------------------------------------------------

    minimum = _positive_decimal(contract.min_quantity)

    if minimum is None:
        return _block(
            PreflightReason.BLOCK_MIN_QUANTITY,
            "Provider minimum quantity is unknown or invalid.",
        )

    if quantity < minimum:
        return _block(
            PreflightReason.BLOCK_MIN_QUANTITY,
            "Quantity is below provider minimum.",
        )

    maximum = _positive_decimal(contract.max_quantity)

    if maximum is None:
        return _block(
            PreflightReason.BLOCK_MAX_QUANTITY,
            "Provider maximum quantity is unknown or invalid.",
        )

    if quantity > maximum:
        return _block(
            PreflightReason.BLOCK_MAX_QUANTITY,
            "Quantity exceeds provider maximum.",
        )

    step = _positive_decimal(contract.quantity_step)

    if step is None:
        return _block(
            PreflightReason.BLOCK_PRECISION_INVALID,
            "Provider quantity step is unknown or invalid.",
        )

    if not _quantity_step_valid(quantity, step):
        return _block(
            PreflightReason.BLOCK_PRECISION_INVALID,
            "Quantity does not satisfy provider quantity step.",
        )

    # ---------------------------------------------------------
    # Notional.
    #
    # Preflight does NOT calculate notional.
    # It only validates an authoritative value supplied by the
    # provider contract when one exists.
    # ---------------------------------------------------------

    minimum_notional = _positive_decimal(
        contract.min_notional
    )

    maximum_notional = _positive_decimal(
        contract.max_notional
    )

    if minimum_notional is None or maximum_notional is None:
        return _block(
            PreflightReason.BLOCK_NOTIONAL_INVALID,
            "Provider notional bounds are unknown or invalid.",
        )

    # ---------------------------------------------------------
    # Position state.
    # ---------------------------------------------------------

    account = evidence.account

    if account.state_known is not True:
        return _block(
            PreflightReason.BLOCK_ACCOUNT_STATE_UNKNOWN,
            "Provider account state is unknown.",
        )

    if account.position_conflict is not False:
        return _block(
            PreflightReason.BLOCK_POSITION_CONFLICT,
            "Position state is conflicting or unknown.",
        )

    # ---------------------------------------------------------
    # Balance / margin / leverage state.
    # ---------------------------------------------------------

    if account.balance_sufficient is not True:
        return _block(
            PreflightReason.BLOCK_BALANCE_INSUFFICIENT,
            "Sufficient account balance is not confirmed.",
        )

    if account.margin_state_known is not True:
        return _block(
            PreflightReason.BLOCK_MARGIN_STATE_UNKNOWN,
            "Margin state is not confirmed.",
        )

    if account.leverage_state_known is not True:
        return _block(
            PreflightReason.BLOCK_LEVERAGE_STATE_UNKNOWN,
            "Leverage state is not confirmed.",
        )

    # ---------------------------------------------------------
    # Duplicate / open-order protection.
    # ---------------------------------------------------------

    orders = evidence.orders

    if orders.state_known is not True:
        return _block(
            PreflightReason.BLOCK_PROVIDER_STATE_INCONSISTENT,
            "Provider order state is unknown.",
        )

    intent_id = request.intent_id.strip()

    if intent_id in orders.open_order_client_ids:
        return _block(
            PreflightReason.BLOCK_OPEN_ORDER_CONFLICT,
            "Intent ID conflicts with an open provider order.",
        )

    if intent_id in orders.recent_order_client_ids:
        return _block(
            PreflightReason.BLOCK_DUPLICATE_ORDER,
            "Intent ID already exists in recent provider order state.",
        )

    # ---------------------------------------------------------
    # Exchange timestamp.
    # ---------------------------------------------------------

    timestamp = evidence.timestamp

    if timestamp.state_known is not True:
        return _block(
            PreflightReason.BLOCK_TIMESTAMP_INVALID,
            "Provider timestamp state is unknown.",
        )

    if timestamp.exchange_timestamp_ms is None:
        return _block(
            PreflightReason.BLOCK_TIMESTAMP_INVALID,
            "Authoritative provider timestamp is unavailable.",
        )

    if timestamp.exchange_timestamp_ms <= 0:
        return _block(
            PreflightReason.BLOCK_TIMESTAMP_INVALID,
            "Provider timestamp is invalid.",
        )

    drift = abs(
        request.timestamp_ms
        - timestamp.exchange_timestamp_ms
    )

    if drift > timestamp.max_drift_ms:
        return _block(
            PreflightReason.BLOCK_TIMESTAMP_DRIFT,
            "Request/provider timestamp drift exceeds policy.",
        )

    # ---------------------------------------------------------
    # Portfolio exposure.
    #
    # No exposure calculation here.
    # ---------------------------------------------------------

    portfolio = evidence.portfolio

    if portfolio.state_known is not True:
        return _block(
            PreflightReason.BLOCK_PORTFOLIO_EXPOSURE,
            "Portfolio exposure state is unknown.",
        )

    if portfolio.exposure_allowed is not True:
        return _block(
            PreflightReason.BLOCK_PORTFOLIO_EXPOSURE,
            "Portfolio exposure is not authorized.",
        )

    return _pass()


__all__ = [
    "PreflightStatus",
    "PreflightReason",
    "ProviderOrderPreflightRequest",
    "ProviderContractState",
    "ProviderAccountState",
    "ProviderOrderState",
    "ProviderTimestampState",
    "ProviderPortfolioState",
    "ProviderPreflightEvidence",
    "ProviderPreflightResult",
    "run_provider_preflight",
]