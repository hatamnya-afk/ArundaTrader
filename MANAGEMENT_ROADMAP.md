# ARUNDA TRADER — MASTER MANAGEMENT ROADMAP

## 0. AUTHORITY
This document is the authoritative management route for ArundaTrader from project birth through the first real trade and subsequent observation/calibration.

The roadmap is the only advancement path. Repository state documents are the source of truth; chat memory, personal Builder plans, side branches, temporary files, and unrecorded work do not override them.

At the end of EVERY checkpoint, the four governance documents MUST be synchronized before the checkpoint is considered governance-complete:
1. `PROJECT_STATE.md`
2. `CURRENT_FRONTIER.md`
3. `CHECKPOINTS.md`
4. `MANAGEMENT_ROADMAP.md`

This synchronization rule is permanent.

## 1. FINAL OBJECTIVE
Build ArundaTrader as a real-market, layered, provider-neutral trading-decision system and take it through a controlled path to the first real trade, real outcome, observation, and calibration.

The system is designed to maximize validated profit opportunity capture through intelligent allocation and disciplined invalidation/exposure control — not through gambling, arbitrary risk minimization, or fixed profit/risk ceilings.

## 2. NON-NEGOTIABLE ARCHITECTURE

### Core principle
The ArundaTrader Core remains exchange-agnostic until the exchange-binding gate is explicitly opened after project completion.

### Information arms
The Market Information Arm is part of the project and legitimately uses external market providers. Providers such as:
- KuCoin
- Bybit
- Gate
- other authorized market-information providers

are information sources, not the execution exchange. Their output is normalized into provider-neutral market observations before entering the Core.

News and Social are also established information arms. They were validated before the current runtime frontier and are not current work unless a direct, provable regression is identified.

### Execution exchange
Toobit is the selected execution exchange/environment at the end of the lifecycle. It is connected through the exchange-agnostic adapter boundary and must not be embedded into Core architecture before the binding gate.

### Cardinality
Production flow is dynamic:
`ELIGIBLE[N] → RISK[N] → TRADE_GATE[N] → TRADE_READY[N]`

`15` is legacy/test-era cardinality and is not a production contract.
`6` is an observed runtime cardinality only and is not a target or fixed universe.

### Data integrity
- Real data only.
- No synthetic data.
- No interpolation.
- No forward-fill/back-fill.
- No padding/fabrication.
- No silent source blending.
- One observation/candle has one attributable source.
- Provenance is mandatory.
- Required unverified real data causes fail-closed behavior.
- Production analysis begins at `LAUNCH_TIMESTAMP = 2026-08-31T00:00:00+00:00`.

### Safety
Until explicit Management authorization:
- `EXECUTION AUTHORIZATION = FALSE`
- order submission/cancellation is forbidden
- exchange writes are forbidden
- withdrawals are forbidden
- production DB writes are forbidden
- credentials/secrets must never be exposed
- `arunda_pipeline.py` is protected unless separately authorized

## 3. PROJECT HISTORY — BUILT / VERIFIED / CLOSED

The following historical stages are completed and must not be reopened or re-audited without direct, provable regression.

### FOUNDATION / DATA
- Data Fabric established on real market sources.
- Production boundary established at the launch timestamp.
- Dynamic Universe established; legacy fixed-15 universe retained only as historical/test residue.
- Real Market path established.

### MARKET INTELLIGENCE → OPPORTUNITY
- Dynamic Signal established.
- Opportunity established.
- Market Information Arm established using real provider sources, with provider-neutral normalization.
- News Arm and Social Arm were approved before the runtime frontier.

### DECISION CHAIN
- Validation established.
- Fusion established.
- Score established.
- Dynamic Decision established.
- Decision is explicitly separated from Risk and Execution.

### RISK / TRADE CHAIN
- Risk established.
- Trade Gate established.
- Risk Contracts established.
- RiskContext established.
- Trade Lifecycle established.
- Exit Evidence established.
- PortfolioRisk Contract established.
- Account/Balance Producer established.
- CP37-J — Toobit Position Wiring — CLOSED / VERIFIED.
- CP37-KA — Toobit Position Reader compatibility — CLOSED / VERIFIED.
- REAL-ENVIRONMENT CONTROLLED RELEASE TEST v0.1 — CLOSED / VERIFIED / PASS.

### SMART RISK / PRE-EXECUTION HISTORY
- CP38-A — CLOSED / VERIFIED / PASS.
- CP38-B — DESIGN PASS.
- CP38-C through CP38-L — CLOSED / VERIFIED / PASS.
- CP38-N — CLOSED / VERIFIED / PASS.
- CP39 — PRE-EXECUTION READINESS → DECISION HANDOFF — CLOSED / VERIFIED / PASS.
- CP40 — DECISION IMPLEMENTATION — CLOSED / VERIFIED / PASS.
- CP41 — DECISION → TRADE INTENT BOUNDARY — CLOSED / VERIFIED / PASS.
  - 12 focused tests passed.
  - Compile/static and scope/diff verification passed.
  - No order, execution, API write, or production DB write occurred.
- CP43 — PRE-EXECUTION READY PACKAGE — CLOSED / VERIFIED / PASS.
  - 77/77 focused tests passed.
  - Compile verification passed.
  - `git diff --check` passed.
  - Worktree clean at closure.
  - Execution authorization remained false.
  - No order, execution, API write, or production DB mutation occurred.

## 4. CURRENT FRONTIER — CP44

### CP44 — REAL-MARKET CONTROLLED TEST
Status:
`MANAGEMENT-AUTHORIZED / NOT YET EXECUTED / NOT VERIFIED / NOT CLOSED`

Objective:
`REAL MARKET → VALIDATED OBSERVATIONS → DECISION → TRADE INTENT → PRE-EXECUTION / CONSTRAINT READINESS → CONTROLLED TEST RESULT`

Current downstream focus:
`ELIGIBLE[N] → REAL/VALIDATED ENTRY → REAL/VALIDATED INVALIDATION → SMART RISK → RISK[N] → TRADE_GATE[N] → TRADE_READY[N] → ORDER INTENT → PRE-EXECUTION → EXCHANGE-AGNOSTIC BOUNDARY`

CP44 must prove, with real and attributable observations:
- REAL_MARKET_DATA
- VALIDATED_OBSERVATIONS
- REAL_CAPITAL_BOUNDARY
- VALID_ENTRY
- VALID_STOP / INVALIDATION
- VALID_QUANTITY
- VALID_EXPOSURE
- DECISION_CONSISTENCY
- TRADE_INTENT_CONSISTENCY
- CONSTRAINT_READINESS
- PROVENANCE
- FAIL_CLOSED
- DYNAMIC_ASSET
- NO_TEST_DATA
- NO_FIXED_15
- NO_ORDER
- NO_AUTHORIZATION
- NO_EXECUTION
- NO_API_WRITE
- NO_DB_WRITE

CP44 does NOT authorize order submission, execution, signature bypass, exchange writes, test capital, or modification of protected pipeline code.

### CP44 operating rule
Use the established downstream `ELIGIBLE[N]` boundary. Do not rebuild Opportunity, Signal, Fusion, Score, or Decision merely to reach CP44.

A single controlled CP44 runtime is permitted under the existing no-write/no-order boundary. No retry or second runtime is implied.

## 5. FORWARD ROADMAP — FROM CP44 TO FIRST REAL TRADING

### CP45 — EXECUTION AUTHORIZATION BOUNDARY
Purpose:
Create and verify the explicit gate between technical `PRE-EXECUTION READY` and any permission to send a real order.

Required properties:
- explicit Management authorization object/boundary
- authorization is distinct from technical readiness
- fail closed by default
- no inferred authorization
- no order submission during CP45
- execution remains disabled until the gate is explicitly opened

Exit condition:
`PRE-EXECUTION READY → EXPLICIT EXECUTION AUTHORIZATION BOUNDARY` is verified and governance documents are synchronized.

### PROJECT COMPLETION GATE
Before exchange binding, Management must explicitly close the exchange-agnostic project/core.

Acceptance must cover the completed Core chain and its contracts, boundaries, real-market readiness, risk/decision/trade-intent path, and execution separation.

Exit condition:
Project completion is explicitly recorded as CLOSED in all four governance documents.

### PHASE B — EXCHANGE BINDING
Only after Project Completion Gate is closed.

Purpose:
- authorize the execution environment
- bind Toobit through the existing replaceable exchange adapter boundary
- preserve provider-neutral Core architecture
- keep Market Information Arm providers separate from execution

No exchange-specific logic may be moved into Core.

### PHASE C — FINAL REAL-MARKET EXCHANGE INTEGRATION / CONTROLLED TEST
After exchange binding is explicitly authorized:
- verify the Toobit adapter/environment against real authorized paths
- verify real account/capital/position/constraint observations as available
- verify final constraint readiness
- run the final controlled real-market integration test
- preserve provenance and fail-closed behavior

The known Toobit private-account blocker `HTTP 400 / -1022 INVALID_SIGNATURE` remains an independent blocker until resolved through an explicitly authorized path. It must not be bypassed or repeatedly diagnosed without authorization.

No real order is implied by Phase C.

### CP46 — FIRST REAL ORDER
Only after:
1. Project Completion Gate is CLOSED.
2. Toobit binding is CLOSED / VERIFIED.
3. Final real-market controlled integration is CLOSED / VERIFIED.
4. CP45 execution authorization boundary is CLOSED / VERIFIED.
5. Real capital, entry, invalidation, quantity, exposure, and exchange constraints are all valid for the specific opportunity.
6. Management explicitly authorizes the first real order.

CP46 must be a single controlled first-order event with complete provenance and fail-closed behavior.

### FIRST REAL FILL
After the first real order is explicitly authorized and accepted by the exchange, verify the actual fill rather than assuming it.

Required evidence includes actual exchange response/fill state, executed quantity/price where available, timestamps, fees where available, and provenance.

### REAL OUTCOME
Capture the actual position outcome:
- fill/open state
- exit/invalidation/closure evidence
- realized result
- exposure lifecycle
- fees/slippage where available
- no fabricated or inferred fill/outcome data

### OBSERVATION
Convert the completed real trade into a structured observation while preserving raw provenance and separating observation from calibration.

### CALIBRATION
Use accumulated real observations to evaluate and, only through an explicitly governed future checkpoint, adjust policies/parameters. Calibration must be empirical; it must not silently alter contracts or reopen closed stages.

## 6. MANAGEMENT GATES

A checkpoint is complete only when:
- BUILT is recorded.
- VERIFIED is recorded with evidence.
- CLOSED or BLOCKED/NOT VERIFIED is recorded.
- blocker is recorded if applicable.
- CURRENT FRONTIER is explicit.
- NEXT ACTION is explicit.
- authorized branch/file scope is recorded when relevant.
- all four governance documents are synchronized.

A route/frontier change requires immediate governance synchronization and its reason + Management authorization.

No next checkpoint starts before the previous checkpoint's governance synchronization is complete.

## 7. BRANCH / FILE GOVERNANCE

No personal, experimental, convenience, speculative, or parallel-truth branch is permitted.

A branch may exist only when explicitly authorized for the active roadmap/checkpoint, with purpose, source, target, and relationship to Canonical recorded.

No file may be added outside the explicitly authorized checkpoint scope.

Temporary, generated, backup, quarantine, forensic, review, and unrelated artifacts are not Canonical project truth.

## 8. SOURCE-OF-TRUTH ORDER
1. Repository state documents
2. Verified contracts and code
3. Git history
4. Chat context

If repository documents conflict, stop and escalate rather than inventing a parallel interpretation.

## 9. CURRENT MANAGEMENT COMMAND

Do not restart.
Do not redesign the project.
Do not reopen closed checkpoints.
Do not re-audit approved information arms without regression evidence.
Do not replace KuCoin/Bybit/Gate market-information providers with the execution exchange.
Do not confuse runtime cardinality with a fixed universe.
Do not use Fixed-15 or Fixed-6 as production contracts.
Do not use test capital as production capital.
Do not guess Entry, Stop/Invalidation, Quantity, Exposure, or authorization.
Do not execute orders during unauthorized stages.
Do not create extra branches/files.

**Current path:**
`CP44 → CP45 → PROJECT COMPLETION → TOOBIT BINDING → FINAL REAL-MARKET CONTROLLED TEST → CP46 FIRST REAL ORDER → FIRST REAL FILL → REAL OUTCOME → OBSERVATION → CALIBRATION`

Every completed checkpoint MUST update the four governance documents before the next frontier begins.

# END MASTER MANAGEMENT ROADMAP
