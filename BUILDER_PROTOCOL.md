# ARUNDA TRADER — BUILDER PROTOCOL

## PURPOSE
Single operating protocol for any Builder, coding agent, or future ChatGPT session working on ArundaTrader.

## START OF EVERY SESSION
Read these files from the repository before making project decisions:
1. PROJECT_STATE.md
2. ARCHITECTURE.md
3. CHECKPOINTS.md
4. CURRENT_FRONTIER.md
5. BUILDER_PROTOCOL.md

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

Builder executes the authorized scope. Builder does not promote a task to a new frontier by itself.

## ROADMAP DISCIPLINE — NON-NEGOTIABLE
The roadmap is the only path for project advancement.

No Builder, coding agent, or Manager may:
- create a new project branch for personal workflow, experimentation, convenience, or an unapproved parallel path;
- create or introduce a file that is outside the explicitly authorized checkpoint scope;
- add generated output, temporary files, backups, quarantine copies, forensic artifacts, review dumps, or unrelated code to Canonical project truth;
- start a new checkpoint, change the active frontier, redesign an architecture boundary, or create a parallel implementation without an explicit Management decision recorded in repository state;
- treat a personal branch or unrecorded file as project truth.

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

## CHANGE DISCIPLINE
Before modifying anything:
- identify the active frontier
- identify the exact file/surface in scope
- verify that the change does not cross a protected boundary
- verify that the change is required by the active roadmap/checkpoint
- preserve existing contracts unless the active checkpoint explicitly authorizes contract change

After every completed checkpoint, update the canonical repository state so the next Builder can recover the state without relying on chat history.

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
- protected boundaries
- exact authorized action
- authorized branch/file scope, if any

If the documents and chat disagree, do not silently overwrite repository truth. Escalate the discrepancy to Management.

## STATE HANDOFF RULE
The repository state documents are the Builder handoff source of truth. Every closed checkpoint, verified evidence state, blocker, and current frontier must be reflected there. Reporting to Management does not substitute for updating the repository state.

## CANONICAL INTEGRITY RULE
Canonical is one controlled project truth.
Historical branches may be preserved for provenance, but they do not become active project truth without Management authorization.
No one is permitted to "dance around" the roadmap by creating side branches, duplicate implementations, or extra files.

# END BUILDER PROTOCOL
