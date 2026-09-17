# CP42 — PRODUCTION TRADE-INTENT READINESS / REAL SOURCE BINDING

## MANAGEMENT STATUS
**INTERPRETATION CORRECTED — EXCHANGE ACCOUNT/CAPITAL IS DEFERRED, NOT A CORE BLOCKER**

## ORIGINAL INSPECTION
CP42 inspected the production-source lineage required by Trade Intent and identified that the repository did not prove a live exchange Account/Balance producer bound into the complete production path.

That observation remains technically true for the exchange-binding layer, but Management has now explicitly determined that a live exchange Account/Balance source is NOT required to complete the exchange-agnostic Core.

## AUTHORITATIVE DECISION
The Core must advance independently of Toobit or any exchange.

The required Core path is:

REAL MARKET DATA → ANALYSIS → OPPORTUNITY → SIGNAL → SCORE → DECISION → RISK → POSITION SIZE → TRADE GATE → TRADE INTENT → PRE-EXECUTION READY → EXECUTION-READY PACKAGE

After that:

PROJECT VERIFICATION → FULL TEST / CLEANUP → PACKAGE → SERIOUS PORTABLE BACKUP

Only then:

EXCHANGE BINDING → EXCHANGE-SPECIFIC TESTS → MANAGEMENT AUTHORIZATION → USER CAPITAL → CONTROLLED REAL TEST

## CAPITAL INTERPRETATION
Live exchange capital is intentionally deferred.

For the current Core:
- no live exchange account is required
- no live exchange balance is required
- no private exchange API is required
- no signature is required
- no user capital is required
- provider-neutral Capital/Portfolio abstractions may be used where the Core requires capital/portfolio state

For the later Exchange Binding phase:
- Account/Balance binding is implemented at the provider boundary
- exchange-specific constraints are integrated and tested
- private API/authentication/signature work is performed only there
- user capital enters only after Management authorization and exchange verification

`capital_config.py` remains TEST / LEGACY / NON-PRODUCTION and must never be promoted to production capital.

## TRADE INTENT FIELD TRACE
The Core still requires every Trade Intent field to have a valid upstream contract and producer lineage. The absence of a live exchange source does not permit invention or fallback.

| Field | Core requirement | Current routing |
|---|---|---|
| asset | dynamic, validated identity | Core/upstream provider-neutral chain |
| direction | validated LONG/SHORT semantics | Decision/Risk/Gate chain |
| entry | explicit validated market observation | real market-data chain |
| stop | explicit validated Stop/Risk observation | risk chain |
| quantity | deterministic Smart Risk output | provider-neutral capital/portfolio abstraction + risk inputs |
| exposure | deterministic Smart Risk output | provider-neutral capital/portfolio abstraction + risk inputs |
| risk_state | validated APPROVED state | Smart Risk / Trade Gate |
| decision_state | READY + VALID | verified CP40/CP41 boundary |
| policy_version | explicit and cross-checked | risk/gate/stop contracts |
| provenance | required, non-test production lineage | existing validation contracts |
| timestamp/snapshot identity | explicit observation identity | observation contracts / source metadata |

No field may be fabricated, interpolated, padded, forward-filled, back-filled, or replaced with a hardcoded/fixed-15 value.

## TOOBIT
Known Toobit Account failure: HTTP 400 / API `-1022 INVALID_SIGNATURE`.

This is a future exchange-binding issue. It is not a reason to stop the Core, and it must not be moved into Core or bypassed with test capital.

## FORBIDDEN DURING CORE
- user capital
- live exchange account requirement
- Toobit/private API
- signature generation
- order submission
- execution authorization
- exchange write
- production DB write
- synthetic/fabricated/fallback values
- fixed-15 logic
- unauthorized `arunda_pipeline.py` modification
- reopening closed checkpoints

## NEXT MANAGEMENT FRONTIER
Do not remain stopped at the exchange Account/Balance gap.

Continue the exchange-agnostic Core from:

**TRADE INTENT → PRE-EXECUTION READY → EXECUTION-READY PACKAGE**

Then perform the project verification / cleanup / package / serious backup phase before any exchange binding.

# END CP42 STATUS
