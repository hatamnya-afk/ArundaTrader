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
- `dynamic_smart_risk_pipeline_adapter_v0_1.py` — fail-closed orchestration adapter. If any of the four required observations is absent, it returns `BLOCKED` without quantity or quantity source.\n- `smart_risk_readonly_producer_boundary_v0_1.py` — validates the four explicit observations, enforces same-cycle timestamps and scope/asset/direction/entry agreement, then invokes the existing sizing boundary. It is an orchestration boundary, not a source generator.\n- `toobit_raw_account_observation_producer_v0_1.py` — newly added provider-native account evidence boundary. It preserves the existing adapter's raw GET-only balance rows and source metadata, but explicitly returns `capital_state=BLOCKED`; it does not calculate capital or usable capital. Its focused tests cover raw preservation, missing timestamps, failed reads, and malformed rows.
- `arunda_pipeline.py` on this candidate branch calls `build_dynamic_risk` in the Decision → Risk → Trade Gate section; static search found no call to `build_dynamic_smart_risk_decision` or `evaluate_smart_risk_for_asset` in that pipeline.

## Missing production connections

No complete production producer was found in the branch tree for any of the following (the raw account observation boundary below does not satisfy the capital/portfolio requirements):

1. Current-cycle real account capital observation, including source and observation timestamp.
2. Current-cycle portfolio state including usable capital, allocated risk, and concurrent positions.
3. Validated per-asset entry + stop policy observation with explicit provenance and matching cycle.
4. Validated risk-policy observation sourced from an approved production policy.

The presence of validators and bridge modules is not evidence that the underlying observations exist. Historical GET-only provider preflight does not establish a complete Smart Risk producer. The new raw account boundary preserves the balance rows, but raw balances still do not establish valued capital, usable capital, portfolio allocated risk, or a valid stop/risk policy.

## Decision

**BLOCKED — do not wire Smart Risk into the active pipeline yet.** Doing so now would require inventing, defaulting, or mislabeling at least one production observation. The adapter remains fail-closed and must not fall back to legacy quantity sizing.

## Next required engineering step

Next: obtain/authorize the valuation policy needed to turn provider-native balances into policy-valued capital; identify an authoritative current portfolio/position-risk ledger; and identify the approved versioned per-asset stop and risk policy. The raw account producer is intentionally not wired into Smart Risk because its output is not a capital observation. Each eventual producer must emit current-cycle values with source, timestamp, account/asset scope, and provenance; reject stale/mismatched observations; and retain `EXECUTION_ENABLED = FALSE`. Only after these inputs are grounded should producer-specific tests and post-Risk Smart Risk wiring be attempted. No Decision/Trade Gate semantics or order behavior may be changed.
