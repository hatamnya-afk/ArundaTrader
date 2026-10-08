# ARUNDATRADER — CURRENT BUILDER HANDOFF

## CANONICAL WORKSPACE

`C:\Users\ASUS\ArundaTrader`

Repository: `hatamnya-afk/ArundaTrader`

Active operational branch: `operational-main-20261007`

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

**REAL-PRODUCTION PHASE-ENTRY REVIEW**

The next action is to verify the already-built evidence package and present ONE phase-entry decision to management.

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

END OF HANDOFF
