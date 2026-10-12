from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from global_selection_outcome_tracker_v0_1 import (
    LAUNCH_TIMESTAMP_MS,
    append_events_idempotent,
    build_market_observation_event,
    build_selection_event,
    evaluate_selection_outcomes,
    load_events,
    track_cycle,
)

BASE = LAUNCH_TIMESTAMP_MS + 10_000_000


def market(ts: int, price: float, *, source: str = "kucoin", real: bool = True):
    return SimpleNamespace(
        status="READY",
        real_data=real,
        source=source,
        candles=[{"timestamp": ts, "close": price}],
    )


def selection(direction: str = "LONG", *, decision_id: str = "D-1", price: float = 100.0):
    return {
        "decision_id": decision_id,
        "asset": "BTC",
        "direction": direction,
        "decision": "ACTIONABLE",
        "rationale": "momentum + structure",
        "selected_at_ms": BASE,
        "reference_timestamp_ms": BASE - 1,
        "reference_price": price,
        "market_source": "kucoin",
        "schema": "arunda.global_selection_outcome",
        "schema_version": "1.0",
        "event_type": "SELECTION",
        "event_id": f"SEL:{decision_id}",
    }


def observation(sel, ts: int, price: float, *, source: str = "kucoin"):
    return {
        "schema": "arunda.global_selection_outcome",
        "schema_version": "1.0",
        "event_type": "MARKET_OBSERVATION",
        "event_id": f"OBS:{sel['decision_id']}:{source}:{ts}",
        "decision_id": sel["decision_id"],
        "asset": sel["asset"],
        "direction": sel["direction"],
        "observed_at_ms": ts,
        "price": price,
        "market_source": source,
        "elapsed_ms": ts - sel["selected_at_ms"],
    }


def test_real_observation_creates_directional_outcome_and_horizons():
    sel = selection("LONG")
    events = [sel, observation(sel, BASE + 3_600_000, 103.0),
              observation(sel, BASE + 14_400_000, 98.0)]
    result = evaluate_selection_outcomes(events)[0]
    assert result["latest_absolute_return_pct"] == pytest.approx(-2.0)
    assert result["latest_directional_return_pct"] == pytest.approx(-2.0)
    assert result["max_favorable_excursion_pct"] == pytest.approx(3.0)
    assert result["max_adverse_excursion_pct"] == pytest.approx(-2.0)
    assert result["horizons"]["1h"]["status"] == "OBSERVED"
    assert result["horizons"]["4h"]["status"] == "OBSERVED"
    assert result["horizons"]["24h"]["status"] == "PENDING"


def test_short_direction_inverts_directional_return():
    sel = selection("SHORT")
    result = evaluate_selection_outcomes([sel, observation(sel, BASE + 3_600_001, 95.0)])[0]
    assert result["latest_absolute_return_pct"] == pytest.approx(-5.0)
    assert result["latest_directional_return_pct"] == pytest.approx(5.0)


def test_no_trade_direction_keeps_directional_quality_unscored():
    sel = selection("NONE")
    result = evaluate_selection_outcomes([sel, observation(sel, BASE + 3_600_001, 95.0)])[0]
    assert result["latest_absolute_return_pct"] == pytest.approx(-5.0)
    assert result["latest_directional_return_pct"] is None
    assert result["max_favorable_excursion_pct"] is None
    assert result["counterfactual_best_direction"] == "SHORT"
    assert result["counterfactual_best_return_pct"] == pytest.approx(5.0)
    assert result["counterfactual_note"] == "HINDSIGHT_REVIEW_ONLY_NOT_A_TRADABLE_SIGNAL"


def test_reference_selection_is_provider_neutral_and_requires_real_market_data():
    decision = {"decision_id": "D-2", "direction": "LONG", "decision": "ACTIONABLE"}
    built = build_selection_event(
        decision_id="D-2", asset="BTC", decision=decision,
        market_data=market(BASE - 100, 100.0, source="kucoin"), selected_at_ms=BASE,
    )
    assert built["market_source"] == "kucoin"
    assert built["reference_price"] == 100.0
    with pytest.raises(ValueError, match="NON_REAL_MARKET_DATA"):
        build_selection_event(
            decision_id="D-3", asset="BTC", decision=decision,
            market_data=market(BASE - 100, 100.0, real=False), selected_at_ms=BASE,
        )
    with pytest.raises(ValueError, match="NON_PRODUCTION_MARKET_SOURCE"):
        build_selection_event(
            decision_id="D-4", asset="BTC", decision=decision,
            market_data=market(BASE - 100, 100.0, source="SIMULATED-feed"), selected_at_ms=BASE,
        )


def test_observations_must_be_after_selection():
    sel = selection()
    assert build_market_observation_event(
        selection=sel, market_data=market(BASE, 101.0)
    ) is None
    with pytest.raises(ValueError, match="predates production launch"):
        build_market_observation_event(
            selection=sel, market_data=market(LAUNCH_TIMESTAMP_MS - 1, 101.0)
        )


def test_append_is_idempotent_and_conflicting_identity_fails_closed(tmp_path):
    path = tmp_path / "outcomes.jsonl"
    sel = selection()
    assert append_events_idempotent([sel], path)[0] == 1
    assert append_events_idempotent([sel], path)[0] == 0
    changed = dict(sel, rationale="changed")
    with pytest.raises(ValueError, match="payload conflict"):
        append_events_idempotent([changed], path)
    assert len(load_events(path)) == 1


def test_track_cycle_records_selection_then_real_followup(tmp_path):
    path = tmp_path / "outcomes.jsonl"
    market_map = {"BTC/USDT": market(BASE - 100, 100.0)}
    decision = {"decision_id": "D-5", "direction": "LONG", "decision": "ACTIONABLE"}
    first = track_cycle(
        decisions={"BTC": decision}, market_data_by_symbol=market_map,
        cycle_timestamp_ms=BASE, stream_path=path,
    )
    assert first["selections_seen"] == 1
    assert first["outcomes"][0]["outcome_state"] == "AWAITING_REAL_MARKET_OBSERVATION"
    assert first["execution_touched"] is False and first["database_touched"] is False

    market_map["BTC/USDT"] = market(BASE + 3_600_000, 102.0)
    second = track_cycle(
        decisions={"BTC": decision}, market_data_by_symbol=market_map,
        cycle_timestamp_ms=BASE + 3_600_100, stream_path=path,
    )
    assert second["observations_seen"] == 1
    assert second["outcomes"][0]["latest_directional_return_pct"] == pytest.approx(2.0)
    persisted = load_events(path)
    assert sum(row["event_type"] == "SELECTION" for row in persisted) == 1
    assert sum(row["event_type"] == "MARKET_OBSERVATION" for row in persisted) == 1
    assert sum(row["event_type"] == "OUTCOME_EVALUATION" for row in persisted) == 1


def test_missing_decision_id_is_reported_not_fabricated(tmp_path):
    result = track_cycle(
        decisions={"BTC": {"direction": "LONG"}},
        market_data_by_symbol={"BTC/USDT": market(BASE - 100, 100.0)},
        cycle_timestamp_ms=BASE, stream_path=tmp_path / "outcomes.jsonl",
    )
    assert result["selections_seen"] == 0
    assert result["skipped"] == [{"asset": "BTC", "reason": "DECISION_ID_MISSING"}]
