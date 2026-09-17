# ARUNDA TRADER — CURRENT FRONTIER

## MANAGEMENT DIRECTIVE
The exchange-agnostic Core must be completed before exchange binding and real-capital deployment. Lack of a live exchange Account/Balance source is NOT a blocker for completing the Core.

Authoritative roadmap: `MANAGEMENT_ROADMAP.md`

## CURRENT FRONTIER
**CP44 — PROJECT VERIFICATION / FULL CORE INTEGRITY → CLEANUP → PACKAGE → SERIOUS PORTABLE BACKUP**

Completed Core boundary:

TRADE INTENT → PRE-EXECUTION READY → EXECUTION-READY PACKAGE

Then:

PROJECT VERIFICATION → FULL TEST / CLEANUP → CONTRACT / BOUNDARY REVIEW → DOCUMENTATION SYNC → PACKAGE → SERIOUS PORTABLE BACKUP

Only after that:

EXCHANGE BINDING → EXCHANGE-SPECIFIC TESTS → MANAGEMENT AUTHORIZATION → USER CAPITAL → CONTROLLED REAL TEST

## CLOSED STATE
CP38 = CLOSED / VERIFIED / PASS (with CP38-B = DESIGN PASS as previously recorded)
CP39 = CLOSED / VERIFIED / PASS
CP40 = CLOSED / VERIFIED
CP41 = CLOSED / VERIFIED / PASS
CP42 = CLOSED / SUPERSEDED BY MANAGEMENT CORRECTION
CP43 = IMPLEMENTED / VERIFICATION PENDING LOCAL EXECUTION

Closed checkpoints are historical truth and are not to be re-audited without a demonstrated regression.

## CP42 CORRECTION
The earlier CP42 interpretation treated absence of a live exchange Account/Balance producer as a blocker for the Core. Management corrected this: the Core uses provider-neutral Capital/Portfolio abstractions where needed; actual exchange Account/Balance binding belongs to the later Exchange Binding phase.

The known Toobit `-1022 INVALID_SIGNATURE` condition remains a future exchange-binding issue and is not the current Core frontier.

## CP43 COMPLETION
CP43 implemented the provider-neutral boundary:

TRADE INTENT → PRE-EXECUTION READY → EXECUTION-READY PACKAGE

Files:
- `pre_execution_readiness_v0_1.py`
- `test_cp43_pre_execution_readiness_v0_1.py`
- `execution_ready_package_v0_1.py`
- `test_cp43_execution_ready_package_v0_1.py`
- `CP43_PRE_EXECUTION_READY_STATUS.md`

The implementation is exchange-neutral and fail-closed. It does not calculate new trading values, require live account/balance data, request capital, call APIs, write the database, authorize execution, sign, submit, or execute orders.

## CAPITAL RULE
Real capital is intentionally deferred until the exchange-binding phase has been implemented and tested.

During Core development:
- do not request user capital
- do not require a live exchange Account/Balance source
- do not promote `capital_config.py` TEST/LEGACY values to production
- do not use synthetic/fabricated/fallback capital
- do not hardcode fixed-15 capital/sizing

## BUILDER INSTRUCTION
Every new Builder/Manager session must read `MANAGEMENT_ROADMAP.md` first as the strategic routing document, together with:
- PROJECT_STATE.md
- ARCHITECTURE.md
- CHECKPOINTS.md
- CURRENT_FRONTIER.md
- BUILDER_PROTOCOL.md

The Builder must follow the roadmap literally. Complete CP44 verification/cleanup/package/backup before exchange binding. If local verification has not been run, do not mark CP43 VERIFIED/PASS.

# END CURRENT FRONTIER
