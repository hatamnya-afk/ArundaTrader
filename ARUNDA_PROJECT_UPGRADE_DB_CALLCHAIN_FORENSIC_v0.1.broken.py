```powershell
@'
import ast
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

VERSION = "v0.1"
PROJECT_DIR = Path(r"C:\Users\ASUS\ArundaTrader")
TARGET = "upgrade_db.py"

OUTPUT_JSON = PROJECT_DIR / "ARUNDA_PROJECT_UPGRADE_DB_CALLCHAIN_FORENSIC_v0.1.json"
OUTPUT_TXT = PROJECT_DIR / "ARUNDA_PROJECT_UPGRADE_DB_CALLCHAIN_FORENSIC_v0.1.txt"

EXCLUDED_DIRS = {
    "__pycache__",
    ".git",
    "_QUARANTINE_NONPRODUCTION_SYNTAX_FAILURES",
}

EXECUTION_FUNCTIONS = {
    "exec",
    "run",
    "run_path",
    "run_module",
    "check_call",
    "check_output",
    "Popen",
    "call",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def is_excluded(path: Path) -> bool:
    return any(part in EXCLUDED_DIRS for part in path.parts)


def relative_path(path: Path) -> str:
    return str(path.relative_to(PROJECT_DIR))


def parse_source(source: str):
    try:
        return ast.parse(source), None
    except SyntaxError as exc:
        return None, (
            f"{type(exc).__name__}: {exc.msg} "
            f"(line {exc.lineno}, column {exc.offset})"
        )
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def inspect_file(path: Path) -> dict:
    result = {
        "file": relative_path(path),
        "sha256": None,
        "syntax_pass": False,
        "syntax_error": None,
        "references": [],
        "db_context": [],
        "production_context": [],
    }

    try:
        source = path.read_text(
            encoding="utf-8",
            errors="replace",
        )
        result["sha256"] = sha256_file(path)
    except Exception as exc:
        result["syntax_error"] = (
            f"READ_ERROR: {type(exc).__name__}: {exc}"
        )
        return result

    tree, error = parse_source(source)

    if error is None:
        result["syntax_pass"] = True
    else:
        result["syntax_error"] = error

    lines = source.splitlines()

    for line_no, line in enumerate(lines, start=1):
        lower = line.lower()

        if TARGET.lower() in lower:
            result["references"].append({
                "file": relative_path(path),
                "line": line_no,
                "type": "TEXT_REFERENCE",
                "token": TARGET,
                "source": line.strip(),
            })

    if tree is not None:
        for node in ast.walk(tree):

            if isinstance(node, ast.Import):
                for alias in node.names:
                    if (
                        alias.name == "upgrade_db"
                        or alias.name.endswith(".upgrade_db")
                    ):
                        result["references"].append({
                            "file": relative_path(path),
                            "line": node.lineno,
                            "type": "IMPORT",
                            "token": alias.name,
                            "source": lines[node.lineno - 1].strip(),
                        })

            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if (
                    module == "upgrade_db"
                    or module.endswith(".upgrade_db")
                ):
                    result["references"].append({
                        "file": relative_path(path),
                        "line": node.lineno,
                        "type": "FROM_IMPORT",
                        "token": module,
                        "source": lines[node.lineno - 1].strip(),
                    })

            elif isinstance(node, ast.Call):
                name = ""

                if isinstance(node.func, ast.Name):
                    name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    name = node.func.attr

                if name in EXECUTION_FUNCTIONS:
                    start = max(0, node.lineno - 1)
                    end = min(
                        len(lines),
                        getattr(
                            node,
                            "end_lineno",
                            node.lineno,
                        ),
                    )
                    block = "\n".join(lines[start:end])

                    if TARGET.lower() in block.lower():
                        result["references"].append({
                            "file": relative_path(path),
                            "line": node.lineno,
                            "type": "EXECUTION_CALL",
                            "token": name,
                            "source": block.strip(),
                        })

    db_terms = {
        "sqlite3.connect",
        "DB_PATH",
        "DATABASE",
        "database",
        "arunda.db",
    }

    production_terms = {
        "production",
        "live",
        "execution",
        "order",
        "trade",
        "bitpin",
    }

    for line_no, line in enumerate(lines, start=1):
        lower = line.lower()

        for token in db_terms:
            if token.lower() in lower:
                result["db_context"].append({
                    "file": relative_path(path),
                    "line": line_no,
                    "token": token,
                    "source": line.strip(),
                })

        for token in production_terms:
            if token in lower:
                result["production_context"].append({
                    "file": relative_path(path),
                    "line": line_no,
                    "token": token,
                    "source": line.strip(),
                })

    return result


def collect_files():
    files = []

    for path in PROJECT_DIR.rglob("*.py"):
        if not path.is_file():
            continue
        if is_excluded(path):
            continue
        files.append(path)

    return sorted(files)


def main():
    started = datetime.now(timezone.utc)

    files = collect_files()
    results = [inspect_file(path) for path in files]

    target = next(
        (
            item
            for item in results
            if Path(item["file"]).name.lower() == TARGET.lower()
        ),
        None,
    )

    references = []

    for item in results:
        if Path(item["file"]).name.lower() == TARGET.lower():
            continue

        references.extend(item["references"])

    if target is None:
        status = "TARGET_NOT_FOUND"
    elif not target["syntax_pass"]:
        status = "TARGET_SYNTAX_FAILURE"
    elif references:
        status = "CALLCHAIN_REFERENCE_FOUND"
    elif target["db_context"]:
        status = "STANDALONE_DB_WRITE_TARGET_UNRESOLVED"
    else:
        status = "NO_PROJECT_CALLCHAIN_FOUND"

    finished = datetime.now(timezone.utc)

    report = {
        "version": VERSION,
        "target": TARGET,
        "project_directory": str(PROJECT_DIR),
        "started_utc": started.isoformat(),
        "finished_utc": finished.isoformat(),
        "mode": "READ ONLY",
        "database_used": False,
        "network_used": False,
        "execution": False,
        "file_modification": False,
        "files_scanned": len(files),
        "status": status,
        "target": target,
        "external_references": references,
    }

    text = []
    sep = "=" * 100
    dash = "-" * 100

    text.extend([
        sep,
        "ARUNDA PROJECT UPGRADE DB CALLCHAIN FORENSIC v0.1",
        sep,
        f"Project Directory : {PROJECT_DIR}",
        f"Target            : {TARGET}",
        f"Started UTC       : {started.isoformat()}",
        f"Finished UTC      : {finished.isoformat()}",
        "Mode              : READ ONLY",
        "Database          : NOT USED",
        "Network           : NOT USED",
        "Execution         : STATIC ANALYSIS ONLY",
        "File Modification : FORBIDDEN",
        "",
        sep,
        "TARGET",
        sep,
    ])

    if target is None:
        text.append("TARGET : NOT FOUND")
    else:
        text.extend([
            f"EXISTS      : True",
            f"SYNTAX PASS : {target['syntax_pass']}",
            f"SHA256      : {target['sha256']}",
        ])

        if target["syntax_error"]:
            text.append(
                f"SYNTAX ERROR: {target['syntax_error']}"
            )

    text.extend([
        "",
        sep,
        "CALLCHAIN REFERENCES",
        sep,
    ])

    if not references:
        text.append("NONE")
    else:
        for ref in references:
            text.extend([
                dash,
                f"FILE   : {ref['file']}",
                f"LINE   : {ref['line']}",
                f"TYPE   : {ref['type']}",
                f"TOKEN  : {ref['token']}",
                f"SOURCE : {ref['source']}",
            ])

    text.extend([
        "",
        sep,
        "TARGET DATABASE CONTEXT",
        sep,
    ])

    if target and target["db_context"]:
        for item in target["db_context"]:
            text.extend([
                dash,
                f"LINE   : {item['line']}",
                f"TOKEN  : {item['token']}",
                f"SOURCE : {item['source']}",
            ])
    else:
        text.append("NONE")

    text.extend([
        "",
        sep,
        "FORENSIC VERDICT",
        sep,
        f"FORENSIC STATUS : {status}",
        "PREDICTIVE CLAIM : NOT ESTABLISHED",
        "DATABASE USED    : False",
        "NETWORK USED     : False",
        "EXECUTION        : False",
        "FILE MODIFICATION: False",
        "",
        "upgrade_db.py WAS NOT EXECUTED",
        "arunda.db WAS NOT OPENED",
        "NO SQL WAS EXECUTED",
        "NO NETWORK WAS USED",
        "NO PRODUCTION STATE WAS CHANGED",
        "",
        sep,
        "ARTIFACT",
        sep,
        f"Artifact : {OUTPUT_JSON}",
        f"Report   : {OUTPUT_TXT}",
        sep,
    ])

    final_text = "\n".join(text)

    OUTPUT_JSON.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    OUTPUT_TXT.write_text(
        final_text,
        encoding="utf-8",
    )

    print(final_text)


if __name__ == "__main__":
    main()
'@ | Set-Content -LiteralPath ".\ARUNDA_PROJECT_UPGRADE_DB_CALLCHAIN_FORENSIC_v0.1.py" -Encoding UTF8
```
