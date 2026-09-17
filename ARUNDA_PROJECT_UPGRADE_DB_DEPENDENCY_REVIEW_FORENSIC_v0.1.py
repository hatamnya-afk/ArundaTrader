import ast
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VERSION = "v0.1"

PROJECT_DIR = Path(r"C:\Users\ASUS\ArundaTrader")
TARGET_NAME = "upgrade_db.py"

QUARANTINE_DIR_NAME = "_QUARANTINE_NONPRODUCTION_SYNTAX_FAILURES"

OUTPUT_JSON = (
    PROJECT_DIR
    / "ARUNDA_PROJECT_UPGRADE_DB_DEPENDENCY_REVIEW_FORENSIC_v0.1.json"
)

OUTPUT_TXT = (
    PROJECT_DIR
    / "ARUNDA_PROJECT_UPGRADE_DB_DEPENDENCY_REVIEW_FORENSIC_v0.1.txt"
)


WRITE_SQL_TERMS = {
    "CREATE TABLE": "CREATE",
    "CREATE INDEX": "CREATE",
    "CREATE VIEW": "CREATE",
    "INSERT INTO": "INSERT",
    "INSERT OR": "INSERT",
    "UPDATE ": "UPDATE",
    "DELETE FROM": "DELETE",
    "ALTER TABLE": "ALTER",
    "DROP TABLE": "DROP",
    "DROP INDEX": "DROP",
}

DB_CONNECT_TERMS = (
    "sqlite3.connect",
    "connect_db",
    "DB_PATH",
    "DATABASE",
    "DATABASE_PATH",
)

PRODUCTION_TERMS = (
    "production",
    "prod",
    "arunda.db",
)

LAUNCH_TERMS = (
    "launch",
    "live",
    "paper",
    "pipeline",
    "scheduler",
    "main",
    "execution",
    "trade",
    "order",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


def relative_path(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_DIR))
    except ValueError:
        return str(path)


def is_quarantined(path: Path) -> bool:
    try:
        relative = path.relative_to(PROJECT_DIR)
    except ValueError:
        return False

    return QUARANTINE_DIR_NAME in relative.parts


def read_source(path: Path) -> tuple[str | None, str | None]:
    try:
        return path.read_text(encoding="utf-8"), None
    except UnicodeDecodeError:
        try:
            return path.read_text(encoding="utf-8-sig"), None
        except Exception as exc:
            return None, repr(exc)
    except Exception as exc:
        return None, repr(exc)


def syntax_check(
    source: str,
) -> tuple[bool, str | None, int | None, int | None]:
    try:
        ast.parse(source)
        return True, None, None, None
    except SyntaxError as exc:
        return (
            False,
            exc.msg,
            exc.lineno,
            exc.offset,
        )


def safe_unparse(node: ast.AST) -> str:
    try:
        return ast.unparse(node)
    except Exception:
        return ""


def find_target_file() -> Path | None:
    direct = PROJECT_DIR / TARGET_NAME

    if direct.exists() and direct.is_file():
        return direct

    matches = []

    for path in PROJECT_DIR.rglob(TARGET_NAME):
        if is_quarantined(path):
            continue

        if path.is_file():
            matches.append(path)

    if not matches:
        return None

    matches.sort(
        key=lambda p: (
            len(p.parts),
            str(p).lower(),
        )
    )

    return matches[0]


def python_files() -> list[Path]:
    files = []

    for path in PROJECT_DIR.rglob("*.py"):
        if is_quarantined(path):
            continue

        if path.is_file():
            files.append(path)

    files.sort(key=lambda p: str(p).lower())

    return files


def collect_import_references(
    source: str,
    source_path: Path,
) -> list[dict[str, Any]]:
    references = []

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return references

    target_stem = Path(TARGET_NAME).stem

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported = alias.name

                if (
                    imported == target_stem
                    or imported.endswith("." + target_stem)
                ):
                    references.append(
                        {
                            "kind": "IMPORT",
                            "line": node.lineno,
                            "column": node.col_offset + 1,
                            "target": imported,
                        }
                    )

        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""

            if (
                module == target_stem
                or module.endswith("." + target_stem)
            ):
                references.append(
                    {
                        "kind": "FROM_IMPORT",
                        "line": node.lineno,
                        "column": node.col_offset + 1,
                        "target": module,
                    }
                )

    return references


def collect_textual_references(
    source: str,
    source_path: Path,
) -> list[dict[str, Any]]:
    references = []

    target_variants = {
        TARGET_NAME.lower(),
        Path(TARGET_NAME).stem.lower(),
    }

    for number, line in enumerate(
        source.splitlines(),
        start=1,
    ):
        lower = line.lower()

        for target in target_variants:
            if target in lower:
                references.append(
                    {
                        "kind": "TEXT_REFERENCE",
                        "line": number,
                        "column": lower.find(target) + 1,
                        "target": target,
                        "source": line.strip(),
                    }
                )
                break

    return references


def collect_execution_references(
    source: str,
    source_path: Path,
) -> list[dict[str, Any]]:
    references = []

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return references

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            call_text = safe_unparse(node)

            if not call_text:
                continue

            lower = call_text.lower()

            if TARGET_NAME.lower() in lower:
                references.append(
                    {
                        "kind": "CALL_REFERENCE",
                        "line": node.lineno,
                        "column": node.col_offset + 1,
                        "source": call_text[:500],
                    }
                )

            if (
                "subprocess" in lower
                and (
                    TARGET_NAME.lower() in lower
                    or Path(TARGET_NAME).stem.lower() in lower
                )
            ):
                references.append(
                    {
                        "kind": "SUBPROCESS_REFERENCE",
                        "line": node.lineno,
                        "column": node.col_offset + 1,
                        "source": call_text[:500],
                    }
                )

            if (
                "runpy" in lower
                and (
                    TARGET_NAME.lower() in lower
                    or Path(TARGET_NAME).stem.lower() in lower
                )
            ):
                references.append(
                    {
                        "kind": "RUNPY_REFERENCE",
                        "line": node.lineno,
                        "column": node.col_offset + 1,
                        "source": call_text[:500],
                    }
                )

    return references


def collect_upgrade_db_structure(
    source: str,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "functions": [],
        "imports": [],
        "main_function": False,
        "main_guard": False,
        "db_paths": [],
        "db_connect_calls": [],
        "write_operations": [],
        "production_markers": [],
        "launch_markers": [],
    }

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return result

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            result["functions"].append(
                {
                    "name": node.name,
                    "line": node.lineno,
                    "end_line": getattr(
                        node,
                        "end_lineno",
                        None,
                    ),
                }
            )

            if node.name == "main":
                result["main_function"] = True

        elif isinstance(node, ast.Import):
            for alias in node.names:
                result["imports"].append(alias.name)

        elif isinstance(node, ast.ImportFrom):
            result["imports"].append(
                node.module or ""
            )

        elif isinstance(node, ast.Call):
            call_text = safe_unparse(node)

            if not call_text:
                continue

            lower = call_text.lower()

            if (
                "sqlite3.connect" in lower
                or "connect_db(" in lower
            ):
                result["db_connect_calls"].append(
                    {
                        "line": node.lineno,
                        "source": call_text[:500],
                    }
                )

        elif isinstance(node, ast.Assign):
            value_text = safe_unparse(node.value)

            for target in node.targets:
                target_text = safe_unparse(target)

                if "DB_PATH" in target_text.upper():
                    result["db_paths"].append(
                        {
                            "line": node.lineno,
                            "target": target_text,
                            "value": value_text[:500],
                        }
                    )

    for number, line in enumerate(
        source.splitlines(),
        start=1,
    ):
        upper = line.upper()
        lower = line.lower()

        for sql_term, write_type in WRITE_SQL_TERMS.items():
            if sql_term in upper:
                result["write_operations"].append(
                    {
                        "line": number,
                        "type": write_type,
                        "sql_term": sql_term,
                        "source": line.strip(),
                    }
                )

        for term in PRODUCTION_TERMS:
            if term in lower:
                result["production_markers"].append(
                    {
                        "line": number,
                        "term": term,
                        "source": line.strip(),
                    }
                )

        for term in LAUNCH_TERMS:
            if term in lower:
                result["launch_markers"].append(
                    {
                        "line": number,
                        "term": term,
                        "source": line.strip(),
                    }
                )

    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            test_text = safe_unparse(node.test)

            normalized = (
                test_text
                .replace(" ", "")
                .replace("\t", "")
                .lower()
            )

            if (
                "__name__" in normalized
                and "__main__" in normalized
            ):
                result["main_guard"] = True

    result["imports"] = sorted(
        set(result["imports"])
    )

    return result


def classify_dependency(
    target_exists: bool,
    target_syntax_pass: bool,
    direct_refs: list[dict[str, Any]],
    db_paths: list[dict[str, Any]],
    write_operations: list[dict[str, Any]],
    production_markers: list[dict[str, Any]],
) -> tuple[str, list[str]]:

    reasons = []

    if not target_exists:
        return (
            "TARGET_NOT_FOUND",
            ["upgrade_db.py_not_found"],
        )

    if not target_syntax_pass:
        reasons.append(
            "target_syntax_failure"
        )

    if direct_refs:
        reasons.append(
            "direct_project_reference_found"
        )

    if write_operations:
        reasons.append(
            "database_write_operations_present"
        )

    if db_paths:
        reasons.append(
            "database_path_present"
        )

    if production_markers:
        reasons.append(
            "production_markers_present"
        )

    if production_markers and direct_refs:
        return (
            "DIRECT_PRODUCTION_DEPENDENCY",
            reasons,
        )

    if direct_refs and write_operations:
        return (
            "LAUNCH_REACHABLE_UNRESOLVED",
            reasons,
        )

    if write_operations and db_paths:
        return (
            "STANDALONE_WRITE_TOOL_UNRESOLVED",
            reasons,
        )

    if write_operations:
        return (
            "STANDALONE_TOOLING",
            reasons,
        )

    if direct_refs:
        return (
            "DIRECT_PROJECT_DEPENDENCY",
            reasons,
        )

    return (
        "STANDALONE_TOOLING",
        reasons,
    )


def build_reference_inventory(
    target: Path,
) -> dict[str, Any]:

    references = []

    for path in python_files():

        if path.resolve() == target.resolve():
            continue

        source, read_error = read_source(path)

        if source is None:
            continue

        ast_refs = collect_import_references(
            source,
            path,
        )

        text_refs = collect_textual_references(
            source,
            path,
        )

        execution_refs = collect_execution_references(
            source,
            path,
        )

        all_refs = (
            ast_refs
            + text_refs
            + execution_refs
        )

        if all_refs:
            references.append(
                {
                    "file": relative_path(path),
                    "sha256": sha256_file(path),
                    "references": all_refs,
                }
            )

    return {
        "files_with_references": references,
        "count": len(references),
    }


def make_report() -> dict[str, Any]:
    started = utc_now()

    target = find_target_file()

    if target is None:
        finished = utc_now()

        return {
            "version": VERSION,
            "frontier": (
                "UPGRADE_DB_DEPENDENCY_REVIEW"
            ),
            "started_utc": started,
            "finished_utc": finished,
            "project_directory": str(PROJECT_DIR),
            "target": TARGET_NAME,
            "target_exists": False,
            "forensic_status": "TARGET_NOT_FOUND",
            "database_used": False,
            "network_used": False,
            "execution_performed": False,
            "file_modification": False,
        }

    source, read_error = read_source(target)

    if source is None:
        finished = utc_now()

        return {
            "version": VERSION,
            "frontier": (
                "UPGRADE_DB_DEPENDENCY_REVIEW"
            ),
            "started_utc": started,
            "finished_utc": finished,
            "project_directory": str(PROJECT_DIR),
            "target": relative_path(target),
            "target_exists": True,
            "read_error": read_error,
            "forensic_status": "READ_ERROR",
            "database_used": False,
            "network_used": False,
            "execution_performed": False,
            "file_modification": False,
        }

    (
        syntax_pass,
        syntax_error,
        syntax_line,
        syntax_column,
    ) = syntax_check(source)

    structure = collect_upgrade_db_structure(
        source
    )

    inventory = build_reference_inventory(
        target
    )

    references = inventory[
        "files_with_references"
    ]

    direct_refs = []

    for item in references:
        direct_refs.extend(
            item["references"]
        )

    classification, reasons = classify_dependency(
        target_exists=True,
        target_syntax_pass=syntax_pass,
        direct_refs=direct_refs,
        db_paths=structure["db_paths"],
        write_operations=structure[
            "write_operations"
        ],
        production_markers=structure[
            "production_markers"
        ],
    )

    production_path_candidates = []

    for item in structure["db_paths"]:
        value = item.get("value", "")

        if (
            "arunda.db" in value.lower()
            or "production" in value.lower()
            or "prod" in value.lower()
        ):
            production_path_candidates.append(item)

    if production_path_candidates:
        if (
            classification
            == "STANDALONE_WRITE_TOOL_UNRESOLVED"
        ):
            classification = (
                "PRODUCTION_DB_PATH_UNRESOLVED"
            )
            reasons.append(
                "production_db_path_candidate_found"
            )

    if (
        direct_refs
        and structure["write_operations"]
        and not production_path_candidates
    ):
        classification = (
            "LAUNCH_REACHABLE_UNRESOLVED"
        )

    if (
        not direct_refs
        and structure["write_operations"]
    ):
        classification = (
            "STANDALONE_WRITE_TOOL_UNRESOLVED"
        )

    finished = utc_now()

    return {
        "version": VERSION,
        "frontier": (
            "UPGRADE_DB_DEPENDENCY_REVIEW"
        ),
        "started_utc": started,
        "finished_utc": finished,
        "project_directory": str(PROJECT_DIR),
        "target": relative_path(target),
        "target_exists": True,
        "target_sha256": sha256_file(target),
        "syntax_pass": syntax_pass,
        "syntax_error": syntax_error,
        "syntax_line": syntax_line,
        "syntax_column": syntax_column,
        "functions": structure["functions"],
        "imports": structure["imports"],
        "main_function": structure[
            "main_function"
        ],
        "main_guard": structure[
            "main_guard"
        ],
        "db_paths": structure["db_paths"],
        "db_connect_calls": structure[
            "db_connect_calls"
        ],
        "write_operations": structure[
            "write_operations"
        ],
        "production_markers": structure[
            "production_markers"
        ],
        "launch_markers": structure[
            "launch_markers"
        ],
        "production_path_candidates": (
            production_path_candidates
        ),
        "direct_project_references": references,
        "direct_reference_count": inventory[
            "count"
        ],
        "classification": classification,
        "classification_reasons": reasons,
        "forensic_status": (
            "DEPENDENCY_REVIEW_COMPLETE"
        ),
        "predictive_claim": (
            "NOT_ESTABLISHED"
        ),
        "database_used": False,
        "network_used": False,
        "execution_performed": False,
        "file_modification": False,
        "deletion_performed": False,
        "quarantine_performed": False,
    }


def render_report(report: dict[str, Any]) -> str:
    sep = "=" * 100
    thin = "-" * 100

    lines = []

    lines.append(sep)
    lines.append(
        "ARUNDA PROJECT UPGRADE DB DEPENDENCY "
        "REVIEW FORENSIC " + VERSION
    )
    lines.append(sep)

    lines.append(
        f"Project Directory : "
        f"{report.get('project_directory')}"
    )
    lines.append(
        f"Target            : "
        f"{report.get('target')}"
    )
    lines.append(
        f"Started UTC       : "
        f"{report.get('started_utc')}"
    )
    lines.append(
        f"Finished UTC      : "
        f"{report.get('finished_utc')}"
    )
    lines.append(
        "Mode              : READ ONLY"
    )
    lines.append(
        "Database          : NOT USED"
    )
    lines.append(
        "Network           : FORBIDDEN"
    )
    lines.append(
        "Execution         : STATIC ANALYSIS ONLY"
    )
    lines.append(
        "File Modification : FORBIDDEN"
    )

    lines.append(sep)
    lines.append("TARGET")
    lines.append(sep)

    lines.append(
        f"EXISTS            : "
        f"{report.get('target_exists')}"
    )
    lines.append(
        f"SYNTAX PASS       : "
        f"{report.get('syntax_pass')}"
    )
    lines.append(
        f"SHA256            : "
        f"{report.get('target_sha256', 'N/A')}"
    )

    if report.get("syntax_error"):
        lines.append(
            f"SYNTAX ERROR      : "
            f"{report.get('syntax_error')}"
        )
        lines.append(
            f"ERROR LINE        : "
            f"{report.get('syntax_line')}"
        )
        lines.append(
            f"ERROR COLUMN      : "
            f"{report.get('syntax_column')}"
        )

    lines.append(sep)
    lines.append("EXECUTION STRUCTURE")
    lines.append(sep)

    lines.append(
        f"MAIN FUNCTION     : "
        f"{report.get('main_function')}"
    )
    lines.append(
        f"MAIN GUARD        : "
        f"{report.get('main_guard')}"
    )

    lines.append("")
    lines.append("FUNCTIONS")

    for item in report.get("functions", []):
        lines.append(
            f"  - {item['name']} "
            f"(line {item['line']})"
        )

    if not report.get("functions"):
        lines.append("  - None")

    lines.append("")
    lines.append("IMPORTS")

    for item in report.get("imports", []):
        lines.append(
            f"  - {item}"
        )

    if not report.get("imports"):
        lines.append("  - None")

    lines.append(sep)
    lines.append("DATABASE PATH / CONNECTIVITY")
    lines.append(sep)

    lines.append("DB PATHS")

    for item in report.get("db_paths", []):
        lines.append(
            f"  LINE {item['line']} | "
            f"{item['target']} = "
            f"{item['value']}"
        )

    if not report.get("db_paths"):
        lines.append("  - None")

    lines.append("")
    lines.append("DB CONNECT CALLS")

    for item in report.get("db_connect_calls", []):
        lines.append(
            f"  LINE {item['line']} | "
            f"{item['source']}"
        )

    if not report.get("db_connect_calls"):
        lines.append("  - None")

    lines.append(sep)
    lines.append("WRITE OPERATIONS")
    lines.append(sep)

    writes = report.get(
        "write_operations",
        [],
    )

    if not writes:
        lines.append("NONE")
    else:
        for item in writes:
            lines.append(
                f"LINE {item['line']} | "
                f"TYPE {item['type']} | "
                f"{item['source']}"
            )

    lines.append(sep)
    lines.append("PRODUCTION PATH CANDIDATES")
    lines.append(sep)

    candidates = report.get(
        "production_path_candidates",
        [],
    )

    if not candidates:
        lines.append("NONE")
    else:
        for item in candidates:
            lines.append(
                f"LINE {item['line']} | "
                f"{item['value']}"
            )

    lines.append(sep)
    lines.append("DIRECT PROJECT REFERENCES")
    lines.append(sep)

    references = report.get(
        "direct_project_references",
        [],
    )

    if not references:
        lines.append("NONE")
    else:
        for item in references:
            lines.append(
                f"FILE : {item['file']}"
            )
            lines.append(
                f"SHA256 : {item['sha256']}"
            )

            for ref in item["references"]:
                lines.append(
                    f"  {ref['kind']} | "
                    f"LINE {ref['line']} | "
                    f"{ref.get('source', ref.get('target', ''))}"
                )

            lines.append(thin)

    lines.append(sep)
    lines.append("LAUNCH MARKERS")
    lines.append(sep)

    markers = report.get(
        "launch_markers",
        [],
    )

    if not markers:
        lines.append("NONE")
    else:
        unique = sorted(
            {
                (
                    item["term"],
                    item["line"],
                )
                for item in markers
            }
        )

        for term, line in unique:
            lines.append(
                f"LINE {line} | {term}"
            )

    lines.append(sep)
    lines.append("DEPENDENCY CLASSIFICATION")
    lines.append(sep)

    lines.append(
        f"CLASSIFICATION : "
        f"{report.get('classification')}"
    )

    lines.append("REASONS:")

    for reason in report.get(
        "classification_reasons",
        [],
    ):
        lines.append(
            f"  - {reason}"
        )

    if not report.get(
        "classification_reasons"
    ):
        lines.append("  - None")

    lines.append(sep)
    lines.append("FORENSIC VERDICT")
    lines.append(sep)

    lines.append(
        f"FORENSIC STATUS : "
        f"{report.get('forensic_status')}"
    )
    lines.append(
        f"PREDICTIVE CLAIM : "
        f"{report.get('predictive_claim')}"
    )
    lines.append(
        f"DATABASE USED    : "
        f"{report.get('database_used')}"
    )
    lines.append(
        f"NETWORK USED     : "
        f"{report.get('network_used')}"
    )
    lines.append(
        f"EXECUTION        : "
        f"{report.get('execution_performed')}"
    )
    lines.append(
        f"FILE MODIFICATION: "
        f"{report.get('file_modification')}"
    )

    lines.append("")
    lines.append(
        "This artifact does NOT execute upgrade_db.py."
    )
    lines.append(
        "This artifact does NOT open arunda.db."
    )
    lines.append(
        "This artifact does NOT modify production state."
    )

    lines.append(sep)
    lines.append("ARTIFACT")
    lines.append(sep)

    lines.append(
        f"Artifact : {OUTPUT_JSON}"
    )
    lines.append(
        f"Report   : {OUTPUT_TXT}"
    )

    return "\n".join(lines)


def main() -> None:
    report = make_report()

    OUTPUT_JSON.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    text = render_report(report)

    OUTPUT_TXT.write_text(
        text,
        encoding="utf-8",
    )

    print(text)


if __name__ == "__main__":
    main()