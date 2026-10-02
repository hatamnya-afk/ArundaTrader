# ARUNDA TRADER — ARCHITECTURE

## ARCHITECTURAL IDENTITY
ArundaTrader is exchange-agnostic and modular. Exchange providers are replaceable environments behind an adapter boundary.

## CORE
CORE → MARKET INTELLIGENCE → OPPORTUNITY → SIGNAL → DECISION → SMART RISK MANAGEMENT → TRADE GATE → ORDER INTENT → EXCHANGE CONSTRAINTS → PRE-EXECUTION AUTHORIZATION

The core produces exchange-neutral trading intent. Provider-specific API behavior must not define core logic.

## CP38 PRE-EXECUTION ARCHITECTURE
The verified provider-neutral pre-execution chain is:
REAL CAPITAL OBSERVATION → VALIDATED ENTRY/STOP → VALIDATED RISK POLICY → PORTFOLIO OBSERVATION → SMART RISK → TRADE GATE → ORDER INTENT BOUNDARY → EXCHANGE CONSTRAINTS → CONSTRAINT EVALUATION → EXECUTION AUTHORIZATION BOUNDARY.

CP38-B is DESIGN PASS only; it is not independently verified.

Execution Authorization is a logical pre-execution boundary only. It does not enable execution or submit an order.

## EXCHANGE BOUNDARY
Core → Exchange Adapter Boundary → Provider Adapter → Exchange API

Toobit is one adapter implementation. It is not a required dependency of the core.

## DATA CONTRACT
Production data must be real and traceable.

Required principles:
- one candle = one source
- provenance preserved
- no synthetic values
- no interpolation
- no forward-fill
- no back-fill
- no fabricated padding
- no silent cross-source blending
- fail closed when required data cannot be verified

## UNIVERSE
Global Universe and provider-specific exchange universes are distinct.
An adapter may report its available symbols, but it must not redefine the global core universe.

## SMART RISK MANAGEMENT
Risk is a core decision layer, not an exchange feature.

It must be:
- provider-neutral
- contract-driven
- logically explainable
- independent of Toobit API details
- evaluated before Trade Gate

## CAPITAL
Production capital must come from REAL_CAPITAL.
Legacy/test capital configuration is non-production.
No verified real capital → fail closed.

## DATABASE
The production database is stateful infrastructure. Database mutation requires explicit authorization.

## EXECUTION
Execution is NOT BUILT / NOT AUTHORIZED in the current state. An adapter connection or pre-execution authorization boundary does not authorize execution. Order submission, cancellation, withdrawal and other exchange writes remain disabled unless explicitly authorized.

## TOOBIT ACCOUNT BLOCKER
The observed Toobit Account path remains blocked by HTTP/API -1022 INVALID_SIGNATURE. This is an independent production Account/Real-Capital source blocker. No blind signing patch is justified without new evidence and explicit authorization.

## PROHIBITED DRIFT
Do not:
- move core logic into an exchange adapter
- make Toobit mandatory
- couple Risk to exchange API quirks
- change closed contracts merely to accommodate an adapter
- redesign the pipeline because of an adapter problem
- introduce synthetic market data
- modify arunda_pipeline.py without explicit authorization

# END ARCHITECTURE


---

# 2026-10-02 — MASTER BUILDER HANDOFF / CURRENT SOURCE OF TRUTH

> **LATEST FORWARD OVERRIDE.** This section exists specifically so a future Builder can continue after chat/context loss without reconstructing project truth from conversation memory. Historical sections above remain preserved as provenance. Do not reinterpret them as the current frontier when they conflict with this section.

## 1. CANONICAL REPOSITORY STATE

- Repository: `hatamnya-afk/ArundaTrader`
- Active controlled branch: `sync/local-project-20260917`
- Latest verified **implementation** HEAD before this documentation sync: `40819760b517614e628b46cdfd1440ca80fd78d6`
- Implementation commit: `CP49: isolate account observation failures per execution request`
- This handoff/documentation sync then advanced the same controlled branch with documentation-only commits; the latest documentation-sync commit is recorded by Git history.
- No code/runtime/DB/execution claim is changed by the documentation sync.
- Local untracked/backup/DB artifacts are **not** project truth and must not be modified, deleted, cleaned, or promoted without explicit authorization.

## 2. WHAT IS CLOSED — DO NOT REOPEN

- CP39 Capital Independence = **CLOSED / VERIFIED / LOCKED**
- Zero-Capital Contract = **CLOSED / VERIFIED / LOCKED**
- CP44 = **VERIFIED / PASS / CLOSED**
- CP46-A..H = **CLOSED / VERIFIED / CANONICAL**
- CP47 = **CLOSED / VERIFIED / CANONICAL**
- CP48 = **CLOSED / VERIFIED / CANONICAL**
- CP64..CP71 = **CLOSED / VERIFIED / CANONICAL**
- CP69 observation contract = **CLOSED / CANONICAL**; current work is operational wiring/continuity, not checkpoint reopening.
- Historical CP44 MHA/context blockers and historical BUY-rule investigation are historical evidence only.
- Never reopen a closed checkpoint because chat context is lost. Require direct regression evidence.

## 3. CORE ARCHITECTURAL INVARIANTS

ArundaTrader is an exchange-agnostic real-market decision system.

Canonical intelligence lifecycle:

`REAL MARKET → DYNAMIC UNIVERSE → OPPORTUNITY → SIGNAL → VALIDATION → FUSION → SCORE → DECISION BIRTH → RISK → POSITION SIZING → TRADE GATE → TRADE READY → ORDER INTENT → CANONICAL ORDER REQUEST → EXECUTION BOUNDARY → PROVIDER → OBSERVATION`

The Trader is **capital-independent**:

`TRADER BEHAVIOR ≠ ACCOUNT CAPITAL STATE`

`CAPITAL INJECTION ≠ TRADER LOGIC CHANGE`

`CAPITAL INCREASE ≠ PERMISSION TO THINK / DECIDE / ANALYZE`

Capital is external Management state. The Trader must continue to observe/analyze/decide/risk/size/gate/build order intent even when observed real account capital is zero, where the established contracts permit it.

The Toobit account is an environment/account boundary, not Trader intelligence.

## 4. ZERO-CAPITAL REAL-ORDER OPERATING MODEL — CURRENT GOVERNANCE

The intended real-market lifecycle is:

`REAL MARKET → TRADER INTELLIGENCE → DECISION → RISK / POSITION SIZING → TRADE GATE → TRADE READY → ORDER INTENT → CANONICAL ORDER REQUEST → REAL TOOBIT ORDER REQUEST → TOOBIT PROVIDER RESPONSE → OBSERVE + RECORD + ANALYZE`

When account capital is zero:
- Trader does **not** switch to a laboratory/research mode.
- Trader does **not** synthesize a local insufficient-balance result.
- Trader may issue the same real order request through the real execution boundary.
- Toobit is responsible for accepting or rejecting the request against the actual account state.
- A provider rejection such as insufficient balance is valid real-world execution evidence and must be preserved.
- No local fake `INSUFFICIENT_BALANCE` is permitted.
- After sufficient evidence is collected, Management may independently decide whether and how much capital to place in the Toobit account.
- Capital injection does not modify Trader logic, strategy, Decision rules, Risk/Sizing architecture, or Intelligence.

**Important:** Capital authorization is not a prerequisite for Trader intelligence and is not a substitute for execution authorization. Execution remains a separate technical/control boundary.

## 5. CURRENT EXECUTION BRIDGE

The already-built bridge is:

`Canonical Order Request → CP46-D Provider Preflight → CP46-E Execution Eligibility → CP49 Readiness/Safety Gate → Toobit Live Transport → Real Provider Response → CP69 Execution Evidence`

Relevant implementation surfaces:
- `cp49_live_execution_bridge_v0_1.py`
- `exchange_execution_boundary.py`
- `toobit_spot_order_live_transport_v0_1.py`
- `toobit_trading_adapter.py`
- `cp49_first_execution_readiness_v0_1.py`
- `cp49_first_execution_evidence_contract_v0_1.py`
- `cp69_runtime_observation.py`

Current bridge properties:
- Real Toobit order endpoint is `POST /api/v1/spot/order`.
- `/api/v1/spot/orderTest` is forbidden.
- No local synthetic insufficient-balance result exists.
- Provider response code/message are preserved.
- Per-order account/provenance observation failures now fail closed for that request instead of terminating the whole pipeline.
- Repeated distinct order submissions are supported after the one-time first activation boundary is already enabled.
- Execution remains fail-closed unless the explicit Management execution control is active.

Current explicit Management execution control used for the authorized runtime:
`ARUNDA_EXECUTION_MANAGEMENT_AUTHORIZED=TRUE`

This is **execution authorization only**, not capital authorization.

## 6. LATEST REPAIRS

### CP49 account identity
Commit `d16d614` established authoritative Toobit account identity resolution:
1. authenticated `/api/v1/account` `accountId`, when present;
2. otherwise one authenticated `/api/v1/account/balanceFlow` lookup;
3. never synthesize an account ID.

### Provenance repair
Commit `dbc48e9950c97ff170cb1082b2ba18de2fe7230d` changed optional account provenance to be fail-closed:
- absent identity means omit `source_id`;
- never emit `source_id=None`;
- no synthetic provenance.

### Per-request fault isolation
Commit `40819760b517614e628b46cdfd1440ca80fd78d6` isolates account observation/API-key failures inside each execution request:
- request becomes `CP49_ACCOUNT_OBSERVATION_FAILED`;
- unsafe write is not permitted;
- other candidates/requests must not be terminated by this single failure.

This is part of the intended 24/7 operating model:
`Order A error → BLOCKED → continue; Order B provider response → continue; Order C error → BLOCKED → continue`

Do not redesign the architecture merely because one provider/account request fails.

## 7. CP69 OBSERVATION

Canonical observation:
- schema: `arunda.runtime_observation`
- producer: `cp69_runtime_observation.py`
- stream: `runtime_observations/arundatrader_runtime_observations.jsonl`
- append-only evidence
- `EXECUTION=ON` is valid when a real provider attempt occurred.
- `REAL_ORDER=True` means a real provider request was submitted.
- `REAL_TRADE=True` means provider accepted/executed the order.
- Valid provider-rejection state is therefore possible:
  `EXECUTION=ON, REAL_ORDER=True, REAL_TRADE=False`.
- `EXECUTION=OFF` with `REAL_ORDER=True` is invalid.
- No DB-write boundary may be claimed when `DB_WRITES=0`.

CP69 producer tests were verified at **14/14 PASS** before the latest authorized runtime.

## 8. LAST RUNTIME STATUS — DO NOT INVENT THE RESULT

A controlled runtime was authorized after the latest static verification with:

`$env:ARUNDA_EXECUTION_MANAGEMENT_AUTHORIZED="TRUE"`

followed by:

`python .\arunda_pipeline.py`

The runtime was started, but its final console result has **not been supplied/recorded in the current governance state**.

Therefore:
- Do **not** claim a Toobit acceptance.
- Do **not** claim an insufficient-balance rejection.
- Do **not** claim a real trade.
- Do **not** claim a provider failure.
- Do **not** run a second runtime/retry merely to discover the missing result.
- First obtain the actual runtime output/evidence from Management, then record the result once.

## 9. CURRENT FRONTIER

**TRADER COMPLETION → REAL-MARKET E2E OUTPUT PROOF → OUTPUT OBSERVATION/CONSUMPTION → OUTPUT ANALYSIS → MANAGEMENT CAPITAL DECISION**

Immediate technical frontier:

`Canonical Order Request → real execution boundary → real Toobit response → CP69 evidence`

Then:

`CP69 canonical observation → Trader UI → Aroonda consumer → analysis/explanation/gap detection`

Only after Trader evidence is analyzed does Management decide whether/how much capital to place in the account.

## 10. AROONDA BOUNDARY

ArundaTrader remains the execution authority.

Aroonda:
- observes;
- consumes canonical observations;
- analyzes;
- explains;
- detects capability gaps;
- proposes/learns within governance.

Aroonda must not silently mutate Trader history/contracts or take over exchange execution.

Post-CP71 route:
`Trader Integration → CP69 Operational Wiring → Read-only E2E Observation → Aroonda Analysis → CP72 Controlled Self-Improvement → CP73 Multi-Environment Generalization → CP74 Controlled Autonomy Expansion → CP75 Self-Directed Growth Gate`

## 11. HARD PROHIBITIONS

- No synthetic/fill/backfill/interpolation/forward-fill/padding/blending.
- No synthetic decision identity.
- No synthetic capital or quantity.
- No DB repair/change.
- No strategy redesign to solve an execution/account adapter issue.
- No exchange-specific logic in Core.
- No reopening closed checkpoints.
- No automatic retry after a failed runtime.
- No reset/rebase/clean/delete/force operations.
- No modification/deletion of known Local untracked or backup artifacts.
- No execution activation merely because the roadmap says it is next; explicit control remains required.
- No claim of runtime/provider/trade outcome without evidence.

## 12. BUILDER START PROTOCOL

A new Builder must read, in this order:

1. `PROJECT_STATE.md`
2. `ARCHITECTURE.md`
3. `CHECKPOINTS.md`
4. `CURRENT_FRONTIER.md`
5. `BUILDER_PROTOCOL.md`
6. `MANAGEMENT_ROADMAP.md`
7. this latest handoff section.

Then:
- establish actual branch/HEAD;
- inspect the latest commit;
- identify the exact active frontier;
- inspect only the files required by that frontier;
- do not re-audit closed stages;
- do not infer missing facts from chat memory;
- if repository state and chat disagree, repository governance wins until Management resolves the discrepancy.

## 13. MANAGEMENT RULE

`BUILD → VERIFY → RECORD → ADVANCE`

The repository must remain self-explanatory enough that a Builder can continue safely after context truncation without reconstructing project truth from conversational memory.

# END 2026-10-02 MASTER BUILDER HANDOFF
