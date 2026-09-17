import json
import hashlib
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

ARTIFACT_PATH = PROJECT_ROOT / (
    "LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_REPORT.json"
)

OUTPUT_REPORT = PROJECT_ROOT / (
    "ARUNDA_TRADER_ARTIFACT_PRODUCER_CONTRACT_FORENSICS_REPORT.json"
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def type_name(value: Any) -> str:
    return type(value).__name__


def describe_value(
    value: Any,
    depth: int = 0,
    max_depth: int = 8,
) -> Any:
    if depth >= max_depth:
        return {
            "type": type_name(value),
            "truncated": True,
        }

    if isinstance(value, dict):
        result = {}

        for key, item in value.items():
            result[str(key)] = describe_value(
                item,
                depth + 1,
                max_depth,
            )

        return result

    if isinstance(value, list):
        result = {
            "type": "list",
            "length": len(value),
        }

        if value:
            result["item_types"] = sorted(
                {
                    type_name(item)
                    for item in value
                }
            )

            result["first_item"] = describe_value(
                value[0],
                depth + 1,
                max_depth,
            )

        return result

    return {
        "type": type_name(value),
        "value": value,
    }


def print_separator(title: str):
    print("=" * 80)
    print(title)
    print("=" * 80)


def print_tree(
    obj: Any,
    prefix: str = "",
    depth: int = 0,
    max_depth: int = 12,
):
    if depth > max_depth:
        print(f"{prefix}<MAX_DEPTH>")
        return

    if isinstance(obj, dict):
        if not obj:
            print(f"{prefix}{{}}")
            return

        for key, value in obj.items():
            print(
                f"{prefix}{key} "
                f"[{type_name(value)}]"
            )

            print_tree(
                value,
                prefix + "    ",
                depth + 1,
                max_depth,
            )

        return

    if isinstance(obj, list):
        print(
            f"{prefix}<list length={len(obj)}>"
        )

        if not obj:
            return

        for index, item in enumerate(
            obj[:5]
        ):
            print(
                f"{prefix}[{index}] "
                f"[{type_name(item)}]"
            )

            print_tree(
                item,
                prefix + "    ",
                depth + 1,
                max_depth,
            )

        if len(obj) > 5:
            print(
                f"{prefix}... "
                f"{len(obj) - 5} more items"
            )

        return

    print(
        f"{prefix}{repr(obj)}"
    )


def find_key_paths(
    obj: Any,
    target_keys,
    current_path="",
):
    matches = []

    if isinstance(obj, dict):
        for key, value in obj.items():
            key_string = str(key)

            path = (
                f"{current_path}.{key_string}"
                if current_path
                else key_string
            )

            if key_string in target_keys:
                matches.append(
                    {
                        "path": path,
                        "value_type": type_name(value),
                        "value": value,
                    }
                )

            matches.extend(
                find_key_paths(
                    value,
                    target_keys,
                    path,
                )
            )

    elif isinstance(obj, list):
        for index, item in enumerate(obj):
            path = (
                f"{current_path}[{index}]"
                if current_path
                else f"[{index}]"
            )

            matches.extend(
                find_key_paths(
                    item,
                    target_keys,
                    path,
                )
            )

    return matches


def locate_candidate_structures(
    obj: Any,
):
    target_keys = {
        "rows",
        "assets",
        "directions",
        "snapshot_id",
        "verified",
        "eligible_rows",
        "no_trade_rows",
        "decision",
        "artifact",
        "summary",
        "report",
        "data",
        "signals",
        "records",
        "results",
    }

    return find_key_paths(
        obj,
        target_keys,
    )


def inspect_rows(
    rows: Any,
):
    result = {
        "exists": isinstance(rows, list),
        "type": type_name(rows),
        "count": (
            len(rows)
            if isinstance(rows, list)
            else None
        ),
        "row_shapes": [],
    }

    if not isinstance(rows, list):
        return result

    for index, row in enumerate(rows):
        if index >= 10:
            break

        if isinstance(row, dict):
            result["row_shapes"].append(
                {
                    "index": index,
                    "keys": list(row.keys()),
                    "types": {
                        str(k): type_name(v)
                        for k, v in row.items()
                    },
                    "values": row,
                }
            )
        else:
            result["row_shapes"].append(
                {
                    "index": index,
                    "type": type_name(row),
                    "value": row,
                }
            )

    return result


def build_report(
    artifact: Any,
    file_sha256: str,
):
    report = {
        "forensic": {
            "project": "ARUNDA TRADER",
            "component": (
                "ARTIFACT PRODUCER/CONSUMER "
                "CONTRACT FORENSICS"
            ),
            "version": "v0.1",
            "mode": "READ_ONLY",
            "producer_execution": False,
            "producer_import": False,
            "production_db_write": False,
            "network_access": False,
            "exchange_access": False,
            "order_creation": False,
            "order_submission": False,
            "artifact_mutation": False,
        },
        "source": {
            "path": str(ARTIFACT_PATH),
            "exists": ARTIFACT_PATH.exists(),
            "sha256": file_sha256,
            "root_type": type_name(artifact),
        },
        "root_schema": describe_value(
            artifact
        ),
        "candidate_key_paths": (
            locate_candidate_structures(
                artifact
            )
        ),
    }

    return report


def main():
    print_separator(
        "ARUNDA TRADER"
    )

    print(
        "ARTIFACT PRODUCER/CONSUMER "
        "CONTRACT FORENSICS v0.1"
    )

    print_separator(
        "SAFETY"
    )

    print(
        "MODE                : READ_ONLY"
    )
    print(
        "PRODUCER EXECUTION  : False"
    )
    print(
        "PRODUCER IMPORT     : False"
    )
    print(
        "DATABASE WRITE      : False"
    )
    print(
        "NETWORK ACCESS      : False"
    )
    print(
        "EXCHANGE ACCESS     : False"
    )
    print(
        "ORDER CREATION      : False"
    )
    print(
        "ORDER SUBMISSION    : False"
    )
    print(
        "ARTIFACT MUTATION   : False"
    )

    print_separator(
        "SOURCE"
    )

    print(
        f"PROJECT ROOT : {PROJECT_ROOT}"
    )

    print(
        f"ARTIFACT    : {ARTIFACT_PATH}"
    )

    print(
        f"OUTPUT      : {OUTPUT_REPORT}"
    )

    if not ARTIFACT_PATH.exists():
        raise FileNotFoundError(
            f"Artifact not found: "
            f"{ARTIFACT_PATH}"
        )

    file_sha256 = sha256_file(
        ARTIFACT_PATH
    )

    artifact = load_json(
        ARTIFACT_PATH
    )

    print_separator(
        "FILE IDENTITY"
    )

    print(
        f"SHA256 : {file_sha256}"
    )

    print(
        f"ROOT TYPE : "
        f"{type_name(artifact)}"
    )

    print_separator(
        "ACTUAL JSON ROOT KEYS"
    )

    if isinstance(artifact, dict):
        for key, value in artifact.items():
            print(
                f"{key} "
                f"[{type_name(value)}]"
            )
    else:
        print(
            "JSON root is not an object."
        )

    print_separator(
        "FULL SCHEMA TREE"
    )

    print_tree(
        artifact
    )

    print_separator(
        "KEY PATH FORENSICS"
    )

    candidates = locate_candidate_structures(
        artifact
    )

    if not candidates:
        print(
            "No target contract keys found."
        )
    else:
        for item in candidates:
            print(
                f"PATH : {item['path']}"
            )

            print(
                f"TYPE : "
                f"{item['value_type']}"
            )

            print(
                f"VALUE: "
                f"{repr(item['value'])}"
            )

            print("-" * 80)

    print_separator(
        "ROWS FORENSICS"
    )

    row_matches = find_key_paths(
        artifact,
        {"rows"},
    )

    if not row_matches:
        print(
            "NO rows KEY FOUND."
        )

    for match in row_matches:
        print(
            f"ROWS PATH : {match['path']}"
        )

        rows_info = inspect_rows(
            match["value"]
        )

        print(
            json.dumps(
                rows_info,
                indent=2,
                ensure_ascii=False,
            )
        )

    print_separator(
        "ASSET / DIRECTION / SNAPSHOT / VERIFIED"
    )

    target_keys = {
        "assets",
        "directions",
        "snapshot_id",
        "verified",
        "eligible_rows",
        "no_trade_rows",
        "decision",
    }

    semantic_matches = find_key_paths(
        artifact,
        target_keys,
    )

    if not semantic_matches:
        print(
            "NO SEMANTIC CONTRACT KEYS FOUND."
        )

    for match in semantic_matches:
        print(
            f"{match['path']} "
            f"[{match['value_type']}] = "
            f"{repr(match['value'])}"
        )

    print_separator(
        "NESTED STRUCTURE INSPECTION"
    )

    if isinstance(artifact, dict):
        for key, value in artifact.items():
            if isinstance(value, dict):
                print(
                    f"\nROOT.{key}"
                )

                print_tree(
                    value,
                    prefix="    ",
                    depth=1,
                    max_depth=8,
                )

    report = build_report(
        artifact,
        file_sha256,
    )

    OUTPUT_REPORT.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print_separator(
        "FORENSIC RESULT"
    )

    print(
        "Artifact loaded       : True"
    )

    print(
        "Producer executed     : False"
    )

    print(
        "Artifact mutated      : False"
    )

    print(
        "Contract modified     : False"
    )

    print(
        f"REPORT WRITTEN        : "
        f"{OUTPUT_REPORT}"
    )

    print_separator(
        "NEXT ACTION"
    )

    print(
        "SEND THE COMPLETE "
        "TERMINAL OUTPUT."
    )

    print(
        "DO NOT MODIFY THE "
        "ARTIFACT JSON."
    )


if __name__ == "__main__":
    main()