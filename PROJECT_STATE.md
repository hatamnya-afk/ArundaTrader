# ARUNDA TRADER — PROJECT STATE

## PURPOSE
Canonical repository-level source of truth for ArundaTrader. Chat memory is not authoritative when these documents are available.

## PROJECT IDENTITY
ArundaTrader is a modular, layered, exchange-agnostic real-market analysis and trading-decision system.
Toobit is an exchange adapter/environment, not the project core.

## FINAL PROJECT OBJECTIVE
The project goal is real trading, but the project must first reach completion as an exchange-agnostic system.
The mandatory lifecycle is:
1. COMPLETE the exchange-agnostic project/core according to the roadmap.
2. Only after explicit project-completion closure, BIND an exchange through an adapter/environment boundary.
3. Perform final real-market exchange integration and controlled testing.
4. Only after final acceptance and explicit Management authorization may real trading be enabled.

No Builder, Manager, or future implementation agent may move these stages earlier, merge them, or introduce exchange-specific architecture into the core merely to accelerate the path to trading.

## CORE FLOW
REAL DYNAMIC UNIVERSE → REAL MARKET DATA → REAL OPPORTUNITY → REAL SIGNAL → REAL DECISION → SMART RISK MANAGEMENT → TRADE GATE → ORDER INTENT → EXECUTION → REAL TRADE → REAL OUTCOME → REAL OBSERVATION → CALIBRATION

## PRODUCTION BOUNDARY
LAUNCH_TIMESTAMP = 2026-08-31T00:00:00+00:00
Production analysis uses real post-launch data only.

## EXECUTION SAFETY
EXECUTION AUTHORIZATION = FALSE
ORDER WRITE = FORBIDDEN
WITHDRAW = FORBIDDEN
DATABASE WRITE = FORBIDDEN unless explicitly authorized
Credentials and secrets must never be exposed.

## CLOSED / VERIFIED CHECKPOINTS
CP38 = CLOSED / VERIFIED / PASS
CP39 = CLOSED / VERIFIED / PASS
CP40 = CLOSED / VERIFIED / PASS
CP41 = CLOSED / VERIFIED / PASS
CP43 = CLOSED / VERIFIED / PASS

Closed checkpoints are historical truth. They must not be reopened or re-audited unless Management identifies a direct, provable regression.

## CP41 STATE — DECISION → TRADE INTENT
CP41 = CLOSED / VERIFIED / PASS

Implementation:
- decision_trade_intent_boundary_v0_1.py
- test_cp41_decision_trade_intent_boundary_v0_1.py

Verification evidence:
- 12 focused CP41 tests passed.
- Compile/static verification passed.
- Scope/diff verification passed.
- No order, execution, API write, or production DB write occurred.

## CP43 STATE — PRE-EXECUTION READY PACKAGE
CP43 = CLOSED / VERIFIED / PASS

Implementation:
- pre_execution_readiness_v0_1.py
- execution_ready_package_v0_1.py
- test_cp43_pre_execution_readiness_v0_1.py
- test_cp43_execution_ready_package_v0_1.py

Verification evidence:
- 77/77 focused tests passed.
- Compile verification passed.
- Diff-check passed.
- Worktree clean at closure.
- EXECUTION AUTHORIZATION = FALSE.
- No runtime order, API write, execution, or DB mutation occurred.

## CURRENT PROJECT STATE
CURRENT FRONTIER: CP44 — REAL-MARKET CONTROLLED TEST

CP44 is NOT VERIFIED or CLOSED yet.
Repository consolidation is a temporary management gate and takes precedence over CP44 runtime execution until Canonical repository governance is finalized.
CP44 runtime must not be executed during consolidation.

## CP44 ACCEPTANCE BOUNDARY
REAL_MARKET_DATA
VALIDATED_OBSERVATIONS
REAL_CAPITAL_BOUNDARY
VALID_ENTRY
VALID_STOP
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

## REPOSITORY CONSOLIDATION STATE
CANONICAL BASE COMMIT = 8945316ae1fec74ecfab40ac33ec9593e6d7ca8b
CANONICAL BRANCH = main
CANONICAL GOVERNANCE STATE = maintained on main; exact commit provenance is preserved in Git history
REMOTE VERIFICATION BRANCH = consolidation-canonical-8945316

CP42 is preserved as historical/source-binding lineage and is NOT merged into Canonical core. Historical branches remain preserved until provenance is explicitly safe.
Generated artifacts, backups, quarantine trees, forensic/review outputs, and unrelated temporary files are not project truth and must not enter Canonical.

## PROTECTED SURFACES
- arunda_pipeline.py
- production database
- execution controls
- order submission/cancellation
- withdrawal
- closed/verified contracts
- backup/quarantine artifacts

## NON-NEGOTIABLE PROJECT RULES
- Real data only.
- No synthetic data, interpolation, forward-fill, back-fill, padding, fabricated fallback, or silent source blending.
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
- No Builder, Manager, or implementation agent may create a new project branch outside an explicitly authorized roadmap/checkpoint scope.
- No Builder, Manager, or implementation agent may introduce files outside the authorized scope.
- No personal/experimental branch, temporary file, backup, quarantine, forensic artifact, generated output, review dump, or unrelated code may become project truth.
- Every authorized branch or new file must have a documented purpose and be connected to the active roadmap/frontier before use as project work.
- The roadmap is the only path for project advancement.
- At the end of every checkpoint, the repository state MUST be synchronized before the checkpoint can be treated as CLOSED.
- At every route/frontier change, the roadmap and repository state MUST be updated before the new route is treated as active.
- Reporting to Management does not substitute for repository state synchronization.
- If the required state update is missing, the checkpoint remains open/incomplete for governance purposes and the next frontier must not start.

## MANDATORY CHECKPOINT / ROUTE SYNCHRONIZATION
At the end of every checkpoint, the responsible Builder/Manager must update, as applicable:
1. PROJECT_STATE.md
2. CURRENT_FRONTIER.md
3. CHECKPOINTS.md
4. MANAGEMENT_ROADMAP.md

The update must record:
- BUILT
- VERIFIED
- CLOSED / BLOCKED / NOT VERIFIED as applicable
- evidence and verification result
- blocker, if any
- CURRENT FRONTIER
- NEXT ACTION
- authorized branch/file scope, if changed

For any route change, the same synchronization is mandatory immediately, including the reason for the route change and its Management authorization.

Until synchronization is complete and internally consistent, the work is NOT a valid completed checkpoint and no next-frontier implementation may begin.

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

Continue only from the active frontier recorded in CURRENT_FRONTIER.md and MANAGEMENT_ROADMAP.md. If repository documents and chat disagree, stop and escalate to Management; do not silently create a parallel truth.

# END PROJECT STATE
