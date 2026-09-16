# ARUNDA TRADER — SMART RISK MANAGEMENT

## PURPOSE
Define the next risk-management frontier without changing the existing Core, closed contracts, database, or execution boundary.

## REQUIRED CHAIN
REAL ENTRY OBSERVATION
→ VALID STOP OBSERVATION / POLICY
→ RISK BUDGET
→ POSITION SIZE
→ PORTFOLIO EXPOSURE
→ TRADE GATE
→ ORDER INTENT

## PRINCIPLES
- Risk is exchange-agnostic.
- Risk uses explicit real observations only.
- No stop is inferred from ATR until the stop policy is explicitly validated.
- No position sizing is created without validated entry, stop distance, and real capital/risk budget.
- Portfolio risk must be evaluated before an order becomes eligible.
- Missing or invalid required risk inputs fail closed.
- Risk calculations must be deterministic and side-effect free.
- No execution, order write, or database mutation is part of this frontier.

## EXISTING FOUNDATION
CP33-D established an InitialRisk boundary with deterministic, non-mutating behavior and explicit invalidation for missing entry price and unvalidated stop policy.

## FRONTIER WORK
1. Inspect the existing InitialRisk, PortfolioRisk, Trade Gate and OrderIntent contracts as they currently exist.
2. Identify the smallest missing contract needed to turn validated risk observations into a controlled risk budget and position-size decision.
3. Implement only that bounded risk layer.
4. Add deterministic and fail-closed tests.
5. Verify compatibility with existing closed contracts without reopening them.

## FIRST-REAL-TRADE REQUIREMENT
A real trade is a downstream milestone, not a reason to bypass risk controls. No real order is permitted until all required risk evidence, Trade Gate conditions, exchange constraints, and execution authorization are independently satisfied.

## FORBIDDEN
- arunda_pipeline.py changes without explicit authorization
- database writes
- runtime execution
- order submission/cancellation
- withdrawal
- exchange-specific risk logic
- synthetic/fabricated data
- reopening closed checkpoints

# END SMART RISK MANAGEMENT
