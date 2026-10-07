# CP47 — MAIN SELECTIVE INTEGRATION MANIFEST

Status: READY_FOR_ENGINEERED_INTEGRATION
Base: main
Source verification branch: cp46-f-futures-readiness-20261006
Source HEAD: 26b73995cc0f51946af13cfe1574dc28bddf2173
Created: 2026-10-07

## Purpose

This branch is the safe integration staging point from the MCP-01 provider-readiness work back into ArundaTrader main.

It intentionally contains NO copied MCP-01 runtime code yet.

## Why no direct copy was performed

The current main branch does not contain the CP46/CP49 provider-boundary modules required by the verified MCP-01 runtime, including:

- execution_venue_routing_policy_v0_1.py
- toobit_trading_adapter.py
- provider_preflight_v0_1.py
- provider_order_translation_v0_1.py
- toobit_provider_preflight_evidence_v0_1.py
- cp46_d_production_provider_preflight_v0_1.py
- cp46_d_provider_execution_handoff_v0_1.py
- toobit_provider_order_state_v0_1.py
- toobit_futures_order_transport_v0_1.py
- toobit_position_reader_v0_1.py
- cp49_first_execution_contract_v0_1.py

Main also has a materially older arunda_pipeline.py whose execution architecture is not the same as the verified MCP-01 pipeline.

Therefore copying individual files now would create orphaned contracts, unresolved imports, or a split architecture.

## Required integration order

1. Establish the CP49/CP46 execution-contract dependency layer on this branch.
2. Port the provider-neutral venue routing contract.
3. Port Toobit read-only provider boundaries.
4. Port provider translation and preflight contracts.
5. Port Futures read-only capability/account/order-state evidence.
6. Integrate the verified provider boundary into the CURRENT main pipeline only at the canonical-order-request boundary.
7. Preserve all existing main-branch strategy, signal, risk and gate behavior.
8. Run focused contract tests.
9. Run one controlled runtime with execution explicitly OFF.
10. Only after verification, prepare a normal PR/merge into main.

## Forbidden

- No merge of cp46-f-futures-readiness-20261006 wholesale.
- No rebase.
- No reset.
- No clean/delete/force.
- No DB repair/change.
- No strategy redesign.
- No synthetic/backfill/interpolation/forward-fill/padding/blending.
- No execution activation.
- No reopening CLOSED/VERIFIED stages.

## Verified source evidence

Latest controlled MCP-01 runtime:
- Universe 843
- Opportunity 423
- Signal 423
- Validation 423 / failures 0
- Decision 423
- CP49 birth persisted 423
- Risk 423
- Trade Gate 423
- Trade Ready 70
- Execution Quality Ready 50
- Order Intents 50
- Canonical Requests 50
- Evidence persistence failures 0
- Execution OFF
- Real Order FALSE
- Real Trade FALSE
- Fail Closed TRUE

## Management verdict

MAIN IS SAFE.
MCP-01 IS VERIFIED.
INTEGRATION MUST BE SELECTIVE, DEPENDENCY-ORDERED, AND TESTED.

The next coding frontier is this branch, not the MCP-01 runtime branch.
