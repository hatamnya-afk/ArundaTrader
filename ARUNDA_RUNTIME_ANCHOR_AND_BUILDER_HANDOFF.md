# ARUNDA TRADER — RUNTIME ANCHOR & BUILDER HANDOFF

## MANAGEMENT AUTHORITY
This document is a management guardrail for continuity across Builder/Manager context limits.
It does not replace the Local Original Project, PROJECT_STATE.md, CURRENT_FRONTIER.md, CHECKPOINTS.md, or MANAGEMENT_ROADMAP.md.

## PRIMARY PROJECT TRUTH
The complete Local Original ArundaTrader project at `C:\Users\ASUS\ArundaTrader` is the primary recovery/reference object for understanding the project's full historical and operational body.

The Canonical GitHub tree is a controlled project reference. It must NOT be treated as a complete replacement for the Local Original Project unless Management explicitly authorizes such a transition.

## OPERATIONAL ANCHOR
The most important runtime fact is that the real Runtime Pipeline reached `ELIGIBLE SIGNAL`.

`ELIGIBLE SIGNAL` is the operational anchor for forward coordination.

The historical Opportunity/Signal/Score/Fusion/Decision path that produced eligibility is not to be rebuilt, redesigned, or replaced merely because a later Builder has incomplete context.

## FORWARD ROUTE
From the established eligibility boundary, coordinate forward only:

`ELIGIBLE SIGNAL`
→ `Risk`
→ `Trade Gate`
→ `TRADE_READY`
→ `Trade Intent / ORDER_INTENT`
→ `Pre-Execution Readiness`
→ `Execution-Ready Package`
→ `Execution Boundary`
→ `Exchange Adapter / Toobit`
→ `Controlled Real-Market Test`

## HARD RULES
1. Do not rebuild Opportunity from zero.
2. Do not rebuild Signal from zero.
3. Do not redesign Score/Fusion/Decision to compensate for lost context.
4. Do not reinterpret historical failure to mean the successful eligibility path never existed.
5. Do not change the historical project to fit a cleaner or smaller architecture.
6. Do not replace the Local Original Project with the Canonical GitHub tree by assumption.
7. Do not delete Local files, databases, backups, forensic evidence, or historical artifacts as a cleanup exercise.
8. Do not modify `arunda_pipeline.py` unless Management explicitly authorizes the exact change.
9. Do not reopen CLOSED/VERIFIED checkpoints unless there is direct evidence of regression.
10. Do not execute a new runtime merely to rediscover an already-established upstream fact.
11. Do not create branches for personal workflow, experimentation, convenience, or parallel project truth.
12. Do not add files unless their responsibility and active checkpoint relation are explicitly authorized.
13. Do not bypass Toobit `-1022 INVALID_SIGNATURE` or repeat private diagnostics without explicit Management authorization.
14. Execution remains disabled unless Management explicitly authorizes otherwise.
15. No order submission, API write, production DB write, execution authorization, or test capital is implied by this handoff.

## CONTEXT-LOSS RECOVERY PROTOCOL
When a new Builder/Manager starts with limited context:

1. Read this file first.
2. Read `PROJECT_STATE.md`.
3. Read `CURRENT_FRONTIER.md`.
4. Read `CHECKPOINTS.md`.
5. Read `MANAGEMENT_ROADMAP.md`.
6. Treat CLOSED/VERIFIED checkpoints as historical truth unless direct regression is demonstrated.
7. Treat `ELIGIBLE SIGNAL` as the forward operational anchor.
8. Inspect only the downstream boundary required by the active frontier.
9. STOP before changing upstream architecture when context is incomplete.
10. Escalate uncertainty to Management instead of guessing.

## CURRENT DOWNSTREAM INSPECTION SCOPE
For the current reconstruction/coordination work, the relevant pipeline sections are the downstream sections around:
- eligibility discovery and handoff
- Risk
- Trade Gate
- Order Intent construction/validation
- fail-closed execution consistency checks

Do not perform a broad re-audit of hundreds of files merely because the Local Original Project is large.

## PROVENANCE PRINCIPLE
The existence of a large Local Original Project is not evidence that all files are active runtime components.
Likewise, a small Canonical tree is not evidence that omitted Local files were irrelevant.
Runtime participation must be established from actual pipeline calls, imports, lineage, and verified runtime evidence.

## MANAGEMENT VERDICT
The project is NOT being restarted.
The upstream eligibility path is NOT being redesigned.
The next coordination boundary is downstream of the established `ELIGIBLE SIGNAL` result.

When uncertain: STOP. Preserve the project. Do not improvise architecture.

# END HANDOFF
