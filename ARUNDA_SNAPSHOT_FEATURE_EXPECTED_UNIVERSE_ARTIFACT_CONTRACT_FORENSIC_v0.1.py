import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone


# =============================================================================
# ARUNDA SNAPSHOT FEATURE -> EXPECTED UNIVERSE ARTIFACT CONTRACT FORENSIC v0.1
# =============================================================================

BASE_DIR = r"C:\Users\ASUS\ArundaTrader"

DB_PATH = os.path.join(BASE_DIR, "arunda.db")

RESOLUTION_PATH = os.path.join(
    BASE_DIR,
    "ARUNDA_SNAPSHOT_FEATURE_EXPECTED_UNIVERSE_RESOLUTION_FORENSIC_v0.1.json",
)

PROVENANCE_PATH = os.path.join(
    BASE_DIR,
    "ARUNDA_SNAPSHOT_FEATURE_EXPECTED_UNIVERSE_PROVENANCE_FORENSIC_v0.1.json",
)

NORMALIZATION_PATH = os.path.join(
    BASE_DIR,
    "ARUNDA_SNAPSHOT_FEATURE_EXPECTED_UNIVERSE_NORMALIZATION_FORENSIC_v0.1.json",
)

OUTPUT_PATH = os.path.join(
    BASE_DIR,
    "ARUNDA_SNAPSHOT_FEATURE_EXPECTED_UNIVERSE_ARTIFACT_CONTRACT_FORENSIC_v0.1.json",
)


MODE = "READ ONLY"
NETWORK = "FORBIDDEN"
DATABASE_WRITE = "FORBIDDEN"
PREDICTION = "FORBIDDEN"
DECISION = "FORBIDDEN"


# =============================================================================
# HELPERS
# =============================================================================

def sha256_text(value):
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()

    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


def load_json(path):
    if not os.path.exists(path):
        return {
            "exists": False,
            "path": path,
            "error": "FILE_NOT_FOUND",
            "data": None,
        }

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return {
            "exists": True,
            "path": path,
            "error": None,
            "data": data,
        }

    except Exception as exc:
        return {
            "exists": True,
            "path": path,
            "error": f"{type(exc).__name__}: {exc}",
            "data": None,
        }


def type_name(value):
    if value is None:
        return "null"

    if isinstance(value, bool):
        return "bool"

    if isinstance(value, dict):
        return "object"

    if isinstance(value, list):
        return "array"

    if isinstance(value, str):
        return "string"

    if isinstance(value, int):
        return "integer"

    if isinstance(value, float):
        return "number"

    return type(value).__name__


def normalize_symbol(value):
    if not isinstance(value, str):
        return None

    value = value.strip()

    if not value:
        return None

    return value.upper()


def looks_like_symbol(value):
    if not isinstance(value, str):
        return False

    value = value.strip()

    if not value:
        return False

    if len(value) > 40:
        return False

    return True


# =============================================================================
# JSON STRUCTURE INSPECTION
# =============================================================================

def inspect_json_structure(data, max_depth=5):
    result = {
        "type": type_name(data),
        "top_level_keys": [],
        "objects": [],
        "arrays": [],
        "candidate_symbol_paths": [],
        "candidate_universe_paths": [],
        "candidate_count_paths": [],
    }

    def walk(value, path, depth):
        if depth > max_depth:
            return

        if isinstance(value, dict):
            for key, child in value.items():

                child_path = (
                    f"{path}.{key}"
                    if path
                    else str(key)
                )

                result["objects"].append({
                    "path": child_path,
                    "key": str(key),
                    "type": type_name(child),
                })

                key_lower = str(key).lower()

                if any(
                    token in key_lower
                    for token in (
                        "symbol",
                        "symbols",
                        "universe",
                        "asset",
                        "assets",
                        "coin",
                        "coins",
                    )
                ):
                    result["candidate_symbol_paths"].append({
                        "path": child_path,
                        "type": type_name(child),
                    })

                if any(
                    token in key_lower
                    for token in (
                        "universe",
                        "expected",
                        "resolved",
                        "normalized",
                    )
                ):
                    result["candidate_universe_paths"].append({
                        "path": child_path,
                        "type": type_name(child),
                    })

                if any(
                    token in key_lower
                    for token in (
                        "count",
                        "total",
                        "size",
                        "number",
                    )
                ):
                    result["candidate_count_paths"].append({
                        "path": child_path,
                        "type": type_name(child),
                    })

                walk(child, child_path, depth + 1)

        elif isinstance(value, list):
            result["arrays"].append({
                "path": path,
                "length": len(value),
                "sample_types": [
                    type_name(x)
                    for x in value[:10]
                ],
            })

            walk_list_for_symbols(
                value,
                path,
                result,
            )

            for index, child in enumerate(value[:100]):
                child_path = f"{path}[{index}]"

                walk(
                    child,
                    child_path,
                    depth + 1,
                )

    def walk_list_for_symbols(value, path, result_obj):
        if not value:
            return

        string_items = [
            x.strip()
            for x in value
            if isinstance(x, str)
            and x.strip()
        ]

        if not string_items:
            return

        plausible = [
            x
            for x in string_items
            if looks_like_symbol(x)
        ]

        if len(plausible) >= 3:
            normalized = sorted(
                set(
                    normalize_symbol(x)
                    for x in plausible
                    if normalize_symbol(x) is not None
                )
            )

            result_obj["candidate_symbol_paths"].append({
                "path": path,
                "type": "array",
                "array_length": len(value),
                "string_count": len(string_items),
                "plausible_symbol_count": len(plausible),
                "normalized_unique_count": len(normalized),
                "sample": normalized[:20],
            })

    if isinstance(data, dict):
        result["top_level_keys"] = [
            str(k)
            for k in data.keys()
        ]

    walk(data, "", 0)

    return result


# =============================================================================
# DEEP SYMBOL DISCOVERY
# =============================================================================

def discover_symbol_lists(data):
    candidates = []

    def walk(value, path, parent_key=None):

        if isinstance(value, dict):

            for key, child in value.items():
                child_path = (
                    f"{path}.{key}"
                    if path
                    else str(key)
                )

                walk(
                    child,
                    child_path,
                    str(key),
                )

        elif isinstance(value, list):

            strings = [
                x.strip()
                for x in value
                if isinstance(x, str)
                and x.strip()
            ]

            if len(strings) >= 3:

                normalized = sorted(
                    set(
                        normalize_symbol(x)
                        for x in strings
                        if normalize_symbol(x) is not None
                    )
                )

                key_lower = (
                    parent_key.lower()
                    if parent_key
                    else ""
                )

                score = 0

                if any(
                    token in key_lower
                    for token in (
                        "symbol",
                        "symbols",
                        "universe",
                        "asset",
                        "assets",
                        "coin",
                        "coins",
                    )
                ):
                    score += 10

                if len(normalized) >= 10:
                    score += 5

                candidates.append({
                    "path": path,
                    "parent_key": parent_key,
                    "raw_count": len(strings),
                    "unique_count": len(normalized),
                    "symbols": normalized,
                    "score": score,
                })

    walk(data, "")

    candidates.sort(
        key=lambda x: (
            x["score"],
            x["unique_count"],
        ),
        reverse=True,
    )

    return candidates


# =============================================================================
# DATABASE INVENTORY
# =============================================================================

def database_inventory(conn):
    tables = []

    rows = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
        ORDER BY name
        """
    ).fetchall()

    for row in rows:
        table_name = row[0]

        columns = conn.execute(
            f'PRAGMA table_info("{table_name}")'
        ).fetchall()

        column_names = [
            column[1]
            for column in columns
        ]

        symbol_columns = [
            column
            for column in column_names
            if column.lower() in (
                "symbol",
                "asset",
                "ticker",
            )
            or "symbol" in column.lower()
            or column.lower() == "asset"
        ]

        tables.append({
            "table": table_name,
            "columns": column_names,
            "candidate_symbol_columns": symbol_columns,
        })

    return tables


def database_symbol_inventory(conn):
    result = []

    tables = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
        ORDER BY name
        """
    ).fetchall()

    for row in tables:

        table_name = row[0]

        columns = conn.execute(
            f'PRAGMA table_info("{table_name}")'
        ).fetchall()

        for column in columns:

            column_name = column[1]

            if not (
                column_name.lower() == "symbol"
                or column_name.lower() == "asset"
                or "symbol" in column_name.lower()
            ):
                continue

            try:

                rows = conn.execute(
                    f'''
                    SELECT DISTINCT "{column_name}"
                    FROM "{table_name}"
                    WHERE "{column_name}" IS NOT NULL
                    '''
                ).fetchall()

                symbols = sorted(
                    set(
                        normalize_symbol(row[0])
                        for row in rows
                        if normalize_symbol(row[0])
                    )
                )

                result.append({
                    "source": (
                        f"DATABASE_TABLE:{table_name}:"
                        f"{column_name}"
                    ),
                    "table": table_name,
                    "column": column_name,
                    "count": len(symbols),
                    "symbols": symbols,
                })

            except Exception as exc:

                result.append({
                    "source": (
                        f"DATABASE_TABLE:{table_name}:"
                        f"{column_name}"
                    ),
                    "table": table_name,
                    "column": column_name,
                    "count": 0,
                    "symbols": [],
                    "error": (
                        f"{type(exc).__name__}: {exc}"
                    ),
                })

    return result


# =============================================================================
# CROSS ARTIFACT COMPARISON
# =============================================================================

def compare_symbol_sets(a, b):
    a_set = set(a)
    b_set = set(b)

    intersection = sorted(a_set & b_set)
    missing = sorted(a_set - b_set)
    extra = sorted(b_set - a_set)

    coverage = (
        len(intersection) / len(a_set) * 100
        if a_set
        else 0.0
    )

    return {
        "expected_count": len(a_set),
        "covered_count": len(intersection),
        "missing_count": len(missing),
        "extra_count": len(extra),
        "coverage_percent": round(coverage, 4),
        "missing": missing,
        "extra": extra,
        "exact_match": (
            len(missing) == 0
            and len(extra) == 0
        ),
    }


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("=" * 90)
    print(
        "ARUNDA SNAPSHOT FEATURE -> "
        "EXPECTED UNIVERSE ARTIFACT CONTRACT FORENSIC v0.1"
    )
    print("=" * 90)

    print(f"Database       : {DB_PATH}")
    print(f"Resolution     : {RESOLUTION_PATH}")
    print(f"Provenance     : {PROVENANCE_PATH}")
    print(f"Normalization  : {NORMALIZATION_PATH}")
    print(f"Mode           : {MODE}")
    print(f"Network        : {NETWORK}")
    print(f"Database Write : {DATABASE_WRITE}")
    print(f"Prediction     : {PREDICTION}")
    print(f"Decision       : {DECISION}")

    print("-" * 90)

    artifacts = {
        "resolution": load_json(
            RESOLUTION_PATH
        ),
        "provenance": load_json(
            PROVENANCE_PATH
        ),
        "normalization": load_json(
            NORMALIZATION_PATH
        ),
    }

    artifact_report = {}

    for name, artifact in artifacts.items():

        print("=" * 90)
        print(
            f"{name.upper()} ARTIFACT CONTRACT"
        )
        print("=" * 90)

        if not artifact["exists"]:

            print("FILE STATUS : NOT FOUND")

            artifact_report[name] = {
                "exists": False,
                "path": artifact["path"],
                "error": artifact["error"],
            }

            continue

        if artifact["error"]:

            print("FILE STATUS : READ ERROR")
            print(
                f"ERROR : {artifact['error']}"
            )

            artifact_report[name] = {
                "exists": True,
                "path": artifact["path"],
                "error": artifact["error"],
            }

            continue

        data = artifact["data"]

        structure = inspect_json_structure(
            data
        )

        symbol_candidates = discover_symbol_lists(
            data
        )

        print(
            f"FILE STATUS : VALID JSON"
        )

        print(
            f"ROOT TYPE : {type_name(data)}"
        )

        print(
            "TOP LEVEL KEYS :"
        )

        for key in structure[
            "top_level_keys"
        ]:
            print(
                f"  {key}"
            )

        print("-" * 90)
        print(
            "SYMBOL / UNIVERSE CANDIDATE PATHS"
        )

        if not symbol_candidates:

            print(
                "  NONE FOUND"
            )

        else:

            for candidate in symbol_candidates[:20]:

                print(
                    f"  PATH : {candidate['path']}"
                )

                print(
                    f"  PARENT KEY : "
                    f"{candidate['parent_key']}"
                )

                print(
                    f"  RAW COUNT : "
                    f"{candidate['raw_count']}"
                )

                print(
                    f"  UNIQUE COUNT : "
                    f"{candidate['unique_count']}"
                )

                print(
                    f"  SCORE : "
                    f"{candidate['score']}"
                )

                print(
                    "  SAMPLE : "
                    + ", ".join(
                        candidate["symbols"][:15]
                    )
                )

                print("-" * 60)

        artifact_report[name] = {
            "exists": True,
            "path": artifact["path"],
            "error": artifact["error"],
            "sha256": sha256_file(
                artifact["path"]
            ),
            "root_type": type_name(data),
            "top_level_keys": structure[
                "top_level_keys"
            ],
            "candidate_symbol_paths": symbol_candidates[:20],
            "structure": structure,
        }

    # =========================================================================
    # DATABASE
    # =========================================================================

    print("=" * 90)
    print("DATABASE SYMBOL INVENTORY")
    print("=" * 90)

    db_inventory = []
    db_symbols = []

    if os.path.exists(DB_PATH):

        conn = sqlite3.connect(
            DB_PATH
        )

        try:

            db_inventory = database_inventory(
                conn
            )

            db_symbols = database_symbol_inventory(
                conn
            )

        finally:

            conn.close()

    else:

        print(
            "DATABASE STATUS : FILE NOT FOUND"
        )

    for item in db_symbols:

        print("-" * 90)
        print(
            f"SOURCE : {item['source']}"
        )
        print(
            f"SYMBOL COUNT : {item['count']}"
        )

        if item["symbols"]:

            print(
                "SAMPLE : "
                + ", ".join(
                    item["symbols"][:20]
                )
            )

    # =========================================================================
    # CONTRACT CROSS-CHECK
    # =========================================================================

    print("=" * 90)
    print("CROSS-ARTIFACT CONTRACT")
    print("=" * 90)

    resolution_candidates = (
        artifact_report
        .get("resolution", {})
        .get("candidate_symbol_paths", [])
    )

    provenance_candidates = (
        artifact_report
        .get("provenance", {})
        .get("candidate_symbol_paths", [])
    )

    normalization_candidates = (
        artifact_report
        .get("normalization", {})
        .get("candidate_symbol_paths", [])
    )

    print(
        "Resolution symbol candidates : "
        f"{len(resolution_candidates)}"
    )

    print(
        "Provenance symbol candidates : "
        f"{len(provenance_candidates)}"
    )

    print(
        "Normalization symbol candidates : "
        f"{len(normalization_candidates)}"
    )

    # =========================================================================
    # BEST CANDIDATE REPORT
    # =========================================================================

    def best_candidate(candidates):

        if not candidates:
            return None

        return candidates[0]

    resolution_best = best_candidate(
        resolution_candidates
    )

    provenance_best = best_candidate(
        provenance_candidates
    )

    normalization_best = best_candidate(
        normalization_candidates
    )

    print("-" * 90)
    print("BEST CANDIDATES")

    for name, candidate in (
        ("RESOLUTION", resolution_best),
        ("PROVENANCE", provenance_best),
        ("NORMALIZATION", normalization_best),
    ):

        if candidate is None:

            print(
                f"{name} : NONE"
            )

        else:

            print(
                f"{name} : {candidate['path']}"
            )

            print(
                f"{name} COUNT : "
                f"{candidate['unique_count']}"
            )

    # =========================================================================
    # CROSS COMPARISON
    # =========================================================================

    comparisons = {}

    if (
        resolution_best
        and provenance_best
    ):

        comparisons[
            "resolution_vs_provenance"
        ] = compare_symbol_sets(
            resolution_best["symbols"],
            provenance_best["symbols"],
        )

    if (
        resolution_best
        and normalization_best
    ):

        comparisons[
            "resolution_vs_normalization"
        ] = compare_symbol_sets(
            resolution_best["symbols"],
            normalization_best["symbols"],
        )

    if (
        provenance_best
        and normalization_best
    ):

        comparisons[
            "provenance_vs_normalization"
        ] = compare_symbol_sets(
            provenance_best["symbols"],
            normalization_best["symbols"],
        )

    print("=" * 90)
    print("CROSS-ARTIFACT SYMBOL COMPARISON")
    print("=" * 90)

    if not comparisons:

        print(
            "NO SYMBOL SET COMPARISON POSSIBLE"
        )

    else:

        for name, comparison in comparisons.items():

            print("-" * 90)
            print(
                f"COMPARISON : {name}"
            )

            print(
                f"EXPECTED : "
                f"{comparison['expected_count']}"
            )

            print(
                f"COVERED : "
                f"{comparison['covered_count']}"
            )

            print(
                f"MISSING : "
                f"{comparison['missing_count']}"
            )

            print(
                f"EXTRA : "
                f"{comparison['extra_count']}"
            )

            print(
                f"COVERAGE : "
                f"{comparison['coverage_percent']:.4f}%"
            )

            print(
                f"EXACT MATCH : "
                f"{comparison['exact_match']}"
            )

    # =========================================================================
    # STATUS
    # =========================================================================

    resolution_exists = (
        artifact_report
        .get("resolution", {})
        .get("exists", False)
    )

    provenance_exists = (
        artifact_report
        .get("provenance", {})
        .get("exists", False)
    )

    normalization_exists = (
        artifact_report
        .get("normalization", {})
        .get("exists", False)
    )

    if not (
        resolution_exists
        and provenance_exists
        and normalization_exists
    ):

        status = (
            "EXPECTED_UNIVERSE_ARTIFACT_CONTRACT_INCOMPLETE"
        )

    elif not resolution_best:

        status = (
            "EXPECTED_UNIVERSE_SYMBOL_ARTIFACT_PATH_UNRESOLVED"
        )

    elif not provenance_best:

        status = (
            "EXPECTED_UNIVERSE_PROVENANCE_SYMBOL_PATH_UNRESOLVED"
        )

    elif not normalization_best:

        status = (
            "EXPECTED_UNIVERSE_NORMALIZATION_SYMBOL_PATH_UNRESOLVED"
        )

    elif all(
        comparison["exact_match"]
        for comparison in comparisons.values()
    ):

        status = (
            "EXPECTED_UNIVERSE_ARTIFACT_CONTRACT_COHERENT"
        )

    else:

        status = (
            "EXPECTED_UNIVERSE_ARTIFACT_CONTRACT_MISMATCH"
        )

    print("=" * 90)
    print("FORENSIC STATUS")
    print("=" * 90)

    print(
        f"FORENSIC STATUS : {status}"
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

    # =========================================================================
    # ARTIFACT
    # =========================================================================

    report = {
        "artifact": (
            "ARUNDA_SNAPSHOT_FEATURE_"
            "EXPECTED_UNIVERSE_ARTIFACT_CONTRACT_FORENSIC_v0.1"
        ),
        "version": "v0.1",
        "generated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),

        "database": DB_PATH,

        "mode": MODE,
        "network": NETWORK,
        "database_write": DATABASE_WRITE,
        "prediction": PREDICTION,
        "decision": DECISION,

        "input_artifacts": artifact_report,

        "database_inventory": db_inventory,

        "database_symbol_inventory": db_symbols,

        "best_symbol_candidates": {
            "resolution": resolution_best,
            "provenance": provenance_best,
            "normalization": normalization_best,
        },

        "cross_artifact_comparisons": comparisons,

        "forensic_status": status,

        "predictive_claim": "NOT ESTABLISHED",
        "relationship_calculation": "NOT PERFORMED",
        "database_write": "NOT PERFORMED",
        "database_repair": "NOT PERFORMED",
    }

    canonical = json.dumps(
        report,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )

    report["report_sha256"] = sha256_text(
        canonical
    )

    with open(
        OUTPUT_PATH,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            report,
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(
        f"Artifact : {OUTPUT_PATH}"
    )

    print(
        f"SHA256   : {report['report_sha256']}"
    )


if __name__ == "__main__":
    main()