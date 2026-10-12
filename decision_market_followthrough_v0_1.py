"""Pure, fail-closed evaluation of post-decision real-market follow-through.

This is decision-quality evidence, NOT trade PnL, a fill, or an execution outcome.
No I/O, database writes, provider calls, synthetic prices, or interpolation occur.
"""
from __future__ import annotations

import math
from typing import Any, Iterable, Mapping

SCHEMA = "arunda.decision_market_followthrough"
SCHEMA_VERSION = "1.0"
DIRECTIONS = {"LONG", "SHORT"}


def evaluate_followthrough(
    *,
    decision: Mapping[str, Any],
    candles: Iterable[Mapping[str, Any]],
    horizon_end_ms: int,
) -> dict[str, Any]:
    """Evaluate one decision against attributable real candles through a horizon.

    Decision keys: decision_id, asset, direction, decision_timestamp_ms,
    decision_price, source_id.
    Candle keys: start_timestamp_ms, timestamp_ms (close time), asset, source_id,
    open, high, low, close. Only candles whose open time is strictly after the
    decision may contribute. The endpoint
    is the first eligible candle at/after horizon_end_ms. If it is absent,
    return INCOMPLETE rather than treating a shorter window as a full horizon.
    """
    required_decision = (
        "decision_id", "asset", "direction", "decision_timestamp_ms",
        "decision_price", "source_id",
    )
    for key in required_decision:
        if key not in decision:
            raise ValueError(f"missing decision field: {key}")
    for key in ("decision_id", "asset", "source_id"):
        if not isinstance(decision[key], str) or not decision[key].strip():
            raise ValueError(f"{key} must be a non-empty string")
    direction = decision["direction"]
    if direction not in DIRECTIONS:
        raise ValueError("direction must be LONG or SHORT")
    decision_ts = _positive_int(decision["decision_timestamp_ms"], "decision_timestamp_ms")
    horizon_end = _positive_int(horizon_end_ms, "horizon_end_ms")
    if horizon_end <= decision_ts:
        raise ValueError("horizon_end_ms must be later than decision_timestamp_ms")
    entry = _positive_number(decision["decision_price"], "decision_price")

    eligible: list[dict[str, Any]] = []
    seen: set[int] = set()
    for raw in candles:
        if not isinstance(raw, Mapping):
            raise ValueError("each candle must be a mapping")
        ts = _positive_int(raw.get("timestamp_ms"), "candle.timestamp_ms")
        start_ts = _positive_int(raw.get("start_timestamp_ms"), "candle.start_timestamp_ms")
        if ts < start_ts:
            raise ValueError("candle close timestamp precedes its open timestamp")
        # A candle overlapping the decision may contain pre-decision highs/lows.
        # Exclude it entirely rather than contaminating follow-through metrics.
        if ts <= decision_ts or start_ts <= decision_ts:
            continue
        if raw.get("asset") != decision["asset"]:
            raise ValueError("asset mismatch in post-decision candle")
        if raw.get("source_id") != decision["source_id"]:
            raise ValueError("source mismatch; source blending is forbidden")
        if ts in seen:
            raise ValueError("duplicate candle timestamp")
        seen.add(ts)
        values = {k: _positive_number(raw.get(k), f"candle.{k}") for k in ("open", "high", "low", "close")}
        if values["high"] < max(values["open"], values["close"], values["low"]):
            raise ValueError("invalid candle high")
        if values["low"] > min(values["open"], values["close"], values["high"]):
            raise ValueError("invalid candle low")
        eligible.append({"start_timestamp_ms": start_ts, "timestamp_ms": ts, **values})

    eligible.sort(key=lambda item: item["timestamp_ms"])
    eligible = [c for c in eligible if c["timestamp_ms"] <= horizon_end]
    endpoint = next((c for c in eligible if c["timestamp_ms"] >= horizon_end), None)
    if endpoint is None:
        # No extrapolation or forward-fill: insufficient horizon evidence.
        return {
            "schema": SCHEMA,
            "schema_version": SCHEMA_VERSION,
            "status": "INCOMPLETE",
            "reason": "HORIZON_ENDPOINT_NOT_OBSERVED",
            "decision_id": decision["decision_id"],
            "asset": decision["asset"],
            "direction": direction,
            "decision_timestamp_ms": decision_ts,
            "horizon_end_ms": horizon_end,
            "source_id": decision["source_id"],
            "observed_candle_count": len(eligible),
            "quality_metrics": None,
            "is_trade_pnl": False,
        }

    # Endpoint inclusion is exact by design: a candle after the horizon is
    # not silently substituted. Caller must supply the candle closing at it.
    window = [c for c in eligible if c["timestamp_ms"] <= endpoint["timestamp_ms"]]
    if not window or endpoint["timestamp_ms"] != horizon_end:
        return {
            "schema": SCHEMA,
            "schema_version": SCHEMA_VERSION,
            "status": "INCOMPLETE",
            "reason": "EXACT_HORIZON_CANDLE_NOT_OBSERVED",
            "decision_id": decision["decision_id"],
            "asset": decision["asset"],
            "direction": direction,
            "decision_timestamp_ms": decision_ts,
            "horizon_end_ms": horizon_end,
            "source_id": decision["source_id"],
            "observed_candle_count": len(window),
            "quality_metrics": None,
            "is_trade_pnl": False,
        }

    if direction == "LONG":
        terminal_return = (endpoint["close"] / entry - 1.0) * 100.0
        mfe = (max(c["high"] for c in window) / entry - 1.0) * 100.0
        mae = max((entry - min(c["low"] for c in window)) / entry * 100.0, 0.0)
    else:
        terminal_return = (entry / endpoint["close"] - 1.0) * 100.0
        mfe = (entry / min(c["low"] for c in window) - 1.0) * 100.0
        mae = max((max(c["high"] for c in window) / entry - 1.0) * 100.0, 0.0)

    metrics = {
        "terminal_directional_return_pct": _round(terminal_return),
        "max_favorable_excursion_pct": _round(max(mfe, 0.0)),
        "max_adverse_excursion_pct": _round(mae),
        "endpoint_close": endpoint["close"],
        "endpoint_timestamp_ms": endpoint["timestamp_ms"],
        "observed_candle_count": len(window),
    }
    return {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "status": "COMPLETE",
        "reason": "REAL_POST_DECISION_CANDLES",
        "decision_id": decision["decision_id"],
        "asset": decision["asset"],
        "direction": direction,
        "decision_timestamp_ms": decision_ts,
        "horizon_end_ms": horizon_end,
        "source_id": decision["source_id"],
        "quality_metrics": metrics,
        "is_trade_pnl": False,
        "execution_or_fill_inferred": False,
    }


def _positive_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _positive_number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a positive finite number")
    result = float(value)
    if not math.isfinite(result) or result <= 0:
        raise ValueError(f"{name} must be a positive finite number")
    return result


def _round(value: float) -> float:
    if not math.isfinite(value):
        raise ValueError("non-finite metric")
    return round(value, 8)
