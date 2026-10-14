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
- `dynamic_smart_risk_pipeline_adapter_v0_1.py` — fail-closed orchestration adapter. If any of the four required observations is absent, it returns `BLOCKED` without quantity or quantity source.\n- `smart_risk_readonly_producer_boundary_v0_1.py` — validates the four explicit observations, enforces same-cycle timestamps and scope/asset/direction/entry agreement, then invokes the existing sizing boundary. It is an orchestration boundary, not a source generator.\n- `toobit_raw_account_observation_producer_v0_1.py` — preserves raw GET-only spot balance rows and metadata but returns `capital_state=BLOCKED`; no capital valuation is inferred.\n- `toobit_raw_position_observation_producer_v0_1.py` — preserves symbol-scoped raw futures position rows from the existing GET-only `futures_account_state` result, but returns `portfolio_state=BLOCKED`; it does not claim account-wide concurrent positions or allocated risk. Both producer boundaries have focused fail-closed tests wired into CI.
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

Next: obtain/authorize the valuation policy needed to turn provider-native balances into policy-valued capital; identify an authoritative current portfolio/position-risk ledger; and identify the approved versioned per-asset stop and risk policy. The raw account and position producers are intentionally not wired into Smart Risk because their outputs are raw evidence, not policy-valued capital or an account-wide portfolio risk observation. Each eventual producer must emit current-cycle values with source, timestamp, account/asset scope, and provenance; reject stale/mismatched observations; and retain `EXECUTION_ENABLED = FALSE`. Only after these inputs are grounded should producer-specific tests and post-Risk Smart Risk wiring be attempted. No Decision/Trade Gate semantics or order behavior may be changed.


## Account-wide ledger source inspection — 2026-10-14 continuation

A recursive static inventory of the candidate branch tree (186 tracked files) found no distinct account-wide portfolio/position-risk ledger producer or persistent ledger module. The matching files were limited to the existing portfolio validator/bridge, Smart Risk sizing/orchestration contracts, risk engine, Toobit adapter/preflight, and the raw symbol-scoped position observation producer. This is a source-tree finding only; no runtime or exchange request was made.

Added `authoritative_portfolio_risk_ledger_contract_v0_1.py` as a **versioned input contract, not a producer**. It fails closed when the ledger is absent, not validated, missing identity/version/account scope/timestamp/provenance, or does not explicitly declare `coverage_scope=ACCOUNT_WIDE`. It rejects the raw symbol-scoped Toobit positions source and validates explicitly supplied capital/risk/position totals without deriving any of them. Focused tests cover absent ledger, valid explicit ledger shape, symbol-scope rejection, missing metadata, invalid risk values, and side-effect surface.

The contract and tests are included in the candidate branch's focused CI workflow. The workflow result is **NOT VERIFIED** until a matching run is observed. This change does not establish that a real ledger exists, does not connect the contract to Smart Risk or `arunda_pipeline.py`, and does not clear the production blocker.

## Remaining authoritative inputs

- A real account-wide ledger source and its approved ownership/provenance remain **NOT VERIFIED**.
- Approved valuation and usable-capital policy remains **BLOCKED**.
- Valid per-asset entry/stop policy and approved versioned risk policy remain **BLOCKED / NOT VERIFIED**.
- Smart Risk production wiring remains **BLOCKED**; no fallback to legacy sizing is authorized.


## Phase-one account scope decision — 2026-10-14

Management selected **both Toobit Spot and Toobit Futures** for the first real-account phase. The candidate ledger contract and focused tests were tightened accordingly:

- A valid ledger observation must explicitly declare account-wide coverage and both `SPOT` and `FUTURES`; either market alone, symbol-scoped evidence, or an unrecognized coverage declaration blocks.
- The ledger must identify one cycle plus separate Spot and Futures observation timestamps; this contract does not assume those timestamps are identical.
- The ledger must identify an approved valuation policy and its version. This is a required declaration, not proof that the policy or source is actually approved by management.
- Portfolio capital, usable capital, allocated risk, and concurrent-position totals must be supplied by an authoritative ledger. This contract does not calculate them from raw exchange balances or positions.

**Status after this change:** the dual-market *input contract* is defined on the candidate branch. A real account-wide ledger producer, policy-valued Spot/Futures balances, policy approval evidence, and current-cycle portfolio risk totals remain **NOT VERIFIED / BLOCKED**. The contract's test fixture is synthetic test data only and must never be treated as production capital or live account evidence.

No pipeline wiring, runtime, exchange request, order attempt, database write, or operational-branch modification was performed.


## Management decisions confirmed — 2026-10-14

- Account scope: **Toobit Spot + Toobit Futures**.
- Reporting currency: **USDT**, with explicit support for both USDT and USDC source balances.
- USDC must not be treated as equal to USDT by assumption. Each currency observation must provide a positive finite conversion rate to USDT, rate source, rate timestamp, the same approved valuation policy ID/version, and the same declared ledger cycle. USDT base rate must be exactly 1.0.
- Both market coverages, account-wide scope, cycle identity, and approved versioned valuation policy are required. A contract fixture is not approval evidence or live account data.

The authoritative ledger contract and focused tests now encode these requirements. They validate supplied evidence only; they do **not** fetch raw account data, prove policy approval, compute balances from provider responses, or calculate portfolio risk.

**Current status:** dual-market/dual-currency input contract = implemented on candidate; current production ledger producer = **NOT VERIFIED**; real approved valuation policy/source = **BLOCKED**; Smart Risk production wiring = **BLOCKED**; latest CI for these latest commits = **NOT VERIFIED** until a run tied to these commits is confirmed.

No runtime, live exchange API call, order, database write, or operational-branch modification was performed.


## Valuation policy evidence boundary — 2026-10-14 continuation

Added `approved_valuation_policy_source_contract_v0_1.py` and focused tests. The contract requires an explicit approval state, policy ID/version, approval reference, approver identity, approval/effective timestamps, and separately declared USDT and USDC rate-source references. It rejects naive timestamps, inactive/future approval windows, missing currency rate-source declarations, and untraceable references.

The authoritative ledger contract now calls this validator, requires policy identity/version to match the ledger declaration, and requires each cycle's currency-rate source to match the source named by the policy evidence. Focused tests cover missing/unapproved policy evidence and mismatched rate-source/policy identity. The workflow compiles and tests the new boundary.

Important limits:
- The approval record and rate-source references are supplied evidence; this validator does not authenticate their provenance cryptographically or grant management approval.
- The test fixtures are synthetic and are not approved policy, live rates, account balances, or production capital.
- This remains an input-validation boundary, not the missing account-wide Spot + Futures ledger producer. It does not aggregate provider balances, account for liabilities/margin/equity, enumerate all positions, or calculate allocated risk.

**Status:** policy-evidence contract = implemented on candidate; authenticated management approval = NOT VERIFIED; live rate source = NOT VERIFIED; authoritative account-wide ledger producer = NOT VERIFIED; Smart Risk pipeline wiring = BLOCKED. Latest CI result remains NOT VERIFIED because no matching run/status has yet been returned for the latest candidate commits. No runtime, exchange call, order attempt, database write, or operational-branch modification was performed.
