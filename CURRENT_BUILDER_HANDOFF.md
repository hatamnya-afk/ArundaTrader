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
- Focused CI run #42 PASS on `351d3321d0f17828fe2f0e54dc56ca7d7aec9362`: https://github.com/hatamnya-afk/ArundaTrader/actions/runs/38780176522

Not cleared for live execution:
- The authoritative standing-mandate record still lacks timezone-aware `issued_at` and `expires_at`. No timestamps or expiry policy have been fabricated.
- No production runtime, live provider POST/order, cancellation, or production DB write was performed.
- Do not enable the two submission switches while the active mandate and all technical gates remain invalid. This is not a per-trade approval dependency.

Older statements in this handoff that the pipeline is unwired or Toobit has no submission implementation are historical and are superseded by this status. Execution remains OFF by default.

END OF HANDOFF
