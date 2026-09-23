from __future__ import annotations

import json

import cp48_command_center_app_v0_1 as app


def test_missing_event_stream_is_safe(tmp_path, monkeypatch):
    monkeypatch.setenv("AROONDA_COMMAND_CENTER_EVENTS", str(tmp_path / "missing.json"))
    projection, status = app.load_projection()
    assert projection is None
    assert status == "WAITING FOR CANONICAL EVENT STREAM"


def test_valid_projection_is_read_only(tmp_path, monkeypatch):
    payload = {
        "generated_at_ms": 100,
        "decision_trace": {
            "decision_id": "D1",
            "event_ids": ["E1"],
            "source_ids": ["S1"],
            "snapshot_id": "SN1",
        },
        "events": [
            {
                "event_id": "E1",
                "decision_id": "D1",
                "stage": "MARKET_SNAPSHOT",
                "occurred_at_ms": 90,
                "knowledge_cutoff_ms": 90,
                "parent_event_ids": [],
                "state": "PASS",
            }
        ],
    }
    path = tmp_path / "events.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setenv("AROONDA_COMMAND_CENTER_EVENTS", str(path))

    projection, status = app.load_projection()

    assert projection is not None
    assert status == "PASS — CANONICAL EVENT STREAM"
    assert projection.execution_controls_visible is True
    assert projection.execution_controls_writable is False
    assert projection.decision_trace.decision_id == "D1"


def test_invalid_cross_decision_event_blocks(tmp_path, monkeypatch):
    payload = {
        "generated_at_ms": 100,
        "decision_trace": {
            "decision_id": "D1",
            "event_ids": ["E1"],
            "source_ids": ["S1"],
            "snapshot_id": "SN1",
        },
        "events": [
            {
                "event_id": "E1",
                "decision_id": "D2",
                "stage": "MARKET_SNAPSHOT",
                "occurred_at_ms": 90,
                "knowledge_cutoff_ms": 90,
                "parent_event_ids": [],
                "state": "PASS",
            }
        ],
    }
    path = tmp_path / "events.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setenv("AROONDA_COMMAND_CENTER_EVENTS", str(path))

    projection, status = app.load_projection()

    assert projection is None
    assert status.startswith("BLOCK — INVALID CANONICAL EVENT STREAM")


def test_invalid_json_blocks(tmp_path, monkeypatch):
    path = tmp_path / "events.json"
    path.write_text("{not-json", encoding="utf-8")
    monkeypatch.setenv("AROONDA_COMMAND_CENTER_EVENTS", str(path))

    projection, status = app.load_projection()

    assert projection is None
    assert status.startswith("BLOCK — INVALID CANONICAL EVENT STREAM")
