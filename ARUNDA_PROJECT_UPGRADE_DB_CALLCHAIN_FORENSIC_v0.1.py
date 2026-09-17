import ast
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


VERSION = "v0.1"

PROJECT_DIR = Path(r"C:\Users\ASUS\ArundaTrader")
TARGET_NAME = "upgrade_db.py"

QUARANTINE_DIR = "_QUARANTINE_NONPRODUCTION_SYNTAX_FAILURES"

OUTPUT_JSON = PROJECT_DIR / (
    "ARUNDA_PROJECT_UPGRADE_DB_CALLCHAIN_FORENSIC_v0.1.json"
)

OUTPUT_TXT = PROJECT_DIR / (
    "ARUNDA_PROJECT_UPGRADE_DB_CALLCHAIN_FORENSIC_v0.1.txt"
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


def is_quarantined(path: Path) -> bool:
    try:
        relative = path.relative_to(PROJECT_DIR)
    except ValueError:
        return True

    return QUARANTINE_DIR in relative.parts


def read_source(path: Path) -> str:
    return path.read_text(
        encoding="utf-8",
        errors="replace",
    )


def parse_python(path: Path):
    source = read_source(path)

    try:
        tree = ast.parse(source, filename=str(path))
        return source, tree, None

    except SyntaxError as exc:
        error = (
            f"{type(exc).__name__}: {exc.msg} "
            f"(line {exc.lineno}, column {exc.offset})"
        )
        return source, None, error

    except Exception as exc:
        return source, None, (
            f"{type(exc).__name__}: {exc}"
        )


def dotted_name(node):
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parent = dotted_name(node.value)

        if parent:
            return f"{parent}.{node.attr}"

        return node.attr

    return None


def constant_string(node):
    if isinstance(node, ast.Constant):
        if isinstance(node.value, str):
            return node.value

    return None


def collect_string_literals(tree):
    values = []

    for node in ast.walk(tree):
        value = constant_string(node)

        if value is not None:
            values.append(
                (
                    getattr(node, "lineno", None),
                    value,
                )
            )

    return values


def source_line(source, line_number):
    lines = source.splitlines()

    if line_number is None:
        return ""

    if 1 <= line_number <= len(lines):
        return lines[line_number - 1].strip()

    return ""


def inspect_target():
    target_path = PROJECT_DIR / TARGET_NAME

    result = {
        "exists": target_path.exists(),
        "path": str(target_path),
        "sha256": None,
        "syntax_pass": False,
        "syntax_error": None,
        "imports": [],
        "functions": [],
        "main_guard": False,
        "db_connect_calls": [],
        "db_paths": [],
        "write_operations": [],
        "production_markers": [],
        "order_markers": [],
        "execution_markers": [],
    }

    if not target_path.exists():
        return result, None, None

    result["sha256"] = sha256_file(target_path)

    source, tree, syntax_error = parse_python(target_path)

    if syntax_error is not None:
        result["syntax_error"] = syntax_error
        return result, source, tree

    result["syntax_pass"] = True

    for node in ast.walk(tree):

        if isinstance(node, ast.Import):
            for alias in node.names:
                result["imports"].append({
                    "line": node.lineno,
                    "module": alias.name,
                    "source": source_line(
                        source,
                        node.lineno,
                    ),
                })

        elif isinstance(node, ast.ImportFrom):
            result["imports"].append({
                "line": node.lineno,
                "module": node.module,
                "source": source_line(
                    source,
                    node.lineno,
                ),
            })

        elif isinstance(node, ast.FunctionDef):
            result["functions"].append({
                "line": node.lineno,
                "name": node.name,
            })

        elif isinstance(node, ast.AsyncFunctionDef):
            result["functions"].append({
                "line": node.lineno,
                "name": node.name,
            })

        elif isinstance(node, ast.Call):
            name = dotted_name(node.func)

            if name == "sqlite3.connect":
                result["db_connect_calls"].append({
                    "line": node.lineno,
                    "source": source_line(
                        source,
                        node.lineno,
                    ),
                })

            if name == "connect":
                result["db_connect_calls"].append({
                    "line": node.lineno,
                    "source": source_line(
                        source,
                        node.lineno,
                    ),
                })

    for line_number, value in collect_string_literals(tree):
        lower = value.lower()

        if "arunda.db" in lower:
            result["db_paths"].append({
                "line": line_number,
                "value": value,
            })

    write_sql_terms = (
        "insert into",
        "insert or",
        "update ",
        "delete from",
        "create table",
        "create index",
        "alter table",
        "drop table",
        "replace into",
    )

    for line_number, line in enumerate(
        source.splitlines(),
        start=1,
    ):
        lower = line.lower().strip()

        for term in write_sql_terms:
            if term in lower:
                result["write_operations"].append({
                    "line": line_number,
                    "type": term.upper(),
                    "source": line.strip(),
                })
                break

        marker_groups = {
            "production": (
                "production",
                "prod_db",
                "production_db",
            ),
            "order": (
                "order",
                "place_order",
                "submit_order",
            ),
            "execution": (
                "execution",
                "execute",
                "live execution",
            ),
        }

        for marker in marker_groups["production"]:
            if marker in lower:
                result["production_markers"].append({
                    "line": line_number,
                    "marker": marker,
                    "source": line.strip(),
                })

        for marker in marker_groups["order"]:
            if marker in lower:
                result["order_markers"].append({
                    "line": line_number,
                    "marker": marker,
                    "source": line.strip(),
                })

        for marker in marker_groups["execution"]:
            if marker in lower:
                result["execution_markers"].append({
                    "line": line_number,
                    "marker": marker,
                    "source": line.strip(),
                })

    for node in ast.walk(tree):
        if isinstance(node, ast.If):

            test = node.test

            if (
                isinstance(test, ast.Compare)
                and len(test.ops) == 1
                and isinstance(test.ops[0], ast.Eq)
            ):
                left = dotted_name(test.left)

                if left == "__name__":
                    for comparator in test.comparators:
                        value = constant_string(comparator)

                        if value == "__main__":
                            result["main_guard"] = True

    return result, source, tree


def inspect_project_references():
    references = []

    for path in PROJECT_DIR.rglob("*.py"):

        if not path.is_file():
            continue

        if is_quarantined(path):
            continue

        if path.name == TARGET_NAME:
            continue

        try:
            source, tree, syntax_error = parse_python(path)
        except Exception:
            continue

        relative = str(path.relative_to(PROJECT_DIR))

        for line_number, line in enumerate(
            source.splitlines(),
            start=1,
        ):
            if TARGET_NAME.lower() in line.lower():
                references.append({
                    "file": relative,
                    "line": line_number,
                    "type": "TEXT_REFERENCE",
                    "source": line.strip(),
                })

        if tree is None:
            continue

        for node in ast.walk(tree):

            if isinstance(node, ast.Import):
                for alias in node.names:
                    if (
                        alias.name == "upgrade_db"
                        or alias.name.endswith(".upgrade_db")
                    ):
                        references.append({
                            "file": relative,
                            "line": node.lineno,
                            "type": "IMPORT",
                            "source": source_line(
                                source,
                                node.lineno,
                            ),
                        })

            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""

                if (
                    module == "upgrade_db"
                    or module.endswith(".upgrade_db")
                ):
                    references.append({
                        "file": relative,
                        "line": node.lineno,
                        "type": "FROM_IMPORT",
                        "source": source_line(
                            source,
                            node.lineno,
                        ),
                    })

            elif isinstance(node, ast.Call):
                call_name = dotted_name(node.func)

                if call_name in (
                    "exec",
                    "run",
                    "run_path",
                    "run_module",
                    "subprocess.run",
                    "subprocess.call",
                    "subprocess.check_call",
                ):
                    block_start = max(
                        0,
                        node.lineno - 1,
                    )

                    block_end = min(
                        len(source.splitlines()),
                        getattr(
                            node,
                            "end_lineno",
                            node.lineno,
                        ),
                    )

                    block = "\n".join(
                        source.splitlines()[
                            block_start:block_end
                        ]
                    )

                    if TARGET_NAME.lower() in block.lower():
                        references.append({
                            "file": relative,
                            "line": node.lineno,
                            "type": "EXECUTION_CALL",
                            "source": block.strip(),
                        })

    return references


def determine_classification(target, references):
    if not target["exists"]:
        return "TARGET_NOT_FOUND"

    if not target["syntax_pass"]:
        return "TARGET_SYNTAX_FAILURE"

    if references:
        return "LAUNCH_REACHABLE_REFERENCE_FOUND"

    if target["write_operations"]:
        return "STANDALONE_WRITE_TARGET_UNRESOLVED"

    return "NO_PROJECT_CALLCHAIN_FOUND"


def main():
    started = datetime.now(timezone.utc)

    target, source, tree = inspect_target()
    references = inspect_project_references()

    classification = determine_classification(
        target,
        references,
    )

    production_path_candidates = [
        item
        for item in target["db_paths"]
        if "arunda.db" in item["value"].lower()
    ]

    report = {
        "version": VERSION,
        "project_directory": str(PROJECT_DIR),
        "target_name": TARGET_NAME,
        "started_utc": started.isoformat(),
        "mode": "READ ONLY",
        "database_used": False,
        "network_used": False,
        "execution": False,
        "file_modification": False,
        "quarantine_used": False,
        "target": target,
        "project_references": references,
        "production_path_candidates": (
            production_path_candidates
        ),
        "classification": classification,
        "predictive_claim": "NOT_ESTABLISHED",
        "production_state_changed": False,
        "upgrade_db_executed": False,
        "finished_utc": datetime.now(
            timezone.utc
        ).isoformat(),
    }

    sep = "=" * 100
    dash = "-" * 100

    lines = []

    lines.extend([
        sep,
        "ARUNDA PROJECT UPGRADE DB CALLCHAIN FORENSIC v0.1",
        sep,
        f"Project Directory : {PROJECT_DIR}",
        f"Target            : {TARGET_NAME}",
        f"Started UTC       : {started.isoformat()}",
        f"Mode              : READ ONLY",
        f"Database          : NOT USED",
        f"Network           : NOT USED",
        f"Execution         : STATIC ANALYSIS ONLY",
        f"File Modification : FORBIDDEN",
        f"Quarantine        : NOT USED",
        "",
        sep,
        "TARGET",
        sep,
        f"EXISTS            : {target['exists']}",
        f"SYNTAX PASS       : {target['syntax_pass']}",
        f"SHA256            : {target['sha256']}",
        f"MAIN FUNCTION     : "
        f"{any(x['name'] == 'main' for x in target['functions'])}",
        f"MAIN GUARD        : {target['main_guard']}",
        "",
        "FUNCTIONS",
    ])

    if target["functions"]:
        for item in target["functions"]:
            lines.append(
                f"  - {item['name']} "
                f"(line {item['line']})"
            )
    else:
        lines.append("  - None")

    lines.extend([
        "",
        "IMPORTS",
    ])

    if target["imports"]:
        for item in target["imports"]:
            lines.append(
                f"  - {item['module']} "
                f"(line {item['line']})"
            )
    else:
        lines.append("  - None")

    lines.extend([
        "",
        sep,
        "DATABASE CONNECTIVITY",
        sep,
        f"CONNECT CALLS : "
        f"{len(target['db_connect_calls'])}",
        f"DB PATHS      : "
        f"{len(target['db_paths'])}",
    ])

    for item in target["db_connect_calls"]:
        lines.extend([
            dash,
            f"LINE   : {item['line']}",
            f"SOURCE : {item['source']}",
        ])

    for item in target["db_paths"]:
        lines.extend([
            dash,
            f"LINE  : {item['line']}",
            f"VALUE : {item['value']}",
        ])

    lines.extend([
        "",
        sep,
        "WRITE OPERATIONS",
        sep,
    ])

    if target["write_operations"]:
        for item in target["write_operations"]:
            lines.extend([
                dash,
                f"LINE   : {item['line']}",
                f"TYPE   : {item['type']}",
                f"SOURCE : {item['source']}",
            ])
    else:
        lines.append("NONE")

    lines.extend([
        "",
        sep,
        "DIRECT PROJECT REFERENCES",
        sep,
    ])

    if references:
        for item in references:
            lines.extend([
                dash,
                f"FILE   : {item['file']}",
                f"LINE   : {item['line']}",
                f"TYPE   : {item['type']}",
                f"SOURCE : {item['source']}",
            ])
    else:
        lines.append("NONE")

    lines.extend([
        "",
        sep,
        "PRODUCTION PATH CANDIDATES",
        sep,
    ])

    if production_path_candidates:
        for item in production_path_candidates:
            lines.append(
                f"LINE {item['line']} : {item['value']}"
            )
    else:
        lines.append("NONE")

    lines.extend([
        "",
        sep,
        "CALLCHAIN CLASSIFICATION",
        sep,
        f"CLASSIFICATION : {classification}",
        "",
        sep,
        "FORENSIC VERDICT",
        sep,
        f"FORENSIC STATUS : {classification}",
        "PREDICTIVE CLAIM : NOT_ESTABLISHED",
        "DATABASE USED    : False",
        "NETWORK USED     : False",
        "EXECUTION        : False",
        "FILE MODIFICATION: False",
        "QUARANTINE USED  : False",
        "",
        "IMPORTANT:",
        "This artifact does NOT execute upgrade_db.py.",
        "This artifact does NOT open arunda.db.",
        "This artifact does NOT execute SQL.",
        "This artifact does NOT modify production state.",
        "",
        sep,
        "ARTIFACT",
        sep,
        f"Artifact : {OUTPUT_JSON}",
        f"Report   : {OUTPUT_TXT}",
        sep,
    ])

    final_text = "\n".join(lines)

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
