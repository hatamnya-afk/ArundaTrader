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
> **MANAGEMENT REVIEW — EXPLICIT REAL-ORDER ATTEMPT GATE**
>
> The next task is to define and inspect the bounded, explicit management gate for a future real provider order attempt. This is preparation/governance only.
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
> **STOP CONDITION:** after the gate package is verified, STOP. A separate explicit execution authorization is required before any provider write.

---

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

### EXCHANGE-AGNOSTIC ADAPTER CONTRACT — VERIFIED
Status = VERIFIED / REPLACEABLE BOUNDARY

A provider-neutral adapter contract is now explicit in `exchange_execution_adapter_contract_v0_1.py`. Core-facing execution uses a replaceable adapter interface; the contract contains no exchange name, provider symbol, transport, credential, or exchange-specific semantics. Toobit is only one concrete adapter implementation.

Verified changes:
- `ExchangeExecutionAdapter` structural contract established.
- Adapter capabilities are provider-neutral.
- Toobit conforms to the replaceable adapter boundary while remaining execution-disabled.
- Order submission/cancellation remain fail-closed.
- No Core dependency on Toobit was introduced.

Evidence commits: `98b75b1`, `3b4f184`, `ded818b`, `ac97549`, `726a6e3`.

This checkpoint does NOT authorize execution and does NOT close the final real-market gate.



### CP DYNAMIC EXECUTION ASSET UNIVERSE — IMPLEMENTED
Status = VERIFIED / DYNAMIC / PROVIDER-DRIVEN

The execution instrument path is asset-agnostic. Toobit adapter now exposes read-only `discover_tradable_assets(venue)` derived from current authoritative exchange metadata and filtered to `TRADING`. Spot discovery uses live USDT base assets; Futures discovery uses live underlying assets. Exact provider symbol selection remains a separate provider-neutral instrument-resolution step.

No static BTC/ETH/SOL universe was introduced. BTC is not privileged. A newly listed/tradable provider asset can enter the execution asset universe without Core code changes.

Evidence commits: 91ffc7e (dynamic provider asset discovery), 0e3f59e (multi-asset discovery tests), 3b55141 (asset-agnostic resolver test).

SAFETY: discovery is read-only; no order, provider write, DB mutation, execution authorization, or arunda_pipeline.py wiring.


### FINAL REAL-MARKET EXCHANGE INTEGRATION / CONTROLLED TEST — OPEN

Status = CURRENT FRONTIER / OPEN / NOT EXECUTED

Purpose:
Open and verify the final real-market controlled-test gate after verified Project Completion and verified Toobit Binding. Opening this gate is governance/readiness control only; it does not authorize execution.

Verified real-market read-only evidence:
- Full Read-Only Provider Preflight = PASS against live Toobit.
- Toobit ExchangeInfo returned HTTP 200 and authoritative Futures instrument resolution selected exactly BTC-SWAP-USDT.
- Futures balance, account leverage, positions, open orders, history orders, and server time returned HTTP 200.
- Provider preflight evidence was constructed successfully.
- Provider account state was known with no position conflict; provider order state was known and empty; contract constraints were valid; timestamp state was known.
- Real provider transport was GET-only.
- No order submission, cancellation, withdrawal, exchange write, database mutation, or execution authorization occurred.
- CP46-D focused verification: 12/12 tests passed; git diff --check passed; targeted py_compile passed.
- Evidence-alignment commit: f80fa83 (CP Controlled Test: align Toobit provider evidence with live state).

Controlled-test boundary:
- Core remains exchange-agnostic.
- Toobit remains outside Core through the replaceable adapter boundary.
- arunda_pipeline.py remains unwired to the Toobit provider-preflight chain.
- Execution authorization remains FALSE.

Authorized scope now:
- Inspect and verify the controlled-test contract/readiness boundary.
- Preserve real-data-only and fail-closed rules.
- Preserve execution-off safety.
- No order/cancel/withdraw.
- No DB mutation.
- No execution authorization unless separately and explicitly authorized.
- No modification of closed/verified checkpoints or protected arunda_pipeline.py.

CP46-D / CP46-A6 STATUS

CP46-D test contract = VERIFIED.
Evidence:
- 21/21 focused tests passed across the Toobit adapter and CP46-D provider-preflight test suites.
- py_compile passed for the focused adapter/evidence/test modules.
- git diff --check passed.
- Futures routing, authoritative instrument resolution, contract evidence, provider-native margin state, leverage state, position state, and order state are covered by the focused contract.
- The three Futures PASS expectations were aligned to the strengthened A6 fail-closed contract without weakening production logic.

CP46-A6 = BLOCKED exclusively by missing provider-native Futures exposure authorization evidence.
- exposure_allowed remains UNKNOWN.
- No inference from balance, leverage, margin mode, or absence of positions is permitted.
- No provider-native Toobit Boolean authorizing additional Futures exposure has been established.
- The fail-closed contract correctly returns BLOCK_PORTFOLIO_EXPOSURE when exposure authorization is not directly evidenced.

NEXT ACTION:
Investigate only whether Toobit exposes a direct, authoritative Futures exposure-authorization signal. If no such provider-native evidence exists, keep CP46-A6 BLOCKED. Do not fabricate or infer exposure permission. No additional provider API calls, order/cancel/withdraw, DB mutation, execution authorization, or arunda_pipeline.py wiring. Do not invoke additional provider APIs, submit/cancel orders, mutate the DB, or enable execution unless separately and explicitly authorized.

### PROJECT COMPLETION — CLOSED / VERIFIED
Status = CLOSED / VERIFIED / STATIC CONTRACT PASS

The exchange-agnostic Core is now closed at the Project Completion Gate. The required exchange boundary is present on MAIN and remains fail-closed. Toobit is still outside Core and is not bound.

Evidence:
- exchange_execution_contract.py defines the canonical exchange-neutral request/result and execution-off safety contract.
- pre_execution_readiness_v0_1.py and execution_ready_package_v0_1.py keep provider binding deferred.
- provider-readiness contracts remain separate from Core.
- arunda_pipeline.py does not call the Toobit preflight chain.
- exchange_execution_boundary.py is present on MAIN and provides the required fail-closed execute_order boundary.
- Static syntax verification passed for the restored boundary.

Architecture:
CORE → EXCHANGE-AGNOSTIC EXECUTION BOUNDARY → REPLACEABLE EXCHANGE ADAPTER → TOOBIT

### TOOBIT EXCHANGE BINDING — CLOSED / VERIFIED
Status = CLOSED / VERIFIED / FOCUSED STATIC CONTRACT PASS

Toobit binding is implemented only at the existing replaceable adapter boundary. The provider-specific adapter remains outside Core and arunda_pipeline.py remains unwired.

Safety remains:
EXECUTION AUTHORIZATION = FALSE
ORDER WRITE = FORBIDDEN
PROVIDER WRITE = FORBIDDEN
DATABASE WRITE = FORBIDDEN
NO REAL TRADE
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


## PHASE B — TOOBIT BINDING CHECKPOINT STATUS
Status = CLOSED / VERIFIED / FOCUSED STATIC CONTRACT PASS

Verified scope on main:
- toobit_exchange_adapter_v0_1.py — replaceable Toobit-specific read-only adapter boundary.
- test_toobit_exchange_adapter_v0_1.py — focused adapter safety/contract tests.
- No arunda_pipeline.py wiring.
- No order/cancel/withdraw implementation; adapter write methods fail closed.
- No runtime/provider connectivity was performed.
- No DB mutation and no execution authorization.

Evidence:
- 6/6 focused adapter tests passed.
- py_compile passed for adapter and focused tests.
- git diff --check passed.
- Provider-authoritative Futures position state is preserved without local inference.
- Fix commits: 2f3a79a2 and 30485cb8.

Checkpoint closure: VERIFIED/CLOSED at the static/read-only adapter contract boundary. Runtime/provider API connectivity remains deferred to the later authorized controlled-test gate.


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

## CP46-A6 — MANAGEMENT DECISION / PROVIDER CAPABILITY BOUNDARY

Decision:
- The provider-native exposure investigation is CLOSED as an investigation.
- CP46-A6 itself remains BLOCKED / NOT VERIFIABLE at the current Toobit read-only provider boundary.
- No code weakening, inference, order-test, or execution workaround is approved.
- This blocker is classified as an external provider-capability dependency, not an ArundaTrader implementation defect.

Operational consequence:
- Final real-market controlled test remains execution-closed.
- EXECUTION AUTHORIZATION remains FALSE.
- The project must not manufacture an exposure authorization signal locally.
- The only valid unblock is new authoritative provider evidence or an explicit future management decision that changes the execution contract after separate approval.

# END PROJECT STATE


## CURRENT FRONTIER — EXCHANGE-AGNOSTIC ORDER PREPARATION HANDOFF

Status = BUILT / STATIC CONTRACT INTEGRATION — NOT EXECUTED

Management decision:
- The Core must complete the provider-neutral execution path without becoming dependent on Toobit.
- Toobit is one replaceable adapter, not the execution architecture.
- The missing Toobit-specific `exposure_allowed` Boolean is NOT allowed to become a permanent Core-completion blocker.
- Provider rejection remains valid environmental evidence once an explicitly authorized real order attempt is eventually opened.
- EXECUTION AUTHORIZATION remains FALSE.

Built:
- `exchange_execution_adapter_contract_v0_1.py` now defines an opaque `AdapterOrderPreparation` boundary.
- `exchange_execution_order_preparation_v0_1.py` validates the canonical request and delegates preparation to the selected adapter without inspecting provider fields.
- Toobit implements adapter-owned preparation, including provider-specific instrument resolution and quantity translation.
- Futures base-asset quantity is translated inside the adapter using provider contract multiplier; Core quantity remains unchanged.
- Spot market BUY translation is kept inside the adapter because Toobit's provider semantics use quote-asset quantity for that request form.
- No order endpoint is called by preparation.

Safety:
- EXECUTION AUTHORIZATION = FALSE
- ORDER WRITE = FORBIDDEN
- PROVIDER WRITE = FORBIDDEN
- DATABASE WRITE = FORBIDDEN
- `arunda_pipeline.py` remains unwired to Toobit.

Verification status:
- Tests were added for the generic adapter contract, exchange-neutral handoff, and Toobit-owned preparation.
- Local execution of the newly added tests has not yet been performed in this checkpoint environment; do not claim runtime PASS until the Builder runs them locally.

NEXT ACTION:
Run the focused local tests and static checks for the new exchange-neutral preparation boundary. If green, synchronize this checkpoint's four governance documents again with the verified evidence, then continue toward provider-order-attempt readiness without enabling execution.
\n\n## CP EXCHANGE-AGNOSTIC ORDER ATTEMPT BOUNDARY — VERIFIED\n\nStatus: VERIFIED / PASS / EXECUTION-CLOSED\n\nBuilt:\n- `exchange_execution_adapter_contract_v0_1.py` now includes the provider-neutral `submit_prepared_order` contract.\n- `exchange_execution_order_attempt_boundary_v0_1.py` establishes the final provider-neutral gate from prepared adapter order to a future provider order attempt.\n- Authorization is evaluated explicitly; readiness, adapter capability, account state, or provider metadata cannot infer authorization.\n- Toobit implements the prepared-submission surface but remains fail-closed with `EXECUTION_DISABLED_ORDER_SUBMISSION_NOT_IMPLEMENTED`.\n\nVerification:\n- Focused suite: 22 passed.\n- py_compile: PASS.\n- git diff --check: PASS.\n\nSafety:\n- EXECUTION AUTHORIZATION = FALSE.\n- No real order/cancel/withdrawal.\n- No DB mutation.\n- `arunda_pipeline.py` remains unwired.\n\nManagement verdict:\nThe provider-neutral order-attempt boundary is VERIFIED. The architecture can now reach a selected replaceable adapter only after explicit authorization, while actual provider submission remains separately disabled.\n\nNEXT ACTION:\nAdvance to the explicit execution-attempt contract/readiness gate without activating real execution.\n

## CP FINAL EXECUTION ATTEMPT CONTRACT — VERIFIED

Status = VERIFIED / PASS / EXECUTION-CLOSED

Built:
- `final_execution_attempt_contract_v0_1.py` composes the provider-neutral final execution-attempt path.
- The composition delegates readiness alignment, explicit authorization, adapter preparation, and adapter attempt to the already-verified boundaries.
- `test_final_execution_attempt_contract_v0_1.py` covers unauthorized blocking, authorized reachability of a replaceable adapter, and readiness/package mismatch blocking.

Verification evidence:
- 28/28 focused tests passed across the final contract, readiness, order-attempt boundary, order preparation, adapter contract, and Toobit adapter suites.
- py_compile passed for all focused implementation/test modules.
- git diff --check passed.
- Fast-forward from 91c82a7 to 448806f completed cleanly.

Safety and architecture:
- EXECUTION AUTHORIZATION = FALSE.
- Toobit remains replaceable and outside Core.
- No real order/cancel/withdrawal.
- No DB mutation.
- `arunda_pipeline.py` remains unwired.
- Toobit submission remains fail-closed.
- No authorization is inferred or created by the final contract.

Management verdict:
The provider-neutral execution-attempt composition is VERIFIED. The system can prove the complete pre-attempt route while real execution remains explicitly disabled.

CURRENT FRONTIER:
Controlled decision for the separately authorized real execution-attempt gate; no automatic activation.
