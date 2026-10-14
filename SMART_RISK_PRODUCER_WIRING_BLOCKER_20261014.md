# Smart Risk Producer Inventory — 2026-10-14

## Scope and safety

Static inspection only on `fix/smart-risk-handoff-contract-20261014`. No runtime, exchange API request, database write, order attempt, or execution authorization was performed. This is a historical candidate branch, not `operational-main-20261007`.

## Verified repository evidence

The following modules exist and validate/transform supplied observations:

- `real_capital_observation_contract_v0_1.py` — validates a supplied `RealCapitalObservation`; it is a contract, not a source of account capital.
- `real_capital_source_contract_v0_1.py` — validates a supplied capital mapping; it does not fetch or produce account balances.
- `real_portfolio_state_source_contract_v0_1.py` — validates a supplied portfolio-state mapping; it does not enumerate open positions or calculate allocated risk.
- `smart_risk_capital_bridge_v0_1.py`, `smart_risk_portfolio_bridge_v0_1.py`, `smart_risk_entry_stop_bridge_v0_1.py`, and `smart_risk_policy_bridge_v0_1.py` — read-only mapping/validation boundaries; they do not produce missing observations.
- `validated_stop_risk_policy_source_contract_v0_1.py` — requires explicit entry, stop price, stop distance, direction, asset, timestamp, provenance, and validated risk policy.
- `dynamic_smart_risk_sizing_boundary_v0_1.py` — requires caller-supplied capital, portfolio, stop/policy, and risk-policy observations and rejects mismatches.
- `dynamic_smart_risk_pipeline_adapter_v0_1.py` — fail-closed orchestration adapter. If any of the four required observations is absent, it returns `BLOCKED` without quantity or quantity source.
- `arunda_pipeline.py` on this candidate branch calls `build_dynamic_risk` in the Decision → Risk → Trade Gate section; static search found no call to `build_dynamic_smart_risk_decision` or `evaluate_smart_risk_for_asset` in that pipeline.

## Missing production connections

No dedicated producer module was found in the branch tree for any of the following:

1. Current-cycle real account capital observation, including source and observation timestamp.
2. Current-cycle portfolio state including usable capital, allocated risk, and concurrent positions.
3. Validated per-asset entry + stop policy observation with explicit provenance and matching cycle.
4. Validated risk-policy observation sourced from an approved production policy.

The presence of validators and bridge modules is not evidence that the underlying observations exist. Historical GET-only provider preflight does not establish a live producer because the earlier account read discarded balance values and did not feed Smart Risk.

## Decision

**BLOCKED — do not wire Smart Risk into the active pipeline yet.** Doing so now would require inventing, defaulting, or mislabeling at least one production observation. The adapter remains fail-closed and must not fall back to legacy quantity sizing.

## Next required engineering step

Identify or authorize concrete read-only producers for capital and portfolio, plus the authoritative entry/stop and risk-policy sources. Each producer must return current-cycle values with source, timestamp, asset/account scope, and provenance; the integration should reject stale/mismatched observations and retain `EXECUTION_ENABLED = FALSE`. Then add producer-specific contract tests and wire only the Smart Risk boundary after the existing Risk stage, without changing Decision/Trade Gate semantics or attempting orders.
