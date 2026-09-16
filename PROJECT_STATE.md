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

## CP38 STATE — PRE-EXECUTION ARCHITECTURE COMPLETE
CP38-A = CLOSED / VERIFIED / PASS
CP38-B = DESIGN PASS
CP38-C = CLOSED / VERIFIED / PASS
CP38-D = CLOSED / VERIFIED / PASS
CP38-E = CLOSED / VERIFIED / PASS
CP38-F = CLOSED / VERIFIED / PASS
CP38-G = CLOSED / VERIFIED / PASS
CP38-H = CLOSED / VERIFIED / PASS
CP38-I = CLOSED / VERIFIED / PASS
CP38-J = CLOSED / VERIFIED / PASS
CP38-K = CLOSED / VERIFIED / PASS
CP38-L = CLOSED / VERIFIED / PASS
CP38-N = CLOSED / VERIFIED / PASS

CP38 establishes the provider-neutral Smart Risk through Pre-Execution architecture. Execution is NOT BUILT and NOT AUTHORIZED. No order submission occurred, no production DB mutation occurred, and no execution flag was enabled. Test/Legacy capital was not used as REAL_CAPITAL. Smart Risk remains provider-neutral.

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

## CURRENT PROJECT STATE
CP38 = PRE-EXECUTION ARCHITECTURE COMPLETE
REAL EXECUTION = NOT BUILT / NOT AUTHORIZED
REAL CAPITAL = NOT YET PRODUCTION-AVAILABLE

Next work must first establish authoritative production-bound sources for real Account/Capital, Portfolio, validated Stop/Policy and other required observations. The path must not reopen with Test Capital.

## TOOBIT STATUS
TOOBIT ACCOUNT SIGNATURE = BLOCKED / -1022 INVALID_SIGNATURE
CP37-M / MA / MB / MC established that the observed -1022 was real, local signing construction was contract-compatible, and root cause was not proven. This remains an independent Account/Real-Capital path blocker. No blind signing patch is justified. Do not repeat private Toobit diagnostics without explicit authorization.

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
