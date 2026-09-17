import ast
import os
from pathlib import Path


# =============================================================================
# ARUNDA PROJECT — DYNAMIC EXECUTION GRAPH FORENSIC v0.1
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent
TARGET_PIPELINE = BASE_DIR / "arunda_pipeline.py"
TARGET_UPGRADE = BASE_DIR / "upgrade_db.py"

DYNAMIC_APIS = {
    "importlib.import_module",
    "importlib.util.spec_from_file_location",
    "importlib.util.module_from_spec",
    "runpy.run_module",
    "runpy.run_path",
    "__import__",
    "exec",
    "eval",
    "subprocess.run",
    "subprocess.Popen",
    "subprocess.call",
    "os.system",
}


def source_segment(node):
    try:
        return ast.unparse(node)
    except Exception:
        return "<SOURCE_UNAVAILABLE>"


def dotted_name(node):
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        left = dotted_name(node.value)
        if left:
            return f"{left}.{node.attr}"
        return node.attr

    return None


def scan_file(path):
    result = {
        "file": str(path),
        "functions": [],
        "calls": [],
        "dynamic_calls": [],
        "upgrade_mentions": [],
    }

    try:
        source = path.read_text(
            encoding="utf-8-sig"
        )
    except Exception as exc:
        result["error"] = str(exc)
        return result

    try:
        tree = ast.parse(
            source,
            filename=str(path),
        )
    except Exception as exc:
        result["error"] = str(exc)
        return result

    for node in ast.walk(tree):

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            result["functions"].append({
                "name": node.name,
                "line": node.lineno,
            })

        if isinstance(node, ast.Call):

            name = dotted_name(node.func)

            if name:
                result["calls"].append({
                    "line": node.lineno,
                    "call": name,
                    "source": source_segment(node),
                })

                if name in DYNAMIC_APIS:
                    result["dynamic_calls"].append({
                        "line": node.lineno,
                        "call": name,
                        "source": source_segment(node),
                    })

        if isinstance(node, ast.Constant):
            if isinstance(node.value, str):
                text = node.value.lower()

                if (
                    "upgrade_db" in text
                    or "upgrade db" in text
                ):
                    result["upgrade_mentions"].append({
                        "line": getattr(
                            node,
                            "lineno",
                            None,
                        ),
                        "value": node.value,
                    })

    return result


def function_context(path, target_lines):
    try:
        source = path.read_text(
            encoding="utf-8-sig"
        )
        tree = ast.parse(
            source,
            filename=str(path),
        )
    except Exception:
        return []

    contexts = []

    for node in ast.walk(tree):

        if not isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            continue

        start = node.lineno
        end = getattr(
            node,
            "end_lineno",
            node.lineno,
        )

        hits = [
            line
            for line in target_lines
            if start <= line <= end
        ]

        if hits:
            contexts.append({
                "function": node.name,
                "start": start,
                "end": end,
                "hit_lines": hits,
            })

    return contexts


# =============================================================================
# HEADER
# =============================================================================

print("=" * 110)
print(
    "ARUNDA PROJECT — DYNAMIC EXECUTION GRAPH FORENSIC v0.1"
)
print("=" * 110)

print(
    "MODE                : READ ONLY"
)
print(
    "STATIC ANALYSIS     : YES"
)
print(
    "DATABASE ACCESS     : NONE"
)
print(
    "NETWORK ACCESS      : NONE"
)
print(
    "PROJECT EXECUTION   : NONE"
)
print(
    "FILE MODIFICATION   : NONE"
)

print()
print(
    f"PIPELINE             : {TARGET_PIPELINE}"
)
print(
    f"UPGRADE_DB           : {TARGET_UPGRADE}"
)

print()
print("-" * 110)
print("TARGET DYNAMIC PATH")
print("-" * 110)

print(
    "arunda_pipeline.py"
)
print(
    "      ↓"
)
print(
    "dispatcher / run_stage"
)
print(
    "      ↓"
)
print(
    "dynamic execution mechanism"
)
print(
    "      ↓"
)
print(
    "upgrade_db.py"
)


# =============================================================================
# PIPELINE ANALYSIS
# =============================================================================

print()
print("=" * 110)
print("1. ARUNDA_PIPELINE STATIC DYNAMIC-EXECUTION ANALYSIS")
print("=" * 110)

pipeline = scan_file(
    TARGET_PIPELINE
)

if "error" in pipeline:
    print(
        "ERROR:",
        pipeline["error"],
    )
    raise SystemExit(1)

print()
print("FUNCTIONS OF INTEREST:")

for item in pipeline["functions"]:
    if item["name"] in {
        "main",
        "run_stage",
        "classify_stage_output",
    }:
        print(
            f"  {item['name']:<30} "
            f"line {item['line']}"
        )


print()
print("DYNAMIC EXECUTION CALLS:")

if pipeline["dynamic_calls"]:

    for item in pipeline["dynamic_calls"]:

        print("-" * 100)
        print(
            f"LINE   : {item['line']}"
        )
        print(
            f"CALL   : {item['call']}"
        )
        print(
            f"SOURCE : {item['source']}"
        )

else:

    print(
        "NO STATIC DYNAMIC EXECUTION API FOUND"
    )


# =============================================================================
# UPGRADE_DB MENTIONS INSIDE PIPELINE
# =============================================================================

print()
print("=" * 110)
print("2. UPGRADE_DB REFERENCES INSIDE ARUNDA_PIPELINE.PY")
print("=" * 110)

if pipeline["upgrade_mentions"]:

    for item in pipeline["upgrade_mentions"]:

        print("-" * 100)
        print(
            f"LINE  : {item['line']}"
        )
        print(
            f"VALUE : {item['value']!r}"
        )

else:

    print(
        "NO upgrade_db STATIC STRING REFERENCE FOUND"
    )


# =============================================================================
# RUN_STAGE CONTEXT
# =============================================================================

print()
print("=" * 110)
print("3. RUN_STAGE / DISPATCHER DYNAMIC CONTEXT")
print("=" * 110)

interesting_lines = []

for item in pipeline["dynamic_calls"]:
    interesting_lines.append(
        item["line"]
    )

contexts = function_context(
    TARGET_PIPELINE,
    interesting_lines,
)

if contexts:

    for item in contexts:

        print("-" * 100)
        print(
            f"FUNCTION : {item['function']}"
        )
        print(
            f"RANGE    : "
            f"{item['start']} - {item['end']}"
        )
        print(
            f"HITS     : "
            f"{item['hit_lines']}"
        )

else:

    print(
        "NO DYNAMIC CALL FALLS INSIDE "
        "A DETECTED FUNCTION CONTEXT"
    )


# =============================================================================
# FULL STATIC CALLS AROUND RUN_STAGE
# =============================================================================

print()
print("=" * 110)
print("4. STATIC CALLS INSIDE run_stage()")
print("=" * 110)

try:
    source = TARGET_PIPELINE.read_text(
        encoding="utf-8-sig"
    )
    tree = ast.parse(
        source,
        filename=str(TARGET_PIPELINE),
    )
except Exception as exc:
    print("ERROR:", exc)
    raise SystemExit(1)


run_stage_node = None

for node in ast.walk(tree):

    if isinstance(
        node,
        (
            ast.FunctionDef,
            ast.AsyncFunctionDef,
        ),
    ):

        if node.name == "run_stage":
            run_stage_node = node
            break


if run_stage_node is None:

    print(
        "run_stage() NOT FOUND"
    )

else:

    calls = []

    for node in ast.walk(
        run_stage_node
    ):

        if isinstance(
            node,
            ast.Call,
        ):

            name = dotted_name(
                node.func
            )

            calls.append({
                "line": node.lineno,
                "call": name or "<UNKNOWN>",
                "source": source_segment(node),
            })

    if calls:

        for item in sorted(
            calls,
            key=lambda x: x["line"],
        ):

            print(
                f"{item['line']:>6} | "
                f"{item['call']:<40} | "
                f"{item['source']}"
            )

    else:

        print(
            "NO CALLS FOUND INSIDE run_stage()"
        )


# =============================================================================
# UPGRADE_DB STRUCTURE
# =============================================================================

print()
print("=" * 110)
print("5. UPGRADE_DB.PY STRUCTURE")
print("=" * 110)

upgrade = scan_file(
    TARGET_UPGRADE
)

if "error" in upgrade:

    print(
        "ERROR:",
        upgrade["error"],
    )

else:

    print()
    print("FUNCTIONS:")

    for item in upgrade["functions"]:

        print(
            f"  {item['name']:<40} "
            f"line {item['line']}"
        )

    print()
    print("DYNAMIC CALLS:")

    if upgrade["dynamic_calls"]:

        for item in upgrade["dynamic_calls"]:

            print("-" * 100)
            print(
                f"LINE   : {item['line']}"
            )
            print(
                f"CALL   : {item['call']}"
            )
            print(
                f"SOURCE : {item['source']}"
            )

    else:

        print(
            "NONE"
        )


# =============================================================================
# FINAL
# =============================================================================

print()
print("=" * 110)
print("FINAL FORENSIC STATUS")
print("=" * 110)

print(
    "READ ONLY          : YES"
)
print(
    "STATIC ONLY        : YES"
)
print(
    "DATABASE           : NONE"
)
print(
    "NETWORK            : NONE"
)
print(
    "PROJECT EXECUTION  : NONE"
)
print(
    "FILE MODIFICATION  : NONE"
)

print()
print(
    "QUESTION TO RESOLVE:"
)

print(
    "HOW DOES arunda_pipeline.py RESOLVE AND EXECUTE "
    "A STAGE DYNAMICALLY?"
)

print()
print(
    "TARGET:"
)

print(
    "launcher -> main -> arunda_pipeline.py "
    "-> dispatcher -> dynamic execution -> upgrade_db.py"
)

print()
print(
    "FORENSIC STATUS : COMPLETE"
)

print("=" * 110)