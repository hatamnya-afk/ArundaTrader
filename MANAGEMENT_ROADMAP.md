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

## 4. CURRENT FRONTIER — FINAL REAL-MARKET EXCHANGE INTEGRATION / CONTROLLED TEST

### PROJECT COMPLETION GATE
Status:
CLOSED / VERIFIED / STATIC CONTRACT PASS

Evidence:
- The canonical exchange-neutral execution contract is present.
- Pre-execution readiness and execution-ready package preserve provider binding as DEFERRED.
- Provider-readiness modules remain outside the exchange-agnostic Core.
- arunda_pipeline.py remains free of Toobit preflight binding.
- The required exchange_execution_boundary.py was restored on MAIN as a minimal fail-closed exchange-agnostic boundary.
- Static syntax verification passed for the restored boundary.
- No Runtime, provider API call, order, real trade, or DB mutation was performed.

Architectural verdict:
CORE → EXCHANGE-AGNOSTIC BOUNDARY → REPLACEABLE EXCHANGE ADAPTER → TOOBIT

### CURRENT FRONTIER
FINAL REAL-MARKET EXCHANGE INTEGRATION / CONTROLLED TEST

Project Completion and Toobit Binding are CLOSED / VERIFIED.

The active gate is now the final real-market controlled-test gate. The Toobit adapter remains outside Core and arunda_pipeline.py remains unwired.

### SAFETY
EXECUTION AUTHORIZATION = FALSE
ORDER SUBMISSION/CANCELLATION = FORBIDDEN
WITHDRAWAL = FORBIDDEN
DATABASE WRITE = FORBIDDEN
PROVIDER WRITE = FORBIDDEN
## 5. FORWARD ROADMAP — FINAL CONTROLLED TEST

Project Completion is CLOSED / VERIFIED.
Toobit Binding is CLOSED / VERIFIED.

Current route:
`PROJECT COMPLETION → TOOBIT BINDING → FINAL REAL-MARKET CONTROLLED TEST → EXECUTION AUTHORIZATION → FIRST REAL ORDER → FIRST REAL FILL → REAL OUTCOME → OBSERVATION → CALIBRATION`

### Verified read-only evidence
- Full Read-Only Provider Preflight = PASS against live Toobit.
- Authoritative Futures instrument = BTC-SWAP-USDT.
- Live ExchangeInfo, Futures balance, leverage, positions, open orders, history orders, and server time returned HTTP 200.
- Provider preflight evidence constructed successfully.
- Account/order/contract/timestamp evidence was known and valid.
- GET-only transport; no write endpoint invoked.
- CP46-D focused tests = 12/12 PASS.
- git diff --check = PASS.
- targeted py_compile = PASS.
- evidence-alignment commit = f80fa83.

### Active controlled-test boundary
The evidence above proves read-only provider readiness. It does not authorize execution.

Do not wire Toobit into arunda_pipeline.py.
Do not submit/cancel orders.
Do not withdraw.
Do not mutate the DB.
Do not enable execution.
Do not invoke additional provider APIs unless separately authorized as part of the controlled-test evidence scope.

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
Do not reopen closed checkpoints without direct, provable regression.
Do not wholesale-merge the divergent MCP source branch.
Do not create extra branches/files.
Do not mutate the production DB.
Do not execute orders or real trades without explicit authorization.
Do not fabricate outcome evidence.
Preserve provenance and fail-closed behavior.

**Current path:**
`MCP-01 HANDOFF → MAIN → SELECTIVE, EVIDENCE-BACKED INTEGRATION → PROVIDER READINESS → PROJECT COMPLETION → TOOBIT BINDING → FINAL REAL-MARKET CONTROLLED TEST → EXECUTION AUTHORIZATION → FIRST REAL ORDER → FIRST REAL FILL → REAL OUTCOME → OBSERVATION → CALIBRATION`

Every completed checkpoint MUST update the four governance documents before the next frontier begins.


## PHASE B — TOOBIT BINDING CHECKPOINT STATUS
Current Frontier remains TOOBIT EXCHANGE BINDING.

Checkpoint state: BUILT / NOT VERIFIED / IN PROGRESS

Authorized scope executed:
- Open only the replaceable Toobit adapter boundary.
- Add a read-only Toobit adapter and focused tests.
- Preserve provider-neutral Core and protected arunda_pipeline.py.

Explicitly not executed:
- provider API calls
- Runtime
- order/cancel/withdraw
- DB mutation
- execution authorization

The checkpoint is not governance-complete until focused verification passes and all four governance documents are synchronized with VERIFIED/CLOSED or BLOCKED state.

# END MASTER MANAGEMENT ROADMAP
