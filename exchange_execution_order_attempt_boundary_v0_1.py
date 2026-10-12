"""ARUNDA TRADER — PROVIDER-NEUTRAL ORDER ATTEMPT BOUNDARY v0.3.

Final provider-neutral gate between a prepared adapter order and a future
provider order attempt. Durable ORDER_ATTEMPTED evidence is written before
calling the adapter; provider-result evidence is written afterward.

NO automatic authorization.
NO exchange-specific logic.
NO database write.
The selected adapter owns provider submission behavior.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping

from exchange_execution_adapter_contract_v0_1 import (
    AdapterOrderPreparation,
    validate_adapter_contract,
)
from exchange_execution_contract import (
    CanonicalExecutionResult,
    CanonicalOrderRequest,
    blocked_execution_result,
    validate_order_request,
)
from execution_authorization_boundary_v0_1 import evaluate_execution_authorization
from execution_attempt_readiness_contract_v0_1 import evaluate_execution_attempt_readiness
from exchange_execution_order_preparation_v0_1 import prepare_order_for_adapter
from mcp01_execution_attempt_evidence_v0_1 import (
    build_order_attempt_event,
    build_provider_result_event,
    persist_execution_attempt_events,
)
from mcp01_trade_event_identity_v0_1 import issue_trade_event_id
from exchange_execution_idempotency_contract_v0_1 import (
    derive_validated_client_order_id,
    validate_supplied_client_order_id,
)


def attempt_prepared_order(
    *,
    request: CanonicalOrderRequest,
    readiness_observation: Mapping[str, Any],
    authorization_observation: Mapping[str, Any],
    adapter: Any,
    venue: str,
    execution_instrument: Any,
    execution_ready_package: Mapping[str, Any] | None = None,
    evidence_stream_path: Path | None = None,
    stable_client_order_id: str | None = None,
) -> CanonicalExecutionResult:
    """Fail closed unless authorization and pre-submit evidence are valid.

    An explicit JSONL evidence path is required. ORDER_ATTEMPTED must be durably
    recorded before the provider method is called. Provider outcome is recorded
    separately afterward. Evidence persistence never writes to the production DB.
    """
    valid, reason = validate_order_request(request)
    if not valid:
        return blocked_execution_result(
            asset=getattr(request, "asset", None),
            direction=getattr(request, "direction", None),
            error_code=reason,
            error_message=f"Canonical order request rejected: {reason}.",
        )

    contract_valid, contract_reason = validate_adapter_contract(adapter)
    if not contract_valid:
        return blocked_execution_result(
            asset=request.asset,
            direction=request.direction,
            error_code=contract_reason,
            error_message=f"Execution adapter contract rejected: {contract_reason}.",
        )

    if execution_ready_package is not None:
        try:
            readiness_observation = evaluate_execution_attempt_readiness(
                execution_ready_package=execution_ready_package,
                request=request,
            )
            readiness_observation = dict(readiness_observation)
            readiness_observation["order_type"] = request.order_type
            readiness_observation["execution_instrument"] = execution_instrument
            readiness_observation["venue"] = venue
        except ValueError as exc:
            return blocked_execution_result(
                asset=request.asset,
                direction=request.direction,
                error_code=str(exc),
                error_message=f"Execution-attempt readiness rejected: {exc}.",
            )

    try:
        authorization = evaluate_execution_authorization(
            readiness_observation,
            authorization_observation,
        )
    except ValueError as exc:
        return blocked_execution_result(
            asset=request.asset,
            direction=request.direction,
            error_code=str(exc),
            error_message=f"Explicit execution authorization rejected: {exc}.",
        )

    if authorization.get("authorization_state") != "AUTHORIZED":
        return blocked_execution_result(
            asset=request.asset,
            direction=request.direction,
            error_code="AUTHORIZATION_INVALID",
            error_message="Explicit execution authorization is required.",
        )

    # A provider must declare a verified, evidence-backed ID policy before
    # any attempt can proceed. No generic max length/charset is guessed.
    policy_provider = getattr(adapter, "stable_client_order_id_policy", None)
    try:
        policy = policy_provider() if callable(policy_provider) else None
        if stable_client_order_id is None:
            canonical_client_order_id = derive_validated_client_order_id(
                policy=policy, intent_id=request.intent_id
            )
        else:
            canonical_client_order_id = validate_supplied_client_order_id(
                policy=policy,
                intent_id=request.intent_id,
                client_order_id=canonical_client_order_id,
            )
    except (ValueError, TypeError, KeyError) as exc:
        reason = str(exc) or "CLIENT_ORDER_ID_POLICY_INVALID"
        return blocked_execution_result(
            asset=request.asset,
            direction=request.direction,
            adapter=getattr(adapter, "adapter_name", None),
            error_code=reason,
            error_message=(
                "Stable client-order ID could not be derived and validated "
                "against a verified provider policy; no provider attempt was made."
            ),
        )

    prepared = prepare_order_for_adapter(
        request=request,
        adapter=adapter,
        venue=venue,
        execution_instrument=execution_instrument,
    )
    if not isinstance(prepared, AdapterOrderPreparation) or not prepared.ready:
        return blocked_execution_result(
            asset=request.asset,
            direction=request.direction,
            adapter=getattr(adapter, "adapter_name", None),
            error_code=getattr(prepared, "reason", "ORDER_PREPARATION_BLOCKED"),
            error_message="Provider order preparation did not reach READY.",
        )

    # Bind the same canonical ID to provider payload and evidence.
    bind_client_order_id = getattr(adapter, "bind_stable_client_order_id", None)
    if not callable(bind_client_order_id):
        return blocked_execution_result(
            asset=request.asset,
            direction=request.direction,
            adapter=getattr(adapter, "adapter_name", None),
            error_code="STABLE_CLIENT_ORDER_ID_BINDING_UNSUPPORTED",
            error_message="Adapter cannot bind the canonical stable ID into its provider payload.",
        )
    try:
        prepared = bind_client_order_id(prepared, canonical_client_order_id)
    except Exception as exc:
        return blocked_execution_result(
            asset=request.asset,
            direction=request.direction,
            adapter=getattr(adapter, "adapter_name", None),
            error_code="STABLE_CLIENT_ORDER_ID_BINDING_FAILED",
            error_message=f"Provider client-order ID binding failed ({type(exc).__name__}).",
        )
    if not isinstance(prepared, AdapterOrderPreparation) or not prepared.ready:
        return blocked_execution_result(
            asset=request.asset,
            direction=request.direction,
            adapter=getattr(adapter, "adapter_name", None),
            error_code=getattr(prepared, "reason", "STABLE_CLIENT_ORDER_ID_BINDING_FAILED"),
            error_message="Provider payload did not accept the canonical stable client-order ID.",
        )

    if evidence_stream_path is None:
        return blocked_execution_result(
            asset=request.asset,
            direction=request.direction,
            adapter=getattr(adapter, "adapter_name", None),
            error_code="EXECUTION_ATTEMPT_EVIDENCE_PATH_REQUIRED",
            error_message="No provider call is allowed without an explicit evidence stream path.",
        )

    # The authoritative ID and durable attempt event exist before the provider call.
    trade_event_id = issue_trade_event_id()
    try:
        attempted_event = build_order_attempt_event(
            request=request,
            trade_event_id=trade_event_id,
            provider=getattr(adapter, "adapter_name", None) or "PROVIDER_UNKNOWN",
            event_timestamp=request.timestamp,
            client_order_id=canonical_client_order_id,
        )
    except Exception as exc:
        return blocked_execution_result(
            asset=request.asset,
            direction=request.direction,
            adapter=getattr(adapter, "adapter_name", None),
            error_code="ORDER_ATTEMPT_EVIDENCE_BUILD_FAILED",
            error_message=f"Pre-submit evidence construction failed ({type(exc).__name__}).",
            trade_event_id=trade_event_id,
        )

    attempt_persistence = persist_execution_attempt_events(
        [attempted_event], stream_path=Path(evidence_stream_path)
    )
    if attempt_persistence["persistence_state"] != "PERSISTED":
        return blocked_execution_result(
            asset=request.asset,
            direction=request.direction,
            adapter=getattr(adapter, "adapter_name", None),
            error_code="ORDER_ATTEMPT_EVIDENCE_PERSISTENCE_FAILED",
            error_message="Pre-submit evidence was not durably recorded; provider call was not made.",
            trade_event_id=trade_event_id,
        )

    try:
        result = adapter.submit_prepared_order(
            prepared,
            canonical_request=request,
        )
    except Exception as exc:
        # A transport/adapter exception after invocation cannot prove rejection.
        result = CanonicalExecutionResult(
            accepted=False,
            exchange_order_id=None,
            status="SUBMISSION_OUTCOME_UNKNOWN",
            asset=request.asset,
            direction=request.direction,
            executed_quantity=None,
            executed_price=None,
            timestamp=request.timestamp,
            adapter=getattr(adapter, "adapter_name", None),
            error_code="ADAPTER_SUBMIT_PREPARED_FAILED",
            error_message=(
                "Adapter raised during submission; provider acceptance is unknown "
                f"and requires reconciliation ({type(exc).__name__})."
            ),
            trade_event_id=trade_event_id,
        )

    if not isinstance(result, CanonicalExecutionResult):
        result = CanonicalExecutionResult(
            accepted=False,
            exchange_order_id=None,
            status="SUBMISSION_OUTCOME_UNKNOWN",
            asset=request.asset,
            direction=request.direction,
            executed_quantity=None,
            executed_price=None,
            timestamp=request.timestamp,
            adapter=getattr(adapter, "adapter_name", None),
            error_code="ADAPTER_EXECUTION_RESULT_INVALID",
            error_message=(
                "Adapter returned an invalid result after submission; provider "
                "acceptance is unknown and requires reconciliation."
            ),
            trade_event_id=trade_event_id,
        )
    else:
        # Never accept an adapter-supplied identity as authoritative.
        result = replace(result, trade_event_id=trade_event_id)

    try:
        provider_event = build_provider_result_event(
            request=request, result=result,
            client_order_id=canonical_client_order_id,
        )
        outcome_persistence = persist_execution_attempt_events(
            [provider_event], stream_path=Path(evidence_stream_path)
        )
    except Exception:
        outcome_persistence = {"persistence_state": "INCOMPLETE"}

    if outcome_persistence.get("persistence_state") != "PERSISTED":
        # Preserve provider acceptance/order identifiers, but surface missing evidence.
        return replace(
            result,
            error_code="PROVIDER_RESULT_EVIDENCE_PERSISTENCE_FAILED",
            error_message=(
                "Provider response was received but result evidence was not durably "
                f"recorded; original_status={result.status}; reconcile before retry."
            ),
        )

    return result


__all__ = ["attempt_prepared_order"]
