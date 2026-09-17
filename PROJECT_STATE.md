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

CP38 establishes the provider-neutral Smart Risk through Pre-Execution architecture. Execution is NOT BUILT and NOT AUTHORIZED. No order submission occurred, no production DB mutation occurred, and no execution flag was enabled. Test/Legacy capital was not used as REAL_CAPITAL.

## CP39 STATE
CP39 = CLOSED / VERIFIED / PASS
Scope = Pre-Execution Readiness → Decision Handoff
PRE-EXECUTION READINESS = SEALED

Verified CP39 chain:
REAL PRODUCTION OBSERVATIONS → READINESS INTEGRATION → HANDOFF → INTEGRITY → CERTIFICATION → BOUNDARY SEAL → READINESS-TO-DECISION HANDOFF

The verified CP39 chain is provider-neutral, fail-closed, and contains no execution surface.

## CP40 STATE
CP40 = CLOSED / VERIFIED (CONTRACT + ISOLATED TEST VERIFICATION)
DECISION CONTRACT = VERIFIED
DECISION ENGINE = VERIFIED
DECISION INPUT = SEALED-INPUT ONLY

Implementation:
- decision_contract_v0_1.py
- decision_engine_v0_1.py
- test_cp40_decision_v0_1.py

CP40 validates the CP39 sealed Decision input, rejects TEST/LEGACY/SIMULATED or otherwise unverified provenance, rejects provider/execution coupling, enforces dynamic asset identity, validates timezone-aware observation timestamps, and applies an explicit deterministic staleness window. Valid input produces only a provider-neutral Decision status/result.

Verification evidence:
- Focused CP40 suite: 12 passed in isolated verification environment.
- Static compile verification: PASS.
- Forbidden API/import scan for Decision implementation: PASS.
- No production runtime, DB mutation, exchange API call, order, or execution authorization performed.

## CP41 STATE — DECISION → TRADE INTENT
CP41 = CLOSED / VERIFIED / PASS

Scope = DECISION OUTPUT → TRADE INTENT

Implementation:
- decision_trade_intent_boundary_v0_1.py
- test_cp41_decision_trade_intent_boundary_v0_1.py

CP41 established a provider-neutral boundary/validation layer consuming validated Decision, Trade Gate, Position Sizing, and Stop/Risk outputs. It requires Decision READY + VALID, dynamic asset identity, valid provenance, approved Trade Gate/Risk state, and semantic agreement for direction, entry, stop, quantity, exposure, and policy version. It rejects execution/API/order surfaces.

Fresh local verification evidence recorded by Management:
- focused CP41 suite: 12 passed in 0.09s
- py_compile: PASS
- git diff --check: PASS
- forbidden operation/write/runtime scans: PASS
- fixed-15 / capital / synthetic scan: PASS
- imports limited to standard-library modules
- GitHub scope comparison: six CP41 files changed from the CP40 base; no runtime/Risk/execution modification

CP41 does not calculate or invent price, stop, quantity, exposure, capital, portfolio state, risk policy, exchange constraints, or execution authorization. It does not submit orders, call APIs, execute trades, or write the database.

## CP42 STATE — PRODUCTION TRADE-INTENT READINESS / REAL SOURCE BINDING
CP42 = BLOCKED — REAL CAPITAL SOURCE GAP

Scope = REAL PRODUCTION SOURCES → VALIDATED OBSERVATIONS → DECISION → TRADE INTENT

Repository inspection established that provider-neutral contracts and bridges exist for Real Capital Observation, Real Portfolio State, validated Entry/Stop/Risk Policy, Smart Risk, Trade Gate, and Decision → Trade Intent. However, the inspected branch does not establish a complete verified production-source binding from a real account/balance producer through the required upstream chain into Trade Intent.

Real Capital:
- production capital must originate from REAL ACCOUNT / BALANCE OBSERVATION
- `capital_config.py` remains TEST / LEGACY / NON-PRODUCTION
- existing real-capital contracts are present and fail closed on invalid/forbidden sources
- Toobit Account remains blocked by HTTP 400 / API -1022 INVALID_SIGNATURE
- no alternative verified real-account producer is established in the inspected CP42 state

Entry / Stop:
- validated contracts/bridges exist
- complete real producer binding into the CP42 production path is not established
- no latest-price fallback, ATR inference, interpolation, padding, or fabricated value is permitted

Quantity / Exposure:
- Smart Risk deterministically derives `position_size` and `exposure` from upstream capital, entry, stop distance, risk policy, and portfolio state
- this calculation is not itself a production source
- without verified production-bound upstream inputs, quantity/exposure production readiness cannot be certified

Therefore CP42 stops at the source gap and introduces no workaround, synthetic producer, or redesign.

## CURRENT PROJECT STATE
CURRENT FRONTIER: CP42 — PRODUCTION TRADE-INTENT READINESS / REAL SOURCE BINDING
CP40 = CLOSED / VERIFIED
CP41 = CLOSED / VERIFIED / PASS
CP42 = BLOCKED — REAL CAPITAL SOURCE GAP

EXECUTION = NOT AUTHORIZED
REAL ORDER = NONE
REAL TRADE = NONE
TOOBIT -1022 = INDEPENDENT ACCOUNT / REAL-CAPITAL BLOCKER

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

Closed areas are not re-audited unless a real regression is demonstrated.

## TOOBIT STATUS
TOOBIT ACCOUNT SIGNATURE = BLOCKED / -1022 INVALID_SIGNATURE
This remains an independent Account/Real-Capital path blocker. Do not repeat private Toobit diagnostics without explicit authorization.

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
Then continue from the active frontier recorded in CURRENT_FRONTIER.md.

# END PROJECT STATE
