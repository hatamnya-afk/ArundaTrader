"""Execution attempt -> outcome evidence bridge v0.1.

This bridge consumes the canonical result returned by the existing final
execution-attempt contract. It never submits, retries, cancels, or queries an
exchange. A provider response is persisted only when it carries the identity
and timestamp required to make an auditable record.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from exchange_execution_contract import CanonicalExecutionResult, CanonicalOrderRequest
from final_execution_attempt_contract_v0_1 import run_final_execution_attempt_contract
from execution_outcome_evidence_contract_v0_1 import (
    append_execution_outcome_record,
    build_execution_outcome_record,
    build_outcome_record_from_canonical_result,
)


@dataclass(frozen=True)
class OutcomeCaptureResult:
    execution_result: CanonicalExecutionResult
    capture_state: str
    event_id: str | None = None
    reason: str | None = None
    stream_path: str | None = None


def _observation_id(result: CanonicalExecutionResult) -> str:
    material = {
        "adapter": result.adapter,
        "status": result.status,
        "exchange_order_id": result.exchange_order_id,
        "timestamp": result.timestamp,
        "executed_quantity": (
            None if result.executed_quantity is None else str(result.executed_quantity)
        ),
        "executed_price": (
            None if result.executed_price is None else str(result.executed_price)
        ),
        "error_code": result.error_code,
    }
    encoded = json.dumps(material, sort_keys=True, separators=(",", ":"))
    return "OBS-" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def capture_execution_attempt_outcome(
    *,
    request: CanonicalOrderRequest,
    result: CanonicalExecutionResult,
    stream_path: Path,
    attempt_observed_at: str | None = None,
) -> OutcomeCaptureResult:
    """Persist provider facts, or a distinct local-clock event for ambiguous attempts."""
    if not isinstance(result, CanonicalExecutionResult):
        raise ValueError("CANONICAL_EXECUTION_RESULT_INVALID")
    if not isinstance(request, CanonicalOrderRequest):
        raise ValueError("CANONICAL_ORDER_REQUEST_INVALID")

    # Contract-level fail-closed results are not exchange/provider outcomes.
    if result.status.strip().upper() == "FAIL_CLOSED":
        return OutcomeCaptureResult(
            execution_result=result,
            capture_state="NOT_CAPTURED",
            reason="NO_PROVIDER_RESPONSE_FAIL_CLOSED_BOUNDARY_RESULT",
            stream_path=str(stream_path),
        )
    if not result.trade_event_id:
        return OutcomeCaptureResult(
            execution_result=result,
            capture_state="NOT_CAPTURED",
            reason="TRADE_EVENT_ID_MISSING",
            stream_path=str(stream_path),
        )
    if not request.decision_id:
        return OutcomeCaptureResult(
            execution_result=result,
            capture_state="NOT_CAPTURED",
            reason="AUTHORITATIVE_DECISION_ID_MISSING",
            stream_path=str(stream_path),
        )

    if result.status.strip().upper() == "SUBMISSION_UNKNOWN" and not result.timestamp:
        # This is a local observation of an ambiguous attempt, not a provider
        # timestamp or a claim that the exchange accepted/rejected the order.
        local_observed_at = attempt_observed_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        source_material = f"{_observation_id(result)}|{local_observed_at}"
        source_id = "ATTEMPT-" + hashlib.sha256(source_material.encode("utf-8")).hexdigest()
        record = build_execution_outcome_record(
            provider=result.adapter or "PROVIDER_UNKNOWN",
            decision_id=request.decision_id,
            intent_id=request.intent_id,
            trade_event_id=result.trade_event_id,
            client_order_id=request.intent_id,
            source_observation_id=source_id,
            source_kind="ATTEMPT_EVENT",
            provider_status="SUBMISSION_UNKNOWN",
            observed_at=local_observed_at,
            exchange_order_id=None,
            executed_quantity=None,
            executed_price=None,
            attempt_error_code=result.error_code,
        )
    else:
        if not result.timestamp:
            return OutcomeCaptureResult(
                execution_result=result,
                capture_state="NOT_CAPTURED",
                reason="PROVIDER_RESPONSE_TIMESTAMP_MISSING",
                stream_path=str(stream_path),
            )
        record = build_outcome_record_from_canonical_result(
            request=request,
            result=result,
            client_order_id=request.intent_id,
            source_observation_id=_observation_id(result),
        )
    persisted = append_execution_outcome_record(record, stream_path=Path(stream_path))
    return OutcomeCaptureResult(
        execution_result=result,
        capture_state=persisted["state"],
        event_id=persisted["event_id"],
        stream_path=persisted["path"],
    )


def run_final_execution_attempt_with_outcome_capture(
    *,
    execution_ready_package: dict[str, Any],
    request: CanonicalOrderRequest,
    authorization_observation: dict[str, Any],
    adapter: Any,
    venue: str,
    execution_instrument: Any,
    stream_path: Path,
) -> OutcomeCaptureResult:
    """Run the existing final attempt contract, then capture its observed result."""
    result = run_final_execution_attempt_contract(
        execution_ready_package=execution_ready_package,
        request=request,
        authorization_observation=authorization_observation,
        adapter=adapter,
        venue=venue,
        execution_instrument=execution_instrument,
    )
    return capture_execution_attempt_outcome(
        request=request,
        result=result,
        stream_path=Path(stream_path),
    )


__all__ = [
    "OutcomeCaptureResult",
    "capture_execution_attempt_outcome",
    "run_final_execution_attempt_with_outcome_capture",
]
