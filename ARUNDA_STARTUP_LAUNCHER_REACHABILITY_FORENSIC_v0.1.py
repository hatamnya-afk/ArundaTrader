import ast
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

PROJECT_DIR = Path(r"C:\Users\ASUS\ArundaTrader")
TARGET_PIPELINE = "arunda_pipeline.py"
TARGET_UPGRADE = "upgrade_db.py"

OUT_JSON = PROJECT_DIR / "ARUNDA_STARTUP_LAUNCHER_REACHABILITY_FORENSIC_v0.1.json"
OUT_TXT = PROJECT_DIR / "ARUNDA_STARTUP_LAUNCHER_REACHABILITY_FORENSIC_v0.1.txt"

SKIP_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "env",
}

FORENSIC_PREFIXES = (
    "ARUNDA_",
)

LAUNCHER_EXTENSIONS = {
    ".py",
    ".ps1",
    ".bat",
    ".cmd",
    ".sh",
}

EXEC_FUNCTIONS = {
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


def read_text(path):
    raw = path.read_bytes()

    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig")

    return raw.decode("utf-8", errors="replace")


def relative_name(path):
    try:
        return str(path.relative_to(PROJECT_DIR))
    except ValueError:
        return str(path)


def is_skipped(path):
    try:
        rel = path.relative_to(PROJECT_DIR)
    except ValueError:
        return True

    if any(part in SKIP_DIRS for part in rel.parts):
        return True

    if path.name.startswith(FORENSIC_PREFIXES):
        return True

    if path.name.endswith(".broken.py"):
        return True

    return False


def get_call_name(node):
    try:
        return ast.unparse(node.func)
    except Exception:
        return ""


def analyze_python(path):
    result = {
        "file": relative_name(path),
        "sha256": sha256_file(path),
        "syntax_pass": False,
        "imports": [],
        "execution_calls": [],
        "pipeline_refs": [],
        "upgrade_refs": [],
        "target_refs": [],
    }

    source = read_text(path)

    for number, line in enumerate(source.splitlines(), 1):
        lower = line.lower()

        if "arunda_pipeline.py" in lower or "arunda_pipeline" in lower:
            result["pipeline_refs"].append({
                "line": number,
                "source": line.strip(),
            })

        if "upgrade_db.py" in lower or "upgrade_db" in lower:
            result["upgrade_refs"].append({
                "line": number,
                "source": line.strip(),
            })

    try:
        tree = ast.parse(source, filename=str(path))
        result["syntax_pass"] = True
    except SyntaxError as exc:
        result["syntax_error"] = {
            "message": exc.msg,
            "line": exc.lineno,
            "column": exc.offset,
        }
        return result

    for node in ast.walk(tree):

        if isinstance(node, (ast.Import, ast.ImportFrom)):
            text = ast.unparse(node)

            result["imports"].append({
                "line": node.lineno,
                "source": text,
            })

            lower = text.lower()

            if "arunda_pipeline" in lower:
                result["pipeline_refs"].append({
                    "line": node.lineno,
                    "source": text,
                })

            if "upgrade_db" in lower:
                result["upgrade_refs"].append({
                    "line": node.lineno,
                    "source": text,
                })

        elif isinstance(node, ast.Call):

            function = get_call_name(node)

            if function in EXEC_FUNCTIONS:
                result["execution_calls"].append({
                    "line": node.lineno,
                    "function": function,
                    "source": ast.unparse(node),
                })

            try:
                call_text = ast.unparse(node)
            except Exception:
                call_text = function

            lower = call_text.lower()

            if "arunda_pipeline" in lower:
                result["pipeline_refs"].append({
                    "line": node.lineno,
                    "source": call_text,
                })

            if "upgrade_db" in lower:
                result["upgrade_refs"].append({
                    "line": node.lineno,
                    "source": call_text,
                })

    return result


def analyze_script(path):
    result = {
        "file": relative_name(path),
        "sha256": sha256_file(path),
        "pipeline_refs": [],
        "upgrade_refs": [],
        "execution_lines": [],
    }

    source = read_text(path)

    for number, line in enumerate(source.splitlines(), 1):
        lower = line.lower()

        if (
            "arunda_pipeline.py" in lower
            or "arunda_pipeline" in lower
        ):
            result["pipeline_refs"].append({
                "line": number,
                "source": line.strip(),
            })

        if (
            "upgrade_db.py" in lower
            or "upgrade_db" in lower
        ):
            result["upgrade_refs"].append({
                "line": number,
                "source": line.strip(),
            })

        if any(term in lower for term in (
            "python ",
            "python.exe",
            "py ",
            "powershell",
            "pwsh",
            "start-process",
            "subprocess",
            "runpy",
            "upgrade_db",
            "arunda_pipeline",
        )):
            result["execution_lines"].append({
                "line": number,
                "source": line.strip(),
            })

    return result


def all_project_files():
    files = []

    for path in PROJECT_DIR.rglob("*"):

        if not path.is_file():
            continue

        if is_skipped(path):
            continue

        if path.suffix.lower() not in LAUNCHER_EXTENSIONS:
            continue

        files.append(path)

    return sorted(files)


def dedupe(items):
    seen = set()
    output = []

    for item in items:
        key = (
            item.get("file"),
            item.get("line"),
            item.get("source"),
        )

        if key in seen:
            continue

        seen.add(key)
        output.append(item)

    return output


def main():

    started = datetime.now(timezone.utc)

    print("=" * 100)
    print("ARUNDA STARTUP / LAUNCHER REACHABILITY FORENSIC v0.1")
    print("=" * 100)
    print(f"Project Directory : {PROJECT_DIR}")
    print(f"Pipeline Target   : {TARGET_PIPELINE}")
    print(f"Upgrade Target    : {TARGET_UPGRADE}")
    print(f"Started UTC       : {started.isoformat()}")
    print("Mode              : READ ONLY")
    print("Database          : NOT USED")
    print("Network           : NOT USED")
    print("Execution         : NOT PERFORMED")
    print("File Modification : NOT PERFORMED")
    print("Forensic Files    : EXCLUDED")
    print("-" * 100)

    pipeline = PROJECT_DIR / TARGET_PIPELINE
    upgrade = PROJECT_DIR / TARGET_UPGRADE

    report = {
        "version": "v0.1",
        "started_utc": started.isoformat(),
        "project_directory": str(PROJECT_DIR),
        "pipeline_exists": pipeline.exists(),
        "upgrade_exists": upgrade.exists(),
        "pipeline_analysis": None,
        "upgrade_analysis": None,
        "candidate_files": [],
        "pipeline_launchers": [],
        "upgrade_launchers": [],
        "upgrade_importers": [],
        "startup_candidates": [],
        "verdict": None,
        "database_used": False,
        "network_used": False,
        "execution_performed": False,
        "file_modification": False,
    }

    if pipeline.exists() and pipeline.suffix == ".py":
        report["pipeline_analysis"] = analyze_python(pipeline)

    if upgrade.exists() and upgrade.suffix == ".py":
        report["upgrade_analysis"] = analyze_python(upgrade)

    files = all_project_files()

    report["candidate_files"] = [
        relative_name(path)
        for path in files
    ]

    for path in files:

        if path.suffix.lower() == ".py":
            result = analyze_python(path)
        else:
            result = analyze_script(path)

        if result["pipeline_refs"]:
            report["pipeline_launchers"].append(result)

        if result["upgrade_refs"]:
            report["upgrade_launchers"].append(result)

        if path.suffix.lower() == ".py":
            imports = result.get("imports", [])

            for item in imports:
                if "upgrade_db" in item["source"].lower():
                    report["upgrade_importers"].append({
                        "file": result["file"],
                        "line": item["line"],
                        "source": item["source"],
                    })

    report["pipeline_launchers"] = [
        x for x in report["pipeline_launchers"]
        if x["file"] != TARGET_PIPELINE
    ]

    report["upgrade_launchers"] = [
        x for x in report["upgrade_launchers"]
        if x["file"] != TARGET_UPGRADE
    ]

    report["upgrade_importers"] = dedupe(
        report["upgrade_importers"]
    )

    if not report["upgrade_exists"]:
        report["verdict"] = "UNRESOLVED"

    elif report["upgrade_launchers"] or report["upgrade_importers"]:

        report["verdict"] = "REACHABLE"

    else:

        report["verdict"] = "STANDALONE_LEGACY"

    finished = datetime.now(timezone.utc)
    report["finished_utc"] = finished.isoformat()

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(
            report,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print()
    print("=" * 100)
    print("TARGETS")
    print("=" * 100)

    print(f"arunda_pipeline.py : {report['pipeline_exists']}")
    print(f"upgrade_db.py      : {report['upgrade_exists']}")

    if report["pipeline_analysis"]:
        print(
            "Pipeline Syntax    : "
            f"{report['pipeline_analysis']['syntax_pass']}"
        )

    if report["upgrade_analysis"]:
        print(
            "Upgrade Syntax     : "
            f"{report['upgrade_analysis']['syntax_pass']}"
        )

    print()
    print("=" * 100)
    print("PIPELINE LAUNCHER REFERENCES")
    print("=" * 100)

    if report["pipeline_launchers"]:
        for item in report["pipeline_launchers"]:
            print("-" * 100)
            print(f"FILE : {item['file']}")

            for ref in item["pipeline_refs"]:
                print(
                    f"LINE {ref['line']} : "
                    f"{ref['source']}"
                )
    else:
        print("NONE")

    print()
    print("=" * 100)
    print("UPGRADE_DB STARTUP / LAUNCH REFERENCES")
    print("=" * 100)

    if report["upgrade_launchers"]:
        for item in report["upgrade_launchers"]:
            print("-" * 100)
            print(f"FILE : {item['file']}")

            for ref in item["upgrade_refs"]:
                print(
                    f"LINE {ref['line']} : "
                    f"{ref['source']}"
                )
    else:
        print("NONE")

    print()
    print("=" * 100)
    print("UPGRADE_DB IMPORTERS")
    print("=" * 100)

    if report["upgrade_importers"]:
        for item in report["upgrade_importers"]:
            print(
                f"{item['file']} | "
                f"LINE {item['line']} | "
                f"{item['source']}"
            )
    else:
        print("NONE")

    print()
    print("=" * 100)
    print("STARTUP REACHABILITY VERDICT")
    print("=" * 100)
    print(f"VERDICT : {report['verdict']}")

    if report["verdict"] == "REACHABLE":
        print(
            "upgrade_db.py has a project-level "
            "launch/import reference."
        )

    elif report["verdict"] == "STANDALONE_LEGACY":
        print(
            "No project launcher/importer reference "
            "to upgrade_db.py was found."
        )

    elif report["verdict"] == "UNRESOLVED":
        print(
            "upgrade_db.py could not be resolved."
        )

    print()
    print("DATABASE        : NOT USED")
    print("NETWORK         : NOT USED")
    print("EXECUTION       : NOT PERFORMED")
    print("FILE MODIFIED   : NOT PERFORMED")
    print()
    print("Forensic artifacts were excluded from dependency conclusions.")
    print("=" * 100)

    print()
    print("ARTIFACT")
    print("=" * 100)
    print(f"JSON : {OUT_JSON}")
    print(f"TXT  : {OUT_TXT}")
    print("=" * 100)

    lines = [
        "=" * 100,
        "ARUNDA STARTUP / LAUNCHER REACHABILITY FORENSIC v0.1",
        "=" * 100,
        f"Started UTC  : {started.isoformat()}",
        f"Finished UTC : {finished.isoformat()}",
        f"VERDICT      : {report['verdict']}",
        f"Pipeline     : {report['pipeline_exists']}",
        f"Upgrade DB   : {report['upgrade_exists']}",
        f"Pipeline Launchers : {len(report['pipeline_launchers'])}",
        f"Upgrade Launchers  : {len(report['upgrade_launchers'])}",
        f"Upgrade Importers  : {len(report['upgrade_importers'])}",
        "-" * 100,
        "DATABASE        : NOT USED",
        "NETWORK         : NOT USED",
        "EXECUTION       : NOT PERFORMED",
        "FILE MODIFIED   : NOT PERFORMED",
        "FORENSIC FILES  : EXCLUDED",
        "=" * 100,
    ]

    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("DONE")


if __name__ == "__main__":
    raise SystemExit(main())
