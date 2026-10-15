# Execution Outcome Evidence Contract v0.1

Status: additive contract candidate; not wired to production execution.

## Purpose

Represent a provider response or read-only lookup as append-only outcome evidence tied to the authoritative Decision, intent, attempt, and client-order identities. This is separate from market-performance outcomes and does not create a trade or submit an order.

## Safety and interpretation

- The caller must supply an explicit evidence stream path; there is no implicit production path.
- The module makes no network calls and does not call Toobit.
- OPEN/NEW/ACCEPTED never implies a fill.
- FILLED and PARTIALLY_FILLED require explicit positive execution quantity and price; incomplete records remain explicitly incomplete.
- CANCELED/CANCELLED/EXPIRED without execution quantity remain unreconciled; terminal status alone does not prove zero fills.
- Unknown provider statuses remain UNKNOWN.
- Every record has `fill_inferred=false`.
- Event identity is bound to provider + trade event + source kind + provider observation ID. Reusing that source identity with a different payload fails closed.
- Persistence is append-only and idempotent for one process. It is **not** a cross-process lock, durable order claim, or exactly-once guarantee.

## Bridge to the existing execution contract

`execution_attempt_outcome_capture_v0_1.py` accepts the `CanonicalOrderRequest` and `CanonicalExecutionResult` returned by the existing execution boundary and persists a provider observation only when the result includes a timestamp, trade-event identity, and authoritative Decision ID. It returns the original execution result separately from capture state, so evidence-write failure is not silently represented as an exchange rejection. A `FAIL_CLOSED` contract result is explicitly not misrepresented as a provider response. This is an integration seam, not yet a production-pipeline hook; the caller must explicitly choose the evidence path.

## Toobit read-only reconciliation seam

`toobit_order_observation_normalizer_v0_1.py` accepts an already-observed Toobit order row and records it as `READ_ONLY_LOOKUP`. It requires the exact `clientOrderId` to match the canonical intent and a trade-event ID from the existing attempt boundary. It uses `executedQty` and only an explicitly returned `avgPrice`/`averagePrice`; it never substitutes the order limit price for execution price. Unknown states remain unknown, and terminal states without quantity remain unreconciled. This module performs no HTTP calls and is not wired to production runtime.

Official Toobit API documentation describes Spot `newClientOrderId` as unique among open orders and documents order lookup by order ID or original client order ID. That does not establish exactly-once POST behavior or safe retry after an ambiguous timeout; those guarantees remain unverified. (https://api-docs.toobit.com/api/spot-account-and-trading.html)

## Explicitly not completed

- No live provider response has been captured by this contract.
- No adapter integration, production pipeline wiring, authorization change, order write, cancellation, database write, or runtime was performed.
- Provider-specific status mapping and live outcome semantics still require adapter-backed evidence.
- This contract does not clear the final real-order gate.
