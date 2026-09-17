from __future__ import annotations

from typing import Any, Mapping

import opportunity_engine
import signal_validator


EXPECTED_ASSETS = [
    "BTC",
    "ETH",
    "SOL",
    "XRP",
    "ADA",
    "DOGE",
    "SHIB",
    "LINK",
    "AVAX",
    "DOT",
    "LTC",
    "UNI",
    "AAVE",
    "SUI",
    "NEAR",
]


def asset_of(row: Mapping[str, Any]) -> str | None:

    for key in (
        "asset",
        "symbol",
        "market",
    ):

        value = row.get(key)

        if value is not None:

            value = str(value).strip().upper()

            if value:

                return value

    return None


def extract_opportunities(snapshot: Any) -> dict:

    result = {}

    def walk(value):

        if isinstance(value, Mapping):

            asset = asset_of(value)

            if (
                asset in EXPECTED_ASSETS
                and
                (
                    "status" in value
                    or
                    "opportunity_status" in value
                )
                and
                "direction" in value
            ):

                result[asset] = dict(value)

            for child in value.values():

                walk(child)

        elif isinstance(value, (list, tuple)):

            for child in value:

                walk(child)

    walk(snapshot)

    return result


def normalize_signal(
    asset: str,
    record: Mapping[str, Any],
) -> tuple[str, str]:

    state = record.get(
        "signal_state"
    )

    direction = record.get(
        "direction"
    )

    if state not in (
        "ACTIVE",
        "NEUTRAL",
    ):

        raise RuntimeError(
            f"{asset}: invalid signal state: {state}"
        )

    if direction not in (
        "LONG",
        "SHORT",
        "NONE",
    ):

        raise RuntimeError(
            f"{asset}: invalid signal direction: {direction}"
        )

    if state == "ACTIVE":

        if direction not in (
            "LONG",
            "SHORT",
        ):

            raise RuntimeError(
                f"{asset}: ACTIVE signal without direction"
            )

    if state == "NEUTRAL":

        if direction != "NONE":

            raise RuntimeError(
                f"{asset}: NEUTRAL signal with direction"
            )

    return state, direction


def align_one(
    asset: str,
    opportunity: Mapping[str, Any],
    signal: Mapping[str, Any],
) -> dict:

    opportunity_status = (
        opportunity.get("status")
        or
        opportunity.get("opportunity_status")
    )

    opportunity_direction = (
        opportunity.get("direction")
        or
        "NONE"
    )

    opportunity_direction = str(
        opportunity_direction
    ).strip().upper()

    signal_state, signal_direction = (
        normalize_signal(
            asset,
            signal,
        )
    )

    reasons = []

    # ------------------------------------------------------------------
    # AUTHORITATIVE SIGNAL SEMANTICS
    # ------------------------------------------------------------------

    if signal_state == "NEUTRAL":

        if opportunity_direction != "NONE":

            reasons.append(
                "NEUTRAL_SIGNAL_WITH_DIRECTIONAL_OPPORTUNITY"
            )

    elif signal_state == "ACTIVE":

        if opportunity_direction != signal_direction:

            reasons.append(
                "ACTIVE_SIGNAL_OPPORTUNITY_DIRECTION_MISMATCH"
            )

    # ------------------------------------------------------------------
    # OPPORTUNITY ELIGIBILITY
    # ------------------------------------------------------------------

    if opportunity_status == "ELIGIBLE":

        if signal_state != "ACTIVE":

            reasons.append(
                "ELIGIBLE_OPPORTUNITY_WITHOUT_ACTIVE_SIGNAL"
            )

    # ------------------------------------------------------------------
    # FINAL ALIGNMENT
    # ------------------------------------------------------------------

    aligned = not reasons

    if aligned:

        if signal_state == "NEUTRAL":

            canonical_status = "NO_TRADE"
            canonical_direction = "NONE"

        else:

            canonical_status = opportunity_status
            canonical_direction = signal_direction

    else:

        canonical_status = "BLOCKED_ALIGNMENT"
        canonical_direction = "NONE"

    return {
        "asset": asset,

        "raw_opportunity_status":
            opportunity_status,

        "raw_opportunity_direction":
            opportunity_direction,

        "signal_state":
            signal_state,

        "signal_direction":
            signal_direction,

        "aligned":
            aligned,

        "canonical_status":
            canonical_status,

        "canonical_direction":
            canonical_direction,

        "reasons":
            reasons,
    }


def main():

    print("=" * 100)
    print(
        "ARUNDA OPPORTUNITY <-> SIGNAL "
        "ALIGNMENT CONTRACT v0.1"
    )
    print("=" * 100)

    print("MODE=READ_ONLY")
    print("DB_WRITES=0")
    print("EXECUTION=OFF")
    print("ORDER_INTENTS=0")
    print()

    # ==============================================================
    # OPPORTUNITY CURRENT RUNTIME
    # ==============================================================

    opportunity_snapshot = (
        opportunity_engine.run()
    )

    opportunities = extract_opportunities(
        opportunity_snapshot
    )

    if len(opportunities) != 15:

        raise RuntimeError(
            "Opportunity coverage failure: "
            f"{len(opportunities)}/15"
        )

    # ==============================================================
    # SIGNAL CURRENT RUNTIME
    # ==============================================================

    validated_signals = (
        signal_validator.load_validated_signals()
    )

    if not isinstance(
        validated_signals,
        Mapping,
    ):

        raise RuntimeError(
            "Invalid validated signal snapshot"
        )

    # ==============================================================
    # ALIGN
    # ==============================================================

    results = {}

    print()
    print(
        "ASSET | SIGNAL | OPPORTUNITY | ALIGNMENT | CANONICAL"
    )

    print("-" * 100)

    for asset in EXPECTED_ASSETS:

        if asset not in validated_signals:

            raise RuntimeError(
                f"Missing validated signal: {asset}"
            )

        if asset not in opportunities:

            raise RuntimeError(
                f"Missing opportunity: {asset}"
            )

        result = align_one(
            asset,
            opportunities[asset],
            validated_signals[asset],
        )

        results[asset] = result

        print(
            f"{asset:<5} | "
            f"{result['signal_state']:<7}/"
            f"{result['signal_direction']:<5} | "
            f"{result['raw_opportunity_status']:<15} "
            f"{result['raw_opportunity_direction']:<5} | "
            f"{'PASS' if result['aligned'] else 'BLOCKED':<9} | "
            f"{result['canonical_status']:<18} "
            f"{result['canonical_direction']}"
        )

    # ==============================================================
    # SUMMARY
    # ==============================================================

    aligned_count = sum(
        1
        for row in results.values()
        if row["aligned"]
    )

    blocked_count = (
        len(results)
        - aligned_count
    )

    print()
    print("=" * 100)
    print("ALIGNMENT SUMMARY")
    print("=" * 100)

    print(
        f"ASSETS={len(results)}"
    )

    print(
        f"ALIGNED={aligned_count}"
    )

    print(
        f"BLOCKED_ALIGNMENT={blocked_count}"
    )

    # ==============================================================
    # NEAR
    # ==============================================================

    near = results["NEAR"]

    print()
    print("=" * 100)
    print("NEAR")
    print("=" * 100)

    print(
        f"SIGNAL={near['signal_state']}/"
        f"{near['signal_direction']}"
    )

    print(
        f"OPPORTUNITY={near['raw_opportunity_status']}/"
        f"{near['raw_opportunity_direction']}"
    )

    print(
        f"ALIGNMENT="
        f"{'PASS' if near['aligned'] else 'BLOCKED'}"
    )

    print(
        f"CANONICAL="
        f"{near['canonical_status']}/"
        f"{near['canonical_direction']}"
    )

    if near["reasons"]:

        print(
            "REASONS="
            +
            "|".join(
                near["reasons"]
            )
        )

    # ==============================================================
    # FINAL CONTRACT
    # ==============================================================

    print()
    print("=" * 100)

    if blocked_count == 0:

        print(
            "ALIGNMENT_CONTRACT=PASS"
        )

    else:

        print(
            "ALIGNMENT_CONTRACT=BLOCKED"
        )

        print(
            "REASON=ONE_OR_MORE_REAL_SIGNAL_OPPORTUNITY_CONFLICTS"
        )

    print()
    print("DB_WRITES=0")
    print("EXECUTION=OFF")
    print("ORDER_INTENTS=0")
    print("STATUS=FORENSIC_COMPLETE")
    print("=" * 100)


if __name__ == "__main__":

    main()
