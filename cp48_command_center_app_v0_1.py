from __future__ import annotations

import json
import os
from pathlib import Path
import tkinter as tk
from tkinter import ttk

from cp48_command_center_contract_v0_1 import (
    CommandCenterProjection,
    CommandCenterView,
    DecisionTrace,
    EventRecord,
    ProjectionState,
)

APP_TITLE = "Aroonda Command Center"
EVENT_STREAM_ENV = "AROONDA_COMMAND_CENTER_EVENTS"
DEFAULT_EVENT_STREAM = Path(__file__).resolve().parent / "command_center_events.json"


def _event_stream_path() -> Path:
    configured = os.environ.get(EVENT_STREAM_ENV)
    return Path(configured) if configured else DEFAULT_EVENT_STREAM


def load_projection() -> tuple[CommandCenterProjection | None, str]:
    path = _event_stream_path()
    if not path.exists():
        return None, "WAITING FOR CANONICAL EVENT STREAM"

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return None, "BLOCK — EVENT STREAM ROOT MUST BE AN OBJECT"

        events_payload = payload.get("events")
        trace_payload = payload.get("decision_trace")
        if not isinstance(events_payload, list) or not isinstance(trace_payload, dict):
            return None, "BLOCK — INCOMPLETE PROJECTION PAYLOAD"

        events = tuple(
            EventRecord(
                event_id=str(row["event_id"]),
                decision_id=str(row["decision_id"]),
                stage=str(row["stage"]),
                occurred_at_ms=int(row["occurred_at_ms"]),
                knowledge_cutoff_ms=int(row["knowledge_cutoff_ms"]),
                parent_event_ids=tuple(str(x) for x in row.get("parent_event_ids", ())),
                state=ProjectionState(str(row.get("state", "INCONCLUSIVE"))),
            )
            for row in events_payload
        )

        trace = DecisionTrace(
            decision_id=str(trace_payload["decision_id"]),
            event_ids=tuple(str(x) for x in trace_payload["event_ids"]),
            source_ids=tuple(str(x) for x in trace_payload["source_ids"]),
            snapshot_id=str(trace_payload["snapshot_id"]),
        )

        projection = CommandCenterProjection(
            decision_trace=trace,
            view=CommandCenterView.LIVE_ACTIVITY,
            generated_at_ms=int(payload["generated_at_ms"]),
            events=events,
            execution_controls_visible=True,
            execution_controls_writable=False,
        )
        projection.validate()
        return projection, "PASS — CANONICAL EVENT STREAM"
    except (KeyError, TypeError, ValueError, OSError) as exc:
        return None, f"BLOCK — INVALID CANONICAL EVENT STREAM: {exc}"


class CommandCenterApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1240x780")
        self.root.minsize(980, 640)
        self.root.configure(bg="#0b0d10")

        self.status_var = tk.StringVar(value="INITIALIZING")
        self.decision_var = tk.StringVar(value="No Decision ID")
        self.event_var = tk.StringVar(value="No canonical events loaded")

        self._build_style()
        self._build_shell()
        self.refresh()

    def _build_style(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TFrame", background="#0b0d10")
        style.configure("Card.TFrame", background="#11151a")
        style.configure("TLabel", background="#0b0d10", foreground="#e8edf2")
        style.configure("Card.TLabel", background="#11151a", foreground="#e8edf2")
        style.configure("Muted.Card.TLabel", background="#11151a", foreground="#8e9aa6")
        style.configure("Title.Card.TLabel", background="#11151a", foreground="#ffffff",
                        font=("Segoe UI Semibold", 20))
        style.configure("Section.Card.TLabel", background="#11151a", foreground="#ffffff",
                        font=("Segoe UI Semibold", 12))
        style.configure("Status.Card.TLabel", background="#11151a", foreground="#9fe3b1",
                        font=("Segoe UI Semibold", 11))
        style.configure("TButton", font=("Segoe UI Semibold", 10), padding=(14, 8))

    def _card(self, parent: ttk.Frame, title: str, subtitle: str) -> ttk.Frame:
        card = ttk.Frame(parent, style="Card.TFrame", padding=20)
        ttk.Label(card, text=title, style="Section.Card.TLabel").pack(anchor="w")
        ttk.Label(card, text=subtitle, style="Muted.Card.TLabel").pack(anchor="w", pady=(4, 14))
        return card

    def _build_shell(self) -> None:
        root_frame = ttk.Frame(self.root, padding=24)
        root_frame.pack(fill="both", expand=True)

        header = ttk.Frame(root_frame)
        header.pack(fill="x", pady=(0, 18))
        ttk.Label(header, text="AROONDA", font=("Segoe UI Semibold", 28),
                  foreground="#ffffff", background="#0b0d10").pack(side="left")
        ttk.Label(header, text="  COMMAND CENTER", font=("Segoe UI", 16),
                  foreground="#8e9aa6", background="#0b0d10").pack(side="left", pady=(9, 0))
        ttk.Button(header, text="Refresh", command=self.refresh).pack(side="right")

        status = ttk.Frame(root_frame, style="Card.TFrame", padding=16)
        status.pack(fill="x", pady=(0, 14))
        ttk.Label(status, textvariable=self.status_var, style="Status.Card.TLabel").pack(side="left")
        ttk.Label(status, text="  •  EXECUTION OFF  •  READ-ONLY", style="Muted.Card.TLabel").pack(side="left")

        grid = ttk.Frame(root_frame)
        grid.pack(fill="both", expand=True)
        for col in range(2):
            grid.columnconfigure(col, weight=1)
        for row in range(3):
            grid.rowconfigure(row, weight=1)

        live = self._card(grid, "LIVE ACTIVITY", "Canonical decision/event projection")
        live.grid(row=0, column=0, sticky="nsew", padx=(0, 7), pady=(0, 7))
        ttk.Label(live, textvariable=self.decision_var, style="Card.TLabel").pack(anchor="w")
        ttk.Label(live, textvariable=self.event_var, style="Muted.Card.TLabel").pack(anchor="w", pady=(8, 0))

        supervisor = self._card(grid, "AROONDA AI SUPERVISOR", "Observation, analysis and lessons")
        supervisor.grid(row=0, column=1, sticky="nsew", padx=(7, 0), pady=(0, 7))
        ttk.Label(supervisor, text="SUPERVISION LINK", style="Muted.Card.TLabel").pack(anchor="w")
        ttk.Label(supervisor, text="Ready for canonical observation stream", style="Card.TLabel").pack(anchor="w", pady=(8, 0))

        trader = self._card(grid, "ARUNDATRADER", "Market-first decision engine")
        trader.grid(row=1, column=0, sticky="nsew", padx=(0, 7), pady=7)
        ttk.Label(trader, text="DECISION → RISK → TRADE GATE → ORDER INTENT", style="Card.TLabel").pack(anchor="w")
        ttk.Label(trader, text="The UI does not create or alter decisions.", style="Muted.Card.TLabel").pack(anchor="w", pady=(8, 0))

        health = self._card(grid, "SYSTEM HEALTH", "Safety and contract boundary")
        health.grid(row=1, column=1, sticky="nsew", padx=(7, 0), pady=7)
        for line in (
            "CP47  •  CLOSED / CANONICAL",
            "CP48  •  CONTRACT VERIFIED",
            "EXECUTION  •  OFF",
            "EXCHANGE WRITE  •  OFF",
            "DATABASE WRITE  •  OFF",
        ):
            ttk.Label(health, text=line, style="Card.TLabel").pack(anchor="w", pady=2)

        report = self._card(grid, "DAILY REPORT", "Evidence-first summary")
        report.grid(row=2, column=0, sticky="nsew", padx=(0, 7), pady=(7, 0))
        ttk.Label(report, text="No report is fabricated when no canonical events exist.", style="Muted.Card.TLabel").pack(anchor="w")

        audit = self._card(grid, "AUDIT / DECISION ID", "Traceability")
        audit.grid(row=2, column=1, sticky="nsew", padx=(7, 0), pady=(7, 0))
        ttk.Label(audit, text="Decision ID", style="Muted.Card.TLabel").pack(anchor="w")
        ttk.Label(audit, textvariable=self.decision_var, style="Card.TLabel").pack(anchor="w", pady=(6, 0))

    def refresh(self) -> None:
        projection, status = load_projection()
        self.status_var.set(status)
        if projection is None:
            self.decision_var.set("No Decision ID")
            self.event_var.set("Waiting for canonical producer")
            return

        self.decision_var.set(f"Decision ID  •  {projection.decision_trace.decision_id}")
        self.event_var.set(f"{len(projection.events)} canonical event(s)  •  view={projection.view.value}")


def main() -> None:
    root = tk.Tk()
    CommandCenterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
