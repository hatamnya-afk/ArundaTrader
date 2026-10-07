# ARUNDA TRADER — CURRENT FRONTIER

## STATUS
CURRENT FRONTIER — PROVIDER READINESS → MAIN / SELECTIVE INTEGRATION

## CURRENT STATE
MCP-01 handoff is complete and frozen. Main is canonical. The next step is a **static forensic map** of the closed provider-readiness contracts. Runtime remains NOT EXECUTED.

## AUTHORITATIVE HANDOFFS
- `MCP01_HANDOFF_TO_MAIN.md`
- `BUILDER_HANDOFF_PROVIDER_READINESS.md`

## ROUTE
`MCP-01 HANDOFF → MAIN → SELECTIVE, EVIDENCE-BACKED INTEGRATION → PROVIDER READINESS → PROJECT COMPLETION → TOOBIT BINDING → FINAL REAL-MARKET CONTROLLED TEST → EXECUTION AUTHORIZATION → FIRST REAL ORDER → FIRST REAL FILL → REAL OUTCOME → OBSERVATION → CALIBRATION`

## ACTIVE SCOPE
- Static/selective integration map only.
- MAIN only.
- No Runtime.
- No provider API call.
- No order / real trade.
- No provider write.
- No DB mutation.
- No strategy/Decision/Risk/Gate/Order/Execution redesign.
- No new branch.
- Do not wholesale-merge the divergent CP46-F source branch.
- Closed/verified stages remain historical truth unless direct regression is proven.

## CURRENT FORENSIC FINDING
MAIN currently exposes the legacy Toobit provider-preflight evidence files, but the authoritative CP46-D/F provider modules are not present by their known source names on MAIN. This must be mapped before any implementation decision.

## REQUIRED MAP
For each carry-forward contract report PRESENT / PARTIAL / MISSING / BLOCKED with exact MAIN file:function:
1. CP46-A3 SHORT/Futures vs Spot/SELL routing.
2. Provider order translation.
3. Toobit authoritative contract/filter state.
4. Toobit authoritative account state.
5. Authoritative open/recent order state.
6. Authoritative server timestamp.
7. Futures contract/account/exposure evidence.
8. Provider preflight fail-closed.
9. Quantity provenance.
10. Execution-quality dependency only if proven necessary.

## NEXT ACTION
Builder runs the exact commands in `BUILDER_HANDOFF_PROVIDER_READINESS.md` and returns **only the forensic map**. Management approval is required before any provider-readiness code is changed.

## SAFETY
EXECUTION AUTHORIZATION = FALSE
ORDER WRITE = FORBIDDEN
DATABASE WRITE = FORBIDDEN
PROVIDER WRITE = FORBIDDEN

# END CURRENT FRONTIER
