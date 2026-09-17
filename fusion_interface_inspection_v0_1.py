# =============================================================================
# ARUNDA FUSION INTERFACE INSPECTION v0.1
# =============================================================================
# READ ONLY
# NO FUSION EXECUTION
# NO PRODUCTION DB WRITE
# NO SIGNAL EXECUTION
# NO SCORE
# NO DECISION
# NO ORDER INTENT
# NO EXECUTION
# =============================================================================

from pathlib import Path
import ast
import importlib
import inspect
import sys


ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

print("=" * 90)
print("ARUNDA FUSION INTERFACE INSPECTION v0.1")
print("=" * 90)
print("ROOT              :", ROOT)
print("FUSION EXECUTION  : OFF")
print("PRODUCTION WRITE  : OFF")
print("SCORE             : OFF")
print("DECISION          : OFF")
print("ORDER INTENTS     : 0")
print("EXECUTION         : OFF")
print()


# =============================================================================
# FIND FUSION CANDIDATES
# =============================================================================

patterns = [
    "fusion*.py",
    "*fusion*.py",
]

files = {}

for pattern in patterns:
    for p in ROOT.glob(pattern):
        if p.is_file():
            files[str(p.resolve())] = p

files = sorted(
    files.values(),
    key=lambda p: p.name.lower()
)

print("=" * 90)
print("FUSION FILE CANDIDATES")
print("=" * 90)

if not files:
    print("NONE")

else:
    for p in files:
        print(p)

print()


# =============================================================================
# AST INSPECTION
# =============================================================================

def inspect_file(path):

    print("=" * 90)
    print("FILE:", path)
    print("=" * 90)

    try:
        source = path.read_text(
            encoding="utf-8",
            errors="replace"
        )

        tree = ast.parse(source)

    except Exception as exc:

        print("AST_PARSE_ERROR:", repr(exc))
        return

    print("SIZE_BYTES:", path.stat().st_size)

    print()
    print("MODULE CONSTANTS:")

    for node in tree.body:

        if isinstance(
            node,
            ast.Assign
        ):

            for target in node.targets:

                if isinstance(
                    target,
                    ast.Name
                ):

                    name = target.id

                    if (
                        name.isupper()
                        or "VERSION" in name.upper()
                        or "ENGINE" in name.upper()
                        or "CONTRACT" in name.upper()
                    ):

                        try:
                            value = ast.literal_eval(
                                node.value
                            )
                        except Exception:
                            value = "<non-literal>"

                        print(
                            f"  {name} = {value!r}"
                        )

        elif isinstance(
            node,
            ast.AnnAssign
        ):

            if isinstance(
                node.target,
                ast.Name
            ):

                name = node.target.id

                if (
                    name.isupper()
                    or "VERSION" in name.upper()
                    or "ENGINE" in name.upper()
                    or "CONTRACT" in name.upper()
                ):

                    try:
                        value = ast.literal_eval(
                            node.value
                        ) if node.value else None
                    except Exception:
                        value = "<non-literal>"

                    print(
                        f"  {name} = {value!r}"
                    )

    print()
    print("PUBLIC FUNCTIONS:")

    for node in tree.body:

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            )
        ):

            args = []

            for arg in node.args.args:
                args.append(arg.arg)

            print(
                f"  {node.name}({', '.join(args)})"
            )

    print()
    print("CLASSES:")

    for node in tree.body:

        if isinstance(
            node,
            ast.ClassDef
        ):

            print(
                f"  class {node.name}"
            )

            for child in node.body:

                if isinstance(
                    child,
                    (
                        ast.FunctionDef,
                        ast.AsyncFunctionDef,
                    )
                ):

                    args = []

                    for arg in child.args.args:
                        args.append(arg.arg)

                    print(
                        f"      {child.name}("
                        f"{', '.join(args)})"
                    )

    print()
    print("IMPORTS:")

    for node in tree.body:

        if isinstance(
            node,
            ast.Import
        ):

            for alias in node.names:
                print(
                    "  import",
                    alias.name
                )

        elif isinstance(
            node,
            ast.ImportFrom
        ):

            module = node.module or ""

            names = ", ".join(
                alias.name
                for alias in node.names
            )

            print(
                f"  from {module} import {names}"
            )

    print()
    print("FUSION-RELATED SYMBOLS:")

    keywords = [
        "fusion",
        "signal",
        "score",
        "decision",
        "calculate",
        "build",
        "validate",
        "persist",
        "insert",
        "update",
        "write",
        "db",
    ]

    found = set()

    for node in ast.walk(tree):

        if isinstance(
            node,
            ast.Name
        ):

            name = node.id

            low = name.lower()

            if any(
                k in low
                for k in keywords
            ):
                found.add(name)

        elif isinstance(
            node,
            ast.Attribute
        ):

            name = node.attr

            low = name.lower()

            if any(
                k in low
                for k in keywords
            ):
                found.add(name)

    for name in sorted(found):

        print(
            "  ",
            name
        )


# =============================================================================
# INSPECT ONLY LIKELY PRIMARY FILES
# =============================================================================

for path in files:

    lower = path.name.lower()

    if (
        lower.startswith("fusion")
        or lower == "fusion_engine.py"
        or "fusion_v0.5" in lower
        or "fusion_engine_v0.5" in lower
    ):

        inspect_file(path)


# =============================================================================
# IMPORT TEST — NO EXECUTION
# =============================================================================

print()
print("=" * 90)
print("IMPORT INTERFACE TEST")
print("=" * 90)

module_names = []

for path in files:

    if path.parent == ROOT:

        name = path.stem

        if (
            name.startswith("fusion")
            and name.isidentifier()
        ):
            module_names.append(name)

module_names = sorted(
    set(module_names)
)

for name in module_names:

    print()
    print("MODULE:", name)

    try:

        module = importlib.import_module(
            name
        )

        print(
            "IMPORT=PASS"
        )

        print(
            "VERSION=",
            getattr(
                module,
                "ENGINE_VERSION",
                getattr(
                    module,
                    "VERSION",
                    None
                )
            )
        )

        print(
            "ENGINE=",
            getattr(
                module,
                "ENGINE",
                None
            )
        )

        print(
            "PUBLIC CALLABLES:"
        )

        for attr_name in sorted(
            dir(module)
        ):

            if attr_name.startswith("_"):
                continue

            try:
                obj = getattr(
                    module,
                    attr_name
                )
            except Exception:
                continue

            if callable(obj):

                try:
                    signature = inspect.signature(
                        obj
                    )
                except Exception:
                    signature = "(signature unavailable)"

                print(
                    f"  {attr_name}{signature}"
                )

    except Exception as exc:

        print(
            "IMPORT=FAILED"
        )

        print(
            "ERROR=",
            repr(exc)
        )


# =============================================================================
# SAFETY SCAN
# =============================================================================

print()
print("=" * 90)
print("STATIC SAFETY SCAN")
print("=" * 90)

dangerous_terms = [
    "sqlite3.connect",
    "INSERT INTO",
    "UPDATE ",
    "DELETE FROM",
    "CREATE TABLE",
    "executemany",
    "commit(",
]

for path in files:

    try:
        text = path.read_text(
            encoding="utf-8",
            errors="replace"
        )
    except Exception:
        continue

    hits = []

    upper = text.upper()

    for term in dangerous_terms:

        if term.upper() in upper:
            hits.append(term)

    if hits:

        print(
            path.name,
            "DB/WRITE TOKENS:",
            ", ".join(hits)
        )

    else:

        print(
            path.name,
            "DB/WRITE TOKENS: NONE"
        )


print()
print("=" * 90)
print("INSPECTION COMPLETE")
print("=" * 90)
print("NO FUSION RUNTIME EXECUTED")
print("NO PRODUCTION DB WRITE")
print("NO SCORE")
print("NO DECISION")
print("NO ORDER INTENT")
print("EXECUTION=OFF")
print("=" * 90)
