from pathlib import Path
import ast
import re

ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

TARGETS = {
    "decision_engine",
    "signal_scorer",
    "signal_validator",
    "feature_engine",
    "feature_contract",
}

CALL_PATTERNS = [
    "decision_engine",
    "signal_scorer",
    "signal_validator",
    "feature_engine",
    "load_scores",
    "build_decision",
    "build_decision_snapshot",
    "run(",
    "main(",
]

print("=" * 100)
print("ARUNDA DECISION ENGINE RUNTIME INPUT BOUNDARY FORENSIC v0.1")
print("=" * 100)
print("MODE       : READ ONLY")
print("ROOT       :", ROOT)
print("WRITE      : NONE")
print("SQL        : NOT USED")
print("=" * 100)


# =============================================================================
# DISCOVER PYTHON FILES
# =============================================================================

files = sorted(
    p for p in ROOT.rglob("*.py")
    if p.is_file()
    and "audit_decision_runtime_boundary" not in p.name
)

print()
print("PYTHON FILES :", len(files))
print("=" * 100)


# =============================================================================
# STATIC AST ANALYSIS
# =============================================================================

records = []

for path in files:

    try:
        source = path.read_text(
            encoding="utf-8",
            errors="replace",
        )
    except Exception:
        continue

    try:
        tree = ast.parse(
            source,
            filename=str(path),
        )
    except Exception:
        continue

    relative = path.relative_to(ROOT)

    imports = []
    calls = []
    functions = []
    mains = []

    for node in ast.walk(tree):

        if isinstance(node, ast.Import):

            for alias in node.names:

                imports.append(alias.name)

        elif isinstance(node, ast.ImportFrom):

            if node.module:
                imports.append(node.module)

        elif isinstance(node, ast.FunctionDef):

            functions.append(node.name)

            if node.name == "main":
                mains.append(node.lineno)

        elif isinstance(node, ast.AsyncFunctionDef):

            functions.append(node.name)

        elif isinstance(node, ast.Call):

            try:
                text = ast.unparse(node)
            except Exception:
                text = ""

            calls.append(
                (
                    node.lineno,
                    text,
                )
            )

    relevant_imports = [
        x for x in imports
        if any(
            target in x
            for target in TARGETS
        )
    ]

    relevant_calls = []

    for lineno, text in calls:

        if any(
            pattern in text
            for pattern in CALL_PATTERNS
        ):

            relevant_calls.append(
                (
                    lineno,
                    text,
                )
            )

    if (
        relevant_imports
        or relevant_calls
        or mains
    ):

        records.append(
            {
                "path": str(relative),
                "imports": relevant_imports,
                "calls": relevant_calls,
                "functions": functions,
                "mains": mains,
            }
        )


# =============================================================================
# REPORT RELEVANT FILES
# =============================================================================

print()
print("RELEVANT FILES")
print("=" * 100)

for item in records:

    print()
    print("FILE :", item["path"])

    if item["mains"]:
        print(
            "MAIN :", item["mains"]
        )

    if item["imports"]:
        print(
            "IMPORTS:"
        )

        for value in item["imports"]:
            print(
                "  ",
                value,
            )

    if item["functions"]:
        print(
            "FUNCTIONS:"
        )

        for value in item["functions"]:
            print(
                "  ",
                value,
            )

    if item["calls"]:

        print(
            "RELEVANT CALLS:"
        )

        for lineno, text in item["calls"]:

            print(
                f"  L{lineno}: {text}"
            )


# =============================================================================
# DECISION ENGINE SPECIFIC CALL GRAPH
# =============================================================================

print()
print("=" * 100)
print("DECISION ENGINE CALL-SITE FORENSIC")
print("=" * 100)

decision_sites = []

for path in files:

    try:
        source = path.read_text(
            encoding="utf-8",
            errors="replace",
        )
    except Exception:
        continue

    lines = source.splitlines()

    for i, line in enumerate(lines, start=1):

        if (
            "decision_engine" in line
            or "build_decision" in line
            or "build_decision_snapshot" in line
        ):

            decision_sites.append(
                (
                    path.relative_to(ROOT),
                    i,
                    line.strip(),
                )
            )

for path, lineno, line in decision_sites:

    print(
        f"{path}:{lineno}: {line}"
    )


# =============================================================================
# SCORER CALL-SITE FORENSIC
# =============================================================================

print()
print("=" * 100)
print("SIGNAL SCORER CALL-SITE FORENSIC")
print("=" * 100)

scorer_sites = []

for path in files:

    try:
        source = path.read_text(
            encoding="utf-8",
            errors="replace",
        )
    except Exception:
        continue

    lines = source.splitlines()

    for i, line in enumerate(lines, start=1):

        if (
            "signal_scorer" in line
            or "load_scores(" in line
        ):

            scorer_sites.append(
                (
                    path.relative_to(ROOT),
                    i,
                    line.strip(),
                )
            )

for path, lineno, line in scorer_sites:

    print(
        f"{path}:{lineno}: {line}"
    )


# =============================================================================
# POTENTIAL ZERO-ARGUMENT CALLS
# =============================================================================

print()
print("=" * 100)
print("ZERO-ARGUMENT BOUNDARY CHECK")
print("=" * 100)

zero_arg_patterns = [
    r"\bsignal_scorer\.run\s*\(\s*\)",
    r"\bsignal_scorer\.load_scores\s*\(\s*\)",
    r"\bload_scores\s*\(\s*\)",
    r"\bdecision_engine\.main\s*\(\s*\)",
    r"\bdecision_engine\.build_decision_snapshot\s*\(\s*\)",
]

found_zero = False

for path in files:

    try:
        source = path.read_text(
            encoding="utf-8",
            errors="replace",
        )
    except Exception:
        continue

    for pattern in zero_arg_patterns:

        for match in re.finditer(
            pattern,
            source,
        ):

            found_zero = True

            line = (
                source[:match.start()]
                .count("\n")
                + 1
            )

            print(
                f"{path.relative_to(ROOT)}:"
                f"{line}: "
                f"{match.group(0)}"
            )

if not found_zero:

    print(
        "NO ZERO-ARGUMENT TARGET CALL FOUND"
    )


# =============================================================================
# FUNCTION SIGNATURE FORENSIC
# =============================================================================

print()
print("=" * 100)
print("FUNCTION SIGNATURE FORENSIC")
print("=" * 100)

signature_targets = {
    "load_scores",
    "run",
    "build_decision_snapshot",
    "load_features",
    "load_validated_signals",
}

for path in files:

    try:
        source = path.read_text(
            encoding="utf-8",
            errors="replace",
        )
    except Exception:
        continue

    try:
        tree = ast.parse(
            source,
            filename=str(path),
        )
    except Exception:
        continue

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):

            if node.name not in signature_targets:
                continue

            try:
                signature = ast.unparse(
                    node.args
                )
            except Exception:
                signature = "UNAVAILABLE"

            print()
            print(
                "FILE :",
                path.relative_to(ROOT),
            )

            print(
                f"L{node.lineno} "
                f"{node.name}("
                f"{signature}"
                f")"
            )


# =============================================================================
# RAW TEXT PIPELINE EVIDENCE
# =============================================================================

print()
print("=" * 100)
print("PIPELINE KEYWORD EVIDENCE")
print("=" * 100)

pipeline_keywords = [
    "bars_by_asset",
    "indicators_by_asset",
    "structures_by_asset",
    "feature_snapshot",
    "load_features",
    "load_scores",
    "scores",
    "decision_snapshot",
    "build_decision_snapshot",
]

for path in files:

    try:
        source = path.read_text(
            encoding="utf-8",
            errors="replace",
        )
    except Exception:
        continue

    hits = []

    for i, line in enumerate(
        source.splitlines(),
        start=1,
    ):

        if any(
            keyword in line
            for keyword in pipeline_keywords
        ):

            hits.append(
                (
                    i,
                    line.strip(),
                )
            )

    if hits:

        print()
        print(
            "FILE :",
            path.relative_to(ROOT),
        )

        for lineno, line in hits[:80]:

            print(
                f"  L{lineno}: {line}"
            )


# =============================================================================
# FINAL
# =============================================================================

print()
print("=" * 100)
print("FORENSIC STATUS : COMPLETE")
print("=" * 100)
print()
print(
    "Paste the COMPLETE output above into the chat."
)
print()