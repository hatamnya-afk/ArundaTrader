import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone


PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

RUNTIME_PATH = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_LIVE_SIGNAL_EXECUTION_RUNTIME_REPORT.json"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_RUNTIME_CONTRACT_FORENSICS_REPORT.json"
)


# ============================================================================
# SAFETY
# ============================================================================

MODE = "READ_ONLY"

PRODUCER_EXECUTION = False
PRODUCER_IMPORT = False
DATABASE_WRITE = False
NETWORK_ACCESS = False
EXCHANGE_ACCESS = False
ORDER_CREATION = False
ORDER_SUBMISSION = False
ORDER_EXECUTION = False
ARTIFACT_MUTATION = False


# ============================================================================
# HELPERS
# ============================================================================

def sha256_file(path):
    digest = hashlib.sha256()

    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)

    return digest.hexdigest()


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def type_name(value):
    if value is None:
        return "NoneType"

    if isinstance(value, bool):
        return "bool"

    if isinstance(value, int):
        return "int"

    if isinstance(value, float):
        return "float"

    if isinstance(value, str):
        return "str"

    if isinstance(value, list):
        return "list"

    if isinstance(value, dict):
        return "dict"

    return type(value).__name__


def display_value(value, limit=300):
    if isinstance(value, (dict, list)):
        text = json.dumps(
            value,
            ensure_ascii=False,
            default=str,
        )
    else:
        text = repr(value)

    if len(text) > limit:
        return text[:limit] + "...<TRUNCATED>"

    return text


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def print_section(title):
    print("=" * 80)
    print(title)
    print("=" * 80)


def print_kv(key, value):
    print(f"{key:<30}: {value}")


# ============================================================================
# FULL JSON TREE
# ============================================================================

def walk_json(value, path="$", output=None, depth=0):
    if output is None:
        output = []

    node = {
        "path": path,
        "type": type_name(value),
        "depth": depth,
    }

    if isinstance(value, dict):
        node["keys"] = list(value.keys())
        output.append(node)

        for key, child in value.items():
            child_path = f"{path}.{key}"
            walk_json(
                child,
                child_path,
                output,
                depth + 1,
            )

    elif isinstance(value, list):
        node["length"] = len(value)
        output.append(node)

        for index, child in enumerate(value):
            child_path = f"{path}[{index}]"
            walk_json(
                child,
                child_path,
                output,
                depth + 1,
            )

    else:
        node["value"] = value
        output.append(node)

    return output


# ============================================================================
# KEY INDEX
# ============================================================================

def build_key_index(tree):
    index = {}

    for node in tree:
        path = node["path"]

        if path == "$":
            continue

        if "[" in path:
            clean_path = path.split("[")[0]
            leaf = clean_path.split(".")[-1]
        else:
            leaf = path.split(".")[-1]

        if leaf not in index:
            index[leaf] = []

        index[leaf].append(
            {
                "path": path,
                "type": node["type"],
                "value": node.get("value"),
            }
        )

    return index


# ============================================================================
# IMPORTANT KEY FORENSICS
#
# This does NOT decide which key is "correct".
# It simply reports every occurrence.
# ============================================================================

TARGET_KEYS = [
    "runtime_ready",
    "operational_safety",
    "upstream_verified",
    "artifact_verified",
    "verdict_verified",
    "runtime_verified",
    "verdict",
    "contracts_verified",
    "identity_verified",
    "release_verified",
    "execution",
    "orders_created",
    "orders_submitted",
    "producer_execution",
    "producer_import",
    "production_db_write",
    "network_access",
    "order_execution",
    "order_creation",
    "order_submission",
    "artifact_mutation",
    "contract",
    "verified",
]


def inspect_target_keys(tree):
    findings = []

    for node in tree:
        path = node["path"]

        if path == "$":
            continue

        if "[" in path:
            base = path.split("[")[0]
            leaf = base.split(".")[-1]
        else:
            leaf = path.split(".")[-1]

        if leaf in TARGET_KEYS:
            findings.append(
                {
                    "key": leaf,
                    "path": path,
                    "type": node["type"],
                    "value": node.get("value"),
                }
            )

    return findings


# ============================================================================
# DICTIONARY SECTIONS
# ============================================================================

def inspect_dict_sections(runtime):
    sections = []

    if not isinstance(runtime, dict):
        return sections

    for key, value in runtime.items():
        if isinstance(value, dict):
            sections.append(
                {
                    "path": f"$.{key}",
                    "key": key,
                    "type": "dict",
                    "keys": list(value.keys()),
                }
            )

        elif isinstance(value, list):
            sections.append(
                {
                    "path": f"$.{key}",
                    "key": key,
                    "type": "list",
                    "length": len(value),
                }

            )

        else:
            sections.append(
                {
                    "path": f"$.{key}",
                    "key": key,
                    "type": type_name(value),
                    "value": value,
                }
            )

    return sections


# ============================================================================
# SEMANTIC VALUE OCCURRENCES
#
# Again: this is evidence collection only.
# No inference.
# ============================================================================

TARGET_VALUES = {
    "LIVE_SIGNAL_EXECUTION_RUNTIME_READY",
    "LIVE_SIGNAL_EXECUTION_RUNTIME_BLOCKED",
    "LIVE_SIGNAL_EXECUTION_GATE_READY",
    "NOT_EXECUTED",
    "READY",
    "BLOCKED",
    "True",
    "False",
}


def inspect_interesting_values(tree):
    findings = []

    for node in tree:
        if "value" not in node:
            continue

        value = node["value"]

        if isinstance(value, bool):
            value_text = str(value)
        else:
            value_text = str(value)

        if value_text in TARGET_VALUES:
            findings.append(
                {
                    "path": node["path"],
                    "type": node["type"],
                    "value": value,
                }
            )

    return findings


# ============================================================================
# RUNTIME ROOT SNAPSHOT
# ============================================================================

def inspect_root(runtime):
    if not isinstance(runtime, dict):
        return {
            "type": type_name(runtime),
            "contract": False,
            "keys": [],
        }

    return {
        "type": "dict",
        "contract": True,
        "keys": list(runtime.keys()),
        "key_count": len(runtime.keys()),
    }


# ============================================================================
# POSSIBLE CONTRACT CONTAINERS
#
# Evidence only. We report containers whose keys overlap with the
# contract vocabulary. We DO NOT select one automatically.
# ============================================================================

CONTRACT_KEYS = {
    "contract",
    "verified",
    "runtime_ready",
    "operational_safety",
    "upstream_verified",
    "artifact_verified",
    "verdict_verified",
    "runtime_verified",
    "verdict",
    "contracts_verified",
    "identity_verified",
    "release_verified",
}


def inspect_contract_like_containers(runtime):
    tree = walk_json(runtime)
    findings = []

    for node in tree:
        if node["type"] != "dict":
            continue

        keys = set(node.get("keys", []))
        overlap = sorted(keys.intersection(CONTRACT_KEYS))

        if overlap:
            findings.append(
                {
                    "path": node["path"],
                    "keys": node.get("keys", []),
                    "contract_key_overlap": overlap,
                }
            )

    return findings


# ============================================================================
# ROOT HASH / IDENTITY
# ============================================================================

def inspect_identity(runtime):
    result = {
        "sha256": sha256_file(RUNTIME_PATH),
        "runtime_path": str(RUNTIME_PATH),
        "file_exists": RUNTIME_PATH.is_file(),
        "root_type": type_name(runtime),
    }

    return result


# ============================================================================
# REPORT
# ============================================================================

def build_report(runtime):

    tree = walk_json(runtime)

    root = inspect_root(runtime)

    key_index = build_key_index(tree)

    target_keys = inspect_target_keys(tree)

    interesting_values = inspect_interesting_values(tree)

    root_sections = inspect_dict_sections(runtime)

    contract_like = inspect_contract_like_containers(runtime)

    return {
        "frontier": "RUNTIME_CONTRACT_FORENSICS_v0.1",
        "timestamp_utc": utc_now(),

        "safety": {
            "mode": MODE,
            "producer_execution": PRODUCER_EXECUTION,
            "producer_import": PRODUCER_IMPORT,
            "database_write": DATABASE_WRITE,
            "network_access": NETWORK_ACCESS,
            "exchange_access": EXCHANGE_ACCESS,
            "order_creation": ORDER_CREATION,
            "order_submission": ORDER_SUBMISSION,
            "order_execution": ORDER_EXECUTION,
            "artifact_mutation": ARTIFACT_MUTATION,
        },

        "source": {
            "runtime_path": str(RUNTIME_PATH),
            "file_exists": RUNTIME_PATH.is_file(),
            "sha256": sha256_file(RUNTIME_PATH),
            "root_type": type_name(runtime),
        },

        "root": root,

        "root_sections": root_sections,

        "target_key_forensics": target_keys,

        "interesting_value_forensics": interesting_values,

        "contract_like_containers": contract_like,

        "key_index": key_index,

        "full_schema_tree": tree,

        "conclusion": {
            "artifact_modified": False,
            "runtime_modified": False,
            "producer_executed": False,
            "contract_modified": False,
            "automatic_contract_selection": False,
            "automatic_runtime_repair": False,
            "status": "FORENSIC_ONLY",
            "next_action": (
                "USE ACTUAL RUNTIME CONTRACT PATHS FROM THIS REPORT "
                "TO BUILD THE NEXT CONSUMER"
            ),
        },
    }


# ============================================================================
# TERMINAL OUTPUT
# ============================================================================

def print_terminal_report(report):

    print_section(
        "ARUNDA TRADER\n"
        "RUNTIME CONTRACT FORENSICS v0.1"
    )

    print_section("SAFETY")

    safety = report["safety"]

    print_kv("MODE", safety["mode"])
    print_kv("PRODUCER EXECUTION", safety["producer_execution"])
    print_kv("PRODUCER IMPORT", safety["producer_import"])
    print_kv("DATABASE WRITE", safety["database_write"])
    print_kv("NETWORK ACCESS", safety["network_access"])
    print_kv("EXCHANGE ACCESS", safety["exchange_access"])
    print_kv("ORDER CREATION", safety["order_creation"])
    print_kv("ORDER SUBMISSION", safety["order_submission"])
    print_kv("ORDER EXECUTION", safety["order_execution"])
    print_kv("ARTIFACT MUTATION", safety["artifact_mutation"])

    print_section("SOURCE")

    source = report["source"]

    print_kv("RUNTIME", source["runtime_path"])
    print_kv("FILE EXISTS", source["file_exists"])
    print_kv("SHA256", source["sha256"])
    print_kv("ROOT TYPE", source["root_type"])

    print_section("ACTUAL JSON ROOT")

    root = report["root"]

    print_kv("ROOT TYPE", root["type"])
    print_kv("ROOT IS DICT", root["contract"])
    print_kv("KEY COUNT", root.get("key_count", 0))

    for key in root.get("keys", []):
        print(f"  {key}")

    print_section("ROOT SECTIONS")

    for section in report["root_sections"]:
        print(
            f"PATH={section['path']} | "
            f"TYPE={section['type']}"
        )

        if "keys" in section:
            print(
                "  KEYS="
                + json.dumps(
                    section["keys"],
                    ensure_ascii=False,
                )
            )

        if "value" in section:
            print(
                "  VALUE="
                + display_value(section["value"])
            )

    print_section("TARGET KEY FORENSICS")

    if not report["target_key_forensics"]:
        print("NO TARGET KEYS FOUND")

    else:
        for item in report["target_key_forensics"]:
            print(
                f"KEY={item['key']} | "
                f"PATH={item['path']} | "
                f"TYPE={item['type']} | "
                f"VALUE={display_value(item.get('value'))}"
            )

    print_section("INTERESTING VALUE FORENSICS")

    if not report["interesting_value_forensics"]:
        print("NO TARGET VALUES FOUND")

    else:
        for item in report["interesting_value_forensics"]:
            print(
                f"PATH={item['path']} | "
                f"TYPE={item['type']} | "
                f"VALUE={display_value(item.get('value'))}"
            )

    print_section("CONTRACT-LIKE CONTAINERS")

    if not report["contract_like_containers"]:
        print("NO CONTRACT-LIKE CONTAINER FOUND")

    else:
        for item in report["contract_like_containers"]:
            print(
                f"PATH={item['path']}"
            )

            print(
                "  KEYS="
                + json.dumps(
                    item["keys"],
                    ensure_ascii=False,
                )
            )

            print(
                "  OVERLAP="
                + json.dumps(
                    item["contract_key_overlap"],
                    ensure_ascii=False,
                )
            )

    print_section("FULL SCHEMA TREE")

    for node in report["full_schema_tree"]:

        indent = "  " * node["depth"]

        line = (
            f"{indent}{node['path']} "
            f"[{node['type']}]"
        )

        if "value" in node:
            line += (
                " = "
                + display_value(node["value"])
            )

        elif "length" in node:
            line += (
                f" length={node['length']}"
            )

        print(line)

    print_section("FORENSIC RESULT")

    conclusion = report["conclusion"]

    print_kv(
        "Artifact modified",
        conclusion["artifact_modified"],
    )

    print_kv(
        "Runtime modified",
        conclusion["runtime_modified"],
    )

    print_kv(
        "Producer executed",
        conclusion["producer_executed"],
    )

    print_kv(
        "Contract modified",
        conclusion["contract_modified"],
    )

    print_kv(
        "Automatic contract selection",
        conclusion["automatic_contract_selection"],
    )

    print_kv(
        "Automatic runtime repair",
        conclusion["automatic_runtime_repair"],
    )

    print_kv(
        "Status",
        conclusion["status"],
    )

    print_kv(
        "Next action",
        conclusion["next_action"],
    )

    print("=" * 80)
    print(
        "REPORT WRITTEN : "
        + str(OUTPUT_PATH)
    )
    print("=" * 80)


# ============================================================================
# MAIN
# ============================================================================

def main():

    if not RUNTIME_PATH.is_file():
        raise FileNotFoundError(
            "Runtime report not found:\n"
            + str(RUNTIME_PATH)
        )

    runtime = load_json(RUNTIME_PATH)

    report = build_report(runtime)

    OUTPUT_PATH.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print_terminal_report(report)


if __name__ == "__main__":
    main()