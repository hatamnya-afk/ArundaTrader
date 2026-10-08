# CURRENT GOVERNANCE OVERRIDE — 2026-10-08

> **THIS SECTION IS THE ACTIVE STATE.**
> Historical sections below are preserved as evidence/history and MUST NOT be interpreted as the current frontier when they conflict with this section.
>
> ## CURRENT CROSS-REPOSITORY MAP
> Read `ARUNDA_ECOSYSTEM_MASTER_MAP.md` first.
>
> ## VERIFIED POSITION
> The provider-neutral execution-attempt contract is VERIFIED / PASS / CLOSED for its defined scope.
> Latest verified endpoint: `448806f`.
>
> ## CURRENT FRONTIER
> **MANAGEMENT REVIEW — ONE-TIME REAL-PRODUCTION PHASE-ENTRY / STANDING MANDATE**
>
> The next task is to verify the one-time management phase-entry mandate and its separation from technical execution authorization. The management review package is review-only and cannot authorize an individual order attempt.
>
> ## SAFETY
> `EXECUTION AUTHORIZATION = FALSE`
> `ORDER WRITE = FORBIDDEN`
> `PROVIDER WRITE = FORBIDDEN`
> `DATABASE WRITE = FORBIDDEN`
> `arunda_pipeline.py` remains unwired.
>
> ## FORBIDDEN
> - Do not submit an order.
> - Do not call provider write endpoints.
> - Do not activate execution.
> - Do not reopen CP46-A6.
> - Do not redesign Core or bind Core to Toobit.
> - Do not treat historical A6 BLOCKED text as the current frontier.
>
> ## ALLOWED NOW
> - Define the explicit real-attempt gate.
> - Verify its preconditions, authorization separation, scope, safety interlocks, and evidence requirements.
> - Prepare a management decision package.
>
> **STOP CONDITION:** after the standing-mandate package is verified, STOP. Provider write remains forbidden until the ONE-TIME REAL-PRODUCTION PHASE-ENTRY MANDATE is explicitly authorized. After that, no per-trade management approval is required; the existing technical authorization boundary validates each ready request against the active standing mandate.

---

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

## 4. CURRENT FRONTIER — PROVIDER-NEUTRAL EXECUTION PATH COMPLETION

### EXCHANGE-AGNOSTIC ADAPTER CONTRACT — VERIFIED
The execution adapter boundary is now explicit and replaceable.

- Core-facing contract is provider-neutral.
- No exchange-specific name, symbol, transport, credential, or API semantics are required by Core.
- Toobit is one concrete adapter, not an architectural dependency.
- Submission/cancellation remain disabled and fail-closed.
- Adapter conformance is structurally tested without provider calls.

Commits: `98b75b1`, `3b4f184`, `ded818b`, `ac97549`, `726a6e3`.

Management verdict: **Toobit is an interchangeable execution environment.** The completion target is the Arunda execution path and its provider-neutral boundary, not Toobit itself. A future exchange can replace Toobit by implementing the same adapter contract.

### Safety
EXECUTION AUTHORIZATION = FALSE
ORDER SUBMISSION/CANCELLATION = FORBIDDEN
WITHDRAWAL = FORBIDDEN
DATABASE WRITE = FORBIDDEN
PROVIDER WRITE = FORBIDDEN

## 4A. HISTORICAL FINAL REAL-MARKET EXCHANGE INTEGRATION / CONTROLLED TEST
 — EXECUTION PATH COMPLETION / DYNAMIC ASSET BOUNDARY

### CP DYNAMIC EXECUTION ASSET UNIVERSE — VERIFIED
The execution side is now explicitly provider-driven rather than BTC-driven.

- Toobit exposes a read-only dynamic asset discovery surface from authoritative `exchangeInfo` metadata.
- Spot discovery selects current `TRADING` USDT base assets.
- Futures discovery selects current `TRADING` contract underlyings.
- No static production coin list is maintained.
- BTC has no special status.
- Exact provider symbol resolution remains a separate fail-closed operation.
- Multi-asset coverage is verified with ETH/SOL/XRP fixtures.

Commits: `91ffc7e`, `0e3f59e8`, `3b55141a9c2cf3b3d42ee1e285d18fb81c598dd1`.

Management verdict: dynamic asset support is a completed contract improvement. The next frontier is completing the provider handoff to a valid Order Request while keeping Core exchange-agnostic. Toobit rejection, if it occurs later under explicit authorization, is treated as provider/environment evidence and does not justify a BTC-specific or hardcoded Core design.

### Safety
EXECUTION AUTHORIZATION = FALSE
ORDER SUBMISSION/CANCELLATION = FORBIDDEN
WITHDRAWAL = FORBIDDEN
DATABASE WRITE = FORBIDDEN
PROVIDER WRITE = FORBIDDEN

## 4A. HISTORICAL FINAL REAL-MARKET EXCHANGE INTEGRATION / CONTROLLED TEST

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
- CP46-D test contract = 21/21 PASS across the Toobit adapter and CP46-D provider-preflight suites.
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

## CP46-D / CP46-A6 MANAGEMENT STATE

CP46-D test contract = CLOSED / VERIFIED.

Evidence:
- 21/21 focused tests PASS.
- py_compile PASS.
- git diff --check PASS.
- Futures routing, authoritative instrument resolution, contract evidence, provider-native margin state, leverage state, position state, and order state verified by focused contract tests.
- A6 fail-closed behavior is explicitly tested.

CP46-A6 = BLOCKED.

Exclusive blocker:
- No provider-native Toobit Futures signal has been established that directly authorizes additional portfolio exposure.
- exposure_allowed therefore remains UNKNOWN.
- Balance presence, leverage presence, margin mode, or empty positions MUST NOT be converted into exposure_allowed=True.

Management verdict:
The test contract is verified; the execution-readiness gate is correctly blocked. Do not weaken the contract to obtain PASS.

NEXT ACTION:
Investigate only provider-native Futures exposure authorization evidence. If no direct authoritative signal exists, preserve CP46-A6 as BLOCKED and advance no execution boundary.

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


## FINAL REAL-MARKET CONTROLLED TEST CHECKPOINT STATUS
Current Frontier: FINAL REAL-MARKET EXCHANGE INTEGRATION / CONTROLLED TEST.

Checkpoint state: OPEN / NOT EXECUTED.

Verified readiness evidence:
- Toobit Binding checkpoint is CLOSED / VERIFIED.
- Full Read-Only Provider Preflight = PASS on live Toobit.
- Authoritative Futures instrument resolved to BTC-SWAP-USDT.
- Live signed read-only account/order endpoints returned HTTP 200.
- Provider preflight evidence constructed successfully.
- CP46-D = 12/12 PASS; git diff --check PASS; targeted py_compile PASS.
- Commit f80fa83 records the final provider-evidence compatibility fixes.

The checkpoint is governance-open but execution-closed.

NEXT ACTION:
Provider-native Futures exposure authorization investigation only. No inference, no execution, no DB mutation, no order/cancel/withdraw.


CP46-A6 PROVIDER-NATIVE EXPOSURE INVESTIGATION — CONCLUSION

Investigation result:
- Toobit's documented read-only Futures surfaces expose balance/availableBalance, leverage and marginType, positions, and risk-limit configuration.
- The documented API-key permission model distinguishes read permissions from trade permissions; it does not expose a Futures account Boolean equivalent to exposure_allowed.
- Toobit documents order-time rejection conditions including no-opening-trades, insufficient order margin, and maximum Futures risk-limit exceeded. These are execution-time outcomes/constraints, not a pre-execution provider-native authorization Boolean.
- Therefore no direct authoritative provider-native Futures exposure_allowed signal has been established.

Classification:
DIRECT AUTHORITATIVE exposure_allowed = NOT FOUND
INFERRED exposure_allowed = FORBIDDEN
UNKNOWN exposure_allowed = YES

Management verdict:
CP46-A6 remains BLOCKED exclusively by missing provider-native Futures exposure authorization evidence. Do not convert balance, leverage, marginType, empty positions, risk-limit configuration, API-key trade permission, or hypothetical order acceptance into exposure_allowed=True.

No additional provider API call, order, cancel, withdrawal, DB mutation, execution authorization, or pipeline wiring is authorized by this investigation.

## CP46-A6 — MANAGEMENT DECISION: EXTERNAL PROVIDER CAPABILITY BOUNDARY

Management decision:
Stop further speculative implementation/search at the current evidence boundary. The investigation is CLOSED, while the checkpoint remains BLOCKED / NOT VERIFIABLE.

Reason:
No authoritative read-only Toobit Futures signal equivalent to `exposure_allowed` has been established. Existing account/risk fields are evidence of state and constraints, not authorization to increase exposure.

Strategic consequence:
This is now an external provider-capability dependency. ArundaTrader remains correctly fail-closed. No redesign, weakening, order probe, DB mutation, execution activation, or pipeline wiring is justified.

CURRENT FRONTIER:
FINAL REAL-MARKET EXECUTION READINESS — PROVIDER EVIDENCE BLOCKED.

NEXT ACTION:
Seek authoritative provider clarification/new documented or account-native evidence. Resume only if such evidence exists or a separately approved execution-contract decision changes the requirement.

# END MASTER MANAGEMENT ROADMAP


## CURRENT ROADMAP FRONTIER — EXCHANGE-AGNOSTIC ORDER PREPARATION

Management decision:
The execution roadmap proceeds through the replaceable adapter boundary rather than waiting for a Toobit-specific preflight Boolean that the provider does not expose.

Target:
`Canonical Order Request → Exchange-Agnostic Adapter Contract → Adapter-Owned Provider Order Preparation → Explicitly Authorized Order Attempt`

Rules:
- Core remains exchange-agnostic.
- Toobit remains replaceable.
- Provider-specific translation stays inside the adapter.
- Canonical quantity is never mutated by Core.
- No order/cancel/withdrawal is performed in preparation.
- No DB mutation.
- EXECUTION AUTHORIZATION = FALSE.
- `arunda_pipeline.py` remains unwired until the exchange-neutral completion gate is independently verified.

Current checkpoint:
CP EXCHANGE-AGNOSTIC ORDER PREPARATION HANDOFF — BUILT / NOT YET LOCALLY VERIFIED.

Evidence:
- Generic adapter contract extended with opaque preparation envelope.
- Generic preparation boundary added.
- Toobit adapter translates Futures base quantity using provider contract multiplier and constructs provider-specific payload internally.
- Focused tests added.

NEXT ACTION:
Builder runs local focused tests + py_compile + git diff --check. Then governance is synchronized with actual evidence before the next frontier.
\n\n## CURRENT ROADMAP FRONTIER — EXCHANGE-AGNOSTIC ORDER ATTEMPT\n\nStatus: VERIFIED / PASS / EXECUTION-CLOSED\n\nCompleted path:\n`Canonical Order Request → Exchange-Agnostic Adapter Contract → Adapter-Owned Provider Order Preparation → Provider-Neutral Order Attempt Boundary`\n\nEvidence:\n- `submit_prepared_order` is now part of the replaceable adapter contract.\n- Final order-attempt boundary requires valid technical authorization derived from the active standing mandate and delegates only to the selected adapter.\n- Toobit submission remains fail-closed; no real provider write occurs.\n- 22/22 focused tests passed.\n- py_compile passed.\n- git diff --check passed.\n\nStrategic rules remain unchanged:\n- Core is exchange-agnostic.\n- Toobit is replaceable.\n- Provider-specific payload remains inside the adapter.\n- EXECUTION AUTHORIZATION = FALSE until the ONE-TIME REAL-PRODUCTION PHASE-ENTRY MANDATE is explicitly authorized.\n- No DB mutation and no pipeline wiring.\n\nNEXT FRONTIER:\nExecution-attempt readiness and technical authorization verification against the active standing mandate. A future real order attempt, after phase-entry authorization, does not require a new management authorization.\n

## CURRENT ROADMAP FRONTIER — FINAL EXECUTION ATTEMPT CONTRACT

Status: VERIFIED / PASS / EXECUTION-CLOSED

Completed route:
`Execution Ready Package → Execution-Attempt Readiness → Explicit Authorization → Adapter Preparation → Provider-Neutral Order Attempt → Replaceable Exchange Adapter`

Evidence:
- `final_execution_attempt_contract_v0_1.py` composes the final provider-neutral execution-attempt route.
- `test_final_execution_attempt_contract_v0_1.py` verifies the three critical branches.
- 28/28 focused tests passed across the final contract and all directly dependent execution surfaces.
- py_compile PASS.
- git diff --check PASS.
- Fast-forward to `448806f` PASS.

Management rules remain unchanged:
- Core remains exchange-agnostic.
- Toobit remains replaceable.
- EXECUTION AUTHORIZATION = FALSE.
- No order/cancel/withdrawal.
- No DB mutation.
- No pipeline wiring.
- No execution activation is implied by contract verification.
- Provider rejection, if eventually observed under the active standing mandate after phase entry, is environment evidence rather than a reason to redesign Core.

Management verdict:
The provider-neutral execution path is now contract-complete through the adapter-attempt boundary and VERIFIED. The next management gate is the ONE-TIME REAL-PRODUCTION PHASE-ENTRY DECISION; verification itself does not authorize that phase entry. After phase entry, the trader operates autonomously and the technical authorization boundary uses the standing mandate for each request.

NEXT ACTION:
Do not activate execution automatically. Review/approve the explicit real-attempt scope separately before any provider write is permitted.


## CURRENT MANAGEMENT FRONTIER — STANDING REAL-PRODUCTION TRADING MANDATE

Status: MANAGEMENT REVIEW / READY FOR PHASE-ENTRY DECISION

The management authorization is clarified as a one-time phase-entry mandate for the initial real-production trading phase, not a requirement to request management permission for every trade.

### Standing scope
- Market modes: SPOT + FUTURES.
- Trader operation: autonomous within the already-verified decision, risk, Trade Gate, readiness, and execution contracts.
- Management role: review accumulated real-market evidence and decide capital scaling, not approve each order.
- Provider role: authoritative acceptance/rejection of each submitted request.
- Initial capital: may be zero; zero balance is not a local architecture blocker.
- Capital scaling: progressive and management-reviewed after real outcome evidence demonstrates acceptable opportunity quality and non-destructive loss behavior.
- 24-hour operation/analysis: later maturity target after the feedback loop is functioning; not a prerequisite for first real-market operation.

### Required evidence loop
REAL MARKET -> DECISION -> TRADE GATE -> ORDER ATTEMPT -> PROVIDER RESPONSE -> FILL/REJECTION -> OUTCOME -> OBSERVATION -> CALIBRATION -> MANAGEMENT CAPITAL REVIEW

### Governance rule
No per-trade management authorization request is required after phase-entry authorization. Any later restriction or halt must be a new explicit management decision, or a fail-closed technical/provider safety condition already defined by the contracts.


## NON-NEGOTIABLE OPERATING INVARIANT — DO NOT REPEAT THIS DECISION

The management model is a ONE-TIME PHASE-ENTRY MANDATE, not per-trade approval.

After explicit phase-entry authorization:
- Spot and Futures are both in scope.
- The trader operates autonomously under the already-verified Decision/Risk/Trade Gate/Execution contracts.
- No management approval request is generated for each trade.
- Zero exchange balance is not a local blocker; the provider is authoritative for acceptance/rejection.
- Real rejection is evidence and must not trigger contract weakening.
- Capital is scaled progressively only after real-market outcome/quality evidence and management review.
- 24-hour operation/analysis is a later maturity stage, not a prerequisite for starting the real feedback loop.

Any future Builder must treat REAL_PRODUCTION_PHASE_ENTRY_REVIEW.md and this section as active governance constraints. Historical text that conflicts with this invariant is historical residue and MUST NOT reopen the per-trade authorization model.
