import ast
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

PROJECT_DIR = Path(r"C:\Users\ASUS\ArundaTrader")
TARGET = "arunda_pipeline.py"
VERSION = "v0.1"

OUT_JSON = PROJECT_DIR / "ARUNDA_PROJECT_REAL_LAUNCHER_FORENSIC_v0.1.json"
OUT_TXT = PROJECT_DIR / "ARUNDA_PROJECT_REAL_LAUNCHER_FORENSIC_v0.1.txt"

SKIP_DIRS = {
    ".git",
    "__pycache__",
    "_QUARANTINE_NONPRODUCTION_SYNTAX_FAILURES",
    ".venv",
    "venv",
    "env",
}

EXEC_CALL_NAMES = {
    "subprocess.run",
    "subprocess.call",
    "subprocess.Popen",
    "subprocess.check_call",
    "subprocess.check_output",
    "os.system",
    "os.popen",
    "runpy.run_module",
    "runpy.run_path",
    "importlib.import_module",
}

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def read_source(path):
    raw = path.read_bytes()

    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig"), "UTF-8-BOM"

    try:
        return raw.decode("utf-8"), "UTF-8"
    except UnicodeDecodeError:
        return raw.decode("utf-8", errors="replace"), "UTF-8-REPLACED"

def is_skipped(path):
    try:
        rel = path.relative_to(PROJECT_DIR)
    except ValueError:
        return True

    return any(part in SKIP_DIRS for part in rel.parts)

def call_name(node):
    try:
        return ast.unparse(node.func)
    except Exception:
        return ""

def literal_string(node):
    try:
        value = ast.literal_eval(node)
        return value if isinstance(value, str) else None
    except Exception:
        return None

def analyze_file(path):
    record = {
        "file": str(path.relative_to(PROJECT_DIR)),
        "sha256": None,
        "syntax_pass": False,
        "encoding": None,
        "imports": [],
        "execution_calls": [],
        "pipeline_references": [],
        "launcher_references": [],
        "upgrade_db_references": [],
    }

    try:
        record["sha256"] = sha256_file(path)
        source, encoding = read_source(path)
        record["encoding"] = encoding
    except Exception as exc:
        record["error"] = f"{type(exc).__name__}: {exc}"
        return record

    try:
        tree = ast.parse(source, filename=str(path))
        record["syntax_pass"] = True
    except SyntaxError as exc:
        record["syntax_error"] = {
            "message": exc.msg,
            "line": exc.lineno,
            "column": exc.offset,
        }
        tree = None

    lines = source.splitlines()

    for number, line in enumerate(lines, 1):
        lower = line.lower()

        if "arunda_pipeline.py" in lower:
            record["pipeline_references"].append({
                "line": number,
                "source": line.strip(),
            })

        if "arunda_pipeline" in lower:
            record["pipeline_references"].append({
                "line": number,
                "source": line.strip(),
            })

        if "upgrade_db.py" in lower or "upgrade_db" in lower:
            record["upgrade_db_references"].append({
                "line": number,
                "source": line.strip(),
            })

    if tree is None:
        return record

    for node in ast.walk(tree):

        if isinstance(node, (ast.Import, ast.ImportFrom)):
            text = ast.unparse(node)
            record["imports"].append({
                "line": node.lineno,
                "source": text,
            })

            if "arunda_pipeline" in text.lower():
                record["pipeline_references"].append({
                    "line": node.lineno,
                    "source": text,
                })

            if "upgrade_db" in text.lower():
                record["upgrade_db_references"].append({
                    "line": node.lineno,
                    "source": text,
                })

        elif isinstance(node, ast.Call):

            name = call_name(node)

            if name in EXEC_CALL_NAMES:
                item = {
                    "line": node.lineno,
                    "function": name,
                    "source": ast.unparse(node),
                }
                record["execution_calls"].append(item)

            try:
                call_text = ast.unparse(node)
            except Exception:
                call_text = name

            lower_call = call_text.lower()

            if "arunda_pipeline" in lower_call:
                record["pipeline_references"].append({
                    "line": node.lineno,
                    "source": call_text,
                })

            if "upgrade_db" in lower_call:
                record["upgrade_db_references"].append({
                    "line": node.lineno,
                    "source": call_text,
                })

    return record

def find_candidate_files():
    candidates = []

    for path in PROJECT_DIR.rglob("*"):
        if not path.is_file():
            continue

        if is_skipped(path):
            continue

        if path.suffix.lower() in {
            ".py",
            ".ps1",
            ".bat",
            ".cmd",
        }:
            candidates.append(path)

    return sorted(candidates)

def main():

    started = datetime.now(timezone.utc)

    print("=" * 100)
    print("ARUNDA PROJECT REAL LAUNCHER FORENSIC v0.1")
    print("=" * 100)
    print(f"Project Directory : {PROJECT_DIR}")
    print(f"Target            : {TARGET}")
    print(f"Started UTC       : {started.isoformat()}")
    print("Mode              : READ ONLY")
    print("Database          : NOT USED")
    print("Network           : NOT USED")
    print("Execution         : STATIC ANALYSIS ONLY")
    print("File Modification : FORBIDDEN")
    print("-" * 100)

    target_path = PROJECT_DIR / TARGET

    report = {
        "version": VERSION,
        "project_directory": str(PROJECT_DIR),
        "target": TARGET,
        "started_utc": started.isoformat(),
        "database_used": False,
        "network_used": False,
        "execution_performed": False,
        "file_modification": False,
        "target_exists": target_path.exists(),
        "target_analysis": None,
        "candidate_count": 0,
        "candidate_files": [],
        "pipeline_launchers": [],
        "upgrade_db_references": [],
        "status": None,
    }

    if target_path.exists():
        report["target_analysis"] = analyze_file(target_path)

    candidates = find_candidate_files()
    report["candidate_count"] = len(candidates)

    for path in candidates:

        name_lower = path.name.lower()

        if name_lower in {
            "arunda_pipeline.py",
            "arunda_project_real_launcher_forensic_v0.1.py",
        }:
            continue

        record = analyze_file(path)

        pipeline_refs = record["pipeline_references"]

        if pipeline_refs:
            report["pipeline_launchers"].append({
                "file": record["file"],
                "syntax_pass": record["syntax_pass"],
                "sha256": record["sha256"],
                "imports": record["imports"],
                "execution_calls": record["execution_calls"],
                "pipeline_references": pipeline_refs,
            })

        if record["upgrade_db_references"]:
            report["upgrade_db_references"].append({
                "file": record["file"],
                "syntax_pass": record["syntax_pass"],
                "sha256": record["sha256"],
                "references": record["upgrade_db_references"],
            })

    report["pipeline_launchers"].sort(
        key=lambda x: (
            x["file"].lower(),
            len(x["pipeline_references"]),
        )
    )

    report["upgrade_db_references"].sort(
        key=lambda x: x["file"].lower()
    )

    target = report["target_analysis"]

    if not report["target_exists"]:
        report["status"] = "PIPELINE_NOT_FOUND"
    elif target and not target["syntax_pass"]:
        report["status"] = "PIPELINE_SYNTAX_FAILURE"
    elif report["pipeline_launchers"]:
        report["status"] = "LAUNCHER_REFERENCE_FOUND"
    else:
        report["status"] = "REAL_LAUNCHER_NOT_FOUND"

    finished = datetime.now(timezone.utc)
    report["finished_utc"] = finished.isoformat()

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print()
    print("=" * 100)
    print("TARGET")
    print("=" * 100)
    print(f"EXISTS       : {report['target_exists']}")

    if target:
        print(f"SYNTAX PASS  : {target['syntax_pass']}")
        print(f"SHA256       : {target['sha256']}")

    print()
    print("=" * 100)
    print("REAL LAUNCHER / PIPELINE REFERENCES")
    print("=" * 100)

    if report["pipeline_launchers"]:
        for item in report["pipeline_launchers"]:
            print("-" * 100)
            print(f"FILE        : {item['file']}")
            print(f"SYNTAX PASS : {item['syntax_pass']}")
            print(f"SHA256      : {item['sha256']}")

            if item["execution_calls"]:
                print("EXECUTION CALLS:")
                for call in item["execution_calls"]:
                    print(
                        f"  LINE {call['line']} | "
                        f"{call['function']} | "
                        f"{call['source']}"
                    )

            print("PIPELINE REFERENCES:")
            for ref in item["pipeline_references"]:
                print(
                    f"  LINE {ref['line']} | "
                    f"{ref['source']}"
                )
    else:
        print("NONE")

    print()
    print("=" * 100)
    print("UPGRADE_DB REFERENCES OUTSIDE PIPELINE")
    print("=" * 100)

    if report["upgrade_db_references"]:
        for item in report["upgrade_db_references"]:
            print("-" * 100)
            print(f"FILE : {item['file']}")
            print(f"SYNTAX PASS : {item['syntax_pass']}")
            for ref in item["references"]:
                print(
                    f"  LINE {ref['line']} | "
                    f"{ref['source']}"
                )
    else:
        print("NONE")

    print()
    print("=" * 100)
    print("FORENSIC VERDICT")
    print("=" * 100)
    print(f"STATUS          : {report['status']}")
    print("DATABASE        : NOT USED")
    print("NETWORK         : NOT USED")
    print("EXECUTION       : NOT PERFORMED")
    print("FILE MODIFIED   : NOT PERFORMED")
    print()
    print("This artifact performs static analysis only.")
    print("No launcher, pipeline, stage, database, or network operation was executed.")
    print("=" * 100)

    print()
    print("ARTIFACT")
    print("=" * 100)
    print(f"JSON : {OUT_JSON}")
    print(f"TXT  : {OUT_TXT}")
    print("=" * 100)

    text_lines = [
        "=" * 100,
        "ARUNDA PROJECT REAL LAUNCHER FORENSIC v0.1",
        "=" * 100,
        f"Project Directory : {PROJECT_DIR}",
        f"Target            : {TARGET}",
        f"Started UTC       : {started.isoformat()}",
        f"Finished UTC      : {finished.isoformat()}",
        "Mode              : READ ONLY",
        "Database          : NOT USED",
        "Network           : NOT USED",
        "Execution         : STATIC ANALYSIS ONLY",
        "File Modification : FORBIDDEN",
        "-" * 100,
        "FORENSIC STATUS",
        "-" * 100,
        f"STATUS : {report['status']}",
        f"PIPELINE REFERENCES : {len(report['pipeline_launchers'])}",
        f"UPGRADE_DB REFERENCES : {len(report['upgrade_db_references'])}",
        "-" * 100,
        "IMPORTANT",
        "-" * 100,
        "No launcher, pipeline, stage, database, or network operation was executed.",
        "This artifact performs static analysis only.",
        "=" * 100,
    ]

    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(text_lines))

    print("DONE")

if __name__ == "__main__":
    raise SystemExit(main())
