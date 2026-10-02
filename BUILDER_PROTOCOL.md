# ARUNDA TRADER — BUILDER PROTOCOL

## PURPOSE
Single operating protocol for any Builder, coding agent, Manager, or future ChatGPT session working on ArundaTrader.

## START OF EVERY SESSION
Read these files from the repository before making project decisions:
1. PROJECT_STATE.md
2. ARCHITECTURE.md
3. CHECKPOINTS.md
4. CURRENT_FRONTIER.md
5. BUILDER_PROTOCOL.md
6. MANAGEMENT_ROADMAP.md

Do not reconstruct project state from chat history when repository state is available.

## AUTHORITY
Management controls:
- frontier selection
- scope
- runtime authorization
- database writes
- execution
- architecture changes
- changes to protected files/contracts
- creation of project branches
- addition of project files
- route changes and checkpoint sequencing
- project-completion declaration
- exchange binding
- final real-trading authorization

Builder executes the authorized scope. Builder does not promote a task to a new frontier by itself.

## FINAL PROJECT LIFECYCLE — NON-NEGOTIABLE
The project goal is real trading. The project must first become complete as an exchange-agnostic system.

Mandatory sequence:
1. COMPLETE the exchange-agnostic project/core through the approved roadmap.
2. Explicitly close the project-completion gate.
3. Only then BIND an exchange through an adapter/environment boundary.
4. Perform final real-market exchange integration and controlled testing.
5. Only after final acceptance and explicit Management authorization may real trading be enabled.

No Builder, Manager, or implementation agent may move exchange binding, final exchange testing, or real trading into an earlier phase merely to accelerate delivery.
Exchange-specific behavior must not be moved into the exchange-agnostic core.

## ROADMAP DISCIPLINE — NON-NEGOTIABLE
The roadmap is the only path for project advancement.

No Builder, coding agent, or Manager may:
- create a new project branch for personal workflow, experimentation, convenience, or an unapproved parallel path;
- create or introduce a file that is outside the explicitly authorized checkpoint scope;
- add generated output, temporary files, backups, quarantine copies, forensic artifacts, review dumps, or unrelated code to Canonical project truth;
- start a new checkpoint, change the active frontier, redesign an architecture boundary, reorder the lifecycle, or create a parallel implementation without an explicit Management decision recorded in repository state;
- treat a personal branch or unrecorded file as project truth;
- declare a checkpoint complete while the required repository state synchronization is missing;
- advance to the next frontier while the previous checkpoint's state is undocumented or inconsistent.

A new branch is permitted only when Management explicitly authorizes it as part of the active roadmap/checkpoint. Its purpose, source, target checkpoint, and relationship to Canonical must be recorded before it is treated as project work.

A new file is permitted only when it has a defined responsibility, is required by the active checkpoint, and is recorded in the authorized scope. If a file is not needed by the roadmap, it does not enter Canonical.

When uncertain: STOP. Do not improvise. Escalate to Management.

## STATE LANGUAGE
Use:
- BUILT
- VERIFIED
- CURRENT FRONTIER
- BLOCKED
- NEXT ACTION

CLOSED / VERIFIED is not CURRENT unless Management explicitly authorizes regression investigation.

## MANDATORY CHECKPOINT CLOSURE / ROUTE SYNCHRONIZATION
At the end of EVERY checkpoint, the responsible Builder/Manager MUST update and synchronize, as applicable:
1. PROJECT_STATE.md
2. CURRENT_FRONTIER.md
3. CHECKPOINTS.md
4. MANAGEMENT_ROADMAP.md

The synchronized state must record:
- BUILT
- VERIFIED
- CLOSED / BLOCKED / NOT VERIFIED as applicable
- verification evidence
- blocker, if any
- CURRENT FRONTIER
- NEXT ACTION
- authorized branch/file scope, if changed

For EVERY route/frontier change, the same synchronization is mandatory immediately. The route change must include its reason and Management authorization.

A checkpoint is not governance-complete until the state documents are synchronized and internally consistent.
A missing state update blocks closure. An unsynchronized route change blocks activation of the new route. Reporting to Management does not substitute for repository synchronization.

## CHANGE DISCIPLINE
Before modifying anything:
- identify the active frontier
- identify the exact file/surface in scope
- verify that the change does not cross a protected boundary
- verify that the change is required by the active roadmap/checkpoint
- preserve existing contracts unless the active checkpoint explicitly authorizes contract change
- verify that every new branch/file is explicitly authorized and documented

After every completed checkpoint, update the canonical repository state before starting any next-frontier work.

## PROTECTED SURFACES
Treat these as protected unless explicitly authorized:
- production database
- arunda_pipeline.py
- execution controls
- order submission/cancellation
- withdrawal
- closed/verified contracts
- backup/quarantine artifacts

## RUNTIME RULE
Never run a runtime merely because it is available.
Runtime authorization must be explicit when the current frontier requires it.
Never repeat a forbidden or exhausted diagnostic runtime without new authorization.

## DATA RULE
Never create synthetic production evidence.
No interpolation, forward-fill, back-fill, padding, fabricated fallback, or silent source blending.
Fail closed when required real evidence is unavailable or unverifiable.

## EXCHANGE RULE
Exchange adapters are replaceable boundaries.
Never move exchange-specific behavior into core logic.
Toobit is not the architectural center of ArundaTrader.
Exchange binding is a later lifecycle stage and cannot precede explicit exchange-agnostic project completion.

## REPORTING RULE
Do not flood Management with repeated audits or historical reports.
Management may request a detailed report when needed; otherwise Builder should continue the authorized path without unsolicited full reports.
Repository State maintenance is mandatory and is not replaced by reporting.
When reporting is requested, provide only:
- current state
- evidence
- blocker if any
- next action

## EVIDENCE RULE
No checkpoint may be recorded as CLOSED / VERIFIED without appropriate evidence.
A design-only result must remain DESIGN PASS until independently verified.

## FAILURE RULE
When a problem is found:
1. identify the smallest provable cause
2. fix only within authorized scope
3. verify the fix
4. continue to the active frontier

Do not redesign, reset, or restart the project because of a local adapter problem.

## NEW BUILDER HANDOFF
A Builder joining the project must first establish:
- repository state from the canonical documents
- active frontier from CURRENT_FRONTIER.md
- roadmap position from MANAGEMENT_ROADMAP.md
- protected boundaries
- exact authorized action
- authorized branch/file scope, if any

If the documents and chat disagree, do not silently overwrite repository truth. Escalate the discrepancy to Management.

## STATE HANDOFF RULE
The repository state documents are the Builder handoff source of truth. Every closed checkpoint, verified evidence state, blocker, current frontier, route change, and project-lifecycle transition must be reflected there. Reporting to Management does not substitute for updating the repository state.

## CANONICAL INTEGRITY RULE
Canonical is one controlled project truth.
Historical branches may be preserved for provenance, but they do not become active project truth without Management authorization.
No one is permitted to "dance around" the roadmap by creating side branches, duplicate implementations, or extra files.
No personal workflow is a project exception.

# END BUILDER PROTOCOL


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
