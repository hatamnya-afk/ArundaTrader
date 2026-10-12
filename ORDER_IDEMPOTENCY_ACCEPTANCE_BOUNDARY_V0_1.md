# Stable Client Order ID and Attempt Claim — Acceptance Boundary v0.1

## Status
Contract proposal only. No production integration, provider writes, database writes, runtime, or execution authorization.

## Purpose
A stable provider client-order ID must be derived from the canonical intent_id, in a provider-specific namespace. It is not the same identity as trade_event_id: the latter identifies an individual attempt and is intentionally newly issued per attempt.

## Implemented in this branch
- Pure deterministic candidate-ID derivation plus a policy gate (`verified`, provider namespace, prefix, maximum length, allowed-pattern regex, and evidence reference). The final attempt boundary derives the ID from canonical `request.intent_id`; if a caller supplies an ID, it must exactly match the derived value. The same validated ID is bound into the provider payload and both evidence events.
- Provider-neutral reconciliation policy that never authorizes a retry.
- Isolated SQLite intent-claim store (exchange_execution_atomic_intent_claim_store_v0_1.py) using a real composite primary key, provider-scoped unique client ID, and `BEGIN IMMEDIATE` transaction.
- Claim evidence columns for `intent_id`, `client_order_id`, `trade_event_id`, `decision_id`, provider order ID/status, evidence event ID, timestamps, and detail code.
- Permanent claims: no release/delete API; unknown outcomes and process restarts do not silently free the intent.
- Offline tests include a multi-process contention scenario against the actual SQLite unique-key implementation.
- The claim store is not wired into the order-attempt boundary and is not a production database. The caller must provide an isolated path; tests must never target the production DB.

## Mandatory integration gates still OPEN
1. **Provider constraints — PARTIALLY DOCUMENTED, NOT VERIFIED:** official Toobit USDT-M API docs describe `newClientOrderId` as unique among open orders and show a lookup parameter `origClientOrderId`; the docs inspected did not establish a maximum length, permitted character set, cross-endpoint uniqueness, or complete lookup consistency. Do not treat generic prefix/length defaults as approved. Sources: https://api-docs.toobit.com/api/usdt-m-account-and-trading and https://api-docs.toobit.com/api/usdt-m-api-v2.
2. **Read-only lookup — PARTIAL IMPLEMENTATION / OFFLINE CI PASS:** Toobit Futures regular-order lookup by `origClientOrderId` now returns typed FOUND / NOT_FOUND / ERROR. FOUND requires exact client ID plus non-empty exchange order ID and status; only the documented explicit `-2013` NO_SUCH_ORDER response maps to NOT_FOUND. Timeouts, permission errors, malformed responses, and identity mismatches remain ERROR. Spot, plan/algo orders, history pagination/completeness, and provider lookup guarantees remain unverified. NOT_FOUND after a prior attempt never authorizes retry.
3. **Stable ID policy and evidence:** `CompactEvent` has additive optional `intent_id` and `client_order_id` fields, preserving existing positional construction. The boundary now derives the stable ID from canonical `intent_id` under an adapter-declared policy, validates charset/length and rejects noncanonical caller-supplied IDs, then binds the exact ID into the adapter payload and both `ORDER_ATTEMPTED` / `PROVIDER_RESULT` evidence events. Missing or unverified policy fails closed before provider invocation. Toobit's policy deliberately remains unverified because the inspected official docs did not establish its client-ID maximum length or allowed charset. The JSONL append helper remains non-atomic across processes; this is not a production idempotency guarantee.
4. **Atomic per-intent claim:** a provider-neutral SQLite claim-store contract is now added and uses a database primary key/unique constraint plus an immediate transaction. Its concurrency/restart tests and evidence-conflict tests are now executed by GitHub Actions and PASS on the PR test ref. This is still a candidate isolated store only; production suitability, lifecycle, backup/retention, filesystem durability, and integration remain unverified. It must not point at the production DB. The existing JSONL append helper remains non-atomic across processes.
5. **Outcome reconciliation:** ambiguous provider responses and evidence-persistence failures must remain blocked for reconciliation; never infer rejection from timeout, exception, or absence from a limited query.
6. **Tests:** the full offline contract set now runs in GitHub Actions, including multi-process SQLite contention, restart persistence, identity conflicts, state transitions, immutable evidence, stable-ID derivation, and reconciliation policy. GitHub Actions run 38232788040: PASS — 61 tests passed before the canonical policy gate. GitHub Actions run 38233747494: PASS — 68 tests passed in 1.51s, including canonical boundary derivation, exact caller-ID matching, charset policy validation, and fail-closed behavior for unverified provider constraints. Coverage includes SQLite claim/restart/concurrency, evidence mapping, fake-transport Toobit lookup, matched-order blocking, NOT_FOUND reconciliation without claim release, and fail-closed behavior for noncanonical supplied IDs and unverified provider policies. No live provider query was made. This validates offline contracts only; it does not establish provider-side idempotency or production duplicate-order prevention.
7. **Review:** keep this work layered on PR #29 and PR #28. Do not merge or wire production execution based solely on this contract.

## Current decision
PRODUCTION_DUPLICATE_ORDER_PREVENTION = NOT VERIFIED.
ATOMIC_CLAIM_STORE_CONTRACT = IMPLEMENTED / OFFLINE CI PASS (68-TEST SUITE).
TOOBIT_CLIENT_ID_CONSTRAINTS = PARTIALLY DOCUMENTED / NOT VERIFIED.
TOOBIT_FUTURES_REGULAR_ORDER_LOOKUP = IMPLEMENTED / OFFLINE CI PASS; LIVE PROVIDER SEMANTICS AND BROADER ORDER FAMILIES NOT VERIFIED.
STABLE_CLIENT_ORDER_ID_BOUNDARY = CANONICAL DERIVATION + EXACT MATCH VALIDATION IMPLEMENTED; OFFLINE CI PASS (68 TESTS; run 38233747494). TOOBIT_PROVIDER_POLICY = UNVERIFIED / FAIL-CLOSED. COMPACT_EVENT_IDENTITY_MAPPING = ADDITIVE PATH IMPLEMENTED; same canonical ID is used for provider payload and both attempt/result evidence events.
REAL_ORDER_SUBMISSION = NOT AUTHORIZED.
PRODUCTION_PIPELINE_WIRING = OUT OF SCOPE.
