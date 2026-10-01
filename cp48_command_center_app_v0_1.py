from __future__ import annotations

import json
import os
from pathlib import Path
import tkinter as tk
from tkinter import ttk


APP_TITLE = "Aroonda Command Center"

CP69_STREAM_ENV = "ARUNDA_CP69_RUNTIME_OBSERVATION_STREAM"
DEFAULT_CP69_STREAM = (
    Path(__file__).resolve().parent
    / "runtime_observations"
    / "arundatrader_runtime_observations.jsonl"
)

CP69_SCHEMA = "arunda.runtime_observation"
CP69_SCHEMA_VERSION = "1.0"
CP69_SOURCE_SYSTEM = "ArundaTrader"
CP69_ENVIRONMENT_ID = "arundatrader"
CP69_ADAPTER_ID = "arundatrader_adapter"

CP49_DB_WRITE_BOUNDARY = "CP49_AUTHORITATIVE_BIRTH_PERSISTENCE"

REFRESH_MS = 1000


def _cp69_stream_path() -> Path:
    configured = os.environ.get(CP69_STREAM_ENV)
    return Path(configured) if configured else DEFAULT_CP69_STREAM


def _count(value: object) -> int:
    if isinstance(value, (list, tuple, dict)):
        return len(value)
    return 0


def _latest_cp69_observation() -> tuple[dict | None, str]:
    path = _cp69_stream_path()

    if not path.exists():
        return None, "NOT AVAILABLE / STOPPED — NO CP69 OBSERVATION STREAM"

    if not path.is_file():
        return None, "BLOCK — CP69 STREAM PATH IS NOT A FILE"

    try:
        last_line = None

        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    last_line = line

        if not last_line:
            return None, "NOT AVAILABLE / STOPPED — CP69 STREAM IS EMPTY"

        payload = json.loads(last_line)

        if not isinstance(payload, dict):
            return None, "BLOCK — CP69 OBSERVATION ROOT MUST BE AN OBJECT"

        validation_error = _validate_cp69_observation(payload)

        if validation_error is not None:
            return None, f"BLOCK — INVALID CP69 OBSERVATION: {validation_error}"

        return payload, "PASS — CP69 CANONICAL RUNTIME OBSERVATION"

    except json.JSONDecodeError as exc:
        return None, f"BLOCK — INVALID CP69 JSON: {exc}"

    except (OSError, UnicodeError) as exc:
        return None, f"BLOCK — CP69 STREAM READ FAILURE: {exc}"


def _validate_cp69_observation(payload: dict) -> str | None:
    if payload.get("schema") != CP69_SCHEMA:
        return f"schema={payload.get('schema')!r}"

    if payload.get("schema_version") != CP69_SCHEMA_VERSION:
        return f"schema_version={payload.get('schema_version')!r}"

    if payload.get("source_system") != CP69_SOURCE_SYSTEM:
        return f"source_system={payload.get('source_system')!r}"

    if payload.get("environment_id") != CP69_ENVIRONMENT_ID:
        return f"environment_id={payload.get('environment_id')!r}"

    if payload.get("adapter_id") != CP69_ADAPTER_ID:
        return f"adapter_id={payload.get('adapter_id')!r}"

    if not isinstance(payload.get("observation_id"), str):
        return "missing observation_id"

    if not isinstance(payload.get("emitted_at"), str):
        return "missing emitted_at"

    execution = payload.get("execution_state")
    if not isinstance(execution, dict):
        return "missing execution_state"

    if execution.get("EXECUTION") != "OFF":
        return f"EXECUTION={execution.get('EXECUTION')!r}"

    if execution.get("REAL_ORDER") is not False:
        return f"REAL_ORDER={execution.get('REAL_ORDER')!r}"

    if execution.get("REAL_TRADE") is not False:
        return f"REAL_TRADE={execution.get('REAL_TRADE')!r}"

    provenance = payload.get("provenance")
    if not isinstance(provenance, dict):
        return "missing provenance"

    state = payload.get("state")
    if not isinstance(state, dict):
        return "missing state"

    db_writes = payload.get("DB_WRITES")

    if not isinstance(db_writes, int) or isinstance(db_writes, bool):
        return "DB_WRITES must be a non-negative integer"

    if db_writes < 0:
        return "DB_WRITES must be non-negative"

    boundary = payload.get("db_write_boundary")

    if db_writes > 0:
        if boundary != CP49_DB_WRITE_BOUNDARY:
            return (
                "DB_WRITES > 0 requires "
                f"{CP49_DB_WRITE_BOUNDARY!r}"
            )
    else:
        if boundary is not None:
            return "DB_WRITES == 0 requires db_write_boundary=None"

    return None


def _format_execution(payload: dict) -> str:
    execution = payload.get("execution_state", {})

    return (
        f"EXECUTION={execution.get('EXECUTION', 'UNKNOWN')}  •  "
        f"REAL_ORDER={execution.get('REAL_ORDER', 'UNKNOWN')}  •  "
        f"REAL_TRADE={execution.get('REAL_TRADE', 'UNKNOWN')}"
    )


def _format_state_counts(payload: dict) -> str:
    state = payload.get("state", {})

    universe = _count(state.get("universe_assets"))
    market = _count(state.get("market_data_results"))
    opportunity = _count(state.get("opportunity_by_asset"))
    signals = _count(state.get("dynamic_signals"))
    validation = _count(state.get("validation_results"))
    fusion = _count(state.get("fusion_snapshot"))
    score = _count(state.get("score_snapshot"))
    decisions = _count(state.get("decision_snapshot"))
    risk = _count(state.get("risk_snapshot"))
    trade_gate = _count(state.get("trade_gate_snapshot"))
    trade_ready = _count(state.get("trade_ready_assets"))

    return (
        f"UNIVERSE={universe}  •  "
        f"MARKET={market}  •  "
        f"OPPORTUNITY={opportunity}\n"
        f"SIGNAL={signals}  •  "
        f"VALIDATION={validation}  •  "
        f"FUSION={fusion}  •  "
        f"SCORE={score}\n"
        f"DECISION={decisions}  •  "
        f"RISK={risk}  •  "
        f"TRADE GATE={trade_gate}  •  "
        f"TRADE READY={trade_ready}"
    )


def _format_db(payload: dict) -> str:
    db_writes = payload.get("DB_WRITES", 0)
    boundary = payload.get("db_write_boundary")

    if db_writes > 0:
        return (
            f"DB WRITES • {db_writes}\n"
            f"BOUNDARY • {boundary}"
        )

    return "DB WRITES • 0\nBOUNDARY • NONE"


def _format_failure_attribution(payload: dict) -> str:
    failure = payload.get("state", {}).get("failure_attribution")

    if not isinstance(failure, dict):
        return "Failure attribution not available"

    candidate_count = failure.get("candidate_count", 0)
    trade_ready_count = failure.get("trade_ready_count", 0)

    status_counts = failure.get("status_counts", {})
    reason_counts = failure.get("reason_counts", {})
    predicate_failures = failure.get("predicate_failures", {})

    return (
        f"CANDIDATES • {candidate_count}  •  "
        f"TRADE READY • {trade_ready_count}\n"
        f"STATUS • {status_counts}\n"
        f"REASONS • {reason_counts}\n"
        f"PREDICATES • {predicate_failures}"
    )


def _decision_ids(payload: dict) -> list[str]:
    decisions = payload.get("state", {}).get("decision_snapshot")

    if not isinstance(decisions, dict):
        return []

    result: list[str] = []

    for asset, row in decisions.items():
        if not isinstance(row, dict):
            continue

        decision_id = row.get("decision_id")

        if isinstance(decision_id, str) and decision_id:
            result.append(f"{asset}: {decision_id}")

    return result


class CommandCenterApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1240x820")
        self.root.minsize(980, 680)
        self.root.configure(bg="#0b0d10")

        self.status_var = tk.StringVar(value="INITIALIZING")
        self.observation_var = tk.StringVar(value="No CP69 observation")
        self.snapshot_var = tk.StringVar(value="Not available")
        self.emitted_var = tk.StringVar(value="Not available")
        self.runtime_var = tk.StringVar(value="Runtime not available")
        self.counts_var = tk.StringVar(value="No canonical runtime state loaded")
        self.decision_var = tk.StringVar(value="No canonical decision data")
        self.db_var = tk.StringVar(value="DB WRITES • NOT AVAILABLE")
        self.failure_var = tk.StringVar(value="Failure attribution not available")

        self._build_style()
        self._build_shell()

        self.refresh()
        self.root.after(REFRESH_MS, self._auto_refresh)

    def _build_style(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")

        style.configure(
            "TFrame",
            background="#0b0d10",
        )

        style.configure(
            "Card.TFrame",
            background="#11151a",
        )

        style.configure(
            "TLabel",
            background="#0b0d10",
            foreground="#e8edf2",
        )

        style.configure(
            "Card.TLabel",
            background="#11151a",
            foreground="#e8edf2",
        )

        style.configure(
            "Muted.Card.TLabel",
            background="#11151a",
            foreground="#8e9aa6",
        )

        style.configure(
            "Title.Card.TLabel",
            background="#11151a",
            foreground="#ffffff",
            font=("Segoe UI Semibold", 20),
        )

        style.configure(
            "Section.Card.TLabel",
            background="#11151a",
            foreground="#ffffff",
            font=("Segoe UI Semibold", 12),
        )

        style.configure(
            "Status.Card.TLabel",
            background="#11151a",
            foreground="#9fe3b1",
            font=("Segoe UI Semibold", 11),
        )

        style.configure(
            "TButton",
            font=("Segoe UI Semibold", 10),
            padding=(14, 8),
        )

    def _card(
        self,
        parent: ttk.Frame,
        title: str,
        subtitle: str,
    ) -> ttk.Frame:
        card = ttk.Frame(
            parent,
            style="Card.TFrame",
            padding=20,
        )

        ttk.Label(
            card,
            text=title,
            style="Section.Card.TLabel",
        ).pack(anchor="w")

        ttk.Label(
            card,
            text=subtitle,
            style="Muted.Card.TLabel",
        ).pack(
            anchor="w",
            pady=(4, 14),
        )

        return card

    def _build_shell(self) -> None:
        root_frame = ttk.Frame(
            self.root,
            padding=24,
        )
        root_frame.pack(
            fill="both",
            expand=True,
        )

        header = ttk.Frame(root_frame)
        header.pack(
            fill="x",
            pady=(0, 18),
        )

        ttk.Label(
            header,
            text="AROONDA",
            font=("Segoe UI Semibold", 28),
            foreground="#ffffff",
            background="#0b0d10",
        ).pack(side="left")

        ttk.Label(
            header,
            text="  COMMAND CENTER",
            font=("Segoe UI", 16),
            foreground="#8e9aa6",
            background="#0b0d10",
        ).pack(
            side="left",
            pady=(9, 0),
        )

        ttk.Button(
            header,
            text="Refresh",
            command=self.refresh,
        ).pack(side="right")

        status = ttk.Frame(
            root_frame,
            style="Card.TFrame",
            padding=16,
        )
        status.pack(
            fill="x",
            pady=(0, 14),
        )

        ttk.Label(
            status,
            textvariable=self.status_var,
            style="Status.Card.TLabel",
        ).pack(side="left")

        ttk.Label(
            status,
            text="  •  CP69 CANONICAL STREAM  •  READ-ONLY",
            style="Muted.Card.TLabel",
        ).pack(side="left")

        grid = ttk.Frame(root_frame)
        grid.pack(
            fill="both",
            expand=True,
        )

        for col in range(2):
            grid.columnconfigure(
                col,
                weight=1,
            )

        for row in range(3):
            grid.rowconfigure(
                row,
                weight=1,
            )

        live = self._card(
            grid,
            "LIVE RUNTIME",
            "Latest validated CP69 observation",
        )

        live.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(0, 7),
            pady=(0, 7),
        )

        ttk.Label(
            live,
            textvariable=self.runtime_var,
            style="Card.TLabel",
            wraplength=500,
        ).pack(anchor="w")

        ttk.Label(
            live,
            textvariable=self.emitted_var,
            style="Muted.Card.TLabel",
            wraplength=500,
        ).pack(
            anchor="w",
            pady=(8, 0),
        )

        supervisor = self._card(
            grid,
            "AROONDA AI SUPERVISOR",
            "Read-only consumer of the same CP69 stream",
        )

        supervisor.grid(
            row=0,
            column=1,
            sticky="nsew",
            padx=(7, 0),
            pady=(0, 7),
        )

        ttk.Label(
            supervisor,
            text="SUPERVISION LINK",
            style="Muted.Card.TLabel",
        ).pack(anchor="w")

        ttk.Label(
            supervisor,
            text="READ-ONLY / SAME CP69 OBSERVATION STREAM",
            style="Card.TLabel",
        ).pack(
            anchor="w",
            pady=(8, 0),
        )

        ttk.Label(
            supervisor,
            text="No trading authority • No decision mutation",
            style="Muted.Card.TLabel",
            wraplength=500,
        ).pack(
            anchor="w",
            pady=(8, 0),
        )

        trader = self._card(
            grid,
            "ARUNDATRADER PIPELINE",
            "Observed runtime state",
        )

        trader.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=(0, 7),
            pady=7,
        )

        ttk.Label(
            trader,
            textvariable=self.counts_var,
            style="Card.TLabel",
            wraplength=500,
            justify="left",
        ).pack(anchor="w")

        ttk.Label(
            trader,
            text="The UI does not create or alter decisions.",
            style="Muted.Card.TLabel",
            wraplength=500,
        ).pack(
            anchor="w",
            pady=(10, 0),
        )

        health = self._card(
            grid,
            "SYSTEM HEALTH",
            "Safety and authorized persistence boundary",
        )

        health.grid(
            row=1,
            column=1,
            sticky="nsew",
            padx=(7, 0),
            pady=7,
        )

        self.health_execution = ttk.Label(
            health,
            text="EXECUTION • NOT AVAILABLE",
            style="Card.TLabel",
        )
        self.health_execution.pack(
            anchor="w",
            pady=2,
        )

        self.health_order = ttk.Label(
            health,
            text="REAL ORDER • NOT AVAILABLE",
            style="Card.TLabel",
        )
        self.health_order.pack(
            anchor="w",
            pady=2,
        )

        self.health_trade = ttk.Label(
            health,
            text="REAL TRADE • NOT AVAILABLE",
            style="Card.TLabel",
        )
        self.health_trade.pack(
            anchor="w",
            pady=2,
        )

        self.health_db = ttk.Label(
            health,
            textvariable=self.db_var,
            style="Card.TLabel",
            wraplength=500,
            justify="left",
        )
        self.health_db.pack(
            anchor="w",
            pady=2,
        )

        ttk.Label(
            health,
            text="UI • READ-ONLY",
            style="Muted.Card.TLabel",
        ).pack(
            anchor="w",
            pady=(10, 2),
        )

        report = self._card(
            grid,
            "RUNTIME EVIDENCE",
            "Evidence-first — no fabricated report",
        )

        report.grid(
            row=2,
            column=0,
            sticky="nsew",
            padx=(0, 7),
            pady=(7, 0),
        )

        ttk.Label(
            report,
            text="The UI displays only the latest validated CP69 observation.",
            style="Muted.Card.TLabel",
            wraplength=500,
        ).pack(anchor="w")

        ttk.Label(
            report,
            textvariable=self.failure_var,
            style="Card.TLabel",
            wraplength=500,
            justify="left",
        ).pack(
            anchor="w",
            pady=(10, 0),
        )

        audit = self._card(
            grid,
            "AUDIT / OBSERVATION ID",
            "Traceability",
        )

        audit.grid(
            row=2,
            column=1,
            sticky="nsew",
            padx=(7, 0),
            pady=(7, 0),
        )

        ttk.Label(
            audit,
            text="Observation ID",
            style="Muted.Card.TLabel",
        ).pack(anchor="w")

        ttk.Label(
            audit,
            textvariable=self.observation_var,
            style="Card.TLabel",
            wraplength=500,
        ).pack(
            anchor="w",
            pady=(6, 0),
        )

        ttk.Label(
            audit,
            text="Runtime Snapshot",
            style="Muted.Card.TLabel",
        ).pack(
            anchor="w",
            pady=(14, 0),
        )

        ttk.Label(
            audit,
            textvariable=self.snapshot_var,
            style="Card.TLabel",
            wraplength=500,
        ).pack(
            anchor="w",
            pady=(6, 0),
        )

        ttk.Label(
            audit,
            text="Decision IDs",
            style="Muted.Card.TLabel",
        ).pack(
            anchor="w",
            pady=(14, 0),
        )

        ttk.Label(
            audit,
            textvariable=self.decision_var,
            style="Card.TLabel",
            wraplength=500,
            justify="left",
        ).pack(
            anchor="w",
            pady=(6, 0),
        )

    def refresh(self) -> None:
        payload, status = _latest_cp69_observation()

        self.status_var.set(status)

        if payload is None:
            self.observation_var.set("No CP69 observation")
            self.snapshot_var.set("Not available")
            self.emitted_var.set("")
            self.runtime_var.set(
                "Runtime output is NOT AVAILABLE / STOPPED."
            )
            self.counts_var.set(
                "No canonical runtime state loaded"
            )
            self.decision_var.set(
                "No canonical decision data"
            )
            self.db_var.set(
                "DB WRITES • NOT AVAILABLE"
            )
            self.failure_var.set(
                "Failure attribution not available"
            )

            self.health_execution.configure(
                text="EXECUTION • NOT AVAILABLE"
            )

            self.health_order.configure(
                text="REAL ORDER • NOT AVAILABLE"
            )

            self.health_trade.configure(
                text="REAL TRADE • NOT AVAILABLE"
            )

            return

        execution = payload["execution_state"]
        provenance = payload["provenance"]

        observation_id = str(
            payload["observation_id"]
        )

        snapshot_id = str(
            provenance.get(
                "runtime_snapshot_id",
                "Not available",
            )
        )

        self.observation_var.set(
            f"Observation ID • {observation_id}"
        )

        self.snapshot_var.set(
            snapshot_id
        )

        self.runtime_var.set(
            _format_execution(payload)
        )

        self.emitted_var.set(
            f"EMITTED • {payload.get('emitted_at', 'UNKNOWN')}"
        )

        self.counts_var.set(
            _format_state_counts(payload)
        )

        decision_ids = _decision_ids(payload)

        if decision_ids:
            self.decision_var.set(
                "\n".join(decision_ids[:5])
            )
        else:
            self.decision_var.set(
                "No decision_id exposed in latest decision snapshot"
            )

        self.db_var.set(
            _format_db(payload)
        )

        self.failure_var.set(
            _format_failure_attribution(payload)
        )

        self.health_execution.configure(
            text=f"EXECUTION • {execution.get('EXECUTION')}"
        )

        self.health_order.configure(
            text=f"REAL ORDER • {execution.get('REAL_ORDER')}"
        )

        self.health_trade.configure(
            text=f"REAL TRADE • {execution.get('REAL_TRADE')}"
        )

    def _auto_refresh(self) -> None:
        try:
            self.refresh()
        finally:
            self.root.after(
                REFRESH_MS,
                self._auto_refresh,
            )


def main() -> None:
    root = tk.Tk()
    CommandCenterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
