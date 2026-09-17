# ARUNDA TRADER — PROJECT STATE

## PURPOSE
Canonical repository-level source of truth for ArundaTrader. Chat memory is not authoritative when these documents are available.

## PROJECT IDENTITY
ArundaTrader is a modular, layered, exchange-agnostic real-market analysis and trading-decision system.
Toobit is an exchange adapter/environment, not the project core.

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

## CURRENT PROJECT STATE
CURRENT FRONTIER: CP44 — REAL-MARKET CONTROLLED TEST

CP44 = MANAGEMENT-AUTHORIZED / EXECUTED / OBSERVED / NOT VERIFIED / NOT CLOSED.

## CP44 RUNTIME OBSERVATION
A controlled real-market runtime was executed from the established downstream eligibility boundary.
Observed result: **6 assets reached ELIGIBLE**.

This is recorded as runtime evidence. It is not a CP44 closure claim and does not independently prove every acceptance criterion.

The established upstream ELIGIBLE path remains accepted as the operational boundary for forward work. No upstream rebuild, redesign, or re-audit is authorized merely to reproduce this observation.

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
CONSOLIDATION GATE = CLOSED / MANAGEMENT-AUTHORIZED
CANONICAL BRANCH = main
The Local Original at `C:\Users\ASUS\ArundaTrader` remains the primary operational/recovery object.
GitHub is the controlled durable project-management, state, provenance, and Builder-handoff source.
The synchronization branch `sync/local-project-20260917` is authorized only for this controlled Local→GitHub consolidation task.

Repository organization is now conservative and classification-first:
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
Preserve the 6-asset ELIGIBLE observation, continue downstream from ELIGIBLE toward Risk / Trade Gate, and complete the CP44 evidence synchronization before any closure claim.

# END PROJECT STATE
