# ARUNDA TRADER — CURRENT FRONTIER

## STATUS
ACTIVE — CONTEXT / GOVERNANCE CONSOLIDATION

## OBJECTIVE
Keep the project self-contained in the repository so a new Builder session can recover state without reconstructing the project from chat memory.

## ACTIVE STRATEGIC DIRECTION
Smart Risk Management is the intended next core development direction after the verified core.

Toobit remains an adapter/integration concern only.

## ALLOWED
- Maintain repository state documents.
- Work only on the Management-authorized frontier.
- Preserve provider-neutral architecture.
- Use verified contracts as the baseline.

## FORBIDDEN
- modify arunda_pipeline.py without explicit authorization
- modify production DB without explicit authorization
- run private Toobit runtime without explicit authorization
- enable execution or exchange writes
- reset, clean, delete, stash, or normalize repository artifacts without authorization
- reopen closed checkpoints without proven regression
- redesign the core architecture

## NEXT ACTION
Management explicitly authorizes the next implementation frontier. Builder must not infer or self-authorize a new frontier.

## STOP CONDITIONS
Stop before any action requiring runtime, DB mutation, execution, closed-contract modification, architecture change, or pipeline modification unless explicitly authorized.

# END CURRENT FRONTIER
