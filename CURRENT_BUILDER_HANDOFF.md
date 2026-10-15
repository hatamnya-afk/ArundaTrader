> ## CURRENT ADDENDUM — 2026-10-15 — RECONCILIATION + OUTCOME EVIDENCE CONTRACT
>
> - Added `execution_order_reconciliation_v0_1.py`: only claims already in `SUBMISSION_OUTCOME_UNKNOWN` or `RECONCILIATION_REQUIRED` can be queried. Positive evidence requires exact client-ID and symbol identity; it is persisted before claim promotion. A negative, malformed, or failed lookup remains `RECONCILIATION_REQUIRED`; it never proves non-execution and never allows resubmission.
> - Added append-only `execution_reconciliation_evidence` storage in the isolated `SQLiteIntentClaimStore`, with normalized client ID, venue, symbol, provider order ID/status, executed quantity/price, provider timestamp, detail code, and observed time. Evidence IDs are immutable/idempotent; conflicting reuse fails closed. Do not point this store at the production trading DB.
> - Corrected Futures read-only lookup to documented `GET /api/v1/futures/order` (the existing submission endpoint remains separate). Official provider documentation: [Spot Query Order](https://api-docs.toobit.com/api/spot-account-and-trading.html) states `GET /api/v1/spot/order` accepts `origClientOrderId`; [Futures Query Order](https://api-docs.toobit.com/api/usdt-m-account-and-trading.html) documents `GET /api/v1/futures/order`, `origClientOrderId`, category and order status fields.
> - Client-ID policy: `A + 31 hex chars` derived deterministically from the canonical intent. The provider docs guarantee uniqueness among open Spot orders, not indefinite historical uniqueness; therefore Arunda's own permanent unique constraint per provider namespace is the safety guarantee, and a collision blocks before submission. This guarantee applies only when the same durable claim store is actually used; production pipeline wiring remains intentionally NOT VERIFIED.
> - CI now includes offline reconciliation tests for positive match, unresolved/negative lookup, no query for an ineligible claim, and Futures endpoint selection. Most recent completed focused verification at the time of this addendum: [phase-entry verification](https://github.com/hatamnya-afk/ArundaTrader/actions/runs/38802917420). The new Toobit reconciliation test import correction is pending its own focused CI run; do not claim its PASS until that run completes.
> - **Live gate remains BLOCKED / NOT VERIFIED:** no authoritative guarantee was found that a negative order query proves non-execution or that historical IDs are globally unique. Policy closes this safely by permanent quarantine and no resubmit, not by assuming provider guarantees. No pipeline wiring, production runtime, order, cancellation, provider write, or production DB write was performed.
>
> ---
>
> ## CURRENT ADDENDUM — 2026-10-15 — ORDER RECONCILIATION
>
> - Added `exchange_execution_order_reconciliation_v0_1.py`: queries the exact client ID through the read-only adapter, validates identity, persists immutable reconciliation evidence in the explicitly supplied isolated claim store, and resolves a claim only when a positive order response matches the expected client ID and symbol.
> - Missing/error/malformed/mismatched lookup stays `UNRESOLVED_KEEP_QUARANTINED`; nonterminal claim transitions to `RECONCILIATION_REQUIRED`. No claim release, retry, resubmit, or inference of non-execution. Evidence persistence failure is explicit and never authorizes another POST.
> - CI on `2d37c36726b5542b8e79c8f4e4eefdb4c3bc2cad`: phase-entry focused verification PASS, 57 tests; focused execution contract PASS, 56 tests. Offline tests only.
> - Toobit Spot docs specify client ID uniqueness among open orders, not lifetime uniqueness. The durable Core claim store prevents reuse within its provider namespace for intents recorded in that store; this does not cover external actors or missing historical records. Negative single-order lookup is not proof of non-execution.
> - Official docs: https://api-docs.toobit.com/api/spot-account-and-trading.html and https://api-docs.toobit.com/api/usdt-m-api-v2
> - LIVE GATE remains BLOCKED: provider submission disabled; no production pipeline wiring, order, cancellation, provider write, production runtime, or production DB write. No Futures exposure permission is inferred.
>
> ---
>
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
> ## CURRENT ADDENDUM — 2026-10-15 — READ-ONLY AMBIGUOUS-ORDER RECONCILIATION
>
> - Added `ToobitExchangeAdapter.query_order_by_client_order_id(...)` for read-only lookup by exact provider client ID: Spot `GET /api/v1/spot/order` and Futures v2 `GET /api/v2/futures/order`. The method validates returned client ID, symbol, order ID, and status; it never sends a write request.
> - A positive identity-matched order lookup returns `ORDER_FOUND` evidence. Any provider error, timeout, missing order, or malformed/mismatched response returns `ORDER_LOOKUP_UNRESOLVED`, `state_known=False`, `resubmit_allowed=False`. Negative lookup is deliberately not interpreted as proof that the original order never executed; no automatic retry or claim release is implemented.
> - Official API references: [Toobit Spot order query](https://api-docs.toobit.com/api/spot-account-and-trading.html) documents `GET /api/v1/spot/order` with `origClientOrderId`; [Toobit Futures v2 order query](https://api-docs.toobit.com/api/usdt-m-api-v2) documents `GET /api/v2/futures/order` with `origClientOrderId`.
> - Focused Execution Contract CI passed on `9dc6a6f2bd250ded3bcac2b280bd5f0a960170e0`: 47 tests passed. Phase-entry focused verification passed on the same commit: 54 tests passed. These are scoped offline tests, not live provider verification.
> - Standing-mandate tests now reflect the authorized revocation-controlled policy: missing calendar timestamps are accepted as a no-calendar-expiry standing mandate; explicit expiry, when supplied, is still validated. This does not fabricate timestamps or require per-trade approval.
> - **Remaining live gate:** negative lookup completeness/retention and provider client-ID uniqueness/reuse semantics remain unverified by authoritative documentation. A missing lookup result must remain quarantined indefinitely until positive evidence or an explicit operator-reviewed reconciliation outcome. No order, provider write, cancellation, production runtime, or production DB write was performed; all submission switches remain OFF.
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
# ARUNDATRADER — CURRENT BUILDER HANDOFF

## CANONICAL WORKSPACE

`C:\Users\ASUS\ArundaTrader`

Repository: `hatamnya-afk/ArundaTrader`

**Active consolidation branch:** `operational-main-20261007`

`main` is NOT to be merged/reconciled during this consolidation. Main reconciliation is a later, separate governance task.

Read `ARUNDA_ECOSYSTEM_MASTER_MAP.md`, `REAL_PRODUCTION_PHASE_ENTRY_REVIEW.md`, `FINAL_REAL_ORDER_ATTEMPT_GATE.md`, `PROJECT_STATE.md`, `CURRENT_FRONTIER.md`, and `MANAGEMENT_ROADMAP.md` before making changes.

## NON-NEGOTIABLE MANAGEMENT MODEL

**Management authorization is ONE-TIME PHASE-ENTRY only.**

The single management decision is:

`AUTHORIZE REAL-PRODUCTION TRADING PHASE`

After that decision:
- trader operates autonomously;
- Spot and Futures are both in scope;
- no per-trade management approval exists;
- Decision → Risk → Trade Gate → Readiness → Order Attempt contracts govern each trade;
- Toobit/provider is authoritative for ACCEPT/REJECT;
- zero exchange balance is not a local trade blocker;
- provider rejection is real evidence and must not cause contract weakening;
- capital may be added progressively after real outcome/quality evidence;
- 24/7 operation is a later maturity target.

**No Builder may create, restore, or infer a per-trade management authorization layer.**

## AUTHORIZATION OWNERSHIP

### 1. Management Phase-Entry Mandate
Owner: `management_execution_authorization_v0_1.py`
`management_review_package_v0_1.py` is review-only packaging and is explicitly not an authorization producer.
Its active input schema is closed: unclassified fields fail closed, and trade/attempt aliases are rejected.

This is the only management authorization concept.

It covers:
- REAL_PRODUCTION environment;
- Spot + Futures;
- provider;
- capital policy;
- evidence-before/evidence-after requirements;
- mandate identity and expiry.

It does **not** contain:
- attempt_id;
- asset;
- direction;
- order type;
- quantity;
- per-order exposure.

Its active output is `STANDING_MANDATE`.

### 2. Technical Execution Authorization Boundary
Owner: `execution_authorization_boundary_v0_1.py`

This boundary does not ask management for permission.

It verifies that the current ready request is inside the active standing mandate and that the mandate is still valid. It is a technical safety gate, not a second management decision.

## ACTIVE SAFETY STATE

`EXECUTION AUTHORIZATION = FALSE` remains the repository safety state until management explicitly authorizes phase entry.

Before that decision:
- NO live order;
- NO provider write;
- NO DB mutation;
- NO `arunda_pipeline.py` wiring;
- NO execution activation.

Readiness, tests, provider metadata, account balance, or this handoff do not constitute phase-entry authorization.

## CURRENT FRONTIER

**REAL-PRODUCTION PHASE-ENTRY REVIEW / AUTHORIZATION CONSOLIDATION**

The current task is repository contract consolidation: eliminate any active/stale per-trade management authorization wording or dependency and verify the standing-mandate boundary.

Do not build another authorization layer.

## DO NOT DO

- Do not reopen closed/verified checkpoints without proven regression.
- Do not redesign Core.
- Do not bind Core to Toobit.
- Do not manufacture `exposure_allowed`.
- Do not send an order as a capability probe.
- Do not mutate the production DB.
- Do not modify protected `arunda_pipeline.py`.
- Do not use synthetic data, interpolation, forward-fill, back-fill, padding, fabrication, or silent source blending.
- Do not merge/rebase/reset/clean/delete/force.
- Do not add another governance document merely to restate this model.
- Do not create a per-trade management authorization contract.

## BUILDER START RULE

Start from repository state, not chat reconstruction.

Verify:
- branch;
- HEAD;
- worktree;
- the canonical governance documents above.

If management phase-entry decision is not explicitly `AUTHORIZED`, STOP before execution activation.

## CURRENT EXECUTION-PATH STATUS — 2026-10-15 (SUPERSEDES OLDER WIRING NOTES)

Operational branch: `operational-main-20261007`.

Implemented and verified:
- `arunda_pipeline.py` now passes explicit adapter + durable claim-store dependencies to the final-attempt verifier; no dependencies are constructed on the default path.
- Toobit submission adapter and allowlisted HTTPS transport are implemented for the documented Spot order endpoint and Futures v2 order endpoint. Submission requires two explicit runtime switches, credentials, and an absolute isolated claim-store path.
- The durable SQLite claim store rejects the production trading DB path. One stable client ID is derived from canonical intent; one provider POST maximum; no retry loop.
- Provider response identity is checked. Durable claim state records provider acceptance/rejection after the pre-submit outcome-unknown fence. Unknown/malformed outcomes remain non-replayable.
- Offline end-to-end fixture covers canonical request → standing-mandate contract → adapter → one mock POST → durable provider-accepted evidence.
- Focused CI run #52 PASS on `a2c2c0cae8742d36eb1f3f1b005426abe39541ac`: https://github.com/hatamnya-afk/ArundaTrader/actions/runs/38780574776

Not cleared for live execution:
- The authoritative standing-mandate record still lacks timezone-aware `issued_at` and `expires_at`. No timestamps or expiry policy have been fabricated.
- No production runtime, live provider POST/order, cancellation, or production DB write was performed.
- Do not enable the two submission switches while the active mandate and all technical gates remain invalid. This is not a per-trade approval dependency.

Older statements in this handoff that the pipeline is unwired or Toobit has no submission implementation are historical and are superseded by this status. Execution remains OFF by default.

END OF HANDOFF


### Verification refresh — 2026-10-15

This refresh supersedes earlier test counts in prior addenda: the current reconciliation contract, including terminal exchange-order-ID conflict protection, passed **58/58** in Phase-entry focused verification at commit `736a32101b4edb5c06481e55bc4149d42bf4e5d2` ([CI](https://github.com/hatamnya-afk/ArundaTrader/actions/runs/38802986919)) and **58/58** in Focused Execution Contract Tests at commit `6f5bf87268ad657365061bad82b9baccaba29b9f` ([CI](https://github.com/hatamnya-afk/ArundaTrader/actions/runs/38803055157)). Offline contract verification only; live production order gate remains BLOCKED.
