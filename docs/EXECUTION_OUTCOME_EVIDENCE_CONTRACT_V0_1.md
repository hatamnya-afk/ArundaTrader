# Execution Outcome Evidence Contract v0.1

Status: additive contract candidate; not wired to production execution.

## Purpose

Represent a provider response or read-only lookup as append-only outcome evidence tied to the authoritative Decision, intent, attempt, and client-order identities. This is separate from market-performance outcomes and does not create a trade or submit an order.

## Safety and interpretation

- The caller must supply an explicit evidence stream path; there is no implicit production path.
- The module makes no network calls and does not call Toobit.
- OPEN/NEW/ACCEPTED never implies a fill; an explicit provider `executedQty=0` is preserved as zero rather than rejected or converted into a fill.
- FILLED and PARTIALLY_FILLED require explicit positive execution quantity and price; incomplete records remain explicitly incomplete.
- CANCELED/CANCELLED/EXPIRED without execution quantity remain unreconciled; terminal status alone does not prove zero fills.
- Unknown provider statuses remain UNKNOWN.
- Every record has `fill_inferred=false`.
- Event identity is bound to provider + trade event + source kind + provider observation ID. Reusing that source identity with a different payload fails closed.
- Persistence is append-only and idempotent for one process. It is **not** a cross-process lock, durable order claim, or exactly-once guarantee.

## Bridge to the existing execution contract

`exchange_execution_order_attempt_boundary_v0_1.py` now issues a unique `TE-...` identity immediately before invoking the prepared adapter attempt and overwrites any adapter-supplied trade-event identity. Adapter exceptions retain that attempt identity. `execution_attempt_outcome_capture_v0_1.py` accepts the `CanonicalOrderRequest` and `CanonicalExecutionResult` returned by the existing execution boundary and persists a provider observation when boundary-issued trade-event identity and authoritative Decision ID are present. A missing provider timestamp remains `observed_at: null` with `provider_timestamp_known: false`; `captured_at` records local capture time and is not represented as provider time. It returns the original execution result separately from capture state, so evidence-write failure is explicitly reported as `PERSISTENCE_FAILED` rather than silently represented as an exchange rejection. Replaying the same provider facts is idempotent even if local capture time differs. A `FAIL_CLOSED` contract result is explicitly not misrepresented as a provider response. This is an integration seam, not yet a production-pipeline hook; the caller must explicitly choose the evidence path.

## Toobit read-only reconciliation seam

`toobit_order_observation_normalizer_v0_1.py` accepts an already-observed Toobit order row and records it as `READ_ONLY_LOOKUP`. It requires the exact `clientOrderId` to match the canonical intent and a trade-event ID from the existing attempt boundary. It uses `executedQty` and only an explicitly returned `avgPrice`/`averagePrice`; it never substitutes the order limit price for execution price. Unknown states remain unknown, and terminal states without quantity remain unreconciled. This module performs no HTTP calls and is not wired to production runtime.

Official Toobit API documentation describes Spot `newClientOrderId` as unique among open orders and documents order lookup by order ID or original client order ID. That does not establish exactly-once POST behavior or safe retry after an ambiguous timeout; those guarantees remain unverified. (https://api-docs.toobit.com/api/spot-account-and-trading.html)

## Opt-in Toobit submission candidate (not production-wired)

`toobit_controlled_execution_adapter_v0_1.py` is a separate adapter subclass; the existing read-only adapter is unchanged. Its `allow_order_submission` option defaults to `false`, so capabilities advertise submission disabled and no transport call occurs by default. If explicitly opted in for a controlled technical test, it makes exactly one signed POST to the documented Spot or Futures v2 route and never retries. A transport exception is reported as `SUBMISSION_UNKNOWN`, not rejection or success, and the error explicitly requires reconciliation by client order ID before any retry. Only explicit provider execution fields are carried; the order price is never treated as fill price.

This is still **not** production authorization: it has not been connected to the operational pipeline, does not implement automatic ambiguous-outcome reconciliation, and has not been tested against a live provider. Fake-transport tests prove only local request/response behavior. Do not set the opt-in on a production runtime until the standing mandate, account/instrument constraints, client-order lookup recovery, and controlled-order gate are verified.

## Futures lookup endpoint — corrected on isolated feature branch; verification pending

Static review found that `ToobitExchangeAdapter.futures_duplicate_check` combined the v2 open-orders endpoint (`GET /api/v2/futures/open-orders`) with the legacy `GET /api/v1/futures/historyOrders` path. The isolated feature branch now changes the history lookup to the documented `GET /api/v2/futures/history-orders` route and adds a fake-transport regression test asserting both read routes and GET-only behavior. The workflow was updated to include that test and the ambiguous-submission outcome-bridge test. Official reference: https://api-docs.toobit.com/api/usdt-m-api-v2.

The code/test correction is **implemented but not yet VERIFIED** until the latest branch CI result is available and successful. No live exchange request was made. Do not infer that a missing row proves non-acceptance; `safe_to_retry=false` remains mandatory.

## Explicitly not completed

- No live provider response has been captured by this contract.
- No adapter integration, production pipeline wiring, authorization change, order write, cancellation, database write, or runtime was performed.
- Provider-specific status mapping and live outcome semantics still require adapter-backed evidence.
- This contract does not clear the final real-order gate.
