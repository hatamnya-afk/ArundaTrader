import ast
import hashlib
import json
import os
from datetime import datetime, timezone

PROJECT_DIR = r"C:\Users\ASUS\ArundaTrader"
TARGET = "ARUNDA_TRADER_LIVE_PAPER_LIFECYCLE_STATE_CAPTURE_FROM_ISOLATED_LAUNCH_v0.1.py"
ARTIFACT = os.path.join(
    PROJECT_DIR,
    "ARUNDA_PROJECT_RUNTIME_LIFECYCLE_DEPENDENCY_REVIEW_FORENSIC_v0.1.json",
)
REPORT = os.path.join(
    PROJECT_DIR,
    "ARUNDA_PROJECT_RUNTIME_LIFECYCLE_DEPENDENCY_REVIEW_FORENSIC_v0.1.txt",
)

MODE = "READ ONLY"
DATABASE = "NOT USED"
NETWORK = "FORBIDDEN"
FILE_MODIFICATION = "FORBIDDEN"
EXECUTION = "STATIC ANALYSIS ONLY"


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def safe_read(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read(), None
    except Exception as e:
        return "", str(e)


def syntax_check(source):
    try:
        ast.parse(source)
        return True, None, None, None
    except SyntaxError as e:
        return False, type(e).__name__, str(e), e.lineno


def normalize_import(name):
    if not name:
        return None
    return name.split(".")[0]


def collect_imports(tree):
    imports = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = normalize_import(alias.name)
                if root:
                    imports.add(root)

        elif isinstance(node, ast.ImportFrom):
            root = normalize_import(node.module)
            if root:
                imports.add(root)

    return sorted(imports)


def collect_calls(tree):
    calls = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = None

            if isinstance(node.func, ast.Name):
                name = node.func.id

            elif isinstance(node.func, ast.Attribute):
                parts = []
                cur = node.func

                while isinstance(cur, ast.Attribute):
                    parts.append(cur.attr)
                    cur = cur.value

                if isinstance(cur, ast.Name):
                    parts.append(cur.id)

                name = ".".join(reversed(parts))

            if name:
                calls.append(name)

    return sorted(set(calls))


def collect_sqlite_markers(source):
    markers = []

    upper = source.upper()

    checks = {
        "SQLITE3_IMPORT": "SQLITE3",
        "SQLITE_CONNECT": "SQLITE3.CONNECT",
        "SQLITE_DATABASE_REFERENCE": ".DB",
        "SQL_SELECT": "SELECT ",
        "SQL_INSERT": "INSERT ",
        "SQL_UPDATE": "UPDATE ",
        "SQL_DELETE": "DELETE ",
        "SQL_CREATE": "CREATE TABLE",
        "SQL_ALTER": "ALTER TABLE",
        "SQL_DROP": "DROP TABLE",
    }

    for label, token in checks.items():
        if token in upper:
            markers.append(label)

    return markers


def collect_runtime_markers(source):
    upper = source.upper()
    markers = []

    checks = {
        "MAIN_INVOCATION": 'IF __NAME__ == "__MAIN__"',
        "SUBPROCESS": "SUBPROCESS",
        "OS_SYSTEM": "OS.SYSTEM",
        "OS_POPEN": "OS.POPEN",
        "SYSTEM_CALL": "SYSTEM(",
        "SCHEDULER": "SCHEDUL",
        "LIVE": "LIVE",
        "PAPER": "PAPER",
        "EXECUTION": "EXECUTION",
        "PRODUCTION": "PRODUCTION",
        "ORDER": "ORDER",
        "TRADE": "TRADE",
    }

    for label, token in checks.items():
        if token in upper:
            markers.append(label)

    return markers


def file_reference_scan(all_files, target_filename):
    references = []

    target_stem = os.path.splitext(target_filename)[0]

    candidates = [
        target_filename,
        target_stem,
    ]

    for path in all_files:
        if os.path.basename(path) == target_filename:
            continue

        source, err = safe_read(path)

        if err:
            continue

        for token in candidates:
            if token in source:
                references.append(
                    {
                        "file": os.path.basename(path),
                        "matched_token": token,
                    }
                )
                break

    return references


def discover_python_files():
    result = []

    for root, dirs, files in os.walk(PROJECT_DIR):
        dirs[:] = [
            d for d in dirs
            if d not in {
                "__pycache__",
                ".git",
                ".venv",
                "venv",
                "env",
                "node_modules",
            }
        ]

        for filename in files:
            if filename.lower().endswith(".py"):
                result.append(os.path.join(root, filename))

    return sorted(result)


def inspect_target(path):
    source, read_error = safe_read(path)

    record = {
        "target": TARGET,
        "exists": os.path.exists(path),
        "path": path,
        "read_error": read_error,
        "sha256": sha256_text(source) if source else None,
        "syntax": {},
        "imports": [],
        "calls": [],
        "sqlite_markers": [],
        "runtime_markers": [],
        "function_names": [],
        "class_names": [],
    }

    if read_error or not source:
        return record

    ok, error_type, message, line = syntax_check(source)

    record["syntax"] = {
        "pass": ok,
        "error_type": error_type,
        "message": message,
        "line": line,
    }

    record["sqlite_markers"] = collect_sqlite_markers(source)
    record["runtime_markers"] = collect_runtime_markers(source)

    try:
        tree = ast.parse(source)

        record["imports"] = collect_imports(tree)
        record["calls"] = collect_calls(tree)

        record["function_names"] = sorted(
            {
                node.name
                for node in ast.walk(tree)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
        )

        record["class_names"] = sorted(
            {
                node.name
                for node in ast.walk(tree)
                if isinstance(node, ast.ClassDef)
            }
        )

    except SyntaxError:
        pass

    return record


def classify(record, references):
    if not record["exists"]:
        return "TARGET_MISSING"

    if record["read_error"]:
        return "MANUAL_REVIEW_REQUIRED"

    syntax_pass = record["syntax"].get("pass", False)

    if not syntax_pass:
        return "SYNTAX_FAILURE_REQUIRES_REPAIR_OR_QUARANTINE"

    if references:
        return "DIRECT_PROJECT_REFERENCE_FOUND"

    sqlite = record["sqlite_markers"]
    runtime = record["runtime_markers"]

    if sqlite and runtime:
        return "RUNTIME_REVIEW_REQUIRED"

    if runtime:
        return "RUNTIME_MARKERS_PRESENT_NO_DIRECT_REFERENCE"

    if sqlite:
        return "SQLITE_USAGE_PRESENT_NO_RUNTIME_REFERENCE"

    return "NO_RUNTIME_DEPENDENCY_OBSERVED"


def build_report(result):
    lines = []

    def p(text=""):
        lines.append(text)

    p("=" * 90)
    p("ARUNDA PROJECT RUNTIME LIFECYCLE DEPENDENCY REVIEW FORENSIC v0.1")
    p("=" * 90)
    p(f"Project Directory : {PROJECT_DIR}")
    p(f"Target            : {TARGET}")
    p(f"Started UTC       : {result['started_utc']}")
    p(f"Finished UTC      : {result['finished_utc']}")
    p(f"Mode              : {MODE}")
    p(f"Database          : {DATABASE}")
    p(f"Network           : {NETWORK}")
    p(f"File Modification : {FILE_MODIFICATION}")
    p(f"Execution         : {EXECUTION}")
    p("-" * 90)

    p()
    p("=" * 90)
    p("TARGET FILE")
    p("=" * 90)

    r = result["target_analysis"]

    p(f"EXISTS            : {r['exists']}")
    p(f"SYNTAX PASS       : {r['syntax'].get('pass')}")
    p(f"SHA256            : {r['sha256']}")
    p(f"CLASSIFICATION    : {result['classification']}")

    if r["syntax"].get("pass") is False:
        p(f"ERROR TYPE        : {r['syntax'].get('error_type')}")
        p(f"ERROR MESSAGE     : {r['syntax'].get('message')}")
        p(f"ERROR LINE        : {r['syntax'].get('line')}")

    p()
    p("IMPORTS")
    for item in r["imports"]:
        p(f"  - {item}")
    if not r["imports"]:
        p("  - None")

    p()
    p("FUNCTIONS")
    for item in r["function_names"]:
        p(f"  - {item}")
    if not r["function_names"]:
        p("  - None")

    p()
    p("SQLITE / DATABASE MARKERS")
    for item in r["sqlite_markers"]:
        p(f"  - {item}")
    if not r["sqlite_markers"]:
        p("  - None")

    p()
    p("RUNTIME MARKERS")
    for item in r["runtime_markers"]:
        p(f"  - {item}")
    if not r["runtime_markers"]:
        p("  - None")

    p()
    p("=" * 90)
    p("DIRECT PROJECT REFERENCES")
    p("=" * 90)

    refs = result["references"]

    if refs:
        for ref in refs:
            p(f"FILE           : {ref['file']}")
            p(f"MATCHED TOKEN  : {ref['matched_token']}")
            p("-" * 60)
    else:
        p("None")

    p()
    p("=" * 90)
    p("DEPENDENCY ASSESSMENT")
    p("=" * 90)

    p(f"DIRECT REFERENCE FOUND : {bool(refs)}")
    p(
        f"SQLITE USAGE PRESENT  : "
        f"{bool(r['sqlite_markers'])}"
    )
    p(
        f"RUNTIME MARKERS       : "
        f"{bool(r['runtime_markers'])}"
    )

    if refs:
        p("ASSESSMENT : DIRECT_PROJECT_DEPENDENCY_REQUIRES_REVIEW")
    elif r["sqlite_markers"] and r["runtime_markers"]:
        p("ASSESSMENT : RUNTIME_LIFECYCLE_ARTIFACT_REQUIRES_REVIEW")
    elif r["sqlite_markers"]:
        p("ASSESSMENT : SQLITE_USAGE_WITHOUT_DIRECT_RUNTIME_DEPENDENCY")
    elif r["runtime_markers"]:
        p("ASSESSMENT : RUNTIME_MARKERS_WITHOUT_DIRECT_PROJECT_REFERENCE")
    else:
        p("ASSESSMENT : NO_RUNTIME_DEPENDENCY_OBSERVED")

    p()
    p("=" * 90)
    p("FORENSIC STATUS")
    p("=" * 90)

    if refs:
        status = "DIRECT_RUNTIME_DEPENDENCY_REVIEW_REQUIRED"
    elif r["sqlite_markers"] and r["runtime_markers"]:
        status = "RUNTIME_REVIEW_REQUIRED"
    elif not r["exists"]:
        status = "TARGET_MISSING"
    elif not r["syntax"].get("pass", False):
        status = "TARGET_SYNTAX_FAILURE"
    else:
        status = "NO_DIRECT_RUNTIME_DEPENDENCY_OBSERVED"

    p(f"FORENSIC STATUS : {status}")
    p("PREDICTIVE CLAIM : NOT ESTABLISHED")
    p("DATABASE WRITE   : NOT PERFORMED")
    p("NETWORK          : NOT USED")
    p("PRODUCTION RUN   : NOT PERFORMED")
    p("FILE MODIFICATION: NOT PERFORMED")
    p("QUARANTINE       : NOT PERFORMED")
    p("DELETION         : NOT PERFORMED")

    p()
    p("=" * 90)
    p("ARTIFACT")
    p("=" * 90)
    p(f"Artifact : {ARTIFACT}")
    p(f"Report   : {REPORT}")
    p(f"SHA256   : {result['artifact_sha256']}")

    return "\n".join(lines)


def main():
    started = utc_now()

    print("=" * 90)
    print("ARUNDA PROJECT RUNTIME LIFECYCLE DEPENDENCY REVIEW FORENSIC v0.1")
    print("=" * 90)
    print(f"Project Directory : {PROJECT_DIR}")
    print(f"Target            : {TARGET}")
    print(f"Mode              : {MODE}")
    print(f"Database          : {DATABASE}")
    print(f"Network           : {NETWORK}")
    print(f"File Modification : {FILE_MODIFICATION}")
    print(f"Execution         : {EXECUTION}")
    print("-" * 90)

    all_files = discover_python_files()
    target_path = os.path.join(PROJECT_DIR, TARGET)

    target_analysis = inspect_target(target_path)

    references = file_reference_scan(
        all_files,
        TARGET,
    )

    classification = classify(
        target_analysis,
        references,
    )

    result = {
        "artifact_version": "v0.1",
        "artifact_name": os.path.basename(ARTIFACT),
        "project_directory": PROJECT_DIR,
        "target": TARGET,
        "started_utc": started,
        "finished_utc": utc_now(),
        "mode": MODE,
        "database": DATABASE,
        "network": NETWORK,
        "file_modification": FILE_MODIFICATION,
        "execution": EXECUTION,
        "python_files_scanned": len(all_files),
        "target_analysis": target_analysis,
        "references": references,
        "classification": classification,
        "database_write": False,
        "production_run": False,
        "quarantine": False,
        "deletion": False,
    }

    json_without_hash = json.dumps(
        result,
        indent=2,
        ensure_ascii=False,
        sort_keys=True,
    )

    artifact_hash = sha256_text(json_without_hash)

    result["artifact_sha256"] = artifact_hash

    final_json = json.dumps(
        result,
        indent=2,
        ensure_ascii=False,
        sort_keys=True,
    )

    with open(
        ARTIFACT,
        "w",
        encoding="utf-8",
    ) as f:
        f.write(final_json)

    result["finished_utc"] = utc_now()

    report = build_report(result)

    with open(
        REPORT,
        "w",
        encoding="utf-8",
    ) as f:
        f.write(report)

    print()
    print(report)
    print()
    print("=" * 90)
    print("DONE")
    print("=" * 90)
    print(f"Artifact : {ARTIFACT}")
    print(f"Report   : {REPORT}")
    print("=" * 90)


if __name__ == "__main__":
    main()