# ARUNDA TRADER — ARCHITECTURE

## ARCHITECTURAL IDENTITY
ArundaTrader is exchange-agnostic and modular. Exchange providers are replaceable environments behind an adapter boundary.

## CORE
CORE → MARKET INTELLIGENCE → OPPORTUNITY → SIGNAL → DECISION → SMART RISK MANAGEMENT → TRADE GATE → ORDER INTENT → EXCHANGE CONSTRAINTS → PRE-EXECUTION AUTHORIZATION

The core produces exchange-neutral trading intent. Provider-specific API behavior must not define core logic.

## CP38 PRE-EXECUTION ARCHITECTURE
The verified provider-neutral pre-execution chain is:
REAL CAPITAL OBSERVATION → VALIDATED ENTRY/STOP → VALIDATED RISK POLICY → PORTFOLIO OBSERVATION → SMART RISK → TRADE GATE → ORDER INTENT BOUNDARY → EXCHANGE CONSTRAINTS → CONSTRAINT EVALUATION → EXECUTION AUTHORIZATION BOUNDARY.

CP38-B is DESIGN PASS only; it is not independently verified.

Execution Authorization is a logical pre-execution boundary only. It does not enable execution or submit an order.

## EXCHANGE BOUNDARY
Core → Exchange Adapter Boundary → Provider Adapter → Exchange API

Toobit is one adapter implementation. It is not a required dependency of the core.

## DATA CONTRACT
Production data must be real and traceable.

Required principles:
- one candle = one source
- provenance preserved
- no synthetic values
- no interpolation
- no forward-fill
- no back-fill
- no fabricated padding
- no silent cross-source blending
- fail closed when required data cannot be verified

## UNIVERSE
Global Universe and provider-specific exchange universes are distinct.
An adapter may report its available symbols, but it must not redefine the global core universe.

## SMART RISK MANAGEMENT
Risk is a core decision layer, not an exchange feature.

It must be:
- provider-neutral
- contract-driven
- logically explainable
- independent of Toobit API details
- evaluated before Trade Gate

## CAPITAL
Production capital must come from REAL_CAPITAL.
Legacy/test capital configuration is non-production.
No verified real capital → fail closed.

## DATABASE
The production database is stateful infrastructure. Database mutation requires explicit authorization.

## EXECUTION
Execution is NOT BUILT / NOT AUTHORIZED in the current state. An adapter connection or pre-execution authorization boundary does not authorize execution. Order submission, cancellation, withdrawal and other exchange writes remain disabled unless explicitly authorized.

## TOOBIT ACCOUNT BLOCKER
The observed Toobit Account path remains blocked by HTTP/API -1022 INVALID_SIGNATURE. This is an independent production Account/Real-Capital source blocker. No blind signing patch is justified without new evidence and explicit authorization.

## PROHIBITED DRIFT
Do not:
- move core logic into an exchange adapter
- make Toobit mandatory
- couple Risk to exchange API quirks
- change closed contracts merely to accommodate an adapter
- redesign the pipeline because of an adapter problem
- introduce synthetic market data
- modify arunda_pipeline.py without explicit authorization

# END ARCHITECTURE
