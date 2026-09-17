# ARUNDA TRADER — PROJECT STATE

## PURPOSE
Canonical repository-level source of truth for ArundaTrader. Chat memory is not authoritative when these documents are available.

## PROJECT IDENTITY
ArundaTrader is a modular, layered, exchange-agnostic real-market analysis and trading-decision system.
Toobit is an exchange adapter/environment, not the project core.

## MANAGEMENT ROADMAP
See `MANAGEMENT_ROADMAP.md` for the authoritative strategic sequence.

Approved sequence:
REAL MARKET DATA → ANALYSIS → OPPORTUNITY → SIGNAL → SCORE → DECISION → RISK → POSITION SIZE → TRADE GATE → TRADE INTENT → PRE-EXECUTION READY → EXECUTION-READY PACKAGE
→ PROJECT VERIFICATION → FULL TEST / CLEANUP → PACKAGE → SERIOUS PORTABLE BACKUP
→ EXCHANGE BINDING → EXCHANGE-SPECIFIC TESTS → MANAGEMENT AUTHORIZATION → USER CAPITAL → CONTROLLED REAL TEST

**Critical rule:** the exchange-agnostic Core does NOT wait for a live exchange account, live exchange balance, private API, signature, or user capital. Those belong to the later Exchange Binding / Controlled Real Test phase.

## PRODUCTION BOUNDARY
LAUNCH_TIMESTAMP = 2026-08-31T00:00:00+00:00
Production analysis uses real post-launch data only.

## EXECUTION SAFETY
Execution is disabled unless Management explicitly authorizes it.
ORDER WRITE = FORBIDDEN
WITHDRAW = FORBIDDEN
DATABASE WRITE = FORBIDDEN unless explicitly authorized
Credentials and secrets must never be exposed.

## CLOSED STATES
CP38-A/C/D/E/F/G/H/I/J/K/L/N = CLOSED / VERIFIED / PASS
CP38-B = DESIGN PASS
CP39 = CLOSED / VERIFIED / PASS
CP40 = CLOSED / VERIFIED
CP41 = CLOSED / VERIFIED / PASS
CP42 = CLOSED / SUPERSEDED BY MANAGEMENT CORRECTION

Closed checkpoints are historical truth and are not re-audited unless a real regression is demonstrated.

## CP43 — PRE-EXECUTION READY / EXECUTION-READY PACKAGE
Implementation completed for the exchange-agnostic handoff:
TRADE INTENT → PRE-EXECUTION READY → EXECUTION-READY PACKAGE

Files:
- `pre_execution_readiness_v0_1.py`
- `test_cp43_pre_execution_readiness_v0_1.py`
- `execution_ready_package_v0_1.py`
- `test_cp43_execution_ready_package_v0_1.py`
- `CP43_PRE_EXECUTION_READY_STATUS.md`

The readiness boundary is validation/sealing only. The package boundary copies only certified provider-neutral fields and explicitly keeps provider binding deferred and execution unauthorized/unsubmitted.

Local pytest/compile verification is still required before CP43 can be declared VERIFIED/PASS. No GitHub CI workflow was found at the inspected standard path, so repository writes alone are not treated as test evidence.

## CURRENT PROJECT STATE
CURRENT FRONTIER: CP44 — PROJECT VERIFICATION / FULL CORE INTEGRITY → CLEANUP → PACKAGE → SERIOUS PORTABLE BACKUP

Next sequence:
1. Run local CP43 focused tests and static verification.
2. Verify the complete Core without reopening closed checkpoints.
3. Perform contract/boundary cleanup and contamination checks.
4. Package the complete exchange-agnostic project.
5. Create a serious portable backup / ready package.
6. Only then begin exchange binding.
7. Implement/test exchange-specific Account/Balance/API/signature/constraints at that later phase.
8. Only after exchange verification and Management authorization does user capital enter for a controlled real test.

## CAPITAL POLICY
- User capital is NOT required for the current Core frontier.
- Do not ask the user to provide capital during Core development.
- `capital_config.py` remains TEST / LEGACY / NON-PRODUCTION and cannot be promoted to production capital.
- No synthetic, fabricated, interpolated, padded, or hardcoded capital.
- No fixed-15 sizing.
- Exchange-specific capital binding is a later integration concern.

## TOOBIT STATUS
TOOBIT ACCOUNT SIGNATURE = BLOCKED / -1022 INVALID_SIGNATURE
This is a future exchange-binding issue, not a Core blocker. Do not repeat private Toobit diagnostics without explicit Management authorization for the Exchange Binding phase.

## NON-NEGOTIABLE PROJECT RULES
- Core remains exchange-agnostic.
- Real data only; no synthetic/fabricated/interpolated/forward-filled/back-filled/padded fallback values.
- Fail closed when required data cannot be verified.
- Legacy test capital is not production capital.
- No user capital during Core development.
- Read-only layers remain read-only unless a writer is explicitly authorized.
- No order submission, execution authorization, signature generation, exchange write, or production DB write during the Core frontier.
- Do not modify `arunda_pipeline.py` without explicit authorization.
- Do not reopen closed checkpoints without proven regression.
- Do not begin exchange binding before Core completion, verification, cleanup, packaging, and backup.

## SOURCE-OF-TRUTH ORDER
1. Repository state documents
2. Verified contracts and code
3. Git history
4. Chat context

## BUILDER START RULE
A new Builder/Manager session must read:
- MANAGEMENT_ROADMAP.md
- PROJECT_STATE.md
- ARCHITECTURE.md
- CHECKPOINTS.md
- CURRENT_FRONTIER.md
- BUILDER_PROTOCOL.md

Then continue from the active frontier. The roadmap must not be reinterpreted: deferred exchange capital is not a current blocker.

# END PROJECT STATE
