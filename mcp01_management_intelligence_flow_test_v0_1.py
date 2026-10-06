"""Focused verification for the MCP-01 management intelligence flow."""

from __future__ import annotations

import tempfile
from pathlib import Path

from mcp01_compact_event_evidence_v0_1 import build_event
from mcp01_management_intelligence_flow_v0_1 import (
    build_management_intelligence,
    render_management_summary,
)


def event(
    *,
    event_id: str,
    event_type: str,
    timestamp: str,
    cycle_id: str,
    asset: str,
    decision_id: str | None = None,
    trade_event_id: str | None = None,
    provider: str | None = None,
    status: str | None = None,
) -> dict:
    return build_event(
        event_id=event_id,
        event_type=event_type,
        event_timestamp=timestamp,
        cycle_id=cycle_id,
        decision_id=decision_id,
        asset=asset,
        direction="LONG",
        stage=(
            "EXECUTION"
            if event_type in {"ORDER_ATTEMPTED", "PROVIDER_RESULT"}
            else "DECISION"
        ),
        status=status,
        provider=provider,
        trade_event_id=trade_event_id,
    ).to_dict()


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        stream = Path(tmp) / "compact.jsonl"

        events = [
            event(
                event_id="e1",
                event_type="SELECTED",
                timestamp="2026-10-06T00:00:00+00:00",
                cycle_id="RC-1",
                asset="BTC/USDT",
                decision_id="D-1",
            ),
            event(
                event_id="e2",
                event_type="TRADE_READY",
                timestamp="2026-10-06T00:00:01+00:00",
                cycle_id="RC-1",
                asset="BTC/USDT",
                decision_id="D-1",
            ),
            event(
                event_id="e3",
                event_type="ORDER_ATTEMPTED",
                timestamp="2026-10-06T00:00:02+00:00",
                cycle_id="RC-1",
                asset="BTC/USDT",
                decision_id="D-1",
                trade_event_id="TE-1",
            ),
            event(
                event_id="e4",
                event_type="PROVIDER_RESULT",
                timestamp="2026-10-06T00:00:03+00:00",
                cycle_id="RC-1",
                asset="BTC/USDT",
                decision_id="D-1",
                trade_event_id="TE-1",
                provider="TOOBIT",
                status="REJECTED",
            ),
        ]

        with stream.open("w", encoding="utf-8", newline="\n") as handle:
            for row in events:
                import json
                handle.write(json.dumps(row, sort_keys=True) + "\n")

        result = build_management_intelligence(
            cycle_id="RC-1",
            emitted_at="2026-10-06T00:05:00+00:00",
            universe_size=1,
            opportunity_ready=1,
            signal_ready=1,
            validation_ready=1,
            fusion_ready=1,
            decision_ready=1,
            risk_ready=1,
            trade_gate_ready=1,
            trade_ready=1,
            order_intents_created=1,
            canonical_order_requests_created=1,
            execution="ON",
            real_order=True,
            real_trade=False,
            selected_assets=["BTC"],
            current_events=events,
            stream_path=stream,
        )

        assert result["runtime_projection"]["cycle_id"] == "RC-1"
        assert result["intelligence_24h"]["cycles"]["count"] == 1
        assert result["intelligence_24h"]["cases"]["unique_count"] == 1
        assert result["intelligence_24h"]["trades"]["unique_count"] == 1
        assert result["intelligence_24h"]["reconciliation"]["complete_provider_chains"] == 1
        assert result["email_24h"]["delivery"]["enabled"] is False
        assert "email_enabled=False" in render_management_summary(result)

    print("MCP01 MANAGEMENT INTELLIGENCE FLOW TESTS=7/7 PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
