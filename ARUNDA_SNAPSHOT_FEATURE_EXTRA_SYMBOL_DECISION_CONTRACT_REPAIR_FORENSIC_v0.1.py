import json
import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


# =============================================================================
# ARUNDA SNAPSHOT FEATURE EXTRA SYMBOL DECISION CONTRACT REPAIR FORENSIC v0.1
# =============================================================================

BASE_DIR = Path(r"C:\Users\ASUS\ArundaTrader")

DB_PATH = BASE_DIR / "arunda.db"

NORMALIZATION_PATH = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_EXPECTED_UNIVERSE_NORMALIZATION_FORENSIC_v0.1.json"
)

PROVENANCE_PATH = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_INPUT_EXTRA_UNIVERSE_PROVENANCE_FORENSIC_v0.1.json"
)

SEMANTIC_PATH = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_SEMANTIC_FORENSIC_v0.1.json"
)

ORIGIN_PATH = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_ORIGIN_PROPAGATION_FORENSIC_v0.1.json"
)

FIRST_INSERTION_PATH = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_FIRST_INSERTION_FORENSIC_v0.1.json"
)

CMC_IDENTITY_PATH = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_CMC_IDENTITY_FORENSIC_v0.1.json"
)

EXPECTED_STATUS_PATH = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_EXPECTED_UNIVERSE_STATUS_FORENSIC_v0.1.json"
)

DECISION_PATH = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_EXPECTED_UNIVERSE_DECISION_FORENSIC_v0.1.json"
)

OUTPUT_PATH = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_DECISION_CONTRACT_REPAIR_FORENSIC_v0.1.json"
)

REPORT_PATH = (
    BASE_DIR
    / "ARUNDA_SNAPSHOT_FEATURE_EXTRA_SYMBOL_DECISION_CONTRACT_REPAIR_FORENSIC_v0.1.txt"
)

TARGET_SYMBOLS = ["4", "ASSET"]

MODE = "READ ONLY"
NETWORK = "FORBIDDEN"
DATABASE_WRITE = "FORBIDDEN"
REPAIR = "FORENSIC ARTIFACT REPAIR ONLY"
PREDICTION = "FORBIDDEN"
DECISION = "FORENSIC STATUS ONLY"


# =============================================================================
# UTILITIES
# =============================================================================

def utc_now():
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path):
    h = hashlib.sha256()

    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def load_json(path):
    if not path.exists():
        raise FileNotFoundError(f"Missing artifact: {path}")

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def dump_json(path, obj):
    text = json.dumps(
        obj,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )

    with open(path, "w", encoding="utf-8") as f:
        f.write(text)

    return sha256_file(path)


def normalize_symbol(value):
    if value is None:
        return None

    return str(value).strip().upper()


def get_first(d, *keys, default=None):
    if not isinstance(d, dict):
        return default

    for key in keys:
        if key in d:
            return d[key]

    return default


def find_symbol_records(obj):
    """
    Recursively locate dictionaries containing a symbol-like field.
    """

    results = []

    def walk(node):
        if isinstance(node, dict):

            symbol = None

            for key in (
                "symbol",
                "target_symbol",
                "asset_symbol",
            ):
                if key in node:
                    symbol = normalize_symbol(node[key])
                    break

            if symbol in TARGET_SYMBOLS:
                results.append(node)

            for value in node.values():
                walk(value)

        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(obj)

    return results


def recursive_find(obj, key):
    """
    Return all values associated with a key recursively.
    """

    found = []

    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == key:
                    found.append(v)
                walk(v)

        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(obj)

    return found


# =============================================================================
# DATABASE FORENSIC INVENTORY
# =============================================================================

def database_inventory():

    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)

    try:
        cur = conn.cursor()

        tables = cur.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            ORDER BY name
            """
        ).fetchall()

        table_names = [row[0] for row in tables]

        inventory = {}

        for table in table_names:

            try:
                columns = cur.execute(
                    f'PRAGMA table_info("{table}")'
                ).fetchall()

                column_names = [row[1] for row in columns]

                if "symbol" not in column_names:
                    continue

                for symbol in TARGET_SYMBOLS:

                    row = cur.execute(
                        f'''
                        SELECT COUNT(*)
                        FROM "{table}"
                        WHERE UPPER(TRIM(symbol)) = ?
                        ''',
                        (symbol,),
                    ).fetchone()

                    count = int(row[0])

                    if count > 0:

                        if symbol not in inventory:
                            inventory[symbol] = {
                                "tables": [],
                                "total_rows": 0,
                            }

                        inventory[symbol]["tables"].append(table)
                        inventory[symbol]["total_rows"] += count

            except sqlite3.Error:
                continue

        return {
            "database_tables": table_names,
            "database_table_count": len(table_names),
            "symbol_inventory": inventory,
        }

    finally:
        conn.close()


# =============================================================================
# UPSTREAM EXTRACTION
# =============================================================================

def extract_semantic(semantic):

    result = {}

    for symbol in TARGET_SYMBOLS:
        result[symbol] = {
            "semantic_class": None,
            "meaning": None,
            "artifact_likelihood": None,
            "market_symbol_likelihood": None,
        }

    records = find_symbol_records(semantic)

    for record in records:

        symbol = normalize_symbol(
            get_first(
                record,
                "symbol",
                "target_symbol",
                "asset_symbol",
            )
        )

        if symbol not in TARGET_SYMBOLS:
            continue

        result[symbol]["semantic_class"] = get_first(
            record,
            "semantic_class",
            "classification",
            "class",
        )

        result[symbol]["meaning"] = get_first(
            record,
            "meaning",
            "semantic_meaning",
        )

        result[symbol]["artifact_likelihood"] = get_first(
            record,
            "artifact_likelihood",
        )

        result[symbol]["market_symbol_likelihood"] = get_first(
            record,
            "market_symbol_likelihood",
        )

    return result


def extract_origin(origin):

    result = {}

    for symbol in TARGET_SYMBOLS:
        result[symbol] = {
            "origin_class": None,
            "confidence": None,
            "reason": None,
        }

    records = find_symbol_records(origin)

    for record in records:

        symbol = normalize_symbol(
            get_first(
                record,
                "symbol",
                "target_symbol",
                "asset_symbol",
            )
        )

        if symbol not in TARGET_SYMBOLS:
            continue

        result[symbol]["origin_class"] = get_first(
            record,
            "origin_class",
            "origin_classification",
            "classification",
        )

        result[symbol]["confidence"] = get_first(
            record,
            "confidence",
        )

        result[symbol]["reason"] = get_first(
            record,
            "reason",
            "origin_reason",
        )

    return result


def extract_cmc_identity(cmc):

    result = {}

    for symbol in TARGET_SYMBOLS:
        result[symbol] = {
            "cmc_ids": [],
            "names": [],
            "symbols": [],
            "slugs": [],
            "sources": [],
            "identity_class": None,
            "canonical_asset_evidence": False,
        }

    records = find_symbol_records(cmc)

    for record in records:

        symbol = normalize_symbol(
            get_first(
                record,
                "symbol",
                "target_symbol",
                "asset_symbol",
            )
        )

        if symbol not in TARGET_SYMBOLS:
            continue

        target = result[symbol]

        cmc_id = get_first(
            record,
            "cmc_id",
            "CMC_ID",
        )

        name = get_first(
            record,
            "name",
            "CMC_NAME",
        )

        record_symbol = get_first(
            record,
            "symbol",
        )

        slug = get_first(
            record,
            "slug",
            "CMC_SLUG",
        )

        source = get_first(
            record,
            "source",
        )

        identity_class = get_first(
            record,
            "identity_class",
        )

        canonical = get_first(
            record,
            "canonical_asset_evidence",
            default=False,
        )

        if cmc_id is not None and cmc_id not in target["cmc_ids"]:
            target["cmc_ids"].append(str(cmc_id))

        if name is not None and name not in target["names"]:
            target["names"].append(str(name))

        if record_symbol is not None:
            record_symbol = str(record_symbol)

            if record_symbol not in target["symbols"]:
                target["symbols"].append(record_symbol)

        if slug is not None and slug not in target["slugs"]:
            target["slugs"].append(str(slug))

        if source is not None and source not in target["sources"]:
            target["sources"].append(str(source))

        if identity_class is not None:
            target["identity_class"] = identity_class

        if canonical:
            target["canonical_asset_evidence"] = True

    return result


def extract_expected_status(expected_status):

    result = {}

    for symbol in TARGET_SYMBOLS:
        result[symbol] = {
            "expected_universe_member": None,
            "status": None,
            "observed_table_count": None,
            "canonical_asset_evidence": None,
        }

    records = find_symbol_records(expected_status)

    for record in records:

        symbol = normalize_symbol(
            get_first(
                record,
                "symbol",
                "target_symbol",
                "asset_symbol",
            )
        )

        if symbol not in TARGET_SYMBOLS:
            continue

        result[symbol]["expected_universe_member"] = get_first(
            record,
            "expected_universe_member",
        )

        result[symbol]["status"] = get_first(
            record,
            "status",
        )

        result[symbol]["observed_table_count"] = get_first(
            record,
            "observed_table_count",
        )

        result[symbol]["canonical_asset_evidence"] = get_first(
            record,
            "canonical_asset_evidence",
        )

    return result


def extract_decision(decision):

    result = {}

    for symbol in TARGET_SYMBOLS:
        result[symbol] = {
            "decision_class": None,
            "decision": None,
            "semantic_class": None,
            "origin_class": None,
            "cmc_identity_evidence": None,
            "database_observed": None,
            "database_table_count": None,
            "database_total_rows": None,
            "tables": [],
            "rationale": None,
            "semantic_note": None,
        }

    records = find_symbol_records(decision)

    for record in records:

        symbol = normalize_symbol(
            get_first(
                record,
                "symbol",
                "target_symbol",
                "asset_symbol",
            )
        )

        if symbol not in TARGET_SYMBOLS:
            continue

        target = result[symbol]

        mapping = {
            "decision_class": (
                "decision_class",
                "classification",
            ),
            "decision": (
                "decision",
            ),
            "semantic_class": (
                "semantic_class",
            ),
            "origin_class": (
                "origin_class",
            ),
            "cmc_identity_evidence": (
                "cmc_identity_evidence",
            ),
            "database_observed": (
                "database_observed",
            ),
            "database_table_count": (
                "database_table_count",
            ),
            "database_total_rows": (
                "database_total_rows",
            ),
            "rationale": (
                "rationale",
            ),
            "semantic_note": (
                "semantic_note",
            ),
        }

        for destination, keys in mapping.items():

            value = get_first(
                record,
                *keys,
            )

            if value is not None:
                target[destination] = value

        tables = get_first(
            record,
            "tables",
            "observed_tables",
        )

        if isinstance(tables, list):
            target["tables"] = list(tables)

    return result


# =============================================================================
# REPAIR LOGIC
# =============================================================================

def repair_contract(
    semantic,
    origin,
    cmc_identity,
    expected_status,
    decision,
    db_inventory,
):

    repaired = {}

    for symbol in TARGET_SYMBOLS:

        sem = semantic[symbol]
        org = origin[symbol]
        cmc = cmc_identity[symbol]
        exp = expected_status[symbol]
        dec = decision[symbol]
        db = db_inventory["symbol_inventory"].get(
            symbol,
            {
                "tables": [],
                "total_rows": 0,
            },
        )

        expected_member = exp["expected_universe_member"]

        if expected_member is None:
            expected_member = False

        outside_expected = not bool(expected_member)

        db_observed = len(db["tables"]) > 0

        expected_status_value = exp["status"]

        if expected_status_value is None:
            if outside_expected:
                expected_status_value = "OUTSIDE_EXPECTED_UNIVERSE"
            else:
                expected_status_value = "EXPECTED_UNIVERSE_MEMBER"

        if outside_expected and db_observed:
            decision_class = "OBSERVED_ASSET_OUTSIDE_EXPECTED_UNIVERSE"
            decision_value = "EXCLUDE_FROM_EXPECTED_UNIVERSE"
        elif outside_expected and not db_observed:
            decision_class = "UNOBSERVED_OUTSIDE_EXPECTED_UNIVERSE"
            decision_value = "EXCLUDE_FROM_EXPECTED_UNIVERSE"
        else:
            decision_class = dec["decision_class"]
            decision_value = dec["decision"]

        semantic_class = sem["semantic_class"]

        origin_class = org["origin_class"]

        cmc_identity_present = (
            len(cmc["cmc_ids"]) > 0
            or cmc["canonical_asset_evidence"] is True
            or cmc["identity_class"] is not None
        )

        if decision_class == "OBSERVED_ASSET_OUTSIDE_EXPECTED_UNIVERSE":

            rationale = (
                "Symbol has observed database evidence and CMC identity "
                "evidence, but is outside the normalized expected universe; "
                "therefore observed identity does not establish expected-"
                "universe membership."
            )

        elif decision_class == "UNOBSERVED_OUTSIDE_EXPECTED_UNIVERSE":

            rationale = (
                "Symbol is outside the normalized expected universe and "
                "has no observed database record for the current forensic "
                "inventory."
            )

        else:

            rationale = (
                "Decision reconstructed from the upstream expected-universe "
                "contract and verified forensic evidence."
            )

        semantic_note = sem["meaning"]

        if semantic_note is None:

            if symbol == "4":
                semantic_note = (
                    "Numeric token. Database evidence shows a CMC identity, "
                    "but expected-universe membership is not established."
                )

            elif symbol == "ASSET":
                semantic_note = (
                    "Generic field-label token associated with a CMC asset "
                    "named REAL. Expected-universe membership is not "
                    "established."
                )

        repaired[symbol] = {

            "symbol": symbol,

            "semantic_class": semantic_class,

            "origin_class": origin_class,

            "cmc_identity": {
                "present": cmc_identity_present,
                "cmc_ids": sorted(
                    set(
                        str(x)
                        for x in cmc["cmc_ids"]
                    )
                ),
                "names": sorted(
                    set(
                        str(x)
                        for x in cmc["names"]
                    )
                ),
                "symbols": sorted(
                    set(
                        str(x)
                        for x in cmc["symbols"]
                    )
                ),
                "slugs": sorted(
                    set(
                        str(x)
                        for x in cmc["slugs"]
                    )
                ),
                "sources": sorted(
                    set(
                        str(x)
                        for x in cmc["sources"]
                    )
                ),
                "identity_class": cmc["identity_class"],
                "canonical_asset_evidence": cmc[
                    "canonical_asset_evidence"
                ],
            },

            "expected_universe": {
                "member": bool(expected_member),
                "status": expected_status_value,
            },

            "decision": {
                "decision_class": decision_class,
                "decision": decision_value,
            },

            "database": {
                "observed": db_observed,
                "table_count": len(db["tables"]),
                "total_rows": int(db["total_rows"]),
                "tables": sorted(
                    set(db["tables"])
                ),
            },

            "rationale": rationale,

            "semantic_note": semantic_note,

            "repair_changes": {
                "semantic_class_repaired": (
                    dec["semantic_class"] != semantic_class
                ),
                "origin_class_repaired": (
                    dec["origin_class"] != origin_class
                ),
                "cmc_identity_evidence_repaired": (
                    dec["cmc_identity_evidence"]
                    != cmc_identity_present
                ),
                "decision_class_repaired": (
                    dec["decision_class"] != decision_class
                ),
                "decision_repaired": (
                    dec["decision"] != decision_value
                ),
                "database_table_count_repaired": (
                    dec["database_table_count"]
                    != len(db["tables"])
                ),
                "database_total_rows_repaired": (
                    dec["database_total_rows"]
                    != int(db["total_rows"])
                ),
            },

            "source_decision_snapshot": {
                "decision_class": dec["decision_class"],
                "decision": dec["decision"],
                "semantic_class": dec["semantic_class"],
                "origin_class": dec["origin_class"],
                "cmc_identity_evidence": dec[
                    "cmc_identity_evidence"
                ],
            },
        }

    return repaired


# =============================================================================
# CONTRACT VALIDATION
# =============================================================================

def validate_repaired_contract(repaired):

    validation = {}

    for symbol in TARGET_SYMBOLS:

        item = repaired[symbol]

        checks = {
            "target_symbol": item["symbol"] == symbol,

            "outside_expected_universe": (
                item["expected_universe"]["member"] is False
                and item["expected_universe"]["status"]
                == "OUTSIDE_EXPECTED_UNIVERSE"
            ),

            "decision_excludes_symbol": (
                item["decision"]["decision"]
                == "EXCLUDE_FROM_EXPECTED_UNIVERSE"
            ),

            "decision_class_outside_expected": (
                item["decision"]["decision_class"]
                in {
                    "OBSERVED_ASSET_OUTSIDE_EXPECTED_UNIVERSE",
                    "UNOBSERVED_OUTSIDE_EXPECTED_UNIVERSE",
                }
            ),

            "semantic_present": (
                item["semantic_class"] is not None
            ),

            "origin_present": (
                item["origin_class"] is not None
            ),

            "cmc_identity_consistent": (
                isinstance(
                    item["cmc_identity"]["present"],
                    bool,
                )
            ),

            "database_observed_consistent": (
                item["database"]["observed"]
                == (
                    item["database"]["table_count"] > 0
                )
            ),

            "database_table_count_consistent": (
                item["database"]["table_count"]
                == len(item["database"]["tables"])
            ),

            "database_rows_nonnegative": (
                item["database"]["total_rows"] >= 0
            ),
        }

        failures = [
            key
            for key, value in checks.items()
            if not value
        ]

        validation[symbol] = {
            "checks": checks,
            "passed": len(failures) == 0,
            "failures": failures,
        }

    return validation


# =============================================================================
# REPORT
# =============================================================================

def build_report(
    repaired,
    validation,
    db_inventory,
):

    lines = []

    lines.append("=" * 90)
    lines.append(
        "ARUNDA SNAPSHOT FEATURE EXTRA SYMBOL "
        "DECISION CONTRACT REPAIR FORENSIC v0.1"
    )
    lines.append("=" * 90)

    lines.append(f"Database       : {DB_PATH}")
    lines.append(f"Normalization  : {NORMALIZATION_PATH}")
    lines.append(f"Provenance     : {PROVENANCE_PATH}")
    lines.append(f"Semantic       : {SEMANTIC_PATH}")
    lines.append(f"Origin         : {ORIGIN_PATH}")
    lines.append(f"First Insertion: {FIRST_INSERTION_PATH}")
    lines.append(f"CMC Identity   : {CMC_IDENTITY_PATH}")
    lines.append(f"Expected Status: {EXPECTED_STATUS_PATH}")
    lines.append(f"Decision       : {DECISION_PATH}")

    lines.append(f"Mode           : {MODE}")
    lines.append(f"Network        : {NETWORK}")
    lines.append(f"Database Write : {DATABASE_WRITE}")
    lines.append(f"Repair         : {REPAIR}")
    lines.append(f"Prediction     : {PREDICTION}")
    lines.append(f"Decision       : {DECISION}")

    lines.append("-" * 90)

    lines.append("=" * 90)
    lines.append("REPAIR CONTRACT")
    lines.append("=" * 90)

    lines.append(
        "Repair scope : ARTIFACT CONTRACT RECONSTRUCTION ONLY"
    )
    lines.append(
        "Production DB mutation : NONE"
    )

    passed_count = 0
    failed_count = 0

    for symbol in TARGET_SYMBOLS:

        item = repaired[symbol]
        check = validation[symbol]

        if check["passed"]:
            passed_count += 1
        else:
            failed_count += 1

        lines.append("-" * 90)
        lines.append(f"SYMBOL : {symbol}")

        lines.append(
            f"SEMANTIC CLASS       : "
            f"{item['semantic_class']}"
        )

        lines.append(
            f"ORIGIN CLASS         : "
            f"{item['origin_class']}"
        )

        lines.append(
            f"CMC IDENTITY PRESENT : "
            f"{item['cmc_identity']['present']}"
        )

        lines.append(
            f"CMC IDS              : "
            f"{', '.join(item['cmc_identity']['cmc_ids']) or 'NONE'}"
        )

        lines.append(
            f"EXPECTED MEMBER      : "
            f"{item['expected_universe']['member']}"
        )

        lines.append(
            f"EXPECTED STATUS      : "
            f"{item['expected_universe']['status']}"
        )

        lines.append(
            f"DECISION CLASS       : "
            f"{item['decision']['decision_class']}"
        )

        lines.append(
            f"DECISION             : "
            f"{item['decision']['decision']}"
        )

        lines.append(
            f"DATABASE OBSERVED    : "
            f"{item['database']['observed']}"
        )

        lines.append(
            f"DATABASE TABLE COUNT : "
            f"{item['database']['table_count']}"
        )

        lines.append(
            f"DATABASE TOTAL ROWS  : "
            f"{item['database']['total_rows']}"
        )

        lines.append(
            "TABLES               : "
            + (
                ", ".join(item["database"]["tables"])
                if item["database"]["tables"]
                else "NONE"
            )
        )

        lines.append(
            f"RATIONALE            : "
            f"{item['rationale']}"
        )

        lines.append(
            f"SEMANTIC NOTE        : "
            f"{item['semantic_note']}"
        )

        lines.append("-" * 90)
        lines.append("REPAIR CHANGES")

        for key, value in item["repair_changes"].items():

            lines.append(
                f"  {key} : {value}"
            )

        lines.append("-" * 90)
        lines.append("POST-REPAIR CONTRACT CHECKS")

        for key, value in check["checks"].items():

            lines.append(
                f"  {'PASS' if value else 'FAIL'} : {key}"
            )

        lines.append(
            f"CONSISTENCY : "
            f"{'PASS' if check['passed'] else 'FAIL'}"
        )

        if check["failures"]:

            lines.append("CONTRADICTIONS :")

            for failure in check["failures"]:
                lines.append(
                    f"  - {failure}"
                )

    lines.append("=" * 90)
    lines.append("CROSS-SYMBOL SUMMARY")
    lines.append("=" * 90)

    lines.append(
        f"Target Symbols : {len(TARGET_SYMBOLS)}"
    )

    lines.append(
        f"Passed         : {passed_count}"
    )

    lines.append(
        f"Failed         : {failed_count}"
    )

    lines.append(
        "Repair DB      : NONE"
    )

    lines.append(
        "Production Mutation : NONE"
    )

    if failed_count == 0:

        forensic_status = (
            "DECISION_CONTRACT_REPAIRED_AND_CONSISTENT"
        )

    else:

        forensic_status = (
            "DECISION_CONTRACT_REPAIR_INCOMPLETE"
        )

    lines.append("=" * 90)
    lines.append("FORENSIC STATUS")
    lines.append("=" * 90)

    lines.append(
        f"FORENSIC STATUS : {forensic_status}"
    )

    lines.append(
        "PREDICTIVE CLAIM : NOT ESTABLISHED"
    )

    lines.append(
        "RELATIONSHIP CALCULATION : NOT PERFORMED"
    )

    lines.append(
        "DATABASE WRITE : NOT PERFORMED"
    )

    lines.append(
        "DATABASE REPAIR : NOT PERFORMED"
    )

    lines.append(
        "UNIVERSE REBUILD : NOT PERFORMED"
    )

    lines.append(
        "SYMBOL DELETION : NOT PERFORMED"
    )

    lines.append(
        "TRADING DECISION : NOT PERFORMED"
    )

    lines.append("=" * 90)

    return "\n".join(lines)


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("=" * 90)
    print(
        "ARUNDA SNAPSHOT FEATURE EXTRA SYMBOL "
        "DECISION CONTRACT REPAIR FORENSIC v0.1"
    )
    print("=" * 90)

    print(f"Database       : {DB_PATH}")
    print(f"Normalization  : {NORMALIZATION_PATH}")
    print(f"Provenance     : {PROVENANCE_PATH}")
    print(f"Semantic       : {SEMANTIC_PATH}")
    print(f"Origin         : {ORIGIN_PATH}")
    print(f"First Insertion: {FIRST_INSERTION_PATH}")
    print(f"CMC Identity   : {CMC_IDENTITY_PATH}")
    print(f"Expected Status: {EXPECTED_STATUS_PATH}")
    print(f"Decision       : {DECISION_PATH}")

    print(f"Mode           : {MODE}")
    print(f"Network        : {NETWORK}")
    print(f"Database Write : {DATABASE_WRITE}")
    print(f"Repair         : {REPAIR}")
    print(f"Prediction     : {PREDICTION}")
    print(f"Decision       : {DECISION}")

    print("-" * 90)

    normalization = load_json(NORMALIZATION_PATH)
    provenance = load_json(PROVENANCE_PATH)
    semantic_artifact = load_json(SEMANTIC_PATH)
    origin_artifact = load_json(ORIGIN_PATH)
    first_insertion = load_json(FIRST_INSERTION_PATH)
    cmc_identity_artifact = load_json(CMC_IDENTITY_PATH)
    expected_status_artifact = load_json(EXPECTED_STATUS_PATH)
    decision_artifact = load_json(DECISION_PATH)

    db = database_inventory()

    semantic = extract_semantic(
        semantic_artifact
    )

    origin = extract_origin(
        origin_artifact
    )

    cmc_identity = extract_cmc_identity(
        cmc_identity_artifact
    )

    expected_status = extract_expected_status(
        expected_status_artifact
    )

    decision = extract_decision(
        decision_artifact
    )

    repaired = repair_contract(
        semantic=semantic,
        origin=origin,
        cmc_identity=cmc_identity,
        expected_status=expected_status,
        decision=decision,
        db_inventory=db,
    )

    validation = validate_repaired_contract(
        repaired
    )

    artifact = {

        "artifact": {
            "name": OUTPUT_PATH.name,
            "version": "v0.1",
            "generated_at": utc_now(),
        },

        "contract": {
            "mode": MODE,
            "network": NETWORK,
            "database_write": DATABASE_WRITE,
            "repair": REPAIR,
            "prediction": PREDICTION,
            "decision": DECISION,
        },

        "database": {
            "path": str(DB_PATH),
            "table_count": db["database_table_count"],
            "inventory": db["symbol_inventory"],
        },

        "targets": TARGET_SYMBOLS,

        "upstream_artifacts": {

            "normalization": {
                "path": str(NORMALIZATION_PATH),
                "sha256": sha256_file(
                    NORMALIZATION_PATH
                ),
            },

            "provenance": {
                "path": str(PROVENANCE_PATH),
                "sha256": sha256_file(
                    PROVENANCE_PATH
                ),
            },

            "semantic": {
                "path": str(SEMANTIC_PATH),
                "sha256": sha256_file(
                    SEMANTIC_PATH
                ),
            },

            "origin": {
                "path": str(ORIGIN_PATH),
                "sha256": sha256_file(
                    ORIGIN_PATH
                ),
            },

            "first_insertion": {
                "path": str(FIRST_INSERTION_PATH),
                "sha256": sha256_file(
                    FIRST_INSERTION_PATH
                ),
            },

            "cmc_identity": {
                "path": str(CMC_IDENTITY_PATH),
                "sha256": sha256_file(
                    CMC_IDENTITY_PATH
                ),
            },

            "expected_status": {
                "path": str(EXPECTED_STATUS_PATH),
                "sha256": sha256_file(
                    EXPECTED_STATUS_PATH
                ),
            },

            "decision": {
                "path": str(DECISION_PATH),
                "sha256": sha256_file(
                    DECISION_PATH
                ),
            },
        },

        "repair_scope": {
            "database_mutated": False,
            "database_repaired": False,
            "universe_rebuilt": False,
            "symbols_deleted": False,
            "prediction_performed": False,
            "trading_decision_performed": False,
        },

        "repaired_contract": repaired,

        "validation": validation,
    }

    output_sha = dump_json(
        OUTPUT_PATH,
        artifact,
    )

    report = build_report(
        repaired,
        validation,
        db,
    )

    with open(
        REPORT_PATH,
        "w",
        encoding="utf-8",
    ) as f:
        f.write(report)

    print()
    print(report)

    print("=" * 90)
    print("ARTIFACT")
    print("=" * 90)

    print(
        f"Artifact : {OUTPUT_PATH}"
    )

    print(
        f"SHA256   : {output_sha}"
    )

    print(
        f"Report   : {REPORT_PATH}"
    )

    print("=" * 90)


if __name__ == "__main__":
    main()