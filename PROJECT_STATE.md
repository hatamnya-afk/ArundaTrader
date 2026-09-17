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

Closed checkpoints are historical truth and are not re-audited unless a real regression is demonstrated.

## CP42 MANAGEMENT CORRECTION
CP42 inspected production-source binding but initially treated absence of a live exchange Account/Balance producer as a Core blocker. Management has explicitly corrected that interpretation.

CP42 is therefore NOT a justification for stopping the exchange-agnostic Core. Provider-neutral Capital/Portfolio abstractions are sufficient for Core architecture; actual exchange Account/Balance binding is deferred to the Exchange Binding phase.

The known Toobit `-1022 INVALID_SIGNATURE` remains an independent future exchange-binding issue. It is not moved into Core and must not block Core completion.

## CURRENT PROJECT STATE
CURRENT FRONTIER: TRADE INTENT → PRE-EXECUTION READY → EXECUTION-READY PACKAGE

Next major sequence:
1. Complete exchange-agnostic Core to Trade-Ready / Pre-Execution.
2. Verify the complete Core.
3. Clean and review contracts/boundaries.
4. Package the complete project.
5. Create a serious portable backup / ready package.
6. Only then begin exchange binding.
7. Implement and test exchange-specific Account/Balance/API/signature/constraints at that later phase.
8. Only after exchange verification and Management authorization does user capital enter the project for a controlled real test.

## CAPITAL POLICY
- User capital is NOT required for the current Core frontier.
- Do not ask the user to provide capital during Core development.
- `capital_config.py` remains TEST / LEGACY / NON-PRODUCTION and cannot be promoted to production capital.
- No synthetic, fabricated, interpolated, padded, or hardcoded capital.
- No fixed-15 sizing.
- Exchange-specific capital binding is a later integration concern.

## VERIFIED / CLOSED AREAS
- Data Fabric
- Dynamic Universe
- Real Market
- Dynamic Signal
- Opportunity
- Fusion
- Score
- Decision
- Risk
- Trade Gate
- Risk Contracts
- RiskContext
- Trade Lifecycle
- Exit Evidence
- PortfolioRisk Contract
- Account/Balance Producer contract layer
- CP37-J — Toobit Position Wiring
- CP37-KA — Toobit Position Reader compatibility
- REAL-ENVIRONMENT CONTROLLED RELEASE TEST v0.1 — CLOSED / VERIFIED / PASS
- CP38 — Smart Risk / Pre-Execution contract architecture
- CP39 — Pre-Execution Readiness → Decision Handoff
- CP40 — Decision Implementation
- CP41 — Decision → Trade Intent Boundary

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
