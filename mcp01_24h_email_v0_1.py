"""MCP-01.7 24H intelligence email formatter.

Formatting/delivery boundary only. This module does not send email, activate
24/7 operation, create trades, or mutate Trader state. Delivery remains an
explicit integration concern.
"""

from __future__ import annotations

from typing import Mapping


SCHEMA = "arunda.24h_email"
SCHEMA_VERSION = "1.0"


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be non-empty text")
    return value.strip()


def _count(section: Mapping[str, object], key: str) -> int:
    value = section.get(key, 0)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{key} must be a non-negative integer")
    return value


def build_24h_email(report: Mapping[str, object]) -> dict:
    if report.get("schema") != "arunda.24h_intelligence":
        raise ValueError("invalid 24H intelligence report schema")
    if report.get("schema_version") != "1.0":
        raise ValueError("unsupported 24H intelligence report version")

    period = report.get("period")
    cycles = report.get("cycles")
    cases = report.get("cases")
    trades = report.get("trades")
    reconciliation = report.get("reconciliation")
    data_quality = report.get("data_quality")

    if not isinstance(period, Mapping):
        raise ValueError("period must be a mapping")
    if not isinstance(cycles, Mapping):
        raise ValueError("cycles must be a mapping")
    if not isinstance(cases, Mapping):
        raise ValueError("cases must be a mapping")
    if not isinstance(trades, Mapping):
        raise ValueError("trades must be a mapping")
    if not isinstance(reconciliation, Mapping):
        raise ValueError("reconciliation must be a mapping")
    if not isinstance(data_quality, Mapping):
        raise ValueError("data_quality must be a mapping")

    start = _text(period.get("start"), "period.start")
    end = _text(period.get("end"), "period.end")
    cycle_count = _count(cycles, "count")
    case_count = _count(cases, "unique_count")
    trade_count = _count(trades, "unique_count")
    complete_chains = _count(reconciliation, "complete_provider_chains")
    market_outcomes = _count(reconciliation, "market_outcomes")
    case_outcomes = _count(reconciliation, "case_outcomes")
    dq_count = _count(data_quality, "event_count")

    subject = f"ArundaTrader 24H Intelligence | {start} → {end}"

    body = "\n".join(
        (
            "ARUNDATRADER — 24H INTELLIGENCE",
            f"Period: {start} → {end}",
            "",
            f"Cycles: {cycle_count}",
            f"Unique Cases: {case_count}",
            f"Unique Trade Events: {trade_count}",
            f"Complete Provider Chains: {complete_chains}",
            f"Market Outcomes: {market_outcomes}",
            f"Case Outcomes: {case_outcomes}",
            f"Data Quality Events: {dq_count}",
            "",
            "This report is an aggregated management view.",
            "It does not activate 24/7 operation and does not create or infer outcomes.",
        )
    )

    return {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "subject": subject,
        "body": body,
        "delivery": {
            "mode": "ONE_EMAIL_PER_24H_PERIOD",
            "enabled": False,
            "activation_requires_management_authorization": True,
        },
        "source_report_schema": report["schema"],
        "source_report_version": report["schema_version"],
    }
