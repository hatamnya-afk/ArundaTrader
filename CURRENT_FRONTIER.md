# ARUNDA TRADER — CURRENT FRONTIER

## STATUS
CURRENT FRONTIER — PROVIDER READINESS → MAIN / SELECTIVE INTEGRATION — MAP VERIFIED

## CURRENT STATE
MCP-01 handoff is complete and frozen. Main is canonical. The provider-readiness forensic map is now verified from the current MAIN tree. The authoritative CP46-D/F provider modules are present on MAIN as selective evidence-backed contracts. Runtime remains NOT EXECUTED.

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
The previous finding was stale and is corrected here. MAIN contains the selective CP46-D/F/provider-readiness contracts:
- `cp46_d_production_provider_preflight_v0_1.py`
- `cp46_d_provider_execution_handoff_v0_1.py`
- `execution_venue_routing_policy_v0_1.py`
- `provider_order_translation_v0_1.py`
- `provider_preflight_v0_1.py`
- `exchange_execution_contract.py`
- `provider_preflight_evidence_assembler_v0_1.py`
- `toobit_provider_order_state_v0_1.py`
- `toobit_provider_preflight_evidence_v0_1.py`

The modules are evidence/contract boundaries, not a license to bind Toobit into the Core now. `arunda_pipeline.py` remains exchange-agnostic and does not call the Toobit preflight chain. This is architecturally correct while the Project Completion Gate remains open and Toobit Binding is not yet authorized.

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
No provider-readiness code patch is required at this frontier. Preserve the existing MAIN contracts as selective evidence-backed boundaries. The next advancement is the Project Completion Gate; only after that gate is CLOSED may Toobit Binding connect these contracts to the exchange adapter. Do not wire Toobit into `arunda_pipeline.py` before that gate.

## SAFETY
EXECUTION AUTHORIZATION = FALSE
ORDER WRITE = FORBIDDEN
DATABASE WRITE = FORBIDDEN
PROVIDER WRITE = FORBIDDEN

# END CURRENT FRONTIER
