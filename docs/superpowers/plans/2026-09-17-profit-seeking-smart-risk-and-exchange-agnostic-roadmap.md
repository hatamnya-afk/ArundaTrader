# Profit-Seeking Smart Risk and Exchange-Agnostic Roadmap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete CP44 downstream logic as a provider-neutral, profit-seeking trading system whose capital allocation is an output of intelligence rather than a fixed capital/risk cap.

**Architecture:** Keep Universe → Opportunity → Signal → Score → Decision → Entry/Invalidation → Smart Risk → Capital Allocation → Position Sizing → Trade Gate → Trade Ready → Order Intent fully exchange-agnostic. Exchange adapters remain downstream of the exchange-agnostic boundary and cannot influence core decision or risk logic.

**Tech Stack:** Python, existing ArundaTrader contracts, deterministic side-effect-free engines, focused pytest/static/compile verification.

**Spec:** `MANAGEMENT_ROADMAP.md`, `CURRENT_FRONTIER.md`, `PROJECT_STATE.md`, and `CHECKPOINTS.md` on `sync/local-project-20260917`.

## Global Constraints

- EXECUTION AUTHORIZATION = FALSE.
- ORDER WRITE = FORBIDDEN.
- DATABASE WRITE = FORBIDDEN unless explicitly authorized.
- Exchange API writes, order submission, cancellation, withdrawal, and signature work remain forbidden.
- `arunda_pipeline.py` remains protected unless separately authorized.
- `15` is legacy test-universe history, not a production cardinality contract.
- `6` is only an observed runtime cardinality, not a target or contract.
- Runtime cardinality remains dynamic: `ELIGIBLE[N] → RISK[N] → TRADE_GATE[N]`.
- No synthetic data, interpolation, forward-fill, back-fill, fabricated fallback, or silent source blending.
- Closed/verified checkpoints are historical truth and are not reopened without a direct proven regression.
- Capital amount is a scale/input boundary, not the intelligence of the system.
- Profit opportunity is the optimization objective; risk management prevents uninformed/invalid allocation and does not become a fixed profit ceiling.
- Allocation may legitimately be any value supported by validated opportunity and portfolio constraints, including 0% or 100%; no artificial fixed allocation ceiling is introduced by architecture.

## File Map

- Modify: `MANAGEMENT_ROADMAP.md` — authoritative lifecycle and current route.
- Modify: `CURRENT_FRONTIER.md` — CP44 state, objective, blocker, and next action.
- Modify: `PROJECT_STATE.md` — canonical state and non-negotiable architectural principles.
- Modify: `CHECKPOINTS.md` — historical/current checkpoint ledger and closure synchronization rule.
- Inspect/modify later: `smart_risk_contract_v0_1.py` — provider-neutral Smart Risk output contract.
- Inspect/modify later: `smart_risk_engine_v0_1.py` — deterministic risk, allocation, and position-sizing authority.
- Inspect/modify later: production Entry/Invalidation source and dynamic boundary feeding Smart Risk; legacy fixed-15 `market_entry_stop_adapter.py` must not become the production route.
- Inspect/modify later: `dynamic_risk_contract_boundary_v0_1.py` — dynamic integration boundary.
- Inspect/modify later: `dynamic_trade_gate_contract_boundary_v0_1.py` — downstream authoritative Trade Gate boundary.
- Test: focused CP44 Smart Risk/Entry-Invalidation tests; exact existing test paths must be confirmed before creation or modification.

## Task 1: Establish Governance Contract

- [x] Record the exchange-agnostic, profit-seeking architecture in the four governance documents.
- [x] Record that 15 is legacy and 6 is runtime evidence only.
- [x] Record dynamic cardinality and mandatory end-of-checkpoint synchronization.
- [x] Record the distinction between opportunity optimization and risk control.

## Task 2: Trace Production Entry/Invalidation → Smart Risk

- [ ] Inspect the exact active Entry/Invalidation source and its consumers.
- [ ] Confirm which source can produce explicit real `entry_price` and `stop_distance` for dynamic `ELIGIBLE[N]` without fixed-15 iteration.
- [ ] Trace `dynamic_risk_contract_boundary_v0_1.py` into `smart_risk_engine_v0_1.py`.
- [ ] Identify every fixed-policy assumption that incorrectly turns Smart Risk into a fixed risk limiter rather than an intelligent allocation authority.
- [ ] Do not change `arunda_pipeline.py` during this task.

## Task 3: Define Profit-Seeking Allocation Semantics

- [ ] Extend the Smart Risk contract only as needed to represent validated opportunity-driven allocation inputs/outputs.
- [ ] Preserve deterministic, side-effect-free behavior.
- [ ] Ensure capital amount scales the resulting position without changing the underlying opportunity logic.
- [ ] Ensure allocation can be 0% through 100% when validated by the model and constraints; do not hard-code a universal allocation ceiling.
- [ ] Ensure risk/invalidation/exposure/liquidity/portfolio constraints can block or reduce allocation for concrete reasons rather than through arbitrary constants.

## Task 4: Implement and Verify the Dynamic Downstream Chain

- [ ] Add failing focused tests for dynamic Entry/Invalidation → Smart Risk → Trade Gate behavior.
- [ ] Implement the smallest contract-compatible change required.
- [ ] Verify `ELIGIBLE[N] → RISK[N] → TRADE_GATE[N]` cardinality preservation.
- [ ] Verify no fixed-15 path is used by the active production boundary.
- [ ] Verify invalid/missing real inputs fail closed.
- [ ] Verify no exchange adapter is imported or required by Smart Risk.
- [ ] Run focused tests and compile/static checks.

## Task 5: CP44 Closure Gate

- [ ] Collect evidence for REAL_MARKET_DATA, VALIDATED_OBSERVATIONS, REAL_CAPITAL_BOUNDARY, VALID_ENTRY, VALID_STOP, VALID_QUANTITY, VALID_EXPOSURE, DECISION_CONSISTENCY, TRADE_INTENT_CONSISTENCY, CONSTRAINT_READINESS, PROVENANCE, FAIL_CLOSED, DYNAMIC_ASSET, NO_TEST_DATA, and NO_FIXED_15.
- [ ] Confirm NO_ORDER, NO_AUTHORIZATION, NO_EXECUTION, NO_API_WRITE, and NO_DB_WRITE.
- [ ] Synchronize `PROJECT_STATE.md`, `CURRENT_FRONTIER.md`, `CHECKPOINTS.md`, and `MANAGEMENT_ROADMAP.md` at CP44 end.
- [ ] Only after all evidence is verified may CP44 be marked CLOSED/VERIFIED/PASS.

## Checkpoint Synchronization Rule

At the end of every checkpoint, update all four governance documents together. The synchronization must record BUILT, VERIFIED, CLOSED/BLOCKED/NOT VERIFIED, evidence, blocker, CURRENT FRONTIER, NEXT ACTION, and authorized branch/file scope. A checkpoint is not governance-complete until the four documents are internally consistent.
