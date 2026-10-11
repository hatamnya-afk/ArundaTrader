# Stable Client Order ID and Attempt Claim — Acceptance Boundary v0.1

## Status
Contract proposal only. No production integration, provider writes, database writes, runtime, or execution authorization.

## Purpose
A stable provider client-order ID must be derived from the canonical intent_id, in a provider-specific namespace. It is not the same identity as trade_event_id: the latter identifies an individual attempt and is intentionally newly issued per attempt.

## Implemented in this branch
- Pure deterministic candidate-ID derivation (exchange_execution_idempotency_contract_v0_1.py).
- Offline tests for repeatability, intent separation, provider namespace separation, output constraints, and invalid inputs.
- No network/file/database I/O and no execution wiring.

## Mandatory integration gates still OPEN
1. **Provider constraints:** verify the concrete provider client-order ID charset, length, uniqueness scope, and lookup consistency. The generic default is not approved for a provider until verified.
2. **Read-only lookup:** concrete adapter must query by the same client-order ID and return a typed result that distinguishes FOUND, NOT_FOUND, MULTIPLE, and ERROR. A NOT_FOUND result after a previous attempt is not permission to retry.
3. **Durable evidence:** persist the stable client-order ID alongside canonical intent and attempt evidence before any submission call. The current `CompactEvent` schema has no `client_order_id` field, so the end-to-end mapping is not yet represented. Its `append_event_idempotent` helper scans and appends JSONL without a cross-process atomic claim; it is not a safe per-intent concurrency lock.
4. **Atomic per-intent claim:** implement a durable compare-and-set/unique-key claim so concurrent callers and process restarts cannot both claim the same intent. The existing JSONL append helper is not atomic across processes. An in-memory lock or test fake is not sufficient evidence; use an isolated, explicitly approved durable claim store and test its uniqueness/transaction semantics without touching the production DB.
5. **Outcome reconciliation:** ambiguous provider responses and evidence-persistence failures must remain blocked for reconciliation; never infer rejection from timeout, exception, or absence from a limited query.
6. **Tests:** offline unit tests plus concurrency/restart tests against the actual durable claim implementation; provider lookup contract tests with no order writes.
7. **Review:** keep this work layered on PR #29 and PR #28. Do not merge or wire production execution based solely on this contract.

## Current decision
PRODUCTION_DUPLICATE_ORDER_PREVENTION = NOT VERIFIED.
REAL_ORDER_SUBMISSION = NOT AUTHORIZED.
PRODUCTION_PIPELINE_WIRING = OUT OF SCOPE.
