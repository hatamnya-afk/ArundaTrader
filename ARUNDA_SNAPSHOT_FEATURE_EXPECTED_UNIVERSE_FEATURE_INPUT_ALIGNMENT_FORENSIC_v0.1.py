import sqlite3
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone


SCRIPT_VERSION = "ARUNDA_SNAPSHOT_FEATURE_EXPECTED_UNIVERSE_FEATURE_INPUT_ALIGNMENT_FORENSIC_v0.1"

BASE_DIR = Path(r"C:\Users\ASUS\ArundaTrader")
DB_PATH = BASE_DIR / "arunda.db"

NORMALIZATION_ARTIFACT = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_EXPECTED_UNIVERSE_NORMALIZATION_FORENSIC_v0.1.json"
)

ALIGNMENT_ARTIFACT = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_EXPECTED_UNIVERSE_MARKET_HISTORY_ALIGNMENT_FORENSIC_v0.2.json"
)

OUTPUT_ARTIFACT = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_EXPECTED_UNIVERSE_FEATURE_INPUT_ALIGNMENT_FORENSIC_v0.1.json"
)

NETWORK = "FORBIDDEN"
DATABASE_WRITE = "FORBIDDEN"
PREDICTION = "FORBIDDEN"
DECISION = "FORBIDDEN"
MODE = "READ ONLY"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize_symbols(values):
    result = set()

    for value in values:
        if value is None:
            continue

        value = str(value).strip()

        if not value:
            continue

        result.add(value)

    return sorted(result)


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_table_columns(conn, table_name):
    rows = conn.execute(
        f'PRAGMA table_info("{table_name}")'
    ).fetchall()

    return [row[1] for row in rows]


def table_exists(conn, table_name):
    row = conn.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        LIMIT 1
        """,
        (table_name,),
    ).fetchone()

    return row is not None


def discover_symbol_columns(conn):
    inventory = []

    rows = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name
        """
    ).fetchall()

    for (table_name,) in rows:

        columns = get_table_columns(conn, table_name)

        preferred = []

        for column in columns:
            c = column.lower()

            if c in {
                "symbol",
                "asset",
                "asset_symbol",
                "asset_symbols",
            }:
                preferred.append(column)

        for column in preferred:

            try:
                rows2 = conn.execute(
                    f'''
                    SELECT DISTINCT "{column}"
                    FROM "{table_name}"
                    WHERE "{column}" IS NOT NULL
                    '''
                ).fetchall()

                symbols = normalize_symbols(
                    row[0] for row in rows2
                )

            except Exception:
                symbols = []

            inventory.append(
                {
                    "table": table_name,
                    "column": column,
                    "symbols": symbols,
                    "count": len(symbols),
                }
            )

    return inventory


def compare(expected, observed):

    expected_set = set(expected)
    observed_set = set(observed)

    missing = sorted(expected_set - observed_set)
    extra = sorted(observed_set - expected_set)
    covered = sorted(expected_set & observed_set)

    coverage = (
        (len(covered) / len(expected_set)) * 100
        if expected_set
        else 0.0
    )

    return {
        "expected_count": len(expected),
        "observed_count": len(observed),
        "covered_count": len(covered),
        "missing_count": len(missing),
        "extra_count": len(extra),
        "coverage_pct": coverage,
        "exact_match": not missing and not extra,
        "missing_symbols": missing,
        "extra_symbols": extra,
    }


def main():

    print("=" * 90)
    print(
        "ARUNDA SNAPSHOT FEATURE -> EXPECTED UNIVERSE "
        "FEATURE INPUT ALIGNMENT FORENSIC v0.1"
    )
    print("=" * 90)
    print(f"Database        : {DB_PATH}")
    print(f"Normalization   : {NORMALIZATION_ARTIFACT}")
    print(f"History Align   : {ALIGNMENT_ARTIFACT}")
    print(f"Mode            : {MODE}")
    print(f"Network         : {NETWORK}")
    print(f"Database Write  : {DATABASE_WRITE}")
    print(f"Prediction      : {PREDICTION}")
    print(f"Decision        : {DECISION}")
    print("-" * 90)

    if not NORMALIZATION_ARTIFACT.exists():
        print("NORMALIZATION ARTIFACT NOT FOUND")
        return

    normalization = load_json(NORMALIZATION_ARTIFACT)

    normalized = normalize_symbols(
        normalization.get(
            "normalized_expected_universe",
            []
        )
    )

    if not normalized:
        print("EXPECTED UNIVERSE COULD NOT BE RESOLVED")
        return

    normalization_hash = sha256_file(NORMALIZATION_ARTIFACT)

    print("=" * 90)
    print("EXPECTED UNIVERSE INPUT")
    print("=" * 90)
    print(
        f"Artifact SHA256 : {normalization_hash}"
    )
    print(
        f"Resolved source : normalized_expected_universe"
    )
    print(
        f"Expected Universe : {len(normalized)}"
    )

    conn = sqlite3.connect(
        f"file:{DB_PATH}?mode=ro",
        uri=True,
    )

    try:

        inventory = discover_symbol_columns(conn)

        print("=" * 90)
        print("FEATURE INPUT CANDIDATE INVENTORY")
        print("=" * 90)

        comparisons = []

        for item in inventory:

            comparison = compare(
                normalized,
                item["symbols"],
            )

            comparisons.append(
                {
                    "source": (
                        f'DATABASE_TABLE:'
                        f'{item["table"]}:'
                        f'{item["column"]}'
                    ),
                    "table": item["table"],
                    "column": item["column"],
                    "symbol_count": item["count"],
                    "comparison": comparison,
                }
            )

            print("-" * 90)
            print(
                f'SOURCE : DATABASE_TABLE:{item["table"]}:{item["column"]}'
            )
            print(
                f'SYMBOL COUNT : {item["count"]}'
            )
            print(
                f'FEATURE INTERSECTION : '
                f'{comparison["covered_count"]}'
            )
            print(
                f'FEATURE COVERAGE : '
                f'{comparison["coverage_pct"]:.4f}%'
            )
            print(
                f'MISSING : {comparison["missing_count"]}'
            )
            print(
                f'EXTRA : {comparison["extra_count"]}'
            )
            print(
                f'EXACT MATCH : '
                f'{comparison["exact_match"]}'
            )

        print("=" * 90)
        print("PRIMARY FEATURE INPUT ALIGNMENT")
        print("=" * 90)

        # The feature-input layer is expected to consume the
        # normalized expected universe through market_history.
        #
        # We therefore verify the complete normalized universe
        # against market_history without modifying the database.

        market_history = normalize_symbols(
            next(
                (
                    item["symbols"]
                    for item in inventory
                    if item["table"] == "market_history"
                    and item["column"].lower() == "symbol"
                ),
                [],
            )
        )

        if not market_history:

            print("MARKET_HISTORY SYMBOL INPUT NOT FOUND")

            primary = {
                "source": "DATABASE_TABLE:market_history:symbol",
                "status": "NOT_AVAILABLE",
                "comparison": None,
            }

            forensic_status = (
                "EXPECTED_UNIVERSE_FEATURE_INPUT_ALIGNMENT_UNRESOLVED"
            )

        else:

            primary_comparison = compare(
                normalized,
                market_history,
            )

            primary = {
                "source": "DATABASE_TABLE:market_history:symbol",
                "status": "AVAILABLE",
                "comparison": primary_comparison,
            }

            print(
                f"Expected symbols : "
                f'{primary_comparison["expected_count"]}'
            )
            print(
                f"Market History symbols : "
                f'{primary_comparison["observed_count"]}'
            )
            print(
                f"Covered symbols : "
                f'{primary_comparison["covered_count"]}'
            )
            print(
                f"Missing : "
                f'{primary_comparison["missing_count"]}'
            )
            print(
                f"Extra : "
                f'{primary_comparison["extra_count"]}'
            )
            print(
                f"Coverage : "
                f'{primary_comparison["coverage_pct"]:.4f}%'
            )
            print(
                f"Exact Match : "
                f'{primary_comparison["exact_match"]}'
            )

            if primary_comparison["missing_count"] == 0:
                forensic_status = (
                    "EXPECTED_UNIVERSE_FEATURE_INPUT_FULLY_AVAILABLE"
                )
            else:
                forensic_status = (
                    "EXPECTED_UNIVERSE_FEATURE_INPUT_GAP_DETECTED"
                )

        print("=" * 90)
        print("FEATURE INPUT DECISION")
        print("=" * 90)

        if primary["status"] == "AVAILABLE":

            if primary["comparison"]["missing_count"] == 0:

                print(
                    "EXPECTED UNIVERSE FULLY PRESENT IN "
                    "FEATURE INPUT SOURCE : True"
                )

                print(
                    "FEATURE INPUT GAP : 0"
                )

                print(
                    "FEATURE INPUT EXTRA SYMBOLS : "
                    f'{primary["comparison"]["extra_count"]}'
                )

            else:

                print(
                    "EXPECTED UNIVERSE FULLY PRESENT IN "
                    "FEATURE INPUT SOURCE : False"
                )

                print(
                    "FEATURE INPUT GAP : "
                    f'{primary["comparison"]["missing_count"]}'
                )

        print("=" * 90)
        print("FORENSIC STATUS")
        print("=" * 90)

        print(
            f"FORENSIC STATUS : {forensic_status}"
        )
        print(
            "PREDICTIVE CLAIM : NOT ESTABLISHED"
        )
        print(
            "RELATIONSHIP CALCULATION : NOT PERFORMED"
        )
        print(
            "DATABASE WRITE : NOT PERFORMED"
        )
        print(
            "DATABASE REPAIR : NOT PERFORMED"
        )

        artifact = {
            "script_version": SCRIPT_VERSION,
            "generated_at_utc": datetime.now(
                timezone.utc
            ).isoformat(),

            "database": str(DB_PATH),

            "normalization_artifact": str(
                NORMALIZATION_ARTIFACT
            ),

            "normalization_artifact_sha256": (
                normalization_hash
            ),

            "alignment_artifact": str(
                ALIGNMENT_ARTIFACT
            ),

            "mode": MODE,
            "network": NETWORK,
            "database_write": DATABASE_WRITE,
            "prediction": PREDICTION,
            "decision": DECISION,

            "expected_universe": {
                "source": "normalized_expected_universe",
                "count": len(normalized),
                "symbols": normalized,
            },

            "feature_input_inventory": comparisons,

            "primary_feature_input": primary,

            "forensic_constraints": {
                "network": "FORBIDDEN",
                "database_write": "FORBIDDEN",
                "prediction": "FORBIDDEN",
                "decision": "FORBIDDEN",
                "synthetic_data": "FORBIDDEN",
                "interpolation": "FORBIDDEN",
                "forward_fill": "FORBIDDEN",
                "back_fill": "FORBIDDEN",
            },

            "predictive_claim": "NOT ESTABLISHED",
            "relationship_calculation": "NOT PERFORMED",
            "database_repair": "NOT PERFORMED",

            "forensic_status": forensic_status,
        }

        # Artifact is the only file write.
        # Database remains strictly read-only.
        payload = json.dumps(
            artifact,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )

        OUTPUT_ARTIFACT.write_text(
            payload,
            encoding="utf-8",
        )

        artifact_hash = sha256_file(
            OUTPUT_ARTIFACT
        )

        print(
            f"Expected Universe : {len(normalized)}"
        )
        print(
            f"Artifact : {OUTPUT_ARTIFACT}"
        )
        print(
            f"SHA256 : {artifact_hash}"
        )

    finally:
        conn.close()


if __name__ == "__main__":
    main()