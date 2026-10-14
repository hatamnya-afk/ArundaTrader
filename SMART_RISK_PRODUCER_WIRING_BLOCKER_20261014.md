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

**Status:** policy-evidence contract = implemented on candidate; authenticated management approval = NOT VERIFIED; live rate source = NOT VERIFIED; authoritative account-wide ledger producer = NOT VERIFIED; Smart Risk pipeline wiring = BLOCKED. Focused CI = PASS on code-bearing commit `9de45bfe196fee059cfbe0c0a965f3e10de57c11` (workflow run #57 / run ID `38617349451`): compile step and focused test step both completed successfully. The later commit `e8be8c05ae0375108ecba8d7ad36b355235f416e` changed only this blocker report; it did not change executable code or tests. No runtime, exchange call, order attempt, database write, or operational-branch modification was performed.


## Account-wide ledger producer implementation — 2026-10-14

Added `toobit_account_wide_portfolio_risk_ledger_producer_v0_1.py` and focused tests. This pure producer combines already captured, normalized Spot and Futures observations only when both are explicitly `ACCOUNT_WIDE`, account/cycle/timestamp identities match, the dual-currency valuation policy and rate sources validate, and every non-zero balance asset is valued by the current v0.1 scope. It sums explicit USDT/USDC totals and usable amounts, and verifies aggregate allocated risk equals the sum of per-position risk evidence. Unsupported non-zero assets, symbol-scoped positions, missing risk, mixed cycles, unapproved rate sources, or missing observations fail closed. CI now compiles and tests this producer.

Important integration limit: the current Toobit Futures adapter method is symbol-scoped and therefore cannot itself satisfy the account-wide producer's `positions_coverage=ACCOUNT_WIDE` input. The new module is a producer over supplied evidence, not yet a complete provider acquisition path. A real account-wide Futures positions/balance source, all-asset valuation policy (for any nonzero asset beyond USDT/USDC), and authenticated risk-allocation evidence remain unverified. Test amounts/rates are synthetic fixtures only. No exchange calls, runtime, order, DB write, or operational-branch change was performed.


Focused CI for the account-wide producer completed successfully on commit `8e181d65dcbb3ef598495a90211652d5c2ed0bae`: run #58 / [run ID 38618998806](https://github.com/hatamnya-afk/ArundaTrader/actions/runs/38618998806), with compile and focused test steps successful. This verifies the pure aggregation/validation code against fixtures; it does not verify a live provider's account-wide source or authorize production wiring.


## 2026-10-14 — Account-wide Futures and all-asset valuation contract increment

- Added `account_wide_futures_coverage_contract_v0_1.py` and focused tests. It rejects symbol-scoped responses, unproven pagination completeness, mismatched page counts, non-GET access, duplicate position IDs, and missing explicit per-position risk. It deliberately labels endpoint completeness semantics as requiring independent verification; caller-supplied flags alone do not prove Toobit endpoint behavior.
- Added `all_asset_valuation_contract_v0_1.py` and focused tests. It requires an explicit approved, versioned source for every non-zero asset in the supplied balance union; verifies rate freshness against a configured maximum age, cycle and policy alignment, source/reference matching, and does not assume USDC parity with USDT.
- Wired both modules and tests into the candidate branch's focused CI compile/test steps.
- **Integration gate remains closed:** these new contracts are not yet connected to the account-wide ledger producer. Do not connect until focused CI passes and the real provider endpoint's account-wide completeness semantics are documented/verified. The current adapter remains symbol-scoped; no endpoint or pagination behavior has been invented.
- The generic valuation contract is a tested-contract candidate only; actual all-asset aggregation and authoritative-ledger schema still require a compatible integration change after CI verification.
- No live exchange API calls, runtime, orders, cancellations, withdrawals, or DB writes. Operational branch unchanged. All fixture values are synthetic and not production account evidence.


## 2026-10-14 — CI-verified account-wide read boundary, generic valuation, and Smart Risk bridge

- Toobit official account/trading documentation states that `GET /api/v1/futures/positions` returns all contract positions when `symbol` is omitted; `category=USDT` and `category=USDC` are separate settlement categories. The read-only adapter now queries both categories without a symbol filter and rejects malformed/duplicate identities. Documentation reference: https://api-docs.toobit.com/api/usdt-m-account-and-trading
- Added read-only Futures account-wide balances for both categories and a normalizer that joins the separately captured positions and balances into a same-cycle observation. Added a Spot balance normalizer deriving total only from explicit `free + locked`, usable only from explicit `free`, and rejecting duplicate assets/malformed amounts.
- Generalized the approved valuation policy source contract to support versioned rate-source references for every held asset while retaining mandatory USDT and USDC source definitions. The account-wide ledger producer now values all explicitly evidenced non-zero assets and fails closed on any missing/stale/unapproved rate.
- The authoritative ledger contract validates and preserves all-asset valuation evidence. A pure bridge now maps a fully validated ledger into Smart Risk capital/portfolio sources and invokes the existing read-only Smart Risk sizing boundary. The bridge refuses incomplete valuation coverage or a blocked portfolio ledger.
- Capital and portfolio risk are now separated: with complete approved valuation evidence, usable/available capital may be reported as AVAILABLE even when portfolio risk is BLOCKED due to missing per-position risk allocations. Such partial output is not accepted by the Smart Risk bridge; quantity remains unavailable.
- Focused CI run #102 / ID `38622607885`: compile PASS; focused tests **152 passed**. Run: https://github.com/hatamnya-afk/ArundaTrader/actions/runs/38622607885
- **Still NOT VERIFIED against a live Toobit account:** no live API calls were made in this frontier. Endpoint completeness is grounded in official documentation and fake-transport contract tests, not a live response capture. All test amounts and rates are synthetic.
- **Smart Risk remains gated on real per-position risk evidence:** provider position rows do not provide approved stop/risk allocation evidence. The account-wide ledger needs a complete risk allocation for every open position and matching total; no risk is inferred from size, margin, or PnL. An approved stop/risk policy and authenticated valuation/rate approval artifacts must be supplied before the bridge can produce a live Smart Risk quantity.
- No order, cancellation, withdrawal, production runtime, database write, or operational-branch modification was performed. The candidate PR is CI-only and must not be merged as part of this frontier.


## 2026-10-14 — Smart Risk bridge hardening and verification retry

- Hardened `smart_risk_authoritative_ledger_source_bridge_v0_1.py`: now requires ledger ID/version and policy approval reference, explicit Spot/Futures observation timestamps, timezone-aware timestamps, market observations not later than the ledger timestamp, unique normalized asset names, finite positive rates, rate source/reference provenance, matching cycle and valuation-policy identity/version, non-future rate timestamps, and USDT base rate exactly 1.0. Invalid evidence returns BLOCKED and no capital/portfolio source.
- Expanded bridge fixtures and fail-closed regression tests for cycle mismatch, policy mismatch, non-finite rates, future rates, market timestamps after ledger time, and duplicate asset labels after normalization. Fixture values remain synthetic test data only.
- Latest candidate commit: `1fe698584aaf0766589bbcecbd7da4282ca159ec`.
- Latest focused CI: [run #109 / ID 38625769869](https://github.com/hatamnya-afk/ArundaTrader/actions/runs/38625769869). Compile step PASS; focused test suite **158 passed in 0.68s**.
- This is code/contract verification only. The bridge remains a read-only candidate integration and is not connected to the operational `arunda_pipeline.py`; no live account observation, approved production rate/policy evidence, or authenticated per-position risk-allocation ledger was created by these changes.
- Operational branch remains unchanged; PR #35 remains Draft and unmerged. No live exchange API request, production runtime, order/cancel/withdrawal, or database write was performed.


## 2026-10-14 — Ledger evidence integrity hardening (CI #118)

The ledger producer and regression suite were tightened after examining the actual aggregation path:

- Duplicate balance rows for the same normalized asset in one market now block rather than being summed, preventing duplicate provider rows from inflating capital.
- Spot and Futures timestamps are parsed as timezone-aware values; future-dated observations block. Different observation times are accepted only when an explicit `max_observation_age_seconds` freshness policy is supplied. Without that policy, timestamps must match exactly.
- Currency-rate source references must match the approved policy reference, not just the source label.
- Currency rates require timezone-aware observation timestamps; future/stale rates block. Different rate timestamps require an explicit `max_rate_age_seconds` policy; no freshness window is silently invented.
- Regression coverage added for duplicate assets, mismatched source references, stale observations, future observations, and stale currency rates.

Latest candidate code/test commit: `47720737c50988217c732a13074ccf10be7e3456`.
Focused CI run #118 / ID `38627405754`: compile PASS; **163 passed in 0.79s**. [View run](https://github.com/hatamnya-afk/ArundaTrader/actions/runs/38627405754).

## Actual-evidence gate — still open

These changes harden the acceptance boundary; they do not create real account evidence or management approval. The current frontier still prohibits live exchange API requests and production runtime. Therefore no claim is made that this run observed the user's Toobit balances, open positions, current exchange rates, or authentic management risk-policy approval.

To clear the real-evidence gate, the intake must contain authenticated, current-cycle read-only Spot and both Futures settlement-category account observations; complete account-wide position coverage; approved rate-source references and fresh rates for every non-zero asset; and explicit per-position stop/risk allocations reconciled to the portfolio total. The risk-policy artifact must include a verifiable approval identity/reference, version, effective interval, risk-per-trade, maximum portfolio risk, and maximum concurrent positions. Plain strings saying `APPROVED` or test fixtures do not authenticate these facts.

Until those authentic artifacts are supplied through an authorized evidence-capture path, actual capital and portfolio risk remain **NOT VERIFIED / BLOCKED**, and Smart Risk production wiring remains blocked. Operational branch remains unchanged; PR #35 remains Draft/unmerged; no order, cancellation, withdrawal, production runtime, live API call, or DB write was performed.
