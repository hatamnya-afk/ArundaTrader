# CP41 — DECISION → TRADE INTENT BOUNDARY

## STATE
CP41 = CLOSED / VERIFIED / PASS (BOUNDARY + CONTRACT + ISOLATED VERIFICATION)

## CHAIN
SEALED DECISION OUTPUT → VALIDATED TRADE INTENT BOUNDARY

## IMPLEMENTATION
- `decision_trade_intent_boundary_v0_1.py`
- `test_cp41_decision_trade_intent_boundary_v0_1.py`

## SOURCE-OF-TRUTH RULE
The boundary consumes existing upstream outputs only. It does not modify the Decision engine, Smart Risk, Trade Gate, Position Sizing, Stop/Risk source, Exchange Constraints, or `arunda_pipeline.py`.

## REQUIRED UPSTREAMS
- CP40 Decision output
- approved Trade Gate output
- approved Position Sizing / Smart Risk output
- validated production Stop/Risk source

## CONTRACT
Trade Intent is valid only when:
- Decision state = READY and Decision validation = VALID
- asset identity matches across all upstreams
- Trade Gate = APPROVED
- Risk = APPROVED
- Stop/Risk observation = AVAILABLE + VALID
- direction, entry, stop distance, quantity, exposure and policy version agree across sources
- explicit stop price is supplied by the Stop/Risk source; it is never inferred
- provenance is explicit, real/production, non-TEST/LEGACY/SIMULATED, and consistent
- no execution/provider surface is present

## OUTPUT
The boundary exposes only validated upstream values:
- decision state / validation / reason
- asset
- direction
- entry price
- stop price / stop distance
- quantity
- exposure
- risk state
- trade gate state
- policy version
- provenance
- observed timestamp

No capital, portfolio state, exchange, order ID, authorization, signature, API request, submission state, or execution value is created.

## VERIFICATION
- Static compile: PASS in isolated verification environment.
- Focused behavior verification: PASS.
- Decision fail-closed: PASS.
- Dynamic asset: PASS.
- Provider-neutral: PASS.
- Provenance / TEST rejection: PASS.
- Cross-source quantity/entry/stop/exposure/policy consistency: PASS.
- No stop fabrication: PASS.
- No fixed-15 logic: PASS.
- No capital fabrication: PASS.
- No order / execution / authorization / API / DB write: PASS.
- Scope comparison from CP40 parent: only the CP41 boundary and focused test were added.

## SAFETY
No runtime was executed.
No production DB was modified.
No exchange API was called.
No order was created, submitted, cancelled, or authorized.
`arunda_pipeline.py` was not modified.

## LIMIT
Local Windows workspace execution is not directly accessible from this environment. The verification above is repository-code / isolated verification and must not be described as a local Windows runtime test.

## TOOBIT
Toobit `-1022 INVALID_SIGNATURE` remains an independent Account/Real-Capital blocker and is outside CP41.

# END CP41 STATUS
