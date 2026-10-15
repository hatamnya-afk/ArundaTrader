> ## CURRENT ADDENDUM — 2026-10-15 — AMBIGUOUS ORDER RECONCILIATION CONTRACT
>
> - Added `exchange_execution_order_reconciliation_v0_1.py`: takes an existing durable intent claim, queries the exact provider client ID through the adapter's read-only query, validates identity, persists immutable reconciliation evidence in the explicitly supplied claim/evidence store, and transitions the claim to `PROVIDER_ACCEPTED` / `PROVIDER_REJECTED` only for a positive identity-matched order result.
> - Lookup error, missing order, malformed response, or identity mismatch persists `UNRESOLVED_KEEP_QUARANTINED` and transitions a nonterminal claim to `RECONCILIATION_REQUIRED`. It never releases/reopens the claim, never resubmits, and never infers non-execution from a negative lookup. Evidence-write failures are reported explicitly and do not authorize another POST.
> - CI on commit `2d37c36726b5542b8e79c8f4e4eefdb4c3bc2cad`: Phase-entry focused verification PASS, **57 tests**; Focused Execution Contract Tests PASS, **56 tests**. Both are offline/focused contract verification, not live exchange verification.
> - Provider identity constraint: Toobit's Spot documentation says `newClientOrderId` must be unique among open orders; it does not establish lifetime uniqueness or guarantee that a negative single-order lookup proves no prior execution. The durable Core claim store enforces non-reuse within its provider namespace for all intents represented in that store. That guarantee applies only when the configured isolated durable store is actually used; do not generalize it to external actors or unrecorded history.
> - Official references: [Toobit Spot Account/Trade — Query Order and All Orders](https://api-docs.toobit.com/api/spot-account-and-trading.html); [Toobit Futures v2 — Get one regular order and History regular orders](https://api-docs.toobit.com/api/usdt-m-api-v2).
> - **Management verdict remains BLOCKED for live production:** adapter submission is still disabled; no production pipeline wiring, provider write request, cancellation, real order, production runtime, or production DB write occurred. Futures exposure permission is not inferred from balances, leverage, margin mode, or positions. Do not mark the production order gate PASS based on these offline tests.
>
> ---
>
> ## CURRENT ADDENDUM — 2026-10-15 — STANDING-MANDATE EXPIRY POLICY
>
> - The active phase-entry mandate is revocation-controlled with **no calendar expiry**; do not require or fabricate `issued_at`/`expires_at` merely to create a standing mandate. If an explicit expiry is supplied, it must be timezone-aware, future-dated, and consistent with issuance.
> - Code changes are committed on `operational-main-20261007`: management producer `bdc61f8`; technical authorization boundary `fdcd9de`; management tests `4a02fc5`; final-attempt tests `507ab01` and corrective test-fixture commit `eca7b35`.
> - The final-attempt test fixture was corrected to use only an in-memory claim-store double and a fake adapter stable client ID, and to assert the boundary's specific fail-closed errors. This is offline test scaffolding only; it does not contact Toobit.
> - **Focused verification: VERIFIED / PASS for the scoped tests only.** GitHub Actions run `38801470736` on commit `29f36d33c188ce917d78dfbfde1c0517cbb20b47` completed successfully: `20 passed in 0.05s` across `test_management_execution_authorization_v0_1.py` and `test_final_execution_attempt_contract_v0_1.py`. This does not verify the full suite, Toobit live submission, provider recovery guarantees, or production pipeline integration.
> - This change does **not** authorize a live attempt. Toobit submission remains disabled/unverified; provider client-order-ID and ambiguous-recovery guarantees and outcome capture remain blockers. No pipeline wiring, runtime, live order, provider write, cancellation, or production DB write is authorized by this addendum.
>
> This dated addendum supersedes older statements below that claim the mandate must have calendar expiry fields; those older entries remain historical evidence.
>
> ---
>
# REAL-PRODUCTION PHASE ENTRY REVIEW — v0.1

## Purpose
This is the final management review package for entering the first real-production trading phase.

It is a governance/readiness artifact. It does not itself authorize a provider write.

## Standing operational mandate
Once management explicitly authorizes phase entry:
- ArundaTrader may operate autonomously.
- SPOT and FUTURES are in scope.
- No per-trade management approval is required.
- Decision, risk, sizing, invalidation, and Trade Gate remain inside the existing trader contracts.
- Provider acceptance/rejection is authoritative.
- Zero exchange balance is allowed as the starting environmental state and is not a local pre-submit blocker.
- Real provider rejection is recorded as feedback; contracts are not weakened to avoid rejection.
- Capital is added progressively only after management review of real outcome evidence and demonstrated quality.
- 24-hour operation/analysis is a later maturity target, not a prerequisite for starting the real feedback loop.

## Evidence required before phase-entry decision
1. Canonical order path verified.
2. Execution-attempt contract verified.
3. Decision → Risk → Trade Gate path verified.
4. Authoritative provider read-only evidence verified.
5. Exact provider/instrument routing is verified for the attempted market.
6. Fail-closed safety interlocks remain intact.
7. No pipeline/DB mutation is required for the review.
8. Evidence capture path exists for provider response, fill/not-filled state, rejection reason, and outcome.
9. No per-trade management approval dependency exists.
10. Capital policy explicitly permits zero initial exchange balance.

## First-phase operating model
REAL MARKET
→ Dynamic Universe
→ Opportunity
→ Signal / Validation / Fusion / Score
→ Decision
→ Risk / Trade Gate
→ Order Attempt
→ Provider ACCEPT / REJECT
→ FILL / NOT FILLED
→ REAL OUTCOME
→ OBSERVATION
→ CALIBRATION
→ MANAGEMENT CAPITAL REVIEW

## Management decision
Current state: **AUTHORIZED — 2026-10-12**.

Authoritative decision record: `MANAGEMENT_PHASE_ENTRY_DECISION_20261012.md`.
The project owner explicitly authorized entry into the real-production trading phase on 2026-10-12.

This is a one-time standing phase-entry mandate covering SPOT and FUTURES. It must not be converted into repeated per-trade approval requests.

**Important:** the management decision is granted; this does not waive the listed technical/provider preconditions for an actual order attempt. The current active authorization observation and all order-attempt evidence must still validate at the technical gate.

## Safety before authorization
Until phase entry is explicitly authorized:
- EXECUTION AUTHORIZATION = FALSE
- provider write = forbidden
- order = forbidden
- cancellation = forbidden
- withdrawal = forbidden
- database mutation = forbidden
- automatic pipeline wiring = forbidden

## After phase-entry authorization
The standing mandate becomes operational. The trader does not request management approval for each trade.

A later management restriction, halt, or capital-scaling decision is a separate management event.

## Non-negotiable architectural invariant
The provider is the authority for whether an otherwise valid request is accepted or rejected. ArundaTrader must not manufacture a local acceptance/rejection outcome from balance absence, assumptions, or inferred provider behavior.

## Review verdict
**MANAGEMENT PHASE ENTRY: AUTHORIZED.**
**TECHNICAL REAL-ORDER READINESS: NOT YET VERIFIED.**

Continue by verifying each outstanding precondition against current repository/runtime evidence. Do not infer a successful live path from offline tests, and do not activate order execution until the exact technical gate is verified.

## GLOBAL SELECTION QUALITY LOOP — 2026-10-12
- Code integrated on `operational-main-20261007`; focused GitHub Actions contract/wiring tests: **11 passed**.
- The normal pipeline now records canonical decision/selection anchors and later real-market observations independently of Toobit listing and order submission.
- Append-only evidence stream: `runtime_observations/global_selection_outcomes.jsonl`; outcome summaries include observed 1h/4h/24h horizons, directional return, favorable/adverse excursion, and hindsight-only counterfactual movement for review of possible missed opportunities.
- No production DB write, live order, provider write, or production runtime was performed. Actual production observation accumulation and calibration effectiveness remain **NOT VERIFIED**.
- This tracking loop does not satisfy the separate real-order gate. Toobit order submission remains disabled/unverified, and trade/provider outcome capture remains NOT VERIFIED.


## STATIC TECHNICAL GATE AUDIT — 2026-10-12

Scope: source inspection only. No production runtime, live order, provider write, database access/mutation, or pipeline activation was performed.

### Confirmed
1. Management phase-entry decision is recorded as AUTHORIZED in `MANAGEMENT_PHASE_ENTRY_DECISION_20261012.md`.
2. `management_execution_authorization_v0_1.py` emits a structured `authorization_observation` for an authorized standing mandate and requires timezone-aware `issued_at` and future `expires_at`.
3. `execution_authorization_boundary_v0_1.py` validates the active mandate, expiry, REAL_PRODUCTION environment, SPOT/FUTURES scope, and request venue. It does not itself submit orders.
4. `execution_attempt_readiness_contract_v0_1.py` requires a valid canonical request and a validated execution-ready package, while preserving `execution_authorized=False` and `provider_binding=DEFERRED`.
5. `exchange_execution_order_attempt_boundary_v0_1.py` would call `adapter.submit_prepared_order` after its gates pass. That makes adapter capability and the active gate evidence material prerequisites.
6. `toobit_exchange_adapter_v0_1.py` currently advertises `order_submission=False`, `order_cancellation=False`, and its class documentation describes a read-only adapter. No supported live submit operation was verified in this adapter.
7. PR #31 remains Draft/unmerged. Its CI evidence (88 tests) is offline/mock/isolated-SQLite evidence only, not live-provider verification.

### Blocking evidence before any real order attempt
- **ACTIVE MANDATE INSTANCE:** The management code requires `issued_at` and `expires_at`, and the technical boundary rejects expired/missing expiry. The policy/repository does not establish a mandate duration. Do not invent one or manufacture an active observation from a decision record alone.
- **PROVIDER SUBMISSION CAPABILITY:** Current Toobit adapter is read-only and declares submission disabled; no actual provider submit path has been verified.
- **ORDER-ID / AMBIGUOUS RECOVERY:** Toobit client-order-ID charset/maximum length, reuse scope, duplicate POST semantics, lookup consistency/retention, and exhaustive recovery remain unverified in PR #31. The fail-closed block must remain.
- **END-TO-END EVIDENCE:** A current real request flowing through Decision → Risk → Trade Gate → readiness → authorization → provider result → fill/not-filled → real outcome/observation has not been evidenced by this static audit.
- **TEST EXECUTION:** The four governance updates and current branch code were not run in a local test environment by this audit. No new test-pass claim is made.

### Verdict
**MANAGEMENT PHASE ENTRY: AUTHORIZED.**
**TECHNICAL REAL-ORDER READINESS: BLOCKED / NOT VERIFIED.**
**EXECUTION AUTHORIZATION: FALSE.**
**LIVE ORDER / PROVIDER WRITE / DATABASE WRITE / PIPELINE ACTIVATION: NOT PERFORMED AND NOT CLEARED.**

Next work is to resolve the active-mandate expiry policy and provider execution/recovery contract, then add/run focused tests and re-evaluate the final gate. This is not a request for per-trade approval.

# END
