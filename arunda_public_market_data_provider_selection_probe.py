"""
ARUNDA PUBLIC MARKET DATA
PROVIDER SELECTION PROBE v0.1

Evidence-only provider selection support layer.

NO NETWORK
NO DB WRITE
NO PRODUCTION CHANGE
NO AUTOMATIC SELECTION
NO PROVIDER BLENDING
NO QUALIFICATION RE-RUN
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ENGINE_VERSION = (
    "ARUNDA_PUBLIC_MARKET_DATA_PROVIDER_SELECTION_PROBE_v0.1"
)

EXPECTED_EVIDENCE_CONTRACT = (
    "ARUNDA_PUBLIC_MARKET_DATA_"
    "QUALIFICATION_EVIDENCE_V0.3"
)

EXPECTED_SOURCE_ENGINE = (
    "ARUNDA_PUBLIC_MARKET_DATA_"
    "QUALIFICATION_PROBE_V0.3"
)

EXPECTED_PROVIDERS = (
    "BYBIT",
    "KUCOIN",
)

EXPECTED_ASSETS = (
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
)


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def norm_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().upper()


def as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        return value.strip().lower() in {
            "true",
            "1",
            "yes",
            "y",
        }

    return bool(value)


def as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------
# Artifact validation
# ---------------------------------------------------------------------

def validate_artifact_identity(
    payload: dict[str, Any],
) -> list[str]:

    errors: list[str] = []

    evidence_contract = norm_text(
        payload.get("evidence_contract")
    )

    engine = norm_text(
        payload.get("engine")
    )

    source_engine = norm_text(
        payload.get("source_engine")
    )

    if evidence_contract != EXPECTED_EVIDENCE_CONTRACT:
        errors.append(
            "unexpected evidence contract: "
            + (evidence_contract or "MISSING")
        )

    if engine != EXPECTED_EVIDENCE_CONTRACT:
        errors.append(
            "unexpected evidence engine: "
            + (engine or "MISSING")
        )

    if source_engine != EXPECTED_SOURCE_ENGINE:
        errors.append(
            "unexpected source engine: "
            + (source_engine or "MISSING")
        )

    timeframe = norm_text(
        payload.get("timeframe")
        or payload.get("TIMEFRAME")
    )

    if timeframe and timeframe != "1H":
        errors.append(
            "unexpected timeframe: " + timeframe
        )

    mode = norm_text(
        payload.get("mode")
        or payload.get("MODE")
    )

    if mode and "PUBLIC" not in mode:
        errors.append(
            "unexpected mode: " + mode
        )

    return errors


# ---------------------------------------------------------------------
# Provider extraction
# ---------------------------------------------------------------------

def extract_provider_rows(
    payload: dict[str, Any],
) -> dict[str, dict[str, Any]]:

    raw = payload.get("providers")

    if raw is None:
        raw = payload.get("provider_results")

    if raw is None:
        raw = payload.get("results")

    output: dict[str, dict[str, Any]] = {}

    if isinstance(raw, dict):

        for key, value in raw.items():

            provider = norm_text(key)

            if provider not in EXPECTED_PROVIDERS:
                continue

            if isinstance(value, dict):
                output[provider] = value

        return output

    if isinstance(raw, list):

        for item in raw:

            if not isinstance(item, dict):
                continue

            provider = norm_text(
                item.get("provider")
                or item.get("exchange")
                or item.get("name")
            )

            if provider not in EXPECTED_PROVIDERS:
                continue

            output[provider] = item

    return output


# ---------------------------------------------------------------------
# Evidence field readers
# ---------------------------------------------------------------------

def get_status(
    row: dict[str, Any],
) -> str:

    return norm_text(
        row.get("status")
        or row.get("qualification_status")
        or row.get("STATUS")
    )


def get_fatal_error(
    row: dict[str, Any],
) -> str:

    return norm_text(
        row.get("fatal_error")
        or row.get("error")
        or row.get("FATAL ERROR")
    )


def get_market_coverage(
    row: dict[str, Any],
) -> tuple[int, int]:

    value = row.get("market_coverage")

    if value is None:
        value = row.get("MARKET COVERAGE")

    if isinstance(value, str) and "/" in value:

        left, right = value.split("/", 1)

        return (
            as_int(left),
            as_int(right),
        )

    if isinstance(value, dict):

        ready = (
            value.get("ready")
            if value.get("ready") is not None
            else value.get("covered")
        )

        total = value.get("total")

        return (
            as_int(ready),
            as_int(total),
        )

    return (
        as_int(
            row.get("market_ready")
        ),
        as_int(
            row.get("market_total")
        ),
    )


def get_qualified_coverage(
    row: dict[str, Any],
) -> tuple[int, int]:

    value = row.get("qualified_assets")

    if value is None:
        value = row.get("QUALIFIED ASSETS")

    if isinstance(value, str) and "/" in value:

        left, right = value.split("/", 1)

        return (
            as_int(left),
            as_int(right),
        )

    if isinstance(value, dict):

        return (
            as_int(
                value.get("qualified")
            ),
            as_int(
                value.get("total")
            ),
        )

    return (
        as_int(
            row.get("qualified_ready")
        ),
        as_int(
            row.get("qualified_total")
        ),
    )


def get_asset_rows(
    row: dict[str, Any],
) -> list[dict[str, Any]]:

    assets = row.get("assets")

    if assets is None:
        assets = row.get("asset_results")

    if assets is None:
        assets = row.get("matrix")

    if assets is None:
        assets = row.get("forensic_matrix")

    if isinstance(assets, list):

        return [
            item
            for item in assets
            if isinstance(item, dict)
        ]

    if isinstance(assets, dict):

        result: list[dict[str, Any]] = []

        for asset, value in assets.items():

            if not isinstance(value, dict):
                continue

            item = dict(value)

            item.setdefault(
                "asset",
                asset,
            )

            result.append(item)

        return result

    return []


# ---------------------------------------------------------------------
# Asset evidence inspection
# ---------------------------------------------------------------------

def inspect_asset_evidence(
    row: dict[str, Any],
) -> dict[str, Any]:

    asset_rows = get_asset_rows(row)

    if not asset_rows:

        return {
            "asset_count": 0,
            "assets_complete": False,
            "all_fresh": False,
            "all_current": False,
            "all_complete": False,
            "all_clean": False,
        }

    observed: set[str] = set()

    all_fresh = True
    all_current = True
    all_complete = True
    all_clean = True

    freshness_fields_present = False
    current_fields_present = False
    complete_fields_present = False

    for item in asset_rows:

        asset = norm_text(
            item.get("asset")
            or item.get("symbol")
            or item.get("base")
        )

        if asset:
            observed.add(asset)

        if "fresh" in item or "FRESH" in item:
            freshness_fields_present = True

            fresh = as_bool(
                item.get("fresh")
                if "fresh" in item
                else item.get("FRESH")
            )

            all_fresh &= fresh

        if "current" in item or "CURRENT" in item:
            current_fields_present = True

            current = as_bool(
                item.get("current")
                if "current" in item
                else item.get("CURRENT")
            )

            all_current &= current

        if "complete" in item or "COMPLETE" in item:
            complete_fields_present = True

            complete = as_bool(
                item.get("complete")
                if "complete" in item
                else item.get("COMPLETE")
            )

            all_complete &= complete

        duplicates = as_int(
            item.get("duplicates")
            if "duplicates" in item
            else item.get("DUP")
        )

        missing = as_int(
            item.get("missing")
            if "missing" in item
            else item.get("MISS")
        )

        nonmono = as_bool(
            item.get("nonmonotonic")
            if "nonmonotonic" in item
            else item.get("NONMONO")
        )

        bad_interval = as_int(
            item.get("bad_interval")
            if "bad_interval" in item
            else item.get("BADINT")
        )

        future = as_int(
            item.get("future")
            if "future" in item
            else item.get("FUTURE")
        )

        if (
            duplicates != 0
            or missing != 0
            or nonmono
            or bad_interval != 0
            or future != 0
        ):
            all_clean = False

    assets_complete = (
        set(EXPECTED_ASSETS).issubset(observed)
    )

    return {
        "asset_count": len(asset_rows),
        "assets_complete": assets_complete,
        "all_fresh": (
            all_fresh
            if freshness_fields_present
            else None
        ),
        "all_current": (
            all_current
            if current_fields_present
            else None
        ),
        "all_complete": (
            all_complete
            if complete_fields_present
            else None
        ),
        "all_clean": all_clean,
    }


# ---------------------------------------------------------------------
# Provider classification
# ---------------------------------------------------------------------

def classify_provider(
    provider: str,
    row: dict[str, Any],
) -> dict[str, Any]:

    status = get_status(row)

    market_ready, market_total = (
        get_market_coverage(row)
    )

    qualified_ready, qualified_total = (
        get_qualified_coverage(row)
    )

    asset_forensics = inspect_asset_evidence(
        row
    )

    fatal_error = get_fatal_error(row)

    environment_blocked = (
        "BLOCKED" in status
        or "METADATA_ERROR" in status
        or "403" in fatal_error
        or "FORBIDDEN" in fatal_error
        or "ACCESS DENIED" in fatal_error
        or "CLOUDFRONT" in fatal_error
    )

    provider_rejected = (
        "REJECT" in status
        or "INVALID" in status
        or "FAILED" in status
    )

    # -------------------------------------------------------------
    # IMPORTANT:
    #
    # FULLY_QUALIFIED is already a conclusion produced by the
    # Qualification Probe.
    #
    # Selection Probe must consume that conclusion rather than
    # reconstructing qualification from optional fields that may
    # not exist in the evidence artifact.
    # -------------------------------------------------------------

    qualification_pass = (
        status == "FULLY_QUALIFIED"
        and market_ready == 15
        and market_total == 15
        and qualified_ready == 15
        and qualified_total == 15
    )

    if qualification_pass:

        classification = "CANDIDATE_ONLY"

        reason = (
            "Qualification evidence reports FULLY_QUALIFIED "
            "with complete 15/15 market and asset coverage. "
            "Provider is reported as an evidence-derived "
            "production-selection candidate only."
        )

    elif environment_blocked:

        classification = "ENVIRONMENT_BLOCKED"

        reason = (
            "Qualification was blocked by the current runtime "
            "environment. Provider quality is not determined."
        )

    elif provider_rejected:

        classification = "PROVIDER_REJECTED"

        reason = (
            "Qualification evidence explicitly indicates "
            "provider failure or rejection."
        )

    else:

        classification = "INSUFFICIENT_EVIDENCE"

        reason = (
            "Available qualification evidence is insufficient "
            "for production-selection candidacy."
        )

    return {
        "provider": provider,
        "qualification_status": (
            status or "UNKNOWN"
        ),
        "market_coverage": {
            "ready": market_ready,
            "total": market_total,
        },
        "qualified_coverage": {
            "ready": qualified_ready,
            "total": qualified_total,
        },
        "asset_forensics": asset_forensics,
        "classification": classification,
        "reason": reason,
    }


# ---------------------------------------------------------------------
# Selection evidence
# ---------------------------------------------------------------------

def build_selection_evidence(
    provider_results: dict[str, dict[str, Any]],
) -> dict[str, Any]:

    qualified_candidates = [
        provider
        for provider, result in provider_results.items()
        if result["classification"]
        == "CANDIDATE_ONLY"
    ]

    blocked = [
        provider
        for provider, result in provider_results.items()
        if result["classification"]
        == "ENVIRONMENT_BLOCKED"
    ]

    rejected = [
        provider
        for provider, result in provider_results.items()
        if result["classification"]
        == "PROVIDER_REJECTED"
    ]

    insufficient = [
        provider
        for provider, result in provider_results.items()
        if result["classification"]
        == "INSUFFICIENT_EVIDENCE"
    ]

    canonical_selection = "DEFERRED"
    failover_selection = "DEFERRED"

    primary_candidate = None
    secondary_candidate = None

    if len(qualified_candidates) >= 1:
        primary_candidate = qualified_candidates[0]

    if len(qualified_candidates) >= 2:
        secondary_candidate = qualified_candidates[1]

    if len(qualified_candidates) >= 2:

        selection_evidence_status = (
            "MULTI_PROVIDER_SELECTION_EVIDENCE_AVAILABLE"
        )

        conclusion = (
            "At least two providers independently satisfy "
            "qualification evidence. Production canonical and "
            "failover selection remain deferred and require an "
            "explicit architecture decision."
        )

        exit_recommendation = (
            "READY_FOR_EXPLICIT_SELECTION_REVIEW"
        )

    elif len(qualified_candidates) == 1:

        selection_evidence_status = (
            "SINGLE_PROVIDER_CANDIDACY_ONLY"
        )

        conclusion = (
            "Exactly one provider is fully qualified in the "
            "supplied evidence. It may be reported as an "
            "evidence-derived candidate only. Canonical and "
            "failover selection remain deferred."
        )

        exit_recommendation = (
            "SELECTION_DEFERRED"
        )

    else:

        selection_evidence_status = (
            "NO_QUALIFIED_PROVIDER"
        )

        conclusion = (
            "No provider has sufficient qualification evidence "
            "for selection candidacy."
        )

        exit_recommendation = (
            "SELECTION_DEFERRED"
        )

    return {
        "qualified_candidates": qualified_candidates,
        "blocked_providers": blocked,
        "rejected_providers": rejected,
        "insufficient_evidence_providers": insufficient,
        "primary_candidate": primary_candidate,
        "secondary_candidate": secondary_candidate,
        "canonical_selection": canonical_selection,
        "failover_selection": failover_selection,
        "selection_evidence_status": (
            selection_evidence_status
        ),
        "production_change": False,
        "automatic_selection": False,
        "blending": False,
        "exit_recommendation": exit_recommendation,
        "conclusion": conclusion,
    }


# ---------------------------------------------------------------------
# Human-readable report
# ---------------------------------------------------------------------

def print_header() -> None:

    print()
    print("=" * 78)
    print("ARUNDA PUBLIC MARKET DATA")
    print("PROVIDER SELECTION PROBE v0.1")
    print("=" * 78)

    print(
        f"Engine              : {ENGINE_VERSION}"
    )

    print(
        f"Run UTC             : {utc_now()}"
    )

    print(
        "Evidence Mode       : "
        "QUALIFICATION EVIDENCE ARTIFACT ONLY"
    )

    print("Network             : NONE")
    print("CCXT                : NOT USED")
    print("DB WRITE            : NONE")
    print("PRODUCTION CHANGE   : FORBIDDEN")
    print("AUTOMATIC SELECTION : FORBIDDEN")
    print("BLENDING            : FORBIDDEN")
    print("CANONICAL           : DEFERRED")
    print("FAILOVER            : DEFERRED")

    print("=" * 78)


def print_provider_result(
    result: dict[str, Any],
) -> None:

    market = result["market_coverage"]
    qualified = result["qualified_coverage"]
    forensic = result["asset_forensics"]

    print()
    print("-" * 78)

    print(
        f"PROVIDER            : "
        f"{result['provider']}"
    )

    print(
        f"QUALIFICATION       : "
        f"{result['qualification_status']}"
    )

    print(
        f"MARKET COVERAGE     : "
        f"{market['ready']}/{market['total']}"
    )

    print(
        f"QUALIFIED ASSETS    : "
        f"{qualified['ready']}/{qualified['total']}"
    )

    print(
        f"ASSET MATRIX        : "
        f"{forensic['asset_count']}/15"
    )

    print(
        f"ALL FRESH           : "
        f"{forensic['all_fresh']}"
    )

    print(
        f"ALL CURRENT         : "
        f"{forensic['all_current']}"
    )

    print(
        f"ALL COMPLETE        : "
        f"{forensic['all_complete']}"
    )

    print(
        f"ALL CLEAN           : "
        f"{forensic['all_clean']}"
    )

    print(
        f"CLASSIFICATION      : "
        f"{result['classification']}"
    )

    print(
        f"REASON              : "
        f"{result['reason']}"
    )


def print_final(
    evidence: dict[str, Any],
) -> None:

    candidates = evidence[
        "qualified_candidates"
    ]

    blocked = evidence[
        "blocked_providers"
    ]

    rejected = evidence[
        "rejected_providers"
    ]

    insufficient = evidence[
        "insufficient_evidence_providers"
    ]

    candidates_text = (
        ", ".join(candidates)
        if candidates
        else "NONE"
    )

    blocked_text = (
        ", ".join(blocked)
        if blocked
        else "NONE"
    )

    rejected_text = (
        ", ".join(rejected)
        if rejected
        else "NONE"
    )

    insufficient_text = (
        ", ".join(insufficient)
        if insufficient
        else "NONE"
    )

    primary = (
        evidence["primary_candidate"]
        or "NONE"
    )

    secondary = (
        evidence["secondary_candidate"]
        or "NONE"
    )

    print()
    print("=" * 78)
    print("SELECTION EVIDENCE")
    print("=" * 78)

    print(
        f"QUALIFIED CANDIDATES : "
        f"{candidates_text}"
    )

    print(
        f"PRIMARY CANDIDATE    : "
        f"{primary}"
    )

    print(
        f"SECONDARY CANDIDATE  : "
        f"{secondary}"
    )

    print(
        f"BLOCKED PROVIDERS    : "
        f"{blocked_text}"
    )

    print(
        f"REJECTED PROVIDERS   : "
        f"{rejected_text}"
    )

    print(
        f"INSUFFICIENT         : "
        f"{insufficient_text}"
    )

    print(
        f"CANONICAL SELECTION  : "
        f"{evidence['canonical_selection']}"
    )

    print(
        f"FAILOVER SELECTION   : "
        f"{evidence['failover_selection']}"
    )

    print(
        f"AUTOMATIC SELECTION  : "
        f"{evidence['automatic_selection']}"
    )

    print(
        f"PRODUCTION CHANGE    : "
        f"{evidence['production_change']}"
    )

    print(
        f"BLENDING             : "
        f"{evidence['blending']}"
    )

    print(
        f"EVIDENCE STATUS      : "
        f"{evidence['selection_evidence_status']}"
    )

    print(
        f"RECOMMENDATION       : "
        f"{evidence['exit_recommendation']}"
    )

    print()
    print("CONCLUSION:")
    print(evidence["conclusion"])

    print()
    print("=" * 78)
    print("PRODUCTION WAS NOT CHANGED.")
    print("=" * 78)


# ---------------------------------------------------------------------
# JSON artifact
# ---------------------------------------------------------------------

def build_output_artifact(
    source_path: Path,
    payload: dict[str, Any],
    provider_results: dict[str, dict[str, Any]],
    selection_evidence: dict[str, Any],
) -> dict[str, Any]:

    return {
        "engine": ENGINE_VERSION,
        "run_utc": utc_now(),
        "mode": "EVIDENCE_ONLY",
        "source_artifact": str(source_path),
        "source_evidence_contract": (
            payload.get("evidence_contract")
        ),
        "source_engine": (
            payload.get("source_engine")
        ),
        "source_qualification_engine": (
            payload.get("source_engine")
        ),
        "providers": provider_results,
        "selection_evidence": selection_evidence,
        "safety": {
            "network": False,
            "ccxt_network": False,
            "db_write": False,
            "production_change": False,
            "automatic_selection": False,
            "blending": False,
            "synthetic_data": False,
            "interpolation": False,
            "forward_fill": False,
            "back_fill": False,
        },
    }


# ---------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------

def parse_args() -> argparse.Namespace:

    parser = argparse.ArgumentParser(
        description=(
            "Evidence-only Provider Selection Probe v0.1"
        )
    )

    parser.add_argument(
        "evidence",
        help=(
            "Qualification Evidence v0.3 JSON artifact"
        ),
    )

    parser.add_argument(
        "--json-out",
        default=None,
        help="Optional output JSON artifact path",
    )

    return parser.parse_args()


def load_json(
    path: Path,
) -> dict[str, Any]:

    if not path.exists():
        raise FileNotFoundError(
            f"Evidence artifact not found: {path}"
        )

    if not path.is_file():
        raise ValueError(
            f"Evidence path is not a file: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:

        payload = json.load(handle)

    if not isinstance(payload, dict):
        raise ValueError(
            "Evidence artifact root must be a JSON object."
        )

    return payload


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main() -> int:

    args = parse_args()

    print_header()

    evidence_path = Path(
        args.evidence
    )

    try:

        payload = load_json(
            evidence_path
        )

    except Exception as exc:

        print()
        print("SELECTION PROBE : FAIL")
        print(
            f"ERROR           : {exc}"
        )

        return 1

    identity_errors = (
        validate_artifact_identity(
            payload
        )
    )

    if identity_errors:

        print()
        print("SELECTION PROBE : FAIL")
        print("INVALID EVIDENCE ARTIFACT")

        for error in identity_errors:
            print(
                f" - {error}"
            )

        return 1

    provider_rows = (
        extract_provider_rows(
            payload
        )
    )

    if not provider_rows:

        print()
        print("SELECTION PROBE : FAIL")
        print(
            "ERROR           : "
            "no supported provider evidence found"
        )

        return 1

    provider_results: dict[
        str,
        dict[str, Any],
    ] = {}

    for provider in EXPECTED_PROVIDERS:

        row = provider_rows.get(
            provider
        )

        if row is None:

            provider_results[provider] = {
                "provider": provider,
                "qualification_status": (
                    "MISSING_EVIDENCE"
                ),
                "market_coverage": {
                    "ready": 0,
                    "total": 0,
                },
                "qualified_coverage": {
                    "ready": 0,
                    "total": 0,
                },
                "asset_forensics": {
                    "asset_count": 0,
                    "assets_complete": False,
                    "all_fresh": False,
                    "all_current": False,
                    "all_complete": False,
                    "all_clean": False,
                },
                "classification": (
                    "INSUFFICIENT_EVIDENCE"
                ),
                "reason": (
                    "No qualification evidence supplied "
                    "for this provider."
                ),
            }

        else:

            provider_results[provider] = (
                classify_provider(
                    provider,
                    row,
                )
            )

    for result in provider_results.values():

        print_provider_result(
            result
        )

    selection_evidence = (
        build_selection_evidence(
            provider_results
        )
    )

    print_final(
        selection_evidence
    )

    output = build_output_artifact(
        evidence_path,
        payload,
        provider_results,
        selection_evidence,
    )

    if args.json_out:

        output_path = Path(
            args.json_out
        )

        with output_path.open(
            "w",
            encoding="utf-8",
        ) as handle:

            json.dump(
                output,
                handle,
                indent=2,
                ensure_ascii=False,
            )

        print()
        print(
            f"JSON EVIDENCE       : "
            f"{output_path}"
        )

    status = selection_evidence[
        "selection_evidence_status"
    ]

    if status == "SINGLE_PROVIDER_CANDIDACY_ONLY":
        return 0

    if (
        status
        == "MULTI_PROVIDER_SELECTION_EVIDENCE_AVAILABLE"
    ):
        return 0

    if status == "NO_QUALIFIED_PROVIDER":
        return 2

    return 2


if __name__ == "__main__":
    sys.exit(main())