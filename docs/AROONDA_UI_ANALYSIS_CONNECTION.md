# ArundaTrader native UI — optional Aroonda CP72 projection

The existing read-only native UI can display a structured Aroonda CP72 projection from the existing CP69 source observation. It does not import Aroonda modules into ArundaTrader and does not create a new bridge or data source.

## Configure

Set `AROONDA_RUNTIME_ANALYSIS_CLI` to the absolute path of `AroondaAI/arundatrader_runtime_analysis_cli.py` before launching:

```powershell
$env:AROONDA_RUNTIME_ANALYSIS_CLI = "C:\\path\\to\\AroondaAI\\arundatrader_runtime_analysis_cli.py"
python .\\run_live_arundatrader_ui.py
```

The UI calls the CLI with the current CP69 JSONL path using an argument list (no shell), an 8-second timeout, and no output file. It refreshes the Aroonda projection only when the content-derived runtime snapshot ID changes. The projection is accepted only if its snapshot identity matches the current CP69 record and the execution boundary remains fail-closed.

If the CLI path is unset or the analysis fails, the existing ArundaTrader view remains read-only and displays Aroonda analysis as unavailable/blocked; it does not substitute fabricated data or retain a mismatched projection.

This is a local integration contract, not proof that a fresh real runtime artifact exists. Aroonda's CP72 CLI must be available from the separate AroondaAI repository, and actual end-to-end verification still requires a current authorized CP69 observation.
