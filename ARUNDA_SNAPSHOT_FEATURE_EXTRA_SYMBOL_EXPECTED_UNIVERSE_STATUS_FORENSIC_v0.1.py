import json
import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


BASE_DIR = Path(r"C:\Users\ASUS\ArundaTrader")

DB_PATH = BASE_DIR / "arunda.db"

NORMALIZATION_ARTIFACT = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_EXPECTED_UNIVERSE_NORMALIZATION_FORENSIC_v0.1.json"
)

PROVENANCE_ARTIFACT = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_INPUT_EXTRA_UNIVERSE_PROVENANCE_FORENSIC_v0.1.json"
)

SEMANTIC_ARTIFACT = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_SEMANTIC_FORENSIC_v0.1.json"
)

ORIGIN_ARTIFACT = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_ORIGIN_PROPAGATION_FORENSIC_v0.1.json"
)

FIRST_INSERTION_ARTIFACT = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_FIRST_INSERTION_FORENSIC_v0.1.json"
)

CMC_IDENTITY_ARTIFACT = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_CMC_IDENTITY_FORENSIC_v0.1.json"
)

OUTPUT_ARTIFACT = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_EXPECTED_UNIVERSE_STATUS_FORENSIC_v0.1.json"
)


EXPECTED_TABLES = [
    "market_history",
    "market_history_legacy",
    "market_microstructure",
    "market_opportunity",
    "market_state",
    "market_technical",
    "market_universe",
]


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_symbol(value):
    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    return value.upper()


def extract_expected_universe(data):
    candidates = [
        data.get("expected_universe"),
        data.get("expected_symbols"),
        data.get("normalized_expected_universe"),
        data.get("universe"),
    ]

    for candidate in candidates:
        if isinstance(candidate, list):
            return {
                normalize_symbol(x)
                for x in candidate
                if normalize_symbol(x) is not None
            }

        if isinstance(candidate, dict):
            for key in (
                "symbols",
                "expected_symbols",
                "normalized_symbols",
                "universe",
            ):
                value = candidate.get(key)

                if isinstance(value, list):
                    return {
                        normalize_symbol(x)
                        for x in value
                        if normalize_symbol(x) is not None
                    }

    # Recursive fallback.
    found = []

    def walk(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                key_lower = str(key).lower()

                if (
                    "expected_universe" in key_lower
                    or "normalized_expected_universe" in key_lower
                    or key_lower in {"expected_symbols", "normalized_symbols"}
                ):
                    if isinstance(value, list):
                        found.extend(value)

                walk(value)

        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(data)

    return {
        normalize_symbol(x)
        for x in found
        if normalize_symbol(x) is not None
    }


def extract_targets(data):
    targets = set()

    def walk(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                key_lower = str(key).lower()

                if key_lower in {
                    "extra_symbols",
                    "targets",
                    "target_symbols",
                    "resolved_extra_symbols",
                }:
                    if isinstance(value, list):
                        for item in value:
                            symbol = normalize_symbol(item)
                            if symbol:
                                targets.add(symbol)

                walk(value)

        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(data)

    return targets


def get_tables(conn):
    rows = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
        ORDER BY name
        """
    ).fetchall()

    return [row[0] for row in rows]


def table_columns(conn, table):
    rows = conn.execute(
        f'PRAGMA table_info("{table}")'
    ).fetchall()

    return {row[1] for row in rows}


def symbol_inventory(conn, symbol):
    evidence = {}

    for table in EXPECTED_TABLES:
        if table not in get_tables(conn):
            continue

        columns = table_columns(conn, table)

        symbol_columns = [
            column
            for column in ("symbol", "asset")
            if column in columns
        ]

        for column in symbol_columns:
            try:
                row = conn.execute(
                    f'''
                    SELECT COUNT(*)
                    FROM "{table}"
                    WHERE UPPER(TRIM(CAST("{column}" AS TEXT))) = ?
                    ''',
                    (symbol,),
                ).fetchone()

                count = int(row[0])

                if count > 0:
                    evidence[f"{table}.{column}"] = count

            except sqlite3.Error:
                pass

    return evidence


def market_universe_identity(conn, symbol):
    if "market_universe" not in get_tables(conn):
        return []

    columns = table_columns(conn, "market_universe")

    if "symbol" not in columns:
        return []

    rows = conn.execute(
        """
        SELECT *
        FROM market_universe
        WHERE UPPER(TRIM(CAST(symbol AS TEXT))) = ?
        ORDER BY id
        """,
        (symbol,),
    ).fetchall()

    names = [x[0] for x in conn.execute(
        "PRAGMA table_info(market_universe)"
    ).fetchall()]

    result = []

    for row in rows:
        record = dict(zip(names, row))

        selected = {}

        for key in (
            "id",
            "cmc_id",
            "name",
            "symbol",
            "slug",
            "cmc_rank",
            "rank",
            "source",
            "engine_version",
            "is_active",
            "date_added",
            "first_seen",
            "last_seen",
            "last_updated",
        ):
            if key in record:
                selected[key] = record[key]

        result.append(selected)

    return result


def extract_canonical_identities(data):
    identities = {}

    def walk(obj):
        if isinstance(obj, dict):
            symbol = obj.get("symbol")

            if symbol is not None:
                normalized = normalize_symbol(symbol)

                if normalized:
                    if (
                        "cmc_id" in obj
                        or "identity_class" in obj
                        or "canonical_asset_evidence" in obj
                    ):
                        identities[normalized] = obj

            for value in obj.values():
                walk(value)

        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(data)

    return identities


def build_status(expected, targets, conn, identity_data):
    results = []

    for symbol in sorted(targets):
        in_expected = symbol in expected

        inventory = symbol_inventory(conn, symbol)
        identity_rows = market_universe_identity(conn, symbol)

        identity = identity_data.get(symbol, {})

        cmc_ids = set()

        for row in identity_rows:
            if row.get("cmc_id") is not None:
                cmc_ids.add(str(row["cmc_id"]))

        artifact_cmc_ids = identity.get("cmc_ids", [])

        for value in artifact_cmc_ids:
            cmc_ids.add(str(value))

        status = (
            "EXPECTED_UNIVERSE_MEMBER"
            if in_expected
            else "OUTSIDE_EXPECTED_UNIVERSE"
        )

        if not in_expected and cmc_ids:
            status = "CMC_IDENTIFIED_OUTSIDE_EXPECTED_UNIVERSE"

        results.append(
            {
                "symbol": symbol,
                "expected_universe_member": in_expected,
                "status": status,
                "database_evidence": inventory,
                "observed_table_count": len(inventory),
                "market_universe_identity_rows": identity_rows,
                "cmc_ids": sorted(cmc_ids),
                "canonical_asset_evidence": bool(
                    cmc_ids and identity_rows
                ),
            }
        )

    return results


def main():
    print("=" * 90)
    print(
        "ARUNDA SNAPSHOT FEATURE EXTRA SYMBOL EXPECTED UNIVERSE STATUS FORENSIC v0.1"
    )
    print("=" * 90)
    print(f"Database       : {DB_PATH}")
    print(f"Normalization  : {NORMALIZATION_ARTIFACT}")
    print(f"Provenance     : {PROVENANCE_ARTIFACT}")
    print(f"Semantic       : {SEMANTIC_ARTIFACT}")
    print(f"Origin         : {ORIGIN_ARTIFACT}")
    print(f"First Insertion: {FIRST_INSERTION_ARTIFACT}")
    print(f"CMC Identity   : {CMC_IDENTITY_ARTIFACT}")
    print("Mode           : READ ONLY")
    print("Network        : FORBIDDEN")
    print("Database Write : FORBIDDEN")
    print("Prediction     : FORBIDDEN")
    print("Decision       : FORBIDDEN")
    print("-" * 90)

    required = [
        NORMALIZATION_ARTIFACT,
        PROVENANCE_ARTIFACT,
        SEMANTIC_ARTIFACT,
        ORIGIN_ARTIFACT,
        FIRST_INSERTION_ARTIFACT,
        CMC_IDENTITY_ARTIFACT,
    ]

    for path in required:
        if not path.exists():
            raise FileNotFoundError(f"Missing required artifact: {path}")

    normalization = load_json(NORMALIZATION_ARTIFACT)
    provenance = load_json(PROVENANCE_ARTIFACT)
    semantic = load_json(SEMANTIC_ARTIFACT)
    origin = load_json(ORIGIN_ARTIFACT)
    first_insertion = load_json(FIRST_INSERTION_ARTIFACT)
    cmc_identity = load_json(CMC_IDENTITY_ARTIFACT)

    expected = extract_expected_universe(normalization)

    targets = extract_targets(provenance)

    if not targets:
        targets = extract_targets(semantic)

    if not targets:
        targets = extract_targets(origin)

    if not targets:
        targets = extract_targets(first_insertion)

    if not targets:
        targets = extract_targets(cmc_identity)

    if not targets:
        raise RuntimeError(
            "Could not resolve target extra symbols from forensic artifacts."
        )

    print("=" * 90)
    print("INPUT CONTRACT")
    print("=" * 90)
    print(f"Expected Universe : {len(expected)}")
    print(f"Target Symbols    : {', '.join(sorted(targets))}")
    print("-" * 90)

    conn = sqlite3.connect(
        f"file:{DB_PATH.as_posix()}?mode=ro",
        uri=True,
    )

    try:
        tables = get_tables(conn)

        print("=" * 90)
        print("DATABASE INVENTORY")
        print("=" * 90)
        print(f"Database Tables : {len(tables)}")

        identity_data = extract_canonical_identities(cmc_identity)

        results = build_status(
            expected,
            targets,
            conn,
            identity_data,
        )

    finally:
        conn.close()

    print("=" * 90)
    print("EXPECTED UNIVERSE STATUS")
    print("=" * 90)

    expected_members = 0
    outside_expected = 0
    cmc_identified = 0

    for item in results:
        symbol = item["symbol"]

        print("-" * 90)
        print(f"SYMBOL : {symbol}")
        print(
            f"EXPECTED UNIVERSE MEMBER : "
            f"{item['expected_universe_member']}"
        )
        print(f"STATUS : {item['status']}")
        print(
            f"OBSERVED TABLE COUNT : "
            f"{item['observed_table_count']}"
        )

        if item["cmc_ids"]:
            print(
                f"CMC IDs : "
                f"{', '.join(item['cmc_ids'])}"
            )

        print(
            f"CANONICAL ASSET EVIDENCE : "
            f"{item['canonical_asset_evidence']}"
        )

        if item["expected_universe_member"]:
            expected_members += 1
        else:
            outside_expected += 1

        if item["cmc_ids"]:
            cmc_identified += 1

    print("=" * 90)
    print("CROSS-SYMBOL SUMMARY")
    print("=" * 90)
    print(
        f"Target Symbols                  : {len(results)}"
    )
    print(
        f"Expected Universe Members       : {expected_members}"
    )
    print(
        f"Outside Expected Universe      : {outside_expected}"
    )
    print(
        f"CMC Identified Targets          : {cmc_identified}"
    )

    all_resolved = (
        len(results) == len(targets)
        and all(
            item["symbol"] in targets
            for item in results
        )
    )

    if all_resolved and cmc_identified == len(results):
        forensic_status = (
            "EXTRA_SYMBOLS_CMC_IDENTIFIED_AND_EXPECTED_UNIVERSE_STATUS_ESTABLISHED"
        )
    elif all_resolved:
        forensic_status = (
            "EXTRA_SYMBOLS_EXPECTED_UNIVERSE_STATUS_ESTABLISHED"
        )
    else:
        forensic_status = (
            "EXTRA_SYMBOL_EXPECTED_UNIVERSE_STATUS_INCOMPLETE"
        )

    print("=" * 90)
    print("FORENSIC STATUS")
    print("=" * 90)
    print(f"FORENSIC STATUS : {forensic_status}")
    print("PREDICTIVE CLAIM : NOT ESTABLISHED")
    print("RELATIONSHIP CALCULATION : NOT PERFORMED")
    print("DATABASE WRITE : NOT PERFORMED")
    print("DATABASE REPAIR : NOT PERFORMED")

    artifact = {
        "artifact_name": (
            "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_"
            "EXPECTED_UNIVERSE_STATUS_FORENSIC_v0.1"
        ),
        "version": "v0.1",
        "generated_at": utc_now(),
        "database": str(DB_PATH),
        "mode": "READ ONLY",
        "network": "FORBIDDEN",
        "database_write": "FORBIDDEN",
        "prediction": "FORBIDDEN",
        "decision": "FORBIDDEN",
        "input_contract": {
            "expected_universe_count": len(expected),
            "target_symbols": sorted(targets),
        },
        "source_artifacts": {
            "normalization": {
                "path": str(NORMALIZATION_ARTIFACT),
                "sha256": sha256_file(NORMALIZATION_ARTIFACT),
            },
            "provenance": {
                "path": str(PROVENANCE_ARTIFACT),
                "sha256": sha256_file(PROVENANCE_ARTIFACT),
            },
            "semantic": {
                "path": str(SEMANTIC_ARTIFACT),
                "sha256": sha256_file(SEMANTIC_ARTIFACT),
            },
            "origin": {
                "path": str(ORIGIN_ARTIFACT),
                "sha256": sha256_file(ORIGIN_ARTIFACT),
            },
            "first_insertion": {
                "path": str(FIRST_INSERTION_ARTIFACT),
                "sha256": sha256_file(FIRST_INSERTION_ARTIFACT),
            },
            "cmc_identity": {
                "path": str(CMC_IDENTITY_ARTIFACT),
                "sha256": sha256_file(CMC_IDENTITY_ARTIFACT),
            },
        },
        "database_inventory": {
            "table_count": len(tables),
            "tables": sorted(tables),
        },
        "target_results": results,
        "summary": {
            "target_count": len(results),
            "expected_universe_members": expected_members,
            "outside_expected_universe": outside_expected,
            "cmc_identified_targets": cmc_identified,
        },
        "forensic_status": forensic_status,
        "predictive_claim": "NOT ESTABLISHED",
        "relationship_calculation": "NOT PERFORMED",
        "database_write": "NOT PERFORMED",
        "database_repair": "NOT PERFORMED",
    }

    # Explicitly convert all non-JSON-safe values.
    canonical = json.dumps(
        artifact,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")

    artifact_sha256 = hashlib.sha256(canonical).hexdigest()

    artifact["artifact_sha256"] = artifact_sha256

    with open(
        OUTPUT_ARTIFACT,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            artifact,
            f,
            ensure_ascii=False,
            indent=2,
            default=str,
        )

    print("=" * 90)
    print("ARTIFACT")
    print("=" * 90)
    print(f"Artifact : {OUTPUT_ARTIFACT}")
    print(f"SHA256   : {artifact_sha256}")
    print("=" * 90)


if __name__ == "__main__":
    main()