"""Explicitly opt-in Toobit submission adapter candidate.

The existing ToobitExchangeAdapter remains read-only. This subclass is a
separate, opt-in boundary for controlled technical validation only. It never
retries a POST. A transport exception after POST begins is ambiguous and is
reported as SUBMISSION_UNKNOWN; callers must reconcile by client order ID and
must not retry automatically. Default capability remains disabled.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from exchange_execution_adapter_contract_v0_1 import (
    AdapterOrderPreparation,
    ExchangeAdapterCapabilities,
)
from exchange_execution_contract import (
    CanonicalExecutionResult,
    CanonicalOrderRequest,
    blocked_execution_result,
)
from toobit_exchange_adapter_v0_1 import ToobitExchangeAdapter


class ToobitControlledExecutionAdapter(ToobitExchangeAdapter):
    """Separate opt-in submission adapter; disabled unless explicitly enabled."""

    def __init__(self, *, allow_order_submission: bool = False, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        if not isinstance(allow_order_submission, bool):
            raise ValueError("ORDER_SUBMISSION_OPT_IN_MUST_BE_BOOLEAN")
        self._allow_order_submission = allow_order_submission

    def capabilities(self) -> ExchangeAdapterCapabilities:
        base = super().capabilities()
        return ExchangeAdapterCapabilities(
            venue_discovery=base.venue_discovery,
            instrument_resolution=base.instrument_resolution,
            constraint_read=base.constraint_read,
            account_read=base.account_read,
            order_state_read=base.order_state_read,
            order_submission=self._allow_order_submission,
            order_cancellation=False,
        )

    @staticmethod
    def _provider_status(data: Mapping[str, Any]) -> str:
        raw = data.get("status")
        if isinstance(raw, str) and raw.strip():
            return raw.strip().upper()
        # Do not infer acceptance or a fill from the mere presence of orderId.
        return "SUBMISSION_UNKNOWN"

    def submit_prepared_order(
        self,
        preparation: AdapterOrderPreparation,
        *,
        canonical_request: CanonicalOrderRequest,
    ) -> CanonicalExecutionResult:
        if not self._allow_order_submission:
            return blocked_execution_result(
                asset=canonical_request.asset,
                direction=canonical_request.direction,
                adapter=self.name,
                error_code="ORDER_SUBMISSION_OPT_IN_REQUIRED",
                error_message="Controlled Toobit submission is disabled by default.",
            )
        if not isinstance(preparation, AdapterOrderPreparation) or not preparation.ready:
            return blocked_execution_result(
                asset=canonical_request.asset,
                direction=canonical_request.direction,
                adapter=self.name,
                error_code="ORDER_PREPARATION_NOT_READY",
            )
        if preparation.adapter_name != self.adapter_name:
            return blocked_execution_result(
                asset=canonical_request.asset,
                direction=canonical_request.direction,
                adapter=self.name,
                error_code="ORDER_PREPARATION_ADAPTER_MISMATCH",
            )
        venue = str(preparation.venue).strip().upper()
        if venue not in {"SPOT", "FUTURES"}:
            return blocked_execution_result(
                asset=canonical_request.asset,
                direction=canonical_request.direction,
                adapter=self.name,
                error_code="EXECUTION_INSTRUMENT_VENUE_INVALID",
            )
        payload = preparation.request
        if not isinstance(payload, Mapping):
            return blocked_execution_result(
                asset=canonical_request.asset,
                direction=canonical_request.direction,
                adapter=self.name,
                error_code="PROVIDER_ORDER_PAYLOAD_INVALID",
            )
        if payload.get("newClientOrderId") != canonical_request.intent_id:
            return blocked_execution_result(
                asset=canonical_request.asset,
                direction=canonical_request.direction,
                adapter=self.name,
                error_code="CLIENT_ORDER_ID_MISMATCH",
            )
        if not isinstance(payload.get("symbol"), str) or not payload.get("symbol", "").strip():
            return blocked_execution_result(
                asset=canonical_request.asset,
                direction=canonical_request.direction,
                adapter=self.name,
                error_code="PROVIDER_SYMBOL_MISSING",
            )

        # One POST only. Never retry an ambiguous write.
        path = "/api/v1/spot/order" if venue == "SPOT" else "/api/v2/futures/order"
        try:
            response = self._call("POST", path, params=payload, signed=True)
        except Exception as exc:
            return CanonicalExecutionResult(
                accepted=False,
                exchange_order_id=None,
                status="SUBMISSION_UNKNOWN",
                asset=canonical_request.asset,
                direction=canonical_request.direction,
                executed_quantity=None,
                executed_price=None,
                timestamp=None,
                adapter=self.name,
                error_code="PROVIDER_SUBMISSION_OUTCOME_AMBIGUOUS",
                error_message=f"{type(exc).__name__}: {exc}; reconcile by client order ID; do not retry.",
                trade_event_id=None,
            )

        try:
            data = self._unwrap(response)
        except Exception as exc:
            return CanonicalExecutionResult(
                accepted=False,
                exchange_order_id=None,
                status="PROVIDER_REJECTED",
                asset=canonical_request.asset,
                direction=canonical_request.direction,
                executed_quantity=None,
                executed_price=None,
                timestamp=None,
                adapter=self.name,
                error_code="PROVIDER_REJECTED",
                error_message=str(exc),
                trade_event_id=None,
            )
        if not isinstance(data, Mapping):
            return CanonicalExecutionResult(
                accepted=False,
                exchange_order_id=None,
                status="SUBMISSION_UNKNOWN",
                asset=canonical_request.asset,
                direction=canonical_request.direction,
                executed_quantity=None,
                executed_price=None,
                timestamp=None,
                adapter=self.name,
                error_code="PROVIDER_RESPONSE_INVALID",
                error_message="Provider response was not an object; reconcile by client order ID; do not retry.",
                trade_event_id=None,
            )

        status = self._provider_status(data)
        order_id = data.get("orderId")
        # Only explicit provider execution fields are accepted; order price is
        # never copied into executed_price. Provider timestamps only.
        executed_quantity = data.get("executedQty")
        executed_price = data.get("avgPrice")
        if executed_price is None:
            executed_price = data.get("averagePrice")
        raw_timestamp = data.get("updateTime", data.get("transactTime", data.get("time")))
        timestamp = None
        if raw_timestamp is not None:
            try:
                stamp = int(raw_timestamp)
                if stamp > 0:
                    timestamp = datetime.fromtimestamp(stamp / 1000, tz=timezone.utc).isoformat().replace("+00:00", "Z")
            except (TypeError, ValueError, OverflowError, OSError):
                timestamp = None
        accepted = bool(order_id) and status not in {"REJECTED", "PROVIDER_REJECTED", "SUBMISSION_UNKNOWN"}
        return CanonicalExecutionResult(
            accepted=accepted,
            exchange_order_id=None if order_id is None else str(order_id),
            status=status,
            asset=canonical_request.asset,
            direction=canonical_request.direction,
            executed_quantity=executed_quantity,
            executed_price=executed_price,
            timestamp=timestamp,
            adapter=self.name,
            error_code=None if accepted else "PROVIDER_ACCEPTANCE_NOT_CONFIRMED",
            error_message=None if accepted else "Acceptance is not confirmed; reconcile by client order ID.",
            trade_event_id=None,
        )

    def submit_order(self, request: CanonicalOrderRequest) -> CanonicalExecutionResult:
        # Prevent bypassing canonical preparation/instrument constraints.
        return blocked_execution_result(
            asset=getattr(request, "asset", None),
            direction=getattr(request, "direction", None),
            adapter=self.name,
            error_code="PREPARED_ORDER_BOUNDARY_REQUIRED",
            error_message="Use the authorized prepared-order boundary only.",
        )


__all__ = ["ToobitControlledExecutionAdapter"]
