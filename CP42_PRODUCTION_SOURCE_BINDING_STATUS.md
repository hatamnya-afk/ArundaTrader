# CP42 — PRODUCTION TRADE-INTENT READINESS / REAL SOURCE BINDING

## STATUS
BLOCKED — REAL CAPITAL SOURCE GAP

## SCOPE
REAL PRODUCTION SOURCES → VALIDATED OBSERVATIONS → DECISION → TRADE INTENT

## INSPECTION RESULT
Repository State was loaded first from PROJECT_STATE.md, ARCHITECTURE.md, CHECKPOINTS.md, CURRENT_FRONTIER.md, and BUILDER_PROTOCOL.md. Closed checkpoints CP38–CP41 were treated as historical truth and not re-audited.

The repository contains the required provider-neutral contract surfaces for Real Capital Observation, Real Portfolio State, validated Entry/Stop/Risk Policy, Smart Risk, Trade Gate, and Decision → Trade Intent. The inspected state does not, however, prove a complete real production-source binding from a live account/balance producer through the required upstream chain into Trade Intent.

## FIELD TRACE

| Trade Intent field | Source | Producer | Contract / validation | Production boundary | CP42 result |
|---|---|---|---|---|---|
| asset | verified upstream Decision / Gate / Sizing / Stop-Risk outputs | existing upstream producers/boundaries | CP41 cross-check | provider-neutral | BLOCKED: end-to-end real producer lineage not demonstrated |
| direction | Trade Gate / Smart Risk / Stop-Risk outputs | existing upstream risk path | direction validation + cross-check | provider-neutral | BLOCKED: production lineage not demonstrated |
| entry | validated Entry/Stop input | existing upstream market/risk path | Entry validation | provider-neutral | BLOCKED: complete real producer binding not demonstrated |
| stop | validated Stop/Risk observation | existing Stop/Risk contract | observation + risk-policy validation | provider-neutral | BLOCKED: complete real producer binding not demonstrated |
| quantity | Smart Risk `position_size` | `smart_risk_engine_v0_1.py` | real capital + entry + stop + policy + portfolio inputs | provider-neutral | BLOCKED: upstream production inputs not fully bound |
| exposure | Smart Risk `exposure` | `smart_risk_engine_v0_1.py` | derived from validated position size and entry | provider-neutral | BLOCKED: upstream production inputs not fully bound |
| risk_state | Smart Risk / Trade Gate | existing risk boundaries | APPROVED validation | provider-neutral | BLOCKED: production-bound end-to-end path not demonstrated |
| decision_state | Decision output | verified CP40/CP41 path | READY + VALID | provider-neutral | PASS as existing verified boundary; no regression audit |
| policy_version | Risk / Gate / Stop-Risk outputs | existing policy path | cross-check | provider-neutral | BLOCKED: production source lineage not demonstrated |
| provenance | upstream validated observations | existing contracts | forbidden TEST/LEGACY/SIMULATED rejection | provider-neutral | PASS at contract level; real producer lineage missing |
| timestamp / snapshot identity | observation metadata | existing observation contracts | non-empty observed_at / source metadata | production trace | BLOCKED: complete source/snapshot lineage not demonstrated |

## REAL CAPITAL
Production capital must originate from REAL ACCOUNT / BALANCE OBSERVATION.

Existing contract surfaces:
- `real_capital_observation_contract_v0_1.py`
- `real_capital_source_contract_v0_1.py`
- `real_portfolio_state_source_contract_v0_1.py`

These contracts validate explicit real-capital/portfolio observations and reject forbidden sources/states. They are not a live account producer.

The known Toobit Account path remains blocked by HTTP 400 / API `-1022 INVALID_SIGNATURE`. No alternative verified real-account producer is established in the inspected CP42 branch.

Therefore:

**BLOCKED — REAL CAPITAL SOURCE GAP**

`capital_config.py` remains TEST / LEGACY / NON-PRODUCTION and cannot be promoted.

## ENTRY / STOP
Existing provider-neutral Entry/Stop and Stop/Risk contracts require explicit validated values and provenance. CP42 found no verified complete real production producer binding for these values in the path to Trade Intent.

Forbidden workarounds remain:
- latest-price fallback
- inferred stop
- ATR-derived fallback without validated upstream source
- interpolation
- forward-fill / back-fill
- padding
- fabricated defaults

## QUANTITY / EXPOSURE
`smart_risk_engine_v0_1.py` deterministically calculates `position_size` and `exposure` from upstream capital, entry, stop distance, risk policy, and portfolio state. The calculation is provider-neutral and side-effect-free, but the engine is not itself a real account source. Without a verified real-capital and production-bound upstream chain, CP42 cannot certify production quantity/exposure readiness.

## DECISION → TRADE INTENT
The existing CP41 boundary remains the consumer boundary. It validates and cross-checks upstream Decision, Trade Gate, Position Sizing, and Stop/Risk outputs; it does not invent missing production values. CP42 does not modify or re-audit CP41.

## PROVIDER BOUNDARY
Core / Decision / Smart Risk / Trade Intent remain provider-neutral.
Toobit remains an adapter/environment.
The `-1022 INVALID_SIGNATURE` condition is not moved into Core, bypassed with Test Capital, or treated as resolved.

## IMPLEMENTATION
No Production Code changed.
No new producer was invented.
No workaround or redesign was introduced.
The active frontier stops at the smallest provable source gap.

## ACCEPTANCE
- REAL_SOURCE_BINDING = BLOCKED
- TRADE_INTENT_INPUTS = BLOCKED
- REAL_CAPITAL_FIREWALL = PASS (contract-level)
- ENTRY_SOURCE = BLOCKED
- STOP_SOURCE = BLOCKED
- QUANTITY_SOURCE = BLOCKED
- EXPOSURE_SOURCE = BLOCKED
- PROVENANCE = PASS (contract-level)
- DECISION_CONSISTENCY = PASS (existing CP41 boundary; not re-audited)
- FAIL_CLOSED = PASS (existing boundaries)
- DYNAMIC_ASSET = PASS (existing CP41 boundary)
- PROVIDER_NEUTRAL = PASS
- NO_TEST_DATA = PASS
- NO_FIXED_15 = PASS
- NO_ORDER = PASS
- NO_AUTHORIZATION = PASS
- NO_EXECUTION = PASS
- NO_API = PASS
- NO_DB_WRITE = PASS

## NEXT ACTION
Remain blocked at the real production-source gap.
A future Management command may authorize the minimal investigation/integration needed to bind a verified real account/balance producer and any other missing production source. Until then CP42 remains the current frontier and CP43 must not start.
