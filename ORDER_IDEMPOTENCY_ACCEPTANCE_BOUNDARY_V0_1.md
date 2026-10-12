# Stable Client Order ID and Attempt Claim — Acceptance Boundary v0.1

## Status
Contract proposal only. No production integration, provider writes, database writes, runtime, or execution authorization.

## Purpose
A stable provider client-order ID must be derived from the canonical intent_id, in a provider-specific namespace. It is not the same identity as trade_event_id: the latter identifies an individual attempt and is intentionally newly issued per attempt.

## Implemented in this branch
- Pure deterministic candidate-ID derivation (exchange_execution_idempotency_contract_v0_1.py).
- Provider-neutral reconciliation policy that never authorizes a retry.
- Isolated SQLite intent-claim store (exchange_execution_atomic_intent_claim_store_v0_1.py) using a real composite primary key, provider-scoped unique client ID, and `BEGIN IMMEDIATE` transaction.
- Claim evidence columns for `intent_id`, `client_order_id`, `trade_event_id`, `decision_id`, provider order ID/status, evidence event ID, timestamps, and detail code.
- Permanent claims: no release/delete API; unknown outcomes and process restarts do not silently free the intent.
- Offline tests include a multi-process contention scenario against the actual SQLite unique-key implementation.
- The claim store is not wired into the order-attempt boundary and is not a production database. The caller must provide an isolated path; tests must never target the production DB.

## Mandatory integration gates still OPEN
1. **Provider constraints — PARTIALLY DOCUMENTED, NOT VERIFIED:** official Toobit USDT-M API docs describe `newClientOrderId` as unique among open orders and show a lookup parameter `origClientOrderId`; the docs inspected did not establish a maximum length, permitted character set, cross-endpoint uniqueness, or complete lookup consistency. Do not treat generic prefix/length defaults as approved. Sources: https://api-docs.toobit.com/api/usdt-m-account-and-trading and https://api-docs.toobit.com/api/usdt-m-api-v2.
2. **Read-only lookup — PARTIAL IMPLEMENTATION / OFFLINE CI PASS:** Toobit Futures regular-order lookup by `origClientOrderId` now returns typed FOUND / NOT_FOUND / ERROR. FOUND requires exact client ID plus non-empty exchange order ID and status; only the documented explicit `-2013` NO_SUCH_ORDER response maps to NOT_FOUND. Timeouts, permission errors, malformed responses, and identity mismatches remain ERROR. Spot, plan/algo orders, history pagination/completeness, and provider lookup guarantees remain unverified. NOT_FOUND after a prior attempt never authorizes retry.
3. **Durable evidence:** persist the stable client-order ID alongside canonical intent and attempt evidence before any submission call. The compact-event schema now has additive optional `intent_id` and `client_order_id` fields, preserving existing positional construction. The attempt-evidence builders and provider-neutral attempt boundary propagate the same supplied stable client ID into `ORDER_ATTEMPTED` and `PROVIDER_RESULT`. This proves an offline mapping path only: the ID is still optional, no concrete provider lookup supplies/validates it, and the JSONL append helper remains non-atomic across processes; none of these is a production idempotency guarantee.
4. **Atomic per-intent claim:** a provider-neutral SQLite claim-store contract is now added and uses a database primary key/unique constraint plus an immediate transaction. Its concurrency/restart tests and evidence-conflict tests are now executed by GitHub Actions and PASS on the PR test ref. This is still a candidate isolated store only; production suitability, lifecycle, backup/retention, filesystem durability, and integration remain unverified. It must not point at the production DB. The existing JSONL append helper remains non-atomic across processes.
5. **Outcome reconciliation:** ambiguous provider responses and evidence-persistence failures must remain blocked for reconciliation; never infer rejection from timeout, exception, or absence from a limited query.
6. **Tests:** the full offline contract set now runs in GitHub Actions, including multi-process SQLite contention, restart persistence, identity conflicts, state transitions, immutable evidence, stable-ID derivation, and reconciliation policy. The latest completed CI run (38209433523) is PASS: 58 tests passed in 0.95s on the idempotency-cycle test ref. Coverage includes SQLite claim/restart/concurrency, evidence mapping, fake-transport Toobit lookup, matched-order blocking, and NOT_FOUND reconciliation without claim release. No live provider query was made. It validates offline contracts only; no live provider query was made and it does not establish provider-side idempotency or production duplicate-order prevention.
7. **Review:** keep this work layered on PR #29 and PR #28. Do not merge or wire production execution based solely on this contract.

## Current decision
PRODUCTION_DUPLICATE_ORDER_PREVENTION = NOT VERIFIED.
ATOMIC_CLAIM_STORE_CONTRACT = IMPLEMENTED / OFFLINE CI PASS (43 TESTS).
TOOBIT_CLIENT_ID_CONSTRAINTS = PARTIALLY DOCUMENTED / NOT VERIFIED.
TOOBIT_FUTURES_REGULAR_ORDER_LOOKUP = IMPLEMENTED / OFFLINE CI PASS; LIVE PROVIDER SEMANTICS AND BROADER ORDER FAMILIES NOT VERIFIED.
COMPACT_EVENT_IDENTITY_MAPPING = ADDITIVE PATH IMPLEMENTED / OFFLINE CI PASS (56 TESTS); STABLE ID REMAINS OPTIONAL AT BOUNDARY.
REAL_ORDER_SUBMISSION = NOT AUTHORIZED.
PRODUCTION_PIPELINE_WIRING = OUT OF SCOPE.
