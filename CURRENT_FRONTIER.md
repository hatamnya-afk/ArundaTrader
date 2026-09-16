# ARUNDA TRADER — CURRENT FRONTIER

## STATUS
ACTIVE — CP40 DECISION IMPLEMENTATION

## CURRENT FRONTIER
CP40 — DECISION IMPLEMENTATION

## CP39 CLOSED STATE
CP39 = CLOSED / VERIFIED / PASS
PRE-EXECUTION READINESS = SEALED

Verified CP39 chain:
REAL PRODUCTION OBSERVATIONS → READINESS INTEGRATION → HANDOFF → INTEGRITY → CERTIFICATION → BOUNDARY SEAL → READINESS-TO-DECISION HANDOFF

The CP39 chain establishes a sealed, provider-neutral, fail-closed input boundary for Decision.

## FRONTIER OBJECTIVE
Design and implement the Decision layer using only SEALED DECISION INPUT.

Decision must be:
- provider-neutral
- dynamic
- fail-closed
- deterministic
- independent of Execution
- independent of Order Intent
- independent of authorization

Decision must not:
- generate orders
- call exchange APIs
- write the database
- produce execution_authorization
- change execution_enabled

## DECISION BOUNDARY
DECISION ≠ EXECUTION
DECISION ≠ ORDER INTENT
DECISION ≠ AUTHORIZATION

The Decision layer evaluates sealed decision input and produces a provider-neutral decision result only. Any later transition toward Order Intent or Execution requires its own explicit boundary and Management authorization.

## EXECUTION BOUNDARY
EXECUTION = NOT AUTHORIZED
REAL TRADE = NOT EXECUTED
ORDER SUBMISSION = NONE
EXCHANGE WRITE = NONE
DB MUTATION = NONE

## TOOBIT
TOOBIT ACCOUNT SIGNATURE = BLOCKED / -1022 INVALID_SIGNATURE
This remains an independent Account/Real-Capital blocker and was not resolved by CP39. It is outside CP40 Decision logic.

## ALLOWED — CP40
- Design the Decision contract.
- Implement the Decision layer against SEALED DECISION INPUT only.
- Define explicit deterministic decision outputs.
- Enforce provider-neutral and fail-closed behavior.
- Test with contract fixtures only.
- Maintain repository state.

## FORBIDDEN — CP40
- runtime execution
- Toobit API calls
- exchange writes
- order creation/submission/cancellation
- DB mutation
- arunda_pipeline.py modification
- execution authorization
- changing execution_enabled
- Risk modification
- Portfolio modification
- Adapter modification
- reopening closed checkpoints
- reset, clean, stash, delete, merge, rebase, or repository normalization without explicit authorization

## NEXT ACTION
CP40 is CURRENT FRONTIER / NOT STARTED. Begin only with Management authorization. Use TDD: test first, then minimal Decision implementation, with no runtime, DB, pipeline, order, exchange, or execution integration.

## STOP CONDITIONS
Stop before runtime, DB mutation, exchange API, order surface, execution authorization, pipeline modification, closed-contract modification, or architecture drift unless explicitly authorized.

# END CURRENT FRONTIER
