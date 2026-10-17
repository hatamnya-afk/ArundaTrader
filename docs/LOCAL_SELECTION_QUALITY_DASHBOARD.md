# Local selection-quality dashboard

The dashboard is an operator-facing, **read-only** view of the existing Global Selection Quality Loop. This is a selective port of PR #37 onto the current canonical branch; the divergent PR branch is not merged. It reads only the append-only real-observation stream and summarizes genuine post-launch market observations. It does not create market data, call Toobit, write the trading database, change decisions, or enable order submission.

## Run interactively

From the repository root:

```powershell
python .\arunda_selection_quality_dashboard_v0_1.py
```

Open http://127.0.0.1:8765. The server rejects non-loopback bind addresses. The page refreshes every 60 seconds. If the stream is missing or empty, the report stays empty rather than inventing outcomes.

## Optional: keep the dashboard available after Windows logon

This is an opt-in user-level Scheduled Task for the dashboard only; it does **not** start the trading pipeline or enable 24/7 trading.

From the repository root in PowerShell:

```powershell
.\scripts\install_selection_dashboard_task.ps1
```

The task launches a restart supervisor and writes its log to:

`%LOCALAPPDATA%\ArundaTrader\logs\selection-dashboard-supervisor.log`

To remove the task:

```powershell
.\scripts\uninstall_selection_dashboard_task.ps1
```

The scripts do not change repository files, exchange credentials, the database, or execution flags. If local PowerShell policy blocks script execution, follow your organization's policy rather than bypassing it.

## Evidence semantics

- 1h, 4h, and 24h rows are descriptive outcomes for prior selections, not trading signals.
- Favorable/adverse excursion columns summarize the entire observed span for each selection, not the selected horizon; their labels state this explicitly.
- Assets are ranked only after the configured minimum sample size is met.
- A missing observation is not treated as a zero return.
- Provider order acceptance, fill, and realized trading P&L are different from directional market-selection outcomes.
- The dashboard is not a substitute for the final real-order technical gate or a full trading-runtime service supervisor.
