import os
import json
import sqlite3
import hashlib
from datetime import datetime, timezone

DB_PATH = r"C:\Users\ASUS\ArundaTrader\arunda.db"
FEATURE_CONTRACT_PATH = r"C:\Users\ASUS\ArundaTrader\ARUNDA_SNAPSHOT_FEATURE_CONTRACT_v0.1.json"
ARTIFACT_PATH = r"C:\Users\ASUS\ArundaTrader\ARUNDA_SNAPSHOT_FEATURE_SOURCE_SYMBOL_INPUT_FORENSIC_v0.1.json"


def sha256_text(value):
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def normalize(value):
    if value is None:
        return None

    if isinstance(value, str):
        value = value.strip()

        if not value:
            return None

        return value

    return str(value)


def normalize_symbol(value):
    value = normalize(value)

    if value is None:
        return None

    return value.upper()


def parse_timestamp(value):
    if value is None:
        return None

    if isinstance(value, datetime):
        dt = value

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.astimezone(timezone.utc)

    text = str(value).strip()

    if not text:
        return None

    text = text.replace("Z", "+00:00")

    try:
        dt = datetime.fromisoformat(text)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.astimezone(timezone.utc)

    except Exception:
        return None


def load_contract():
    if not os.path.exists(FEATURE_CONTRACT_PATH):
        return False, {}

    with open(
        FEATURE_CONTRACT_PATH,
        "r",
        encoding="utf-8"
    ) as f:
        return True, json.load(f)


def recursive_scan(obj, path="root"):
    results = []

    if isinstance(obj, dict):
        for key, value in obj.items():

            current_path = f"{path}.{key}"
            key_lower = str(key).lower()

            results.append(
                {
                    "path": current_path,
                    "key": str(key),
                    "value": value
                }
            )

            results.extend(
                recursive_scan(
                    value,
                    current_path
                )
            )

    elif isinstance(obj, list):
        for index, value in enumerate(obj):

            current_path = f"{path}[{index}]"

            results.extend(
                recursive_scan(
                    value,
                    current_path
                )
            )

    return results


def extract_symbols(value):
    symbols = set()

    if isinstance(value, str):
        text = value.strip()

        if text:
            symbols.add(text.upper())

        return symbols

    if isinstance(value, list):

        for item in value:
            symbols.update(
                extract_symbols(item)
            )

        return symbols

    if isinstance(value, dict):

        for key, item in value.items():

            key_lower = str(key).lower()

            if (
                "symbol" in key_lower
                or "ticker" in key_lower
                or "asset" in key_lower
            ):
                symbols.update(
                    extract_symbols(item)
                )

        return symbols

    return symbols


def extract_contract_symbols(contract):
    findings = []
    symbols = set()

    scanned = recursive_scan(contract)

    for item in scanned:

        key_lower = item["key"].lower()

        if not (
            "symbol" in key_lower
            or "ticker" in key_lower
            or "asset" in key_lower
            or "universe" in key_lower
        ):
            continue

        found = extract_symbols(
            item["value"]
        )

        if not found:
            continue

        findings.append(
            {
                "path": item["path"],
                "key": item["key"],
                "symbols": sorted(found),
                "count": len(found)
            }
        )

        symbols.update(found)

    return findings, sorted(symbols)


def extract_contract_timestamps(contract):
    timestamps = set()

    scanned = recursive_scan(contract)

    for item in scanned:

        key_lower = item["key"].lower()

        if "timestamp" not in key_lower:
            continue

        value = item["value"]

        values = (
            value
            if isinstance(value, list)
            else [value]
        )

        for candidate in values:

            parsed = parse_timestamp(
                candidate
            )

            if parsed is not None:
                timestamps.add(
                    parsed.isoformat()
                )

    return sorted(timestamps)


def get_tables(conn):
    cursor = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name
        """
    )

    return [
        row[0]
        for row in cursor.fetchall()
    ]


def get_columns(conn, table):
    cursor = conn.execute(
        f'PRAGMA table_info("{table}")'
    )

    return [
        row[1]
        for row in cursor.fetchall()
    ]


def find_symbol_columns(conn, tables):
    results = []

    for table in tables:

        columns = get_columns(
            conn,
            table
        )

        symbol_columns = []

        for column in columns:

            name = column.lower()

            if (
                "symbol" in name
                or "ticker" in name
                or "asset" in name
            ):
                symbol_columns.append(
                    column
                )

        if symbol_columns:

            results.append(
                {
                    "table": table,
                    "symbol_columns": symbol_columns
                }
            )

    return results


def sample_symbols(
    conn,
    table,
    column
):
    values = set()

    try:

        cursor = conn.execute(
            f'''
            SELECT DISTINCT "{column}"
            FROM "{table}"
            WHERE "{column}" IS NOT NULL
            LIMIT 1000
            '''
        )

        for row in cursor.fetchall():

            symbol = normalize_symbol(
                row[0]
            )

            if symbol:
                values.add(symbol)

    except Exception:
        return []

    return sorted(values)


def inspect_database(conn):
    tables = get_tables(conn)

    candidates = find_symbol_columns(
        conn,
        tables
    )

    results = []

    for candidate in candidates:

        table = candidate["table"]

        table_record = {
            "table": table,
            "columns": []
        }

        for column in candidate[
            "symbol_columns"
        ]:

            symbols = sample_symbols(
                conn,
                table,
                column
            )

            table_record["columns"].append(
                {
                    "column": column,
                    "symbol_count": len(symbols),
                    "symbols": symbols
                }
            )

        results.append(
            table_record
        )

    return tables, results


def fingerprint(symbols):
    payload = "|".join(
        sorted(
            normalize_symbol(x)
            for x in symbols
            if normalize_symbol(x)
        )
    )

    return sha256_text(payload)


def main():

    print("=" * 90)
    print(
        "ARUNDA SNAPSHOT FEATURE SOURCE SYMBOL INPUT FORENSIC v0.1"
    )
    print("=" * 90)
    print(
        f"Database        : {DB_PATH}"
    )
    print(
        f"Feature Contract: {FEATURE_CONTRACT_PATH}"
    )
    print("Mode            : READ ONLY")
    print("Network         : FORBIDDEN")
    print("Outcome         : NOT CALCULATED")
    print("Prediction      : FORBIDDEN")
    print("Decision        : FORBIDDEN")
    print("-" * 90)

    contract_exists, contract = load_contract()

    print("=" * 90)
    print("FEATURE CONTRACT")
    print("=" * 90)

    print(
        f"Contract exists : {contract_exists}"
    )

    contract_findings = []
    contract_symbols = []
    contract_timestamps = []

    if contract_exists:

        (
            contract_findings,
            contract_symbols
        ) = extract_contract_symbols(
            contract
        )

        contract_timestamps = (
            extract_contract_timestamps(
                contract
            )
        )

    print(
        "Symbol-bearing paths : "
        f"{len(contract_findings)}"
    )

    print(
        "Contract symbols     : "
        f"{len(contract_symbols)}"
    )

    if contract_symbols:

        print(
            "  "
            + ", ".join(
                contract_symbols
            )
        )

    else:

        print("  NONE")

    print(
        "Contract timestamps  : "
        f"{len(contract_timestamps)}"
    )

    for timestamp in contract_timestamps:
        print(
            f"  {timestamp}"
        )

    conn = sqlite3.connect(
        f"file:{DB_PATH}?mode=ro",
        uri=True
    )

    try:

        tables, database_candidates = (
            inspect_database(conn)
        )

    finally:

        conn.close()

    print("=" * 90)
    print("DATABASE SYMBOL SOURCE CANDIDATES")
    print("=" * 90)

    print(
        f"Tables discovered : {len(tables)}"
    )

    print(
        "Tables containing symbol-like columns : "
        f"{len(database_candidates)}"
    )

    for item in database_candidates:

        print(
            f"TABLE : {item['table']}"
        )

        for column in item["columns"]:

            print(
                f"  COLUMN : {column['column']}"
            )

            print(
                f"  SYMBOL COUNT : "
                f"{column['symbol_count']}"
            )

            if column["symbols"]:

                print(
                    "  SYMBOLS : "
                    + ", ".join(
                        column["symbols"]
                    )
                )

        print("-" * 90)

    established = False
    established_source = None

    if contract_symbols:

        established = True
        established_source = (
            "FEATURE_CONTRACT"
        )

    status = (
        "FEATURE_SYMBOL_SOURCE_ESTABLISHED"
        if established
        else
        "FEATURE_SYMBOL_SOURCE_NOT_ESTABLISHED"
    )

    artifact = {
        "artifact_name": (
            "ARUNDA_SNAPSHOT_FEATURE_SOURCE_SYMBOL_INPUT_FORENSIC_v0.1"
        ),
        "version": "v0.1",
        "mode": "READ ONLY",
        "network": "FORBIDDEN",
        "outcome": "NOT CALCULATED",
        "prediction": "FORBIDDEN",
        "decision": "FORBIDDEN",
        "database": DB_PATH,
        "feature_contract": FEATURE_CONTRACT_PATH,
        "feature_contract_exists": contract_exists,
        "contract_symbol_findings": contract_findings,
        "contract_symbols": contract_symbols,
        "contract_symbol_count": len(
            contract_symbols
        ),
        "contract_symbol_fingerprint": (
            fingerprint(contract_symbols)
            if contract_symbols
            else None
        ),
        "contract_timestamps": contract_timestamps,
        "database_symbol_candidates": (
            database_candidates
        ),
        "feature_symbol_source_established": established,
        "established_source": established_source,
        "forensic_status": status,
        "predictive_claim": "NOT ESTABLISHED",
        "relationship_calculation": "NOT PERFORMED",
    }

    canonical = json.dumps(
        artifact,
        ensure_ascii=False,
        sort_keys=True,
        indent=2
    )

    artifact["sha256"] = sha256_text(
        canonical
    )

    with open(
        ARTIFACT_PATH,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            artifact,
            f,
            ensure_ascii=False,
            indent=2
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
        f"Feature symbols established : "
        f"{len(contract_symbols)}"
    )

    print(
        f"Established source : "
        f"{established_source or 'NONE'}"
    )

    print(
        f"Artifact : {ARTIFACT_PATH}"
    )

    print(
        f"SHA256 : {artifact['sha256']}"
    )


if __name__ == "__main__":
    main()