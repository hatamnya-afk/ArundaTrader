"""Read-only native ArundaTrader UI over its canonical CP69 JSONL stream.

The UI never invents data, imports AroondaAI, or mutates Trader state. A missing,
malformed, identity-invalid, or stale stream is shown as BLOCKED/STALE and its
asset rows are cleared. The reader uses the same current-observation path
setting as the CP69 producer, ARUNDATRADER_CURRENT_OBSERVATION_PATH.
"""
from __future__ import annotations

import json
import os
import tkinter as tk
from datetime import datetime, timezone
from pathlib import Path
from tkinter import ttk
from typing import Any

from arundatrader_observation_consumer import CanonicalRuntimeObservation
from arundatrader_runtime_analysis import analyze_runtime_observation

POLL_MS = 2000
MAX_AGE_SECONDS = 60


def read_latest_observation(path: Path) -> CanonicalRuntimeObservation:
    """Read the last non-empty JSONL record; malformed latest records fail closed."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"CP69 stream not found: {path}")
    latest = None
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if line.strip():
                latest = (line_number, line)
    if latest is None:
        raise ValueError("CP69 stream has no observations")
    line_number, raw = latest
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"latest CP69 record is invalid JSON at line {line_number}") from exc
    return CanonicalRuntimeObservation.from_dict(payload)


def observation_age_seconds(observation: CanonicalRuntimeObservation, now=None) -> float:
    emitted = datetime.fromisoformat(observation.emitted_at.replace("Z", "+00:00"))
    if emitted.tzinfo is None:
        raise ValueError("emitted_at must include a timezone")
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise ValueError("current time must include a timezone")
    age = (current.astimezone(timezone.utc) - emitted.astimezone(timezone.utc)).total_seconds()
    if age < -5:
        raise ValueError("observation timestamp is too far in the future")
    return max(0.0, age)


def _json_cell(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return str(value)


def asset_rows(observation: CanonicalRuntimeObservation) -> list[tuple[str, ...]]:
    """Project source-provided per-asset facts; no inferred score or ranking."""
    state = observation.state
    source_maps = [
        state.get("market_data_results", {}),
        state.get("opportunity_by_asset", {}),
        state.get("dynamic_signals", {}),
        state.get("validation_results", {}),
        state.get("fusion_snapshot", {}),
        state.get("score_snapshot", {}),
        state.get("decision_snapshot", {}),
        state.get("risk_snapshot", {}),
        state.get("trade_gate_snapshot", {}),
    ]
    normalized_maps: list[dict[str, Any]] = []
    keys: set[str] = set()
    for mapping in source_maps:
        normalized: dict[str, Any] = {}
        if isinstance(mapping, dict):
            for raw_key, value in mapping.items():
                # Market data may be keyed by BASE/QUOTE while downstream stages
                # use the canonical base asset. Preserve the original value.
                asset = str(raw_key).strip().upper().split("/", 1)[0]
                if asset:
                    normalized[asset] = value
                    keys.add(asset)
        elif isinstance(mapping, (list, tuple)):
            # Some real runtime producers expose dataclass collections as lists.
            # Index them only by an explicit source-provided asset/symbol field.
            for value in mapping:
                if not isinstance(value, dict):
                    continue
                raw_key = value.get("asset", value.get("symbol", value.get("base_asset")))
                if isinstance(raw_key, str) and raw_key.strip():
                    asset = raw_key.strip().upper().split("/", 1)[0]
                    normalized[asset] = value
                    keys.add(asset)
        normalized_maps.append(normalized)
    universe = state.get("universe_assets", [])
    if isinstance(universe, (list, tuple)):
        keys.update(str(item).strip().upper().split("/", 1)[0] for item in universe if str(item).strip())
    trade_ready = state.get("trade_ready_assets", [])
    ready_set = (
        {str(item).strip().upper().split("/", 1)[0] for item in trade_ready}
        if isinstance(trade_ready, (list, tuple, set))
        else set()
    )
    rows = []
    for asset in sorted(keys):
        values = [_json_cell(mapping.get(asset)) for mapping in normalized_maps]
        if isinstance(trade_ready, dict):
            ready_value = trade_ready.get(asset)
        elif isinstance(trade_ready, (list, tuple, set)):
            ready_value = asset in ready_set
        else:
            ready_value = None
        values.append(_json_cell(ready_value))
        rows.append((asset, *values))
    return rows


class LiveArundaTraderUI:
    def __init__(self, stream_path: Path):
        self.stream_path = Path(stream_path)
        self.root = tk.Tk()
        self.root.title("ArundaTrader — Live Runtime Evidence")
        self.root.geometry("1500x850")
        self.root.minsize(1050, 620)
        self.root.configure(bg="#0b1020")
        self._build()
        self.root.after(0, self.refresh)

    def _build(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("Treeview", background="#11182b", fieldbackground="#11182b",
                        foreground="#eef3ff", rowheight=28)
        style.configure("Treeview.Heading", background="#24304b", foreground="#eef3ff")
        style.map("Treeview", background=[("selected", "#33416b")])
        header = tk.Frame(self.root, bg="#0b1020")
        header.pack(fill="x", padx=20, pady=(16, 6))
        tk.Label(header, text="ARUNDATRADER / LIVE RUNTIME EVIDENCE",
                 font=("Segoe UI", 18, "bold"), fg="#eef3ff", bg="#0b1020").pack(anchor="w")
        tk.Label(header, text="READ-ONLY • CANONICAL CP69 STREAM • NO ORDERS / NO TRADER MUTATION",
                 font=("Segoe UI", 9, "bold"), fg="#91a0bd", bg="#0b1020").pack(anchor="w", pady=(4, 0))
        self.status = tk.Label(self.root, text="CONNECTING — no current CP69 record validated yet",
                               font=("Segoe UI", 10, "bold"), fg="#ffd166", bg="#0b1020", anchor="w")
        self.status.pack(fill="x", padx=22, pady=5)
        self.meta = tk.Label(self.root, text=f"Source file: {self.stream_path}",
                             fg="#91a0bd", bg="#0b1020", anchor="w", wraplength=1400)
        self.meta.pack(fill="x", padx=22, pady=(0, 8))
        self.metrics = tk.Label(self.root, text="Waiting for a current schema-valid runtime observation",
                                fg="#eef3ff", bg="#11182b", font=("Segoe UI", 11),
                                justify="left", anchor="w", padx=12, pady=10)
        self.metrics.pack(fill="x", padx=20, pady=6)
        frame = tk.Frame(self.root, bg="#0b1020")
        frame.pack(fill="both", expand=True, padx=20, pady=(8, 12))
        columns = ("asset", "market_data", "opportunity", "signal", "validation", "fusion",
                   "score", "decision", "risk", "trade_gate", "trade_ready")
        self.table = ttk.Treeview(frame, columns=columns, show="headings")
        headings = {
            "asset": "ASSET", "market_data": "MARKET DATA", "opportunity": "OPPORTUNITY",
            "signal": "DYNAMIC SIGNAL", "validation": "VALIDATION", "fusion": "FUSION",
            "score": "SOURCE SCORE", "decision": "DECISION", "risk": "RISK",
            "trade_gate": "TRADE GATE", "trade_ready": "TRADE-READY (SOURCE)",
        }
        widths = {"asset": 115, "market_data": 180, "opportunity": 180, "signal": 180,
                  "validation": 150, "fusion": 150, "score": 130, "decision": 150,
                  "risk": 150, "trade_gate": 160, "trade_ready": 160}
        for col in columns:
            self.table.heading(col, text=headings[col])
            self.table.column(col, width=widths[col], minwidth=90, stretch=True, anchor="w")
        ybar = ttk.Scrollbar(frame, orient="vertical", command=self.table.yview)
        xbar = ttk.Scrollbar(frame, orient="horizontal", command=self.table.xview)
        self.table.configure(yscrollcommand=ybar.set, xscrollcommand=xbar.set)
        self.table.grid(row=0, column=0, sticky="nsew")
        ybar.grid(row=0, column=1, sticky="ns")
        xbar.grid(row=1, column=0, sticky="ew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        self.footer = tk.Label(self.root, text="No current CP69 observation loaded.",
                               fg="#91a0bd", bg="#0b1020", anchor="w")
        self.footer.pack(fill="x", padx=22, pady=(0, 12))

    def _clear_rows(self):
        for item in self.table.get_children():
            self.table.delete(item)

    def refresh(self):
        try:
            observation = read_latest_observation(self.stream_path)
            age = observation_age_seconds(observation)
            if age > MAX_AGE_SECONDS:
                raise TimeoutError(f"latest observation is stale ({age:.1f}s old; limit {MAX_AGE_SECONDS}s)")
            result = analyze_runtime_observation(observation)
            rows = asset_rows(observation)
            self._clear_rows()
            for row in rows:
                self.table.insert("", "end", values=row)
            coverage = result.safe_for_model_context["coverage"]
            self.status.configure(text=f"FRESH CP69 RECORD • schema/identity valid • age {age:.1f}s",
                                   fg="#7ee787")
            self.metrics.configure(text=(
                f"Observation: {result.observation_id}    Snapshot: {result.runtime_snapshot_id}    "
                f"Emitted: {result.emitted_at}\n"
                f"Assets {coverage['assets']} | Opportunities {coverage['opportunities']} | "
                f"Signals {coverage['signals']} | Validation {coverage['validation']} | "
                f"Fusion {coverage['fusion']} | Scores {coverage['score']} | "
                f"Decisions {coverage['decision']} | Risk {coverage['risk']} | "
                f"Trade-gate candidates {coverage['trade_gate']} | Trade-ready {coverage['trade_ready']}\n"
                f"Execution={result.execution} | REAL_ORDER={result.real_order} | "
                f"REAL_TRADE={result.real_trade} | DB_WRITES={result.db_writes} "
                f"| DB_WRITE_BOUNDARY={result.db_write_boundary or 'NONE'}"
            ))
            self.footer.configure(text=(
                f"Rows are source-provided values, not an invented quality score. "
                f"Gate statuses: {result.trade_gate_status_counts or 'not supplied'} | "
                f"Predicate failures: {result.predicate_failures or 'none supplied'} | "
                f"Failure reasons: {result.reason_counts or 'none supplied'} | "
                f"Last refresh: {datetime.now().astimezone().isoformat(timespec='seconds')}"
            ))
        except Exception as exc:
            # Fail closed: stale/invalid data must never remain displayed as live.
            self._clear_rows()
            self.status.configure(text=f"BLOCKED / NOT LIVE • {type(exc).__name__}: {exc}", fg="#ff7b72")
            self.metrics.configure(text="No current schema-valid observation. Asset rows intentionally cleared.")
            self.footer.configure(text="Fix the source/path/schema or restore fresh canonical observations. No fallback or synthetic data is used.")
        finally:
            self.root.after(POLL_MS, self.refresh)

    def run(self):
        self.root.mainloop()


def main() -> int:
    # Share the producer's exact environment variable and default artifact path.
    configured = os.environ.get("ARUNDATRADER_CURRENT_OBSERVATION_PATH", "").strip()
    path = Path(configured) if configured else (
        Path(__file__).resolve().parent
        / "runtime_observations"
        / "arundatrader_current_runtime_observation.jsonl"
    )
    LiveArundaTraderUI(path).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
