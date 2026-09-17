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

CP44 = MANAGEMENT-AUTHORIZED / IMPLEMENTATION VERIFIED / REAL-MARKET CONTROLLED TEST PENDING / NOT CLOSED.

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
- Generated `__pycache__` is temporary and is not project truth.

This is contract/boundary verification evidence only. It does not constitute CP44 real-market closure.

## CP44 RUNTIME OBSERVATION
A controlled real-market runtime was previously executed from the established downstream eligibility boundary.
Observed result: **6 assets reached ELIGIBLE**.

This is runtime evidence only. It is not a cardinality contract, target, or CP44 closure proof.

`15` is legacy test-universe history and is not a production cardinality contract.

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
1. Run the single authorized CP44 real-market controlled runtime from the established downstream ELIGIBLE boundary.
2. Verify production-compatible Entry + Invalidation/Stop, opportunity-driven allocation, quantity/exposure, Trade Gate, Trade Ready, Order Intent, and pre-execution readiness with dynamic N.
3. Preserve all safety boundaries: no order, execution, API write, or DB write.
4. Synchronize all four governance documents again at CP44 completion before closure.

# END PROJECT STATE
