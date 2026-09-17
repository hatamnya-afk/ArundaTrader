# ARUNDA TRADER — PROJECT STATE

## PURPOSE
Canonical repository-level source of truth for ArundaTrader. Chat memory is not authoritative when these documents are available.

## PROJECT IDENTITY
ArundaTrader is a modular, layered, real-market analysis and trading-decision system. The Core remains exchange-agnostic until project completion is explicitly closed.

Toobit is the execution exchange/environment and is kept outside Core through a replaceable adapter boundary.
KuCoin, Bybit, Gate, and other authorized providers belong to the Market Information Arm. They are market-information sources, not the execution exchange. Their observations are normalized/provider-neutral before entering Core.
News and Social are established information arms and are not current work unless direct, provable regression is identified.

## FINAL OBJECTIVE
Reach the first real trade through a controlled lifecycle, then capture the real fill, real outcome, observation, and empirical calibration.

The intended intelligence objective is maximum validated profit-opportunity capture through intelligent capital allocation and disciplined invalidation/exposure control. Capital allocation is an output of validated opportunity and constraints, not a universal hardcoded ceiling.

## MASTER LIFECYCLE
1. REAL WORLD INFORMATION
2. MARKET INFORMATION ARM — KuCoin / Bybit / Gate / other providers
3. NEWS ARM
4. SOCIAL ARM
5. NORMALIZED / PROVIDER-NEUTRAL MARKET & INFORMATION OBSERVATIONS
6. DATA FABRIC / PRODUCTION BOUNDARY
7. DYNAMIC UNIVERSE
8. OPPORTUNITY
9. SIGNAL
10. VALIDATION
11. FUSION
12. SCORE
13. DECISION
14. ENTRY / INVALIDATION
15. SMART RISK / CAPITAL ALLOCATION / POSITION SIZING
16. TRADE GATE
17. TRADE READY
18. ORDER INTENT
19. EXCHANGE CONSTRAINTS
20. PRE-EXECUTION READY
21. EXCHANGE-AGNOSTIC BOUNDARY
22. PROJECT COMPLETION GATE
23. TOOBIT EXCHANGE BINDING
24. FINAL REAL-MARKET EXCHANGE INTEGRATION / CONTROLLED TEST
25. EXPLICIT EXECUTION AUTHORIZATION
26. FIRST REAL ORDER
27. FIRST REAL FILL
28. REAL OUTCOME
29. OBSERVATION
30. CALIBRATION

## PRODUCTION BOUNDARY
LAUNCH_TIMESTAMP = 2026-08-31T00:00:00+00:00
Production analysis uses real post-launch data only.

## DATA / CARDINALITY RULES
- Real data only.
- No synthetic data, interpolation, forward-fill, back-fill, padding, fabrication, or silent source blending.
- One candle/observation = one attributable source; provenance is mandatory.
- Fail closed when required real data cannot be verified.
- Production flow is dynamic: `ELIGIBLE[N] → RISK[N] → TRADE_GATE[N] → TRADE_READY[N]`.
- Legacy `15` is test-era cardinality, not production truth.
- Observed `6` is runtime cardinality only, not a target or fixed universe.
- Global Universe is not the Toobit Universe.

## EXECUTION SAFETY
EXECUTION AUTHORIZATION = FALSE
ORDER WRITE = FORBIDDEN
WITHDRAW = FORBIDDEN
DATABASE WRITE = FORBIDDEN unless explicitly authorized
Credentials and secrets must never be exposed.

## HISTORICAL COMPLETION — CLOSED / VERIFIED
The following are historical truth and must not be reopened or re-audited without direct, provable regression:
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
- REAL-ENVIRONMENT CONTROLLED RELEASE TEST v0.1 — PASS
- CP38-A, C, D, E, F, G, H, I, J, K, L, N — CLOSED / VERIFIED / PASS
- CP38-B — DESIGN PASS
- CP39 — CLOSED / VERIFIED / PASS
- CP40 — CLOSED / VERIFIED / PASS
- CP41 — CLOSED / VERIFIED / PASS
- CP43 — CLOSED / VERIFIED / PASS

CP41 evidence: 12 focused tests passed; compile/static and scope/diff verification passed; no order, execution, API write, or production DB write.
CP43 evidence: 77/77 focused tests passed; compile passed; `git diff --check` passed; worktree clean at closure; execution authorization false; no runtime order, execution, API write, or DB mutation.

## CURRENT FRONTIER
CP44 — REAL-MARKET CONTROLLED TEST
Status = MANAGEMENT-AUTHORIZED / NOT YET EXECUTED / NOT VERIFIED / NOT CLOSED

Current path:
`ELIGIBLE[N] → REAL/VALIDATED ENTRY → REAL/VALIDATED INVALIDATION → SMART RISK → RISK[N] → TRADE_GATE[N] → TRADE_READY[N] → ORDER INTENT → PRE-EXECUTION → EXCHANGE-AGNOSTIC BOUNDARY`

CP44 acceptance boundary:
REAL_MARKET_DATA
VALIDATED_OBSERVATIONS
REAL_CAPITAL_BOUNDARY
VALID_ENTRY
VALID_STOP / INVALIDATION
VALID_QUANTITY
VALID_EXPOSURE
DECISION_CONSISTENCY
TRADE_INTENT_CONSISTENCY
CONSTRAINT_READINESS
PROVENANCE
FAIL_CLOSED
DYNAMIC_ASSET
NO_TEST_DATA
NO_FIXED_15
NO_ORDER
NO_AUTHORIZATION
NO_EXECUTION
NO_API_WRITE
NO_DB_WRITE

CP44 operating rule: use the established downstream ELIGIBLE boundary. Do not rebuild Opportunity, Signal, Fusion, Score, or Decision merely to reach CP44. One controlled runtime only; no retry/second runtime.

## FORWARD FRONTIER
CP45 = EXECUTION AUTHORIZATION BOUNDARY
Then:
PROJECT COMPLETION GATE → TOOBIT BINDING → FINAL REAL-MARKET CONTROLLED INTEGRATION → CP46 FIRST REAL ORDER → FIRST REAL FILL → REAL OUTCOME → OBSERVATION → CALIBRATION

Project completion must be explicitly closed before exchange binding.
Real execution requires explicit Management authorization after all gates are closed and verified.

## TOOBIT STATUS
TOOBIT ACCOUNT SIGNATURE = BLOCKED / HTTP 400 / -1022 INVALID_SIGNATURE
This is an independent Account/Real-Capital path blocker. Previous diagnostics are historical and must not be repeated or bypassed without explicit authorization.

## REPOSITORY GOVERNANCE
Canonical branch = `main`
Canonical base commit = `8945316ae1fec74ecfab40ac33ec9593e6d7ca8b`
Repository consolidation gate = CLOSED / MANAGEMENT-AUTHORIZED

No unauthorized branch or file may become project truth. Branches are permitted only when explicitly authorized for an active roadmap/checkpoint. New files require defined responsibility, active-checkpoint necessity, and recorded scope.

## PROTECTED SURFACES
- `arunda_pipeline.py`
- production database
- execution controls
- order submission/cancellation
- withdrawal
- closed/verified contracts
- backup/quarantine artifacts

## MANDATORY GOVERNANCE SYNCHRONIZATION
At the end of every checkpoint, synchronize:
1. `PROJECT_STATE.md`
2. `CURRENT_FRONTIER.md`
3. `CHECKPOINTS.md`
4. `MANAGEMENT_ROADMAP.md`

Record BUILT, VERIFIED, CLOSED/BLOCKED/NOT VERIFIED, evidence, blocker, CURRENT FRONTIER, NEXT ACTION, and authorized scope. A checkpoint is not governance-complete until these documents are internally consistent.

## SOURCE-OF-TRUTH ORDER
1. Repository state documents
2. Verified contracts and code
3. Git history
4. Chat context

## MANAGEMENT COMMAND
No restart. No redesign. No reopening closed checkpoints without proven regression. No modification of approved information arms without regression. No Fixed-15/Fixed-6 production assumptions. No test capital as production capital. No guessing of Entry/Invalidation/Quantity/Exposure/Authorization. No order/execution before explicit authorization. No extra branches/files.

The roadmap is the only path.

# END PROJECT STATE
