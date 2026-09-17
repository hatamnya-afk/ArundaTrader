import hashlib
import json
from pathlib import Path


PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

TARGET = (
    PROJECT_ROOT
    / "LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_REPORT.json"
)

FORENSIC_REPORT = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_RUNTIME_OUTPUT_ARTIFACT_CONTENT_FORENSIC_REPORT.json"
)

PRODUCER = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_GATE_v0.1.py"
)

EXPECTED_DB_SHA256 = (
    "3e4e64aa87e80d36f2987992b7eb365b449cabb36413314b2af739424bd28eb7"
)

EXPECTED_SNAPSHOT_ID = (
    "FUSION-20260824T153800744724+0000-b4f75221aa02defa"
)

EXPECTED_ASSETS = {
    "BTC",
    "ETH",
    "SOL",
    "XRP",
}

EXPECTED_ROWS = 4
EXPECTED_ELIGIBLE = 0
EXPECTED_NO_TRADE = 4

EXPECTED_KEYS = {
    "capture_db",
    "decision",
    "eligible_rows",
    "engine",
    "frontier",
    "gate_configuration",
    "no_trade_rows",
    "production_db",
    "row_results",
    "rows",
    "safety",
    "snapshot_id",
    "timestamp_utc",
}


def sha256_file(path):
    h = hashlib.sha256()

    with open(path, "rb") as f:
        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def section(title):
    print("=" * 100)
    print(title)
    print("=" * 100)


def asset_from_row(row):
    if not isinstance(row, dict):
        return None

    for key in (
        "asset",
        "symbol",
        "ticker",
        "ASSET",
    ):
        value = row.get(key)

        if isinstance(value, str):
            return value.upper()

    return None


def direction_from_row(row):
    if not isinstance(row, dict):
        return None

    for key in (
        "direction",
        "dir",
        "signal_direction",
        "DIR",
    ):
        value = row.get(key)

        if isinstance(value, str):
            return value.upper()

    return None


def result_from_row(row):
    if not isinstance(row, dict):
        return None

    for key in (
        "result",
        "decision",
        "eligibility",
        "status",
    ):
        value = row.get(key)

        if isinstance(value, str):
            return value.upper()

    return None


def recursive_text(obj):
    return json.dumps(
        obj,
        ensure_ascii=False,
        sort_keys=True,
    ).upper()


def recursive_contains(obj, token):
    return token.upper() in recursive_text(obj)


def extract_reasons(row):
    if not isinstance(row, dict):
        return []

    reasons = []

    for key in (
        "reasons",
        "no_trade_reasons",
        "NO_TRADE_REASONS",
        "reason",
        "no_trade_reason",
    ):
        value = row.get(key)

        if isinstance(value, list):
            reasons.extend(
                str(x).upper()
                for x in value
            )

        elif isinstance(value, str):
            reasons.append(value.upper())

    return reasons


def main():

    section("ARUNDA TRADER")

    print(
        "HISTORICAL ELIGIBILITY RUNTIME OUTPUT "
        "ARTIFACT CONTENT FORENSIC v0.1"
    )

    section("MODE")

    print(
        "MODE                         : "
        "READ-ONLY ARTIFACT FORENSIC"
    )

    print(
        f"PROJECT ROOT                 : {PROJECT_ROOT}"
    )

    print(
        f"TARGET ARTIFACT              : {TARGET.name}"
    )

    print(
        f"PRODUCER                     : {PRODUCER.name}"
    )

    # ------------------------------------------------------------------
    # ARTIFACT EXISTENCE
    # ------------------------------------------------------------------

    section("ARTIFACT IDENTITY")

    if not TARGET.exists():
        raise FileNotFoundError(
            f"Artifact not found: {TARGET}"
        )

    target_size = TARGET.stat().st_size
    target_sha256 = sha256_file(TARGET)

    try:
        artifact = load_json(TARGET)
        json_valid = True
        json_error = None
    except Exception as exc:
        artifact = None
        json_valid = False
        json_error = str(exc)

    print("Exists                       : True")
    print(f"Size                         : {target_size}")
    print(f"SHA256                       : {target_sha256}")
    print(f"Valid JSON                   : {json_valid}")

    if json_error:
        print(
            f"JSON error                   : {json_error}"
        )

    if not json_valid:
        raise RuntimeError(
            "Target artifact is not valid JSON."
        )

    # ------------------------------------------------------------------
    # TOP LEVEL
    # ------------------------------------------------------------------

    section("TOP-LEVEL CONTRACT")

    actual_keys = set(artifact.keys())

    missing_keys = EXPECTED_KEYS - actual_keys
    unexpected_keys = actual_keys - EXPECTED_KEYS

    print(
        f"Top-level object             : "
        f"{isinstance(artifact, dict)}"
    )

    print(
        f"Actual key count             : "
        f"{len(actual_keys)}"
    )

    print(
        f"Expected key count           : "
        f"{len(EXPECTED_KEYS)}"
    )

    print(
        f"Missing required keys        : "
        f"{sorted(missing_keys)}"
    )

    print(
        f"Unexpected keys              : "
        f"{sorted(unexpected_keys)}"
    )

    top_level_pass = (
        isinstance(artifact, dict)
        and not missing_keys
    )

    print(
        "TOP-LEVEL CONTRACT           : "
        f"{'PASS' if top_level_pass else 'FAIL'}"
    )

    # ------------------------------------------------------------------
    # SNAPSHOT
    # ------------------------------------------------------------------

    section("SNAPSHOT IDENTITY")

    snapshot_id = artifact.get("snapshot_id")

    snapshot_pass = (
        snapshot_id == EXPECTED_SNAPSHOT_ID
    )

    print(
        f"Artifact snapshot_id         : "
        f"{snapshot_id}"
    )

    print(
        f"Expected snapshot_id         : "
        f"{EXPECTED_SNAPSHOT_ID}"
    )

    print(
        "SNAPSHOT IDENTITY            : "
        f"{'PASS' if snapshot_pass else 'FAIL'}"
    )

    # ------------------------------------------------------------------
    # REAL ARTIFACT SCHEMA
    # ------------------------------------------------------------------

    section("RUNTIME ARTIFACT SCHEMA")

    rows_value = artifact.get("rows")
    eligible_value = artifact.get("eligible_rows")
    no_trade_value = artifact.get("no_trade_rows")
    row_results = artifact.get("row_results")

    print(
        f"rows                        : "
        f"{rows_value!r} "
        f"({type(rows_value).__name__})"
    )

    print(
        f"eligible_rows               : "
        f"{eligible_value!r} "
        f"({type(eligible_value).__name__})"
    )

    print(
        f"no_trade_rows              : "
        f"{no_trade_value!r} "
        f"({type(no_trade_value).__name__})"
    )

    print(
        f"row_results type            : "
        f"{type(row_results).__name__}"
    )

    row_results_count = (
        len(row_results)
        if isinstance(row_results, list)
        else None
    )

    schema_pass = (
        isinstance(rows_value, int)
        and rows_value == EXPECTED_ROWS
        and isinstance(eligible_value, int)
        and eligible_value == EXPECTED_ELIGIBLE
        and isinstance(no_trade_value, int)
        and no_trade_value == EXPECTED_NO_TRADE
        and isinstance(row_results, list)
        and row_results_count == EXPECTED_ROWS
    )

    print(
        f"row_results count           : "
        f"{row_results_count}"
    )

    print(
        "RUNTIME ARTIFACT SCHEMA     : "
        f"{'PASS' if schema_pass else 'FAIL'}"
    )

    # ------------------------------------------------------------------
    # ROW RESULTS
    # ------------------------------------------------------------------

    section("ROW RESULT IDENTITY")

    assets = []
    directions = []
    results = []
    all_reasons = []

    if isinstance(row_results, list):

        for index, row in enumerate(row_results, start=1):

            asset = asset_from_row(row)
            direction = direction_from_row(row)
            result = result_from_row(row)
            reasons = extract_reasons(row)

            if asset:
                assets.append(asset)

            if direction:
                directions.append(direction)

            if result:
                results.append(result)

            all_reasons.extend(reasons)

            print(
                f"{index:02d} | "
                f"asset={asset} | "
                f"direction={direction} | "
                f"result={result}"
            )

            if reasons:
                print(
                    f"    reasons={reasons}"
                )

    asset_pass = (
        set(assets) == EXPECTED_ASSETS
    )

    result_pass = (
        len(results) == EXPECTED_ROWS
        and all(
            (
                "NO_TRADE" in value
                or "NO-TRADE" in value
            )
            for value in results
        )
    )

    print(
        f"Assets discovered            : {assets}"
    )

    print(
        f"Expected assets              : "
        f"{sorted(EXPECTED_ASSETS)}"
    )

    print(
        "ASSET IDENTITY               : "
        f"{'PASS' if asset_pass else 'FAIL'}"
    )

    print(
        f"Directions discovered        : "
        f"{directions}"
    )

    print(
        f"Results discovered           : "
        f"{results}"
    )

    print(
        "RESULT IDENTITY              : "
        f"{'PASS' if result_pass else 'FAIL'}"
    )

    # ------------------------------------------------------------------
    # DECISION
    # ------------------------------------------------------------------

    section("DECISION CONTRACT")

    decision = artifact.get("decision")
    frontier = artifact.get("frontier")

    decision_pass = (
        str(decision).upper() == "NO_TRADE"
    )

    frontier_pass = (
        "ELIGIBILITY_NO_TRADE_GATE"
        in str(frontier).upper()
    )

    print(
        f"decision                     : {decision}"
    )

    print(
        f"frontier                     : {frontier}"
    )

    print(
        f"TRADE_ELIGIBLE              : "
        f"{eligible_value}"
    )

    print(
        f"NO_TRADE                    : "
        f"{no_trade_value}"
    )

    print(
        "DECISION = NO_TRADE          : "
        f"{decision_pass}"
    )

    print(
        "FRONTIER IDENTITY            : "
        f"{frontier_pass}"
    )

    decision_contract_pass = (
        decision_pass
        and frontier_pass
        and eligible_value == 0
        and no_trade_value == 4
    )

    print(
        "DECISION CONTRACT            : "
        f"{'PASS' if decision_contract_pass else 'FAIL'}"
    )

    # ------------------------------------------------------------------
    # REASONS
    # ------------------------------------------------------------------

    section("NO-TRADE REASON EVIDENCE")

    reason_text = " ".join(all_reasons)

    confidence_pass = (
        "CONFIDENCE_BELOW_GATE"
        in reason_text
    )

    weak_signal_pass = (
        "WEAK_SIGNAL"
        in reason_text
    )

    print(
        f"Reason records discovered    : "
        f"{len(all_reasons)}"
    )

    print(
        f"CONFIDENCE_BELOW_GATE        : "
        f"{confidence_pass}"
    )

    print(
        f"WEAK_SIGNAL                  : "
        f"{weak_signal_pass}"
    )

    reasons_pass = (
        confidence_pass
        and weak_signal_pass
    )

    print(
        "NO-TRADE REASON EVIDENCE     : "
        f"{'PASS' if reasons_pass else 'FAIL'}"
    )

    # ------------------------------------------------------------------
    # DATABASE
    # ------------------------------------------------------------------

    section("PRODUCTION DATABASE EVIDENCE")

    production_db = artifact.get(
        "production_db"
    )

    production_db_text = recursive_text(
        production_db
    )

    db_hash_pass = (
        EXPECTED_DB_SHA256
        in production_db_text
    )

    print(
        f"production_db type           : "
        f"{type(production_db).__name__}"
    )

    print(
        f"Expected DB SHA256 present   : "
        f"{db_hash_pass}"
    )

    production_db_pass = (
        isinstance(production_db, dict)
        and db_hash_pass
    )

    print(
        "PRODUCTION DB EVIDENCE       : "
        f"{'PASS' if production_db_pass else 'FAIL'}"
    )

    # ------------------------------------------------------------------
    # SAFETY
    # ------------------------------------------------------------------

    section("SAFETY CONTRACT")

    safety = artifact.get("safety")

    safety_text = recursive_text(safety)

    safety_db_write_absent = not any(
        token in safety_text
        for token in (
            "INSERT",
            "UPDATE",
            "DELETE",
            "DDL",
        )
    )

    safety_order_absent = (
        "ORDER_EXECUTION" not in safety_text
        or "NONE" in safety_text
    )

    safety_synthetic_absent = (
        "SYNTHETIC" not in safety_text
        or "NONE" in safety_text
        or "FORBIDDEN" in safety_text
    )

    print(
        f"Safety type                  : "
        f"{type(safety).__name__}"
    )

    print(
        "Production DB write evidence : "
        f"{'PASS' if safety_db_write_absent else 'FAIL'}"
    )

    print(
        "Order execution evidence     : "
        f"{'PASS' if safety_order_absent else 'FAIL'}"
    )

    print(
        "Synthetic data evidence      : "
        f"{'PASS' if safety_synthetic_absent else 'FAIL'}"
    )

    safety_pass = (
        isinstance(safety, dict)
        and safety_db_write_absent
        and safety_order_absent
        and safety_synthetic_absent
    )

    print(
        "SAFETY CONTRACT              : "
        f"{'PASS' if safety_pass else 'FAIL'}"
    )

    # ------------------------------------------------------------------
    # RUNTIME ↔ ARTIFACT
    # ------------------------------------------------------------------

    section("RUNTIME ↔ ARTIFACT IDENTITY")

    runtime_assets_pass = (
        set(assets) == EXPECTED_ASSETS
    )

    runtime_rows_pass = (
        rows_value == EXPECTED_ROWS
    )

    runtime_decision_pass = (
        eligible_value == 0
        and no_trade_value == 4
        and len(results) == 4
        and all(
            "NO_TRADE" in value
            or "NO-TRADE" in value
            for value in results
        )
    )

    runtime_identity_pass = (
        snapshot_pass
        and runtime_assets_pass
        and runtime_rows_pass
        and runtime_decision_pass
    )

    print(
        f"Snapshot identity            : "
        f"{snapshot_pass}"
    )

    print(
        f"Runtime assets               : "
        f"{runtime_assets_pass}"
    )

    print(
        f"Runtime rows                 : "
        f"{runtime_rows_pass}"
    )

    print(
        f"Runtime decision             : "
        f"{runtime_decision_pass}"
    )

    print(
        "RUNTIME ↔ ARTIFACT IDENTITY  : "
        f"{'PASS' if runtime_identity_pass else 'FAIL'}"
    )

    # ------------------------------------------------------------------
    # CONTENT FINGERPRINT
    # ------------------------------------------------------------------

    section("ARTIFACT CONTENT FINGERPRINT")

    canonical = json.dumps(
        artifact,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    canonical_sha256 = hashlib.sha256(
        canonical
    ).hexdigest()

    print(
        f"Raw artifact SHA256           : "
        f"{target_sha256}"
    )

    print(
        f"Canonical content SHA256     : "
        f"{canonical_sha256}"
    )

    # ------------------------------------------------------------------
    # FINAL
    # ------------------------------------------------------------------

    section("FINAL DETERMINISTIC VERIFICATION")

    checks = {
        "json_valid": json_valid,
        "top_level_contract": top_level_pass,
        "snapshot_identity": snapshot_pass,
        "runtime_schema": schema_pass,
        "asset_identity": asset_pass,
        "result_identity": result_pass,
        "decision_contract": decision_contract_pass,
        "reason_evidence": reasons_pass,
        "production_db_evidence": production_db_pass,
        "safety_contract": safety_pass,
        "runtime_artifact_identity": runtime_identity_pass,
    }

    failed = [
        name
        for name, value in checks.items()
        if not value
    ]

    verified = not failed

    if verified:
        verdict = (
            "RUNTIME_OUTPUT_ARTIFACT_CONTENT_VERIFIED"
        )
    else:
        verdict = (
            "RUNTIME_OUTPUT_ARTIFACT_CONTENT_MISMATCH"
        )

    print(
        f"Checks passed                : "
        f"{len(checks) - len(failed)}/{len(checks)}"
    )

    print(
        f"Failed checks                : "
        f"{failed}"
    )

    print(
        "ARTIFACT CONTENT VERDICT     : "
        f"{verdict}"
    )

    # ------------------------------------------------------------------
    # FORENSIC REPORT
    # ------------------------------------------------------------------

    report = {
        "forensic": {
            "name": (
                "ARUNDA_TRADER_HISTORICAL_ELIGIBILITY_"
                "RUNTIME_OUTPUT_ARTIFACT_CONTENT_FORENSIC_v0.1"
            ),
            "mode": "READ-ONLY ARTIFACT FORENSIC",
        },
        "artifact": {
            "path": str(TARGET),
            "exists": True,
            "size": target_size,
            "sha256": target_sha256,
            "canonical_content_sha256": canonical_sha256,
            "valid_json": json_valid,
        },
        "observed": {
            "snapshot_id": snapshot_id,
            "rows": rows_value,
            "eligible_rows": eligible_value,
            "no_trade_rows": no_trade_value,
            "row_results_count": row_results_count,
            "assets": assets,
            "directions": directions,
            "results": results,
            "decision": decision,
            "frontier": frontier,
            "reasons": all_reasons,
        },
        "expected": {
            "snapshot_id": EXPECTED_SNAPSHOT_ID,
            "rows": EXPECTED_ROWS,
            "eligible_rows": EXPECTED_ELIGIBLE,
            "no_trade_rows": EXPECTED_NO_TRADE,
            "assets": sorted(EXPECTED_ASSETS),
            "production_db_sha256": EXPECTED_DB_SHA256,
        },
        "checks": checks,
        "failed_checks": failed,
        "verdict": verdict,
        "safety": {
            "artifact_modified": False,
            "producer_modified": False,
            "producer_executed": False,
            "production_db_modified": False,
            "network_access": False,
        },
    }

    FORENSIC_REPORT.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    section("FINAL VERDICT")

    print(
        "HISTORICAL ELIGIBILITY RUNTIME EVIDENCE : "
        f"{verdict}"
    )

    print(
        f"TARGET ARTIFACT               : {TARGET}"
    )

    print(
        f"TARGET SHA256                 : "
        f"{target_sha256}"
    )

    print(
        f"CANONICAL CONTENT SHA256      : "
        f"{canonical_sha256}"
    )

    print(
        f"SNAPSHOT                      : "
        f"{snapshot_id}"
    )

    print(
        f"ROWS                          : "
        f"{rows_value}"
    )

    print(
        f"TRADE_ELIGIBLE                : "
        f"{eligible_value}"
    )

    print(
        f"NO_TRADE                      : "
        f"{no_trade_value}"
    )

    print(
        f"FORENSIC REPORT               : "
        f"{FORENSIC_REPORT}"
    )

    print("=" * 100)


if __name__ == "__main__":
    main()