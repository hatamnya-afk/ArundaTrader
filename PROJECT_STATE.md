# ARUNDA TRADER — PROJECT STATE

## PURPOSE
Canonical repository-level source of truth for ArundaTrader. Chat memory is not authoritative when these documents are available.

## PROJECT IDENTITY
ArundaTrader is a modular, layered, exchange-agnostic real-market analysis and trading-decision system.

Toobit is an exchange adapter/environment, not the project core.

## CORE FLOW
REAL DYNAMIC UNIVERSE → REAL MARKET DATA → REAL OPPORTUNITY → REAL SIGNAL → REAL DECISION → SMART RISK MANAGEMENT → TRADE GATE → ORDER INTENT → EXECUTION → REAL TRADE → REAL OUTCOME → REAL OBSERVATION → CALIBRATION

## PRODUCTION BOUNDARY
LAUNCH_TIMESTAMP = 2026-08-31T00:00:00+00:00

Production analysis uses real post-launch data only.

## EXECUTION SAFETY
Execution is disabled unless Management explicitly authorizes it.

ORDER WRITE = FORBIDDEN
WITHDRAW = FORBIDDEN
DATABASE WRITE = FORBIDDEN unless explicitly authorized

Credentials and secrets must never be exposed.

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
- Account/Balance Producer
- CP37-J — Toobit Position Wiring
- CP37-KA — Toobit Position Reader compatibility
- REAL-ENVIRONMENT CONTROLLED RELEASE TEST v0.1 — CLOSED / VERIFIED / PASS

Closed areas are not re-audited unless a real regression is demonstrated.

## CURRENT STRATEGIC DIRECTION
Smart Risk Management is the next core development direction. It must remain provider-neutral and independent of Toobit.

## TOOBIT STATUS
CP37-M / MA / MB / MC established that the observed -1022 INVALID_SIGNATURE was real, while the local signing construction was contract-compatible and the root cause was not proven. No blind signing patch is justified.

Do not repeat private Toobit runtime diagnostics unless explicitly authorized.

## REPOSITORY STATE AT LEDGER CREATION
Local working branch reported by Builder: cp37-g-portfolio-observation
Local HEAD reported by Builder: 6a280ff — CP37-G: normalize Toobit position reader result boundary

The working tree contains substantial staged, modified and untracked artifacts. Do not clean, reset, stash, delete, or normalize them without explicit authorization.

## NON-NEGOTIABLE PROJECT RULES
- Real data only.
- No synthetic data, interpolation, forward-fill, back-fill, padding, or fabricated fallback values.
- One candle = one source; provenance is required.
- Fail closed when required real data cannot be verified.
- Global Universe is not Toobit Universe.
- Legacy test capital is not production capital.
- No real capital → fail closed.
- Core remains exchange-agnostic.
- Read-only layers remain read-only unless a writer is explicitly authorized.
- Do not modify arunda_pipeline.py without explicit authorization.
- Do not modify the production DB without explicit authorization.
- Do not reopen closed checkpoints without proven regression.

## SOURCE-OF-TRUTH ORDER
1. Repository state documents
2. Verified contracts and code
3. Git history
4. Chat context

## BUILDER START RULE
A new Builder session must read:
- PROJECT_STATE.md
- ARCHITECTURE.md
- CHECKPOINTS.md
- CURRENT_FRONTIER.md
- BUILDER_PROTOCOL.md

Then continue only from CURRENT_FRONTIER.md.

# END PROJECT STATE
