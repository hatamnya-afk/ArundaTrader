# PRODUCT PATH AUDIT — EVIDENCE LEDGER
Date: 2026-10-18
Canonical ArundaTrader branch: `operational-main-20261007`
Purpose: record the repository-backed state for the signal-product path without reopening closed checkpoints or claiming live verification from static code.

## Status findings

### CP65 / Control Center
- Aroonda `PROJECT_STATE.md` at blob SHA `35332ee881a37caf2048b349a522fde5e6b89440` explicitly lists CP65 as `VERIFIED / CLOSED / CANONICAL`.
- This does **not** prove the customer-facing product Control Center is complete. Product UI/Control Center completeness remains `OPEN / NOT VERIFIED`.
- CP65 must not be reopened merely because the product needs additional UI work. The distinction is checkpoint status versus current product requirements.

### CP69 producer and ArundaTrader UI
- `arunda_pipeline.py`, blob SHA `962475a1185fb8471956d025c9791a8c58fd47b1`, lines 5377–5412, imports `build_observation`, `append_observation`, and `write_current_observation`; lines 5409–5410 append the historical observation and write the current handoff. This is static wiring evidence, not proof that a fresh runtime has emitted an artifact.
- `cp69_runtime_observation.py`, blob SHA `abffc5e2895c1cb0a18301d4aac7f9a8d0ba8341`, defines the canonical CP69 schema, the append-only stream, and the current-observation handoff. It enforces `EXECUTION=OFF`, `REAL_ORDER=False`, `REAL_TRADE=False`, and DB-write attribution.
- Native UI `arundatrader_live_ui.py`, current blob SHA `d8bf5d8491bab5dfdce6678c93fc35efd0439aef`, reads the current CP69 handoff (environment override `ARUNDATRADER_CURRENT_OBSERVATION_PATH` or the canonical default), validates identity and age, and clears rows on stale/malformed/invalid input.
- UI tests are in `test_arundatrader_native_ui.py`, blob SHA `3e2fedc44defe43e57f61b32bb547e0433fc6646`. Native UI contract workflow run `39071371893` and existing native UI run `39071371861` passed.

### Aroonda CP69 / CP72 boundary
- Aroonda `arundatrader_observation_consumer.py`, blob SHA `491f4a8c5a66ac7c8ea8a3be0ceb583f0a8ba371`, validates CP69 and maps it through the existing environment bridge.
- Aroonda `arundatrader_bridge.py`, commit `20900f8920a524dc58246a3faea044969750f762`, is the environment boundary; it does not connect to or mutate ArundaTrader.
- Aroonda `CURRENT_FRONTIER.md`, blob SHA `3c36e953893f0cbb863613dbe3d73a00d1755dc2`, marks CP72 current and management-authorized for read-only CP69 observation analysis. CP72 analyzer is `arundatrader_runtime_analysis.py`, current blob SHA `8f18a1fbca733823682cd46d80df3e78c224c41b`; CLI is `arundatrader_runtime_analysis_cli.py`, blob SHA `ab0e8031e28e97261dc930f583b0405c4fa6a105`.
- Aroonda PR #6 merged at `bbba16b44d098ec62d4ffd96b3b4fdc7df6c02f8`. CP72 compile and contract-test workflow run `39071533922` passed. These tests validate contracts with fixtures; they do not establish that a fresh real runtime observation has been analyzed.
- ArundaTrader PR #55 merged at `9358cefbe9a288fcc2ef40a06c1d2a333b6f8784`. It adds an optional UI projection via `AROONDA_RUNTIME_ANALYSIS_CLI`, calls the configured CLI without a shell and with an 8-second timeout, and accepts the result only when its snapshot identity matches the current CP69 observation and execution/DB-write state remains fail-closed. The actual local cross-repository E2E remains `NOT VERIFIED` until configured and exercised against a fresh authorized observation.

### Signal-quality evidence and PR #37 reuse
- Existing tracker `global_selection_outcome_tracker_v0_1.py`, blob SHA `0d5186646d8f106e186ea4d8ce0f2502f9b4757f`, and report `global_selection_quality_report_v0_1.py`, blob SHA `9d7f676b6136d5f3d2eae348561b7ca05544f07f`, already define real-observation evidence and 1h/4h/24h descriptive outcomes.
- PR #37's branch remains divergent (13 ahead / 183 behind the canonical base) and was **not** merged. Its compatible dashboard capability was selectively ported in ArundaTrader PR #54, merged at `fd0ccbb2cf1cec0394f65edf187795e63e8a274e`; focused Global Selection Outcome Tracker CI run `39071186208` passed. The port reuses the existing tracker/report and excludes the optional Windows task/supervisor scripts.
- Dashboard source `arunda_selection_quality_dashboard_v0_1.py`, blob SHA `2b1259e2a3e9d113d2ce1cb67323a8715b3e5cc8`, is loopback-only, read-only, returns an empty report for a missing stream, and fails closed on corrupt evidence. Excursion columns are explicitly labeled as full-observed-span metrics, not horizon-specific metrics.
- The repository does not contain `runtime_observations/global_selection_outcomes.jsonl` or the CP69 current/historical JSONL artifacts. That means this repository snapshot cannot substantiate a real-data quality evaluation. It does **not** prove those files are absent from the user's local runtime.

## Current gate
- CP65: `VERIFIED / CLOSED / CANONICAL` — unchanged.
- CP69 producer and native UI: `BUILT`; static wiring and contract tests are evidenced; fresh runtime E2E: `NOT VERIFIED`.
- Aroonda CP72 read-only CLI: merged; contract CI passed; fresh runtime E2E: `NOT VERIFIED`.
- Selection-quality evaluation and customer-eligible signal selection: `BLOCKED / NOT VERIFIED` pending the genuine local outcome stream and adequate complete horizons.
- Customer access/subscription/payment: `NOT STARTED / NOT VERIFIED`; must follow quality evaluation and explicit signal selection.
- `EXECUTION AUTHORIZATION = FALSE`. No order, exchange/provider write, production DB mutation, execution switch, or pipeline modification is authorized by this audit.

## Next evidence-producing actions
1. On the local machine, configure `ARUNDATRADER_CURRENT_OBSERVATION_PATH` to the producer's actual current CP69 artifact if the default is not correct.
2. Configure `AROONDA_RUNTIME_ANALYSIS_CLI` to the absolute path of the merged Aroonda CLI, then launch the existing UI and verify the same `runtime_snapshot_id` is shown by both sides.
3. Run the local selection-quality dashboard against the existing real outcome stream. Export or report only the genuine counts and observed/pending status for each horizon; do not fill gaps.
4. Document sample sufficiency and signal-eligibility criteria before choosing customer-facing signals. Only then design the subscription/payment layer.
