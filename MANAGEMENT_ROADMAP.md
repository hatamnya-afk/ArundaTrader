# ARUNDA TRADER — MANAGEMENT ROADMAP

## AUTHORITY
This document is the authoritative management route for project advancement.
The roadmap is the only path. Chat instructions, personal Builder plans, side branches, and unrecorded files do not override it.

## FINAL OBJECTIVE
Reach real trading through a controlled lifecycle, while keeping the ArundaTrader project itself exchange-agnostic until it is complete.

## MANDATORY LIFECYCLE

### PHASE A — EXCHANGE-AGNOSTIC PROJECT COMPLETION
Build and verify the complete ArundaTrader core, contracts, analysis/deployment boundaries, risk/decision/trade-intent chain, and required real-market readiness according to the checkpoint ledger.

Rules:
- No exchange-specific architecture is allowed to become Core.
- Exchange adapters remain replaceable environment boundaries.
- Closed/verified checkpoints remain historical truth unless Management proves a regression.
- No runtime, DB write, API write, or execution is implied merely by roadmap position.

Current position:
- CP41 = CLOSED / VERIFIED / PASS
- CP43 = CLOSED / VERIFIED / PASS
- CP44 = CURRENT FRONTIER / NOT YET EXECUTED / NOT VERIFIED / NOT CLOSED

Project completion is a Management-controlled gate. It is not declared merely because code appears feature-complete.

### PHASE B — EXCHANGE BINDING
This phase may begin ONLY after Phase A project completion is explicitly closed and recorded in:
- PROJECT_STATE.md
- CURRENT_FRONTIER.md
- CHECKPOINTS.md
- MANAGEMENT_ROADMAP.md

Purpose:
- select/authorize the exchange environment
- bind it through the existing exchange-agnostic adapter boundary
- preserve core/provider separation

No exchange-specific binding may be smuggled into an earlier phase.

### PHASE C — FINAL REAL-MARKET EXCHANGE INTEGRATION / CONTROLLED TEST
After Phase B is explicitly authorized:
- integrate the selected exchange using the adapter boundary
- verify real-market data/account/constraint paths as authorized
- perform the final controlled real-market test
- record provenance, evidence, blockers, and fail-closed behavior

No real order is implied by this phase. Execution remains separately authorized.

### PHASE D — REAL TRADING
Real trading may begin ONLY after:
1. Phase A completion is closed.
2. Phase B exchange binding is closed/verified.
3. Phase C final real-market integration and controlled test are closed/verified.
4. All execution/risk/constraint gates are satisfied.
5. Management explicitly authorizes execution.

No Builder or Manager may infer authorization from technical readiness.

## CHECKPOINT ADVANCEMENT GATE
At the end of EVERY checkpoint, the responsible Builder/Manager MUST update:
1. PROJECT_STATE.md
2. CURRENT_FRONTIER.md
3. CHECKPOINTS.md
4. MANAGEMENT_ROADMAP.md

The update must record:
- BUILT
- VERIFIED
- CLOSED / BLOCKED / NOT VERIFIED
- verification evidence
- blocker, if any
- CURRENT FRONTIER
- NEXT ACTION
- authorized branch/file scope, if changed

A checkpoint is not governance-complete until these documents are synchronized and internally consistent.

## ROUTE-CHANGE GATE
Any change in route, frontier, checkpoint sequence, architecture boundary, exchange strategy, or lifecycle ordering requires:
- explicit Management authorization
- immediate update of the roadmap
- immediate update of repository state documents
- a recorded reason for the change

Until that synchronization is complete, the new route is not active.

## BRANCH GOVERNANCE — ABSOLUTE
No Builder, Manager, coding agent, or implementation agent may create a project branch for:
- personal workflow
- experimentation
- convenience
- speculative work
- an unapproved parallel path
- an alternate project truth

A branch is permitted only when Management explicitly authorizes it as part of the active roadmap/checkpoint.
Before project work begins on that branch, repository state must record:
- purpose
- source
- target checkpoint
- relationship to Canonical
- authorization

Historical branches may be preserved for provenance. They do not become active project truth without Management authorization.

## FILE GOVERNANCE — ABSOLUTE
No Builder, Manager, coding agent, or implementation agent may add a project file outside the explicitly authorized checkpoint scope.

A new file is permitted only when:
- it has a defined responsibility
- it is required by the active checkpoint
- its scope is authorized and recorded

The following are not Canonical project truth unless explicitly authorized as historical records:
- temporary files
- generated outputs
- backups
- quarantine copies
- forensic dumps
- review dumps
- unrelated code
- personal workflow artifacts

If a file is not required by the roadmap, it does not enter Canonical.

## MANAGEMENT / BUILDER RULE
No one may "dance around" the roadmap.
No one may silently change the active frontier.
No one may start a next checkpoint before the previous checkpoint state is synchronized.
No one may use chat memory to override repository state.

When uncertain: STOP and escalate to Management.

## CURRENT GOVERNANCE GATE
Repository consolidation is active.
CP44 runtime execution remains forbidden until Management closes the consolidation gate after remote Canonical verification.

## CURRENT NEXT ACTION
1. Verify final remote Canonical state.
2. Close repository-consolidation governance gate.
3. Only then issue the explicit CP44 runtime authorization if still appropriate.

# END MANAGEMENT ROADMAP
