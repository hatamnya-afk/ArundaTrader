"""Read-only global selection quality report; never fetches market data or writes trading state."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from global_selection_outcome_tracker_v0_1 import (
    DEFAULT_STREAM_PATH,
    HORIZONS_MS,
    evaluate_selection_outcomes,
    load_events,
    summarize_selection_quality,
)


def build_quality_report(
    events: Sequence[Mapping[str, Any]], *, min_sample_size: int = 5
) -> dict[str, Any]:
    if isinstance(min_sample_size, bool) or not isinstance(min_sample_size, int) or min_sample_size < 1:
        raise ValueError("min_sample_size must be a positive integer")
    outcomes = evaluate_selection_outcomes(events)
    summary = summarize_selection_quality(outcomes)
    rankings: dict[str, list[dict[str, Any]]] = {}
    for horizon in HORIZONS_MS:
        rows = []
        for asset, group in summary["by_asset"].items():
            metrics = group["horizons"][horizon]
            count = metrics["direction_scored_count"]
            if count < min_sample_size:
                continue
            adverse = [
                float(row["max_adverse_excursion_pct"])
                for row in outcomes
                if row.get("asset") == asset
                and row.get("direction") in {"LONG", "SHORT"}
                and row.get("max_adverse_excursion_pct") is not None
            ]
            favorable = [
                float(row["max_favorable_excursion_pct"])
                for row in outcomes
                if row.get("asset") == asset
                and row.get("direction") in {"LONG", "SHORT"}
                and row.get("max_favorable_excursion_pct") is not None
            ]
            rows.append({
                "asset": asset,
                "horizon": horizon,
                "sample_count": count,
                "win_rate_pct": metrics["win_rate_pct"],
                "mean_directional_return_pct": metrics["mean_directional_return_pct"],
                "median_directional_return_pct": metrics["median_directional_return_pct"],
                "mean_max_adverse_excursion_pct": sum(adverse) / len(adverse) if adverse else None,
                "mean_max_favorable_excursion_pct": sum(favorable) / len(favorable) if favorable else None,
                "ranking_note": "DESCRIPTIVE_ONLY_NOT_A_TRADE_SIGNAL",
            })
        rankings[horizon] = sorted(
            rows,
            key=lambda row: (
                row["median_directional_return_pct"],
                row["win_rate_pct"],
                row["sample_count"],
            ),
            reverse=True,
        )
    return {
        "schema": "arunda.global_selection_quality_report",
        "schema_version": "1.0",
        "evidence_basis": "REAL_MARKET_OBSERVATIONS_ONLY",
        "selection_count": summary["selection_count"],
        "min_sample_size": min_sample_size,
        "overall": summary["overall"],
        "by_asset": summary["by_asset"],
        "by_direction": summary["by_direction"],
        "rankings_by_horizon": rankings,
        "interpretation": {
            "rankings_require_minimum_sample": True,
            "small_sample_assets_are_not_ranked": True,
            "pending_observations_are_not_losses": True,
            "counterfactuals_are_hindsight_only": True,
            "report_is_not_a_trading_signal": True,
            "database_touched": False,
            "execution_touched": False,
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_STREAM_PATH)
    parser.add_argument("--min-sample-size", type=int, default=5)
    parser.add_argument("--output", type=Path, help="Optional report file; defaults to stdout.")
    args = parser.parse_args(argv)
    report = build_quality_report(
        load_events(args.input), min_sample_size=args.min_sample_size
    )
    rendered = json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
