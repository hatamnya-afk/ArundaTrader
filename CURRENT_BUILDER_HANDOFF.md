## SERVICE CONFIGURATION + OPERATIONAL PATH AUDIT — 2026-10-15

- Candidate branch now contains a Windows persistent-journal configuration script (`ops/Configure-ArundaMandateJournal.ps1`), a validated/dry-run-first management activation CLI (`ops/Activate-ArundaStandingMandate.py`), the structured phase-entry observation, and a read-only startup preflight (`standing_mandate_service_preflight_v0_1.py`).
- Configuration defaults to `C:\\ProgramData\\ArundaTrader\\security\\standing_mandate_lifecycle.jsonl`, requires the actual runtime identity as an explicit parameter, applies restrictive ACLs to the directory and existing journal/lock files, and sets machine-level `ARUNDA_MANDATE_LIFECYCLE_PATH`. It does not write or seed the journal. The activation CLI defaults to dry-run and writes ACTIVATE only with explicit `--confirm-activate`.
- Focused CI: standing-mandate + startup/activation preflight **54 passed** ([run 38728746302](https://github.com/hatamnya-afk/ArundaTrader/actions/runs/38728746302)); execution-outcome evidence **58 passed** ([run 38728746246](https://github.com/hatamnya-afk/ArundaTrader/actions/runs/38728746246)).
- Operational path audit on `operational-main-20261007`: `arunda_pipeline.py` still calls `exchange_execution_boundary.execute_order`; `EXECUTION_ENABLED=False`; the operational Toobit adapter advertises `order_submission=False` and fail-closes submission. The candidate lifecycle-aware attempt boundary is not wired into the operational pipeline.
- **Not deployed / NOT VERIFIED:** this repository-only session cannot inspect the Windows host, identify the actual service/task identity, apply the host ACL/environment, persist the management activation event, restart the process, or run host preflight. Do not represent the journal as configured or the operational path as connected until those host checks pass.
- Safety remains unchanged: no operational branch edits, no merge, no production runtime, no provider/database writes, no order/cancel/withdrawal, and no execution flag activation. PR #38 remains open/unmerged. Provider client-order-ID and ambiguous POST recovery semantics remain unresolved.

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

END OF HANDOFF
