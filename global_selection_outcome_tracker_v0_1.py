"""Provider-neutral, order-independent global selection outcome tracking.

This module tracks every production Decision against later real market observations,
regardless of whether the asset is listed on the execution venue or an order exists.
It is append-only JSONL evidence; it never writes the trading database, calls an
exchange, changes a decision, or enables execution.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA = "arunda.global_selection_outcome"
SCHEMA_VERSION = "1.0"
LAUNCH_TIMESTAMP_MS = 1788134400000  # 2026-08-31T00:00:00Z
DEFAULT_STREAM_PATH = Path(__file__).resolve().parent / "runtime_observations" / "global_selection_outcomes.jsonl"
HORIZONS_MS = {"1h": 3_600_000, "4h": 14_400_000, "24h": 86_400_000}


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be non-empty text")
    return value.strip()


def _finite_positive(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be numeric")
    result = float(value)
    if not math.isfinite(result) or result <= 0:
        raise ValueError(f"{field} must be finite and positive")
    return result


def _timestamp(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be an epoch-millisecond number")
    result = int(value)
    if result < LAUNCH_TIMESTAMP_MS:
        raise ValueError(f"{field} predates production launch")
    return result


def _mapping_value(obj: Any, key: str) -> Any:
    return obj.get(key) if isinstance(obj, Mapping) else getattr(obj, key, None)


def _latest_candle(market_data: Any, asset: str) -> tuple[int, float, str]:
    if getattr(market_data, "real_data", False) is not True:
        raise ValueError(f"NON_REAL_MARKET_DATA:{asset}")
    if getattr(market_data, "status", None) != "READY":
        raise ValueError(f"MARKET_DATA_NOT_READY:{asset}")
    source = _text(getattr(market_data, "source", None), "market_data.source")
    if any(token in source.upper() for token in ("TEST", "SIMULAT", "LEGACY", "SYNTHETIC")):
        raise ValueError(f"NON_PRODUCTION_MARKET_SOURCE:{asset}")
    candles = tuple(getattr(market_data, "candles", ()) or ())
    if not candles:
        raise ValueError(f"MARKET_CANDLES_MISSING:{asset}")
    candle = candles[-1]
    timestamp_value = _mapping_value(candle, "timestamp")
    price_value = _mapping_value(candle, "close")
    if isinstance(candle, Sequence) and not isinstance(candle, (str, bytes)) and len(candle) >= 5:
        # CCXT-style OHLCV arrays: [timestamp, open, high, low, close, volume].
        if timestamp_value is None:
            timestamp_value = candle[0]
        if price_value is None:
            price_value = candle[4]
    ts = _timestamp(timestamp_value, "candle.timestamp")
    price = _finite_positive(price_value, "candle.close")
    return ts, price, source


def build_selection_event(
    *,
    decision_id: str,
    asset: str,
    decision: Mapping[str, Any],
    market_data: Any,
    selected_at_ms: int,
) -> dict[str, Any]:
    """Build one durable selection anchor using the latest real close as reference."""
    decision_id = _text(decision_id, "decision_id")
    asset = _text(asset, "asset").upper()
    selected_at_ms = _timestamp(selected_at_ms, "selected_at_ms")
    direction = str(decision.get("direction", "NONE")).strip().upper()
    if direction not in {"LONG", "SHORT", "NONE"}:
        direction = "NONE"
    candle_ts, reference_price, source = _latest_candle(market_data, asset)
    if candle_ts > selected_at_ms:
        raise ValueError(f"REFERENCE_CANDLE_AFTER_SELECTION:{asset}")
    return {
        "schema": SCHEMA, "schema_version": SCHEMA_VERSION,
        "event_type": "SELECTION", "event_id": f"SEL:{decision_id}",
        "decision_id": decision_id, "asset": asset, "direction": direction,
        "decision": str(decision.get("decision", decision.get("decision_state", "UNKNOWN"))),
        "rationale": str(decision.get("rationale", decision.get("reason", ""))),
        "selected_at_ms": selected_at_ms, "reference_timestamp_ms": candle_ts,
        "reference_price": reference_price, "market_source": source,
    }


def build_market_observation_event(
    *, selection: Mapping[str, Any], market_data: Any,
) -> dict[str, Any] | None:
    """Build an observation only when a real market candle is newer than selection."""
    ts, price, source = _latest_candle(market_data, str(selection["asset"]))
    selected_at = int(selection["selected_at_ms"])
    if ts <= selected_at:
        return None
    event_id = f"OBS:{selection['decision_id']}:{source}:{ts}"
    return {
        "schema": SCHEMA, "schema_version": SCHEMA_VERSION,
        "event_type": "MARKET_OBSERVATION", "event_id": event_id,
        "decision_id": selection["decision_id"], "asset": selection["asset"],
        "direction": selection["direction"], "observed_at_ms": ts,
        "price": price, "market_source": source,
        "elapsed_ms": ts - selected_at,
    }


def append_events_idempotent(
    events: Sequence[Mapping[str, Any]],
    stream_path: Path = DEFAULT_STREAM_PATH,
) -> tuple[int, list[dict[str, str]]]:
    """Append original evidence once; same ID with changed payload fails closed."""
    path = Path(stream_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: dict[str, dict[str, Any]] = {}
    if path.exists():
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"invalid selection evidence JSON at line {line_number}") from exc
                event_id = _text(row.get("event_id"), "event_id")
                if event_id in existing and existing[event_id] != row:
                    raise ValueError(f"conflicting persisted event_id: {event_id}")
                existing[event_id] = row
    appended = 0
    for event in events:
        row = dict(event)
        event_id = _text(row.get("event_id"), "event_id")
        if row.get("schema") != SCHEMA or row.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("invalid global selection evidence schema")
        prior = existing.get(event_id)
        if prior is not None:
            if prior != row:
                raise ValueError(f"event_id payload conflict: {event_id}")
            continue
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n")
        existing[event_id] = row
        appended += 1
    return appended, []


def evaluate_selection_outcomes(
    events: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Reconcile selection anchors with later real observations; never infer missing data."""
    selections: dict[str, Mapping[str, Any]] = {}
    observations: dict[str, list[Mapping[str, Any]]] = {}
    for event in events:
        if event.get("schema") != SCHEMA or event.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("unsupported selection evidence schema")
        event_type = event.get("event_type")
        decision_id = _text(event.get("decision_id"), "decision_id")
        if event_type == "SELECTION":
            prior = selections.get(decision_id)
            if prior is not None and dict(prior) != dict(event):
                raise ValueError(f"conflicting selection anchor: {decision_id}")
            selections[decision_id] = event
        elif event_type == "MARKET_OBSERVATION":
            observations.setdefault(decision_id, []).append(event)
        elif event_type == "OUTCOME_EVALUATION":
            # Derived snapshots are durable audit records, never source observations.
            continue
        else:
            raise ValueError(f"unsupported event_type: {event_type}")
    results = []
    for decision_id, selection in sorted(selections.items()):
        reference = _finite_positive(selection.get("reference_price"), "reference_price")
        direction = selection.get("direction")
        rows_by_ts: dict[int, Mapping[str, Any]] = {}
        for row in observations.get(decision_id, []):
            ts = _timestamp(row.get("observed_at_ms"), "observed_at_ms")
            if ts <= int(selection["selected_at_ms"]):
                continue
            if row.get("asset") != selection.get("asset"):
                raise ValueError(f"asset lineage mismatch: {decision_id}")
            rows_by_ts[ts] = row
        rows = [rows_by_ts[ts] for ts in sorted(rows_by_ts)]
        prices = [_finite_positive(row.get("price"), "observation.price") for row in rows]
        signed = [((price / reference) - 1.0) * (1 if direction == "LONG" else -1 if direction == "SHORT" else 0) * 100.0 for price in prices]
        horizon_results = {}
        selected_at = int(selection["selected_at_ms"])
        for name, duration in HORIZONS_MS.items():
            candidates = [row for row in rows if int(row["observed_at_ms"]) >= selected_at + duration]
            if candidates:
                row = candidates[0]
                pct = (float(row["price"]) / reference - 1.0) * 100.0
                horizon_results[name] = {
                    "status": "OBSERVED",
                    "observed_at_ms": int(row["observed_at_ms"]),
                    "price": float(row["price"]),
                    "absolute_return_pct": pct,
                    "directional_return_pct": pct if direction == "LONG" else -pct if direction == "SHORT" else None,
                }
            else:
                horizon_results[name] = {"status": "PENDING", "observed_at_ms": None, "price": None,
                                          "absolute_return_pct": None, "directional_return_pct": None}
        latest = rows[-1] if rows else None
        latest_pct = ((float(latest["price"]) / reference) - 1.0) * 100.0 if latest else None
        raw_returns = [
            ((float(row["price"]) / reference) - 1.0) * 100.0
            for row in rows
        ]
        counterfactual_best_index = (
            max(range(len(raw_returns)), key=lambda index: abs(raw_returns[index]))
            if raw_returns else None
        )
        counterfactual_best_return = (
            raw_returns[counterfactual_best_index]
            if counterfactual_best_index is not None else None
        )
        counterfactual_best_direction = (
            "LONG" if counterfactual_best_return > 0
            else "SHORT" if counterfactual_best_return < 0
            else "NONE" if counterfactual_best_return is not None
            else None
        )
        results.append({
            "decision_id": decision_id, "asset": selection["asset"],
            "direction": direction, "decision": selection.get("decision"),
            "selection_rationale": selection.get("rationale", ""),
            "selected_at_ms": selected_at, "reference_price": reference,
            "observation_count": len(rows),
            "counterfactual_best_direction": counterfactual_best_direction,
            "counterfactual_best_return_pct": (
                abs(counterfactual_best_return)
                if counterfactual_best_return is not None else None
            ),
            "counterfactual_best_observed_at_ms": (
                int(rows[counterfactual_best_index]["observed_at_ms"])
                if counterfactual_best_index is not None else None
            ),
            "counterfactual_note": "HINDSIGHT_REVIEW_ONLY_NOT_A_TRADABLE_SIGNAL",
            "latest_observed_at_ms": int(latest["observed_at_ms"]) if latest else None,
            "latest_price": float(latest["price"]) if latest else None,
            "latest_absolute_return_pct": latest_pct,
            "latest_directional_return_pct": (
                latest_pct if direction == "LONG" else -latest_pct if direction == "SHORT" else None
            ),
            "max_favorable_excursion_pct": max(signed) if signed and direction != "NONE" else None,
            "max_adverse_excursion_pct": min(signed) if signed and direction != "NONE" else None,
            "horizons": horizon_results,
            "outcome_state": "OBSERVATIONS_AVAILABLE" if rows else "AWAITING_REAL_MARKET_OBSERVATION",
            "market_source": selection.get("market_source"),
        })
    return results


def load_events(stream_path: Path = DEFAULT_STREAM_PATH) -> list[dict[str, Any]]:
    path = Path(stream_path)
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid selection evidence JSON at line {line_number}") from exc
    return rows


def track_cycle(
    *,
    decisions: Mapping[str, Mapping[str, Any]],
    market_data_by_symbol: Mapping[str, Any],
    cycle_timestamp_ms: int,
    stream_path: Path = DEFAULT_STREAM_PATH,
) -> dict[str, Any]:
    """Persist current decisions and later observations for prior selections.

    Call once per normal pipeline cycle. Market data is passed in from the existing
    provider-neutral global market arm; this function makes no network/API calls.
    """
    cycle_timestamp_ms = _timestamp(cycle_timestamp_ms, "cycle_timestamp_ms")
    existing = load_events(stream_path)
    selections = {row["decision_id"]: row for row in existing if row.get("event_type") == "SELECTION"}
    pending_events: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    for asset, decision in sorted(decisions.items()):
        decision_id = decision.get("decision_id")
        if not isinstance(decision_id, str) or not decision_id.strip():
            skipped.append({"asset": asset, "reason": "DECISION_ID_MISSING"})
            continue
        symbol = f"{str(asset).upper()}/USDT"
        market_data = market_data_by_symbol.get(symbol)
        if market_data is None:
            skipped.append({"asset": asset, "reason": "CURRENT_REAL_MARKET_DATA_MISSING"})
            continue
        if decision_id not in selections:
            try:
                selection = build_selection_event(
                    decision_id=decision_id, asset=asset, decision=decision,
                    market_data=market_data, selected_at_ms=cycle_timestamp_ms,
                )
                pending_events.append(selection)
                selections[decision_id] = selection
            except (TypeError, ValueError) as exc:
                skipped.append({"asset": asset, "reason": str(exc)})
    # Observe every stored selection that has a current market observation, not just
    # current decisions; this is deliberately independent of Toobit listing/order state.
    for selection in selections.values():
        symbol = f"{selection['asset']}/USDT"
        market_data = market_data_by_symbol.get(symbol)
        if market_data is None:
            continue
        try:
            observation = build_market_observation_event(selection=selection, market_data=market_data)
            if observation is not None:
                pending_events.append(observation)
        except (TypeError, ValueError) as exc:
            skipped.append({"asset": selection["asset"], "reason": str(exc)})
    persisted, failures = append_events_idempotent(pending_events, stream_path)
    all_events = load_events(stream_path)
    outcomes = evaluate_selection_outcomes(all_events)
    outcome_events = []
    for outcome in outcomes:
        latest_ts = outcome.get("latest_observed_at_ms")
        if latest_ts is None:
            continue
        outcome_events.append({
            "schema": SCHEMA, "schema_version": SCHEMA_VERSION,
            "event_type": "OUTCOME_EVALUATION",
            "event_id": f"OUTCOME:{outcome['decision_id']}:{latest_ts}",
            **outcome,
        })
    outcome_persisted, outcome_failures = append_events_idempotent(outcome_events, stream_path)
    persisted += outcome_persisted
    failures.extend(outcome_failures)
    all_events = load_events(stream_path)
    outcomes = evaluate_selection_outcomes(all_events)
    return {
        "selections_seen": len(selections),
        "observations_seen": sum(1 for row in all_events if row.get("event_type") == "MARKET_OBSERVATION"),
        "outcomes": outcomes,
        "events_persisted": persisted,
        "persistence_failures": failures,
        "skipped": skipped,
        "execution_touched": False,
        "database_touched": False,
    }


__all__ = [
    "build_selection_event", "build_market_observation_event",
    "append_events_idempotent", "evaluate_selection_outcomes",
    "load_events", "track_cycle", "DEFAULT_STREAM_PATH", "HORIZONS_MS",
]
