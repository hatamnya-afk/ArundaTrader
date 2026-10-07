# MCP-01 HANDOFF TO ARUNDA TRADER MAIN

Status: HANDOFF_READY
Date: 2026-10-07
Source branch: cp46-f-futures-readiness-20261006
Source HEAD: 26b7399
Latest controlled runtime: RC-c3e44ba3a51c17036f8c380c23c204f7b686ed73c85a5b1c9d255959c77b446d

## Runtime evidence
- Universe: 843
- Opportunity: 423
- Signal: 423
- Validation: 423; failures: 0
- Fusion: 423
- Decision: 423
- CP49 birth persisted: 423
- Risk: 423
- Trade Gate: 423
- Trade Ready: 70
- Execution Quality Ready: 50
- Order Intents: 50
- Canonical Order Requests: 50
- MCP-01 evidence persistence failures: 0
- CP69 observation written: 1
- Execution: OFF
- Real Order: FALSE
- Real Trade: FALSE
- Execution boundary: VERIFIED_BLOCKED
- Fail Closed: TRUE

## Handoff decision
MCP-01 verification objective is complete for the current provider-readiness boundary.
Do NOT merge the MCP-01 branch wholesale into main.

The GitHub comparison shows the CP46-F branch is materially divergent from main. Therefore the next ArundaTrader work must be performed from main using selective, evidence-backed integration only.

## Carry-forward contracts
1. Decision Birth identity: decision_id remains authoritative.
2. case_id, trade_event_id, runtime_cycle_id, exchange_order_id remain distinct.
3. Missing outcome evidence becomes DATA_QUALITY_EVENT; no fabricated outcomes.
4. Quantity provenance remains mandatory; blocked-before-order-intent assets must not receive order-intent quantity.
5. CP46-A3 routing remains authoritative: SHORT requires Futures; Spot SELL is never interpreted as SHORT.
6. Futures readiness must use authoritative provider contract/account state.
7. Futures portfolio exposure evidence must be provider-derived; no generic exposure calculation.
8. Provider preflight remains fail-closed.
9. Execution remains OFF until separately authorized.
10. No DB repair/change, no synthetic/backfill/interpolation/forward-fill/padding/blending, no strategy redesign.

## Explicitly NOT carried forward automatically
- MCP-01 runtime wrappers and forensic scripts.
- Runtime artifacts: arunda.db, __pycache__, runtime_observations/.
- Any broad branch merge/rebase/reset/clean operation.
- Any unrelated historical forensic artifacts.
- No reopening of CLOSED/VERIFIED checkpoints.

## Main-branch next frontier
Return to ArundaTrader main and establish the selective integration boundary for the provider-readiness contracts above. After that, continue the production Trader path toward controlled real trading. UI/Aroonda/email remain presentation/analysis layers over canonical evidence and are not blockers for this handoff.

## Safety
Execution authorization must remain FALSE. This handoff does not authorize real orders or real trades.
