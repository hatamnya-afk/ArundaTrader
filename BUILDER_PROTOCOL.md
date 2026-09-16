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

Builder executes the authorized scope. Builder does not promote a task to a new frontier by itself.

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
- preserve existing contracts unless the active checkpoint explicitly authorizes contract change

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
When reporting is requested, provide only:
- current state
- evidence
- blocker if any
- next action

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

If the documents and chat disagree, do not silently overwrite repository truth. Escalate the discrepancy to Management.

# END BUILDER PROTOCOL
