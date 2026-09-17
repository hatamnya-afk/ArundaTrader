# ARUNDA TRADER — CURRENT FRONTIER

## STATUS
CURRENT FRONTIER — CP44 / REAL-MARKET CONTROLLED TEST

## GOVERNANCE GATE
Repository consolidation is CLOSED by Management. CP44 controlled-test work is authorized only inside the existing safety boundary.

## CURRENT FRONTIER
CP44 — REAL-MARKET CONTROLLED TEST

CP41 = CLOSED / VERIFIED / PASS
CP43 = CLOSED / VERIFIED / PASS
CP44 = MANAGEMENT-AUTHORIZED / EXECUTED / OBSERVED / NOT VERIFIED / NOT CLOSED

## CP44 RUNTIME OBSERVATION
A controlled real-market runtime was executed from the established downstream eligibility boundary.
Observed result: **6 assets reached ELIGIBLE**.

This observation is runtime evidence only. It is not a cardinality contract, target, or CP44 closure proof.
No upstream rebuild, redesign, or re-audit is authorized merely to reproduce this observation.

`15` is legacy test-universe history and is not a production cardinality contract.

## CP44 OBJECTIVE
Complete and verify the provider-neutral downstream chain:

```text
REAL MARKET DATA
→ DYNAMIC ELIGIBLE[N]
→ ENTRY + INVALIDATION / STOP
→ PROFIT / OPPORTUNITY ASSESSMENT
→ SMART RISK
→ CAPITAL ALLOCATION
→ POSITION SIZING
→ TRADE GATE
→ TRADE READY
→ ORDER INTENT
→ PRE-EXECUTION
→ EXCHANGE-AGNOSTIC BOUNDARY
```

The optimization objective is maximum validated profit-opportunity capture. Risk management must prevent invalid/uninformed allocation, not impose an arbitrary universal profit ceiling.

## CP44 ACCEPTANCE REQUIREMENTS
- REAL_MARKET_DATA
- VALIDATED_OBSERVATIONS
- REAL_CAPITAL_BOUNDARY
- VALID_ENTRY
- VALID_STOP_OR_INVALIDATION
- PROFIT_OPPORTUNITY_ASSESSMENT
- INTELLIGENT_CAPITAL_ALLOCATION
- VALID_QUANTITY
- VALID_EXPOSURE
- DECISION_CONSISTENCY
- TRADE_INTENT_CONSISTENCY
- CONSTRAINT_READINESS
- PROVENANCE
- FAIL_CLOSED
- DYNAMIC_ASSET
- DYNAMIC_CARDINALITY
- SCALE_INDEPENDENT_LOGIC
- NO_TEST_DATA
- NO_FIXED_15
- NO_FIXED_RUNTIME_CARDINALITY
- NO_ORDER
- NO_AUTHORIZATION
- NO_EXECUTION
- NO_API_WRITE
- NO_DB_WRITE
- NO_EXCHANGE_DEPENDENCY_BEFORE_BOUNDARY

## CP44 CURRENT BLOCKER
Production-compatible real Entry + Invalidation/Stop is not yet proven as the input to the Smart Risk authority for dynamic `ELIGIBLE[N]`.

The active route must also establish opportunity-driven capital allocation semantics. The legacy fixed-15 `market_entry_stop_adapter.py` snapshot path must not become the production route.

## CP44 FORBIDDEN DURING TEST
- order submission/cancellation
- execution authorization
- signature work
- exchange writes
- test capital
- modification of `arunda_pipeline.py` without explicit separate authorization
- architecture redesign
- reopening closed checkpoints
- upstream rebuild of the established ELIGIBLE path
- exchange-specific logic inside Core Risk/Decision/Allocation

## REPOSITORY GOVERNANCE
Canonical branch is `main`.
The Local Original remains the primary operational/recovery object; GitHub is the controlled durable project-management and builder-handoff source.
The synchronization branch is authorized for the current controlled roadmap/governance work.

Repository organization is classification-first and behavior-neutral:
- governance/control documents remain at root;
- operational source paths are preserved until dependency/path audit authorizes relocation;
- verification, evidence/forensic, and historical material have explicit navigation locations;
- `README.md` and `REPOSITORY_STRUCTURE.md` provide repository navigation and organization rules.

Temporary, generated, backup, quarantine, forensic, review, and unrelated files are not automatically project truth and must be classified before canonical promotion.

## MANDATORY STATE SYNCHRONIZATION
At the end of every checkpoint, the responsible Builder/Manager MUST synchronize:
- PROJECT_STATE.md
- CURRENT_FRONTIER.md
- CHECKPOINTS.md
- MANAGEMENT_ROADMAP.md

The synchronization must record BUILT, VERIFIED, CLOSED/BLOCKED/NOT VERIFIED, evidence, blocker if any, CURRENT FRONTIER, NEXT ACTION, and any authorized branch/file scope change.

## TOOBIT
TOOBIT ACCOUNT SIGNATURE = BLOCKED / -1022 INVALID_SIGNATURE
This remains an independent Account/Real-Capital blocker. CP44 does not authorize bypassing or repeating private diagnostics.
Toobit is not part of the Core Risk/Allocation architecture.

## NEXT ACTION
1. Trace the exact production Entry + Invalidation/Stop source into Smart Risk.
2. Preserve dynamic `ELIGIBLE[N]` and prove `RISK[N] → TRADE_GATE[N]` without fixed cardinality.
3. Define/verify opportunity-driven capital allocation that scales across valid capital amounts.
4. Keep all pre-boundary logic exchange-agnostic.
5. At CP44 completion, synchronize all four governance documents before any VERIFIED/PASS/CLOSED claim.

# END CURRENT FRONTIER
