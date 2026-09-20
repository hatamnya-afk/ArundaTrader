# ARUNDA TRADER — PROJECT STATE

## PURPOSE
Canonical repository-level source of truth for ArundaTrader. Chat memory is not authoritative when these documents are available.

## PROJECT IDENTITY
ArundaTrader is a modular, layered, **profit-seeking and exchange-agnostic** real-market analysis and trading-decision system.
Toobit is an exchange adapter/environment, not the project core.

## CORE OPTIMIZATION PRINCIPLE
The system seeks maximum validated profit-opportunity capture. Risk management is an intelligence/control layer for invalidation, exposure, liquidity, portfolio state, and allocation quality; it is not a universal minimum-risk objective or an arbitrary fixed profit ceiling.

Capital amount is a scale/input boundary, not a fixed architecture assumption. Opportunity logic must remain valid across different valid capital amounts.

Capital allocation is an output of validated opportunity intelligence and constraints. The architecture does not impose a universal 20%, 50%, 0.5%, or other fixed allocation ceiling. Allocation may be 0% through 100% when the complete validated state supports that result.

## EXCHANGE-AGNOSTIC CORE BOUNDARY
The provider-neutral route is:

```text
REAL MARKET DATA
→ DYNAMIC UNIVERSE
→ OPPORTUNITY
→ SIGNAL
→ SCORE
→ DECISION
→ PROFIT / OPPORTUNITY INTELLIGENCE
→ ENTRY + INVALIDATION / STOP
→ SMART RISK
→ CAPITAL ALLOCATION
→ POSITION SIZING
→ TRADE GATE
→ TRADE READY
→ ORDER INTENT
→ PRE-EXECUTION
→ EXCHANGE-AGNOSTIC BOUNDARY
```

No exchange adapter may become a dependency of the Core before the exchange-agnostic boundary.

## PRODUCTION BOUNDARY
LAUNCH_TIMESTAMP = 2026-08-31T00:00:00+00:00
Production analysis uses real post-launch data only.

## EXECUTION SAFETY
EXECUTION AUTHORIZATION = FALSE
ORDER WRITE = FORBIDDEN
WITHDRAW = FORBIDDEN
DATABASE WRITE = FORBIDDEN unless explicitly authorized
Exchange writes = FORBIDDEN
Signature work = FORBIDDEN
Credentials and secrets must never be exposed.

## CLOSED / VERIFIED CHECKPOINTS
CP38 = CLOSED / VERIFIED / PASS
CP39 = CLOSED / VERIFIED / PASS
CP40 = CLOSED / VERIFIED / PASS
CP41 = CLOSED / VERIFIED / PASS
CP43 = CLOSED / VERIFIED / PASS

Closed checkpoints are historical truth. They must not be reopened or re-audited unless Management identifies a direct, provable regression.

## CURRENT PROJECT STATE
CURRENT FRONTIER: CP44 — REAL-MARKET CONTROLLED TEST

CP44 = MANAGEMENT-AUTHORIZED / IMPLEMENTATION VERIFIED / REAL-MARKET CONTROLLED TEST EXECUTED / BLOCKED / NOT VERIFIED / NOT CLOSED.

## CP44 IMPLEMENTATION VERIFICATION
The authorized CP44 downstream implementation is present on branch `sync/local-project-20260917` at HEAD `b9c029ed7ef1da9a7d7fb53617769a35b8280246`.
Verified implementation surfaces:
- `dynamic_smart_risk_contract_boundary_v0_1.py`
- `entry_invalidation_boundary_v0_1.py`
- `smart_risk_contract_v0_1.py`
- `smart_risk_engine_v0_1.py`
- `test_smart_risk_engine_v0_1.py`

Evidence:
- All five CP44 surfaces compiled successfully with Python 3.13.15.
- Existing Smart Risk test exited `0`.
- Corrected Dynamic Smart Risk boundary test exited `0` and emitted `CP44_DYNAMIC_BOUNDARY_PASS`.
- Verified dynamic asset `BTC/USDT`, LONG direction, explicit entry `100000.0`, invalidation `99000.0`, stop distance `1000.0`, APPROVED risk state, and snapshot cardinality `1 → 1`.
- No order, execution, API write, or production DB write occurred.

This is contract/boundary verification evidence only. It does not constitute CP44 real-market closure.

## CP44 REAL-MARKET CONTROLLED RUNTIME
The single authorized CP44 real-market controlled runtime was executed from the established downstream eligibility boundary.

Observed blocker:
`INSUFFICIENT_CONTIGUOUS_CONTEXT:MHA/USDT:7`

Required minimum context:
`MIN_CONTEXT = 21`

The runtime therefore failed closed before a valid downstream real-market Entry + Invalidation/Stop → Smart Risk → Trade Gate → Trade Ready chain could be proven for CP44.

This is the authoritative CP44 runtime result. No second CP44 runtime is authorized until the blocker is resolved and Management explicitly authorizes readiness for another controlled run.

## CP44 ACCEPTANCE BOUNDARY
REAL_MARKET_DATA
VALIDATED_OBSERVATIONS
REAL_CAPITAL_BOUNDARY
VALID_ENTRY
VALID_STOP_OR_INVALIDATION
PROFIT_OPPORTUNITY_ASSESSMENT
INTELLIGENT_CAPITAL_ALLOCATION
VALID_QUANTITY
VALID_EXPOSURE
DECISION_CONSISTENCY
TRADE_INTENT_CONSISTENCY
CONSTRAINT_READINESS
PROVENANCE
FAIL_CLOSED
DYNAMIC_ASSET
DYNAMIC_CARDINALITY
SCALE_INDEPENDENT_LOGIC
NO_TEST_DATA
NO_FIXED_15
NO_FIXED_RUNTIME_CARDINALITY
NO_ORDER
NO_AUTHORIZATION
NO_EXECUTION
NO_API_WRITE
NO_DB_WRITE
NO_EXCHANGE_DEPENDENCY_BEFORE_BOUNDARY

## REPOSITORY CONSOLIDATION STATE
CONSOLIDATION GATE = CLOSED / MANAGEMENT-AUTHORIZED
CANONICAL BRANCH = main
The Local Original at `C:\Users\ASUS\ArundaTrader` remains the primary operational/recovery object.
GitHub is the controlled durable project-management, state, provenance, and Builder-handoff source.
The synchronization branch `sync/local-project-20260917` is authorized for the current controlled roadmap/governance work.

Repository organization is conservative and classification-first:
- Governance/control documents remain at repository root because their paths are part of the control contract.
- Operational source paths are preserved; no mass relocation is performed without dependency/path audit.
- Verification, evidence/forensic, and historical material have explicit navigation/classification locations.
- `README.md` is the repository entrypoint and `REPOSITORY_STRUCTURE.md` defines organization rules.

No Local database or Local backup is to be deleted or altered by this synchronization.
Database files are excluded from the GitHub synchronization snapshot.

## PROTECTED SURFACES
- arunda_pipeline.py
- production database
- execution controls
- order submission/cancellation
- withdrawal
- closed/verified contracts
- backup/quarantine artifacts

## NON-NEGOTIABLE RULES
- Real data only.
- No synthetic data, interpolation, forward-fill, back-fill, padding, fabricated fallback, or silent source blending.
- Provenance is required.
- Fail closed when required real data cannot be verified.
- Core remains exchange-agnostic.
- Read-only layers remain read-only unless a writer is explicitly authorized.
- Do not modify `arunda_pipeline.py` without explicit authorization.
- Do not modify the production DB without explicit authorization.
- Do not reopen closed checkpoints without proven regression.
- No unapproved branch or file may become project truth.
- Temporary, generated, backup, quarantine, forensic, review, and unrelated artifacts must be classified before canonical promotion.
- The roadmap is the only path for project advancement.

## MANDATORY CHECKPOINT / ROUTE SYNCHRONIZATION
At the end of every checkpoint, the responsible Builder/Manager must update:
1. PROJECT_STATE.md
2. CURRENT_FRONTIER.md
3. CHECKPOINTS.md
4. MANAGEMENT_ROADMAP.md

The update must record BUILT, VERIFIED, CLOSED / BLOCKED / NOT VERIFIED, evidence, blocker, CURRENT FRONTIER, NEXT ACTION, and any authorized branch/file scope.

Until synchronization is complete and internally consistent, the checkpoint is not governance-complete and the next frontier must not start.

## SOURCE-OF-TRUTH ORDER
1. Repository state documents
2. Verified contracts and code
3. Git history
4. Chat context

## BUILDER / MANAGEMENT START RULE
Before acting, read:
- PROJECT_STATE.md
- ARCHITECTURE.md
- CHECKPOINTS.md
- CURRENT_FRONTIER.md
- BUILDER_PROTOCOL.md
- MANAGEMENT_ROADMAP.md

Continue only from the active frontier recorded in the repository. If repository documents and chat disagree, stop and escalate to Management.

## NEXT ACTION
1. Resolve the real-data continuity blocker for `MHA/USDT` without fabricating, interpolating, filling, padding, or backfilling production context.
2. Do not rerun CP44 merely to retrieve metrics; a second controlled runtime requires the blocker to be resolved and explicit Management readiness.
3. Once readiness is explicitly established, execute the single next authorized CP44 real-market controlled runtime from the established downstream ELIGIBLE boundary.
4. Preserve all safety boundaries: no order, execution, API write, or DB write.
5. Synchronize all four governance documents again at CP44 completion before closure.

## CP44 BOOTSTRAP PATCH VERIFICATION — 2026-09-17

Authorized minimal repair applied to the local market_arm_contiguous_history_accumulation_v1_1.py bootstrap gate.

Purpose:
- allow the local canonical Fabric Store to be created on first bootstrap;
- preserve the approved Store module as the owner of storage/schema initialization;
- remove the premature FABRIC_DB_NOT_FOUND existence gate.

Verification:
- python -m py_compile .\\market_arm_contiguous_history_accumulation_v1_1.py
- CP44_BOOTSTRAP_PATCH_COMPILE=PASS
- Python compile exit code: 0

Scope:
- only the Fabric DB bootstrap existence gate was changed;
- Dynamic Production Universe and Eligibility were not modified;
- KuCoin discovery and real OHLCV fetch were not modified;
- CEX/DEX architecture was not modified;
- arunda.db was not opened or modified;
- arunda_pipeline.py was not modified;
- no order, execution, API write, or production DB write occurred.

This verification does not authorize or constitute a second CP44 real-market runtime.

__pycache__ generated by compilation is temporary and is not project truth.

## NEXT ACTION
1. Perform static/diff verification of the authorized bootstrap patch.
2. Keep CP44 second runtime forbidden until static/diff verification is complete and Management explicitly authorizes readiness.
3. Then, only if readiness is explicitly established, execute the single next controlled CP44 runtime.


## CP44 FABRIC SCHEMA BOOTSTRAP — LOCAL COMPILE VERIFICATION — 2026-09-18

VERIFIED:
- `python -m py_compile .\\market_arm_contiguous_history_accumulation_v1_1.py` exited 0.
- `CP44_FABRIC_SCHEMA_BOOTSTRAP_COMPILE=PASS`.
- The patched accumulation file is syntactically valid after the Fabric schema bootstrap repair.

STATUS:
CP44 remains MANAGEMENT-AUTHORIZED / IMPLEMENTATION PATCHED / BLOCKED / NOT VERIFIED / NOT CLOSED.

SAFETY:
No CP44 real-market runtime was executed by this verification. No order, execution, API write, exchange write, production DB write, or `arunda_pipeline.py` modification occurred.

NEXT ACTION:
Static/diff verification of the exact authorized patch, then resolve the real contiguous-context blocker for `MHA/USDT`. A second CP44 runtime remains forbidden until blocker resolution and explicit Management readiness.

## CP44 PROVIDER-CONSISTENCY PATCH — 2026-09-18

BUILT:
- `market_arm_contiguous_history_accumulation_v1_1.py` now handles the exact KuCoin response `Unsupported trading pair` as a per-market fail-closed skip.
- Other dynamically discovered markets continue processing; no candle is fabricated or substituted.

VERIFIED:
- `production_universe_binding.py` remains unchanged; dynamic discovery/eligibility remains intact.
- No hardcoded asset removal, provider fallback, symbol reconstruction, synthetic data, interpolation, fill, padding, or backfill was introduced.
- Production DB, `arunda_pipeline.py`, order, execution, and exchange-write paths remain untouched.
- Patch is isolated to the accumulation loop.

STATUS:
CP44 remains MANAGEMENT-AUTHORIZED / IMPLEMENTATION PATCHED / NOT RUNTIME-VERIFIED / BLOCKED / NOT CLOSED.

CURRENT BLOCKER:
The latest accumulation attempt aborted at `BSV/USDT:Unsupported trading pair`; this patch converts that exact condition to explicit `PROVIDER_UNSUPPORTED_PAIR=SKIPPED_FAIL_CLOSED` rather than aborting the whole dynamic run. The authoritative CP44 runtime blocker remains `INSUFFICIENT_CONTIGUOUS_CONTEXT:MHA/USDT:7`, `MIN_CONTEXT=21`.

NEXT ACTION:
1. Local compile/static verification of this exact patch.
2. If compile/static verification passes, continue real-data accumulation; no second CP44 controlled runtime yet.
3. Only after the real-data blocker is resolved and Management explicitly authorizes readiness may the next single CP44 controlled runtime occur.

SAFETY:
No second CP44 controlled runtime, no production DB write, no order, no execution, no API write, and no exchange write occurred during this patch.

## CP44 BOOTSTRAP SCHEMA INITIALIZATION — 2026-09-18

Authorized minimal follow-up repair implemented after static review identified that the approved Store module exposes CREATE_SQL but initializes its schema only inside its fixture verification main().

BUILT:
- market_arm_contiguous_history_accumulation_v1_1.py now performs a Fabric-only schema bootstrap through store.CREATE_SQL before opening the accumulation connection.
- The bootstrap creates the Fabric directory if absent, executes only the approved CREATE_SQL, commits the schema transaction, and closes the bootstrap connection.

VERIFIED:
- Source and approved Store module were inspected on sync/local-project-20260917.
- Store schema contract is CREATE_SQL for canonical_ohlcv.
- The patch does not execute store.main() and does not insert REAL_CANDLE fixture data.
- Production DB remains outside the code path.
- No runtime was executed after this patch.

STATUS:
CP44 = MANAGEMENT-AUTHORIZED / IMPLEMENTATION PATCHED / NOT RUNTIME-VERIFIED / BLOCKED / NOT CLOSED.

BLOCKER:
INSUFFICIENT_CONTIGUOUS_CONTEXT:MHA/USDT:7 with MIN_CONTEXT = 21 remains the authoritative real-market blocker.

NEXT ACTION:
1. Local Python compile/static verification of the patched accumulation file.
2. Resolve the real-data continuity blocker without fabrication, interpolation, fill, padding, or backfill.
3. Only after explicit Management readiness, execute the single next controlled CP44 runtime.

SAFETY:
No arunda.db access/write, no arunda_pipeline.py modification, no order, no execution, no API write, no exchange write, and no second CP44 runtime occurred.

# END PROJECT STATE

## CP44 — CURRENT STATE RECONCILIATION — 2026-09-20

**STATUS:** BLOCKED / NOT VERIFIED / NOT CLOSED

### Latest verified evidence

The previously recorded contiguous-context blocker
INSUFFICIENT_CONTIGUOUS_CONTEXT:MHA/USDT:7 with MIN_CONTEXT = 21
has been resolved through real-data historical discovery and contiguous accumulation.
The historical blocker record remains preserved above as historical evidence and must
not be interpreted as the current CP44 blocker.

Verified controlled accumulation evidence:

- ADX/USDC: RUN=50
- INSERTED=50
- LATEST_CLOSED=1789365600
- CHECKPOINT_COMMITTED=ADX/USDC
- MARKET_ARM_READY=True
- PRODUCTION_DB_TOUCHED=False
- SIGNAL_CHAIN_EXECUTED=False
- ORDER_INTENTS=0
- EXECUTION=OFF
- no order write
- no execution
- no API write
- no exchange write

This establishes that the authorized real-data accumulation path can reach the
required contiguous context without synthetic data, interpolation, fill, padding,
fabrication, backfill, or gap bridging.

### Current CP44 frontier

CP44 is **not closed** by the accumulation result alone. The remaining verification
boundary is the downstream production-compatible controlled chain after established
real-data eligibility, including the authorized Entry / Invalidation-Stop / Smart Risk /
Trade Gate / Trade Ready contract path.

No premature CP44 closure is permitted.

### Current next action

1. Preserve the successful accumulation evidence above.
2. Complete the remaining static/contract reconciliation required for the downstream
   CP44 controlled path.
3. Only after explicit Management readiness, execute the single next authorized
   CP44 real-market controlled runtime from the established downstream ELIGIBLE
   boundary.
4. Do not modify runda.db or runda_pipeline.py.
5. Do not introduce synthetic/fill/interpolation/padding/backfill data.
6. Do not execute orders or enable execution.

The previous MHA/USDT:7 blocker and the earlier no-second-runtime restriction remain
historical records; they do not override this newer verified accumulation evidence.

## CP44 — SMART RISK COMPATIBILITY REPAIR — 2026-09-20

### VERIFIED

The authorized CP44 minimal Smart Risk compatibility repair has completed
technical verification.

VERIFIED EVIDENCE:
- CP38-D direct Smart Risk compatibility = PASS.
- CP38-H SmartRiskDecision constructor compatibility = PASS.
- CP44 explicit LONG Entry + Invalidation = PASS.
- CP44 explicit SHORT Entry + Invalidation = PASS.
- Invalid LONG/SHORT invalidation geometry = BLOCKED / FAIL-CLOSED.
- Dynamic Smart Risk LONG = PASS.
- Dynamic Smart Risk SHORT = PASS.
- Missing explicit invalidation at the Dynamic Boundary = BLOCKED / FAIL-CLOSED.
- Dynamic Smart Risk snapshot asset identity N-to-N = PASS.
- Frozen risk-budget semantics preserved:
  Base Risk = Portfolio Capital × Risk Per Trade.
  Remaining Portfolio Risk = Max Portfolio Risk − Already Allocated Risk.
  Risk Budget = min(Base Risk × Risk Adjustments, Remaining Portfolio Risk).
  Position Size = Risk Budget / Stop Distance.
  Exposure = Position Size × Entry Price.
- No allocation_fraction / allocated_capital sizing semantics restored.
- Dynamic Boundary retains ACTIONABLE decision prerequisite.
- SmartRiskDecision remains constructor-compatible with optional invalidation_price.

SCOPE:
Only the two Management-authorized files were modified:
- smart_risk_contract_v0_1.py
- smart_risk_engine_v0_1.py

PROTECTED:
- arunda.db = UNTOUCHED
- arunda_pipeline.py = UNTOUCHED
- market_arm_contiguous_history_accumulation_v1_1.py = UNTOUCHED
- public_market_data_fabric/canonical_store_v0.1.sqlite = UNTOUCHED

SAFETY:
- Production runtime = NOT EXECUTED
- Fabric runtime = NOT EXECUTED
- Execution = OFF
- Order intents = 0
- API/exchange writes = 0

### STATUS

CP44 SMART RISK COMPATIBILITY REPAIR = VERIFIED.

CP44 = NOT CLOSED.

CP45 = NOT STARTED.

### CURRENT FRONTIER

The Smart Risk compatibility boundary is technically verified.
The remaining CP44 work is the downstream production-compatible controlled
verification boundary: established real-data eligibility → Entry /
Invalidation-Stop → Smart Risk → Trade Gate → Trade Ready.

No premature CP44 closure is permitted.

### NEXT ACTION

Only after explicit Management readiness, proceed to the single authorized
CP44 real-market controlled verification of the established downstream path.

No production DB modification.
No arunda_pipeline.py modification.
No synthetic/fill/interpolation/padding/backfill.
No order creation.
Execution remains OFF.

# END CP44 SMART RISK COMPATIBILITY REPAIR
