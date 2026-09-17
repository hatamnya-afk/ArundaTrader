# =============================================================================
# ARUNDA
# DECISION_ENGINE_RUNTIME_PRODUCTION_BOUNDARY_FORENSIC_v0.2.py
# =============================================================================

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parent

SKIP_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    "site-packages",
}

SKIP_NAME_PARTS = (
    "forensic",
    "locator",
    "audit",
    "diagnostic",
    "repair",
    "verify",
    "verification",
    "test_",
    "_test",
    "step",
    "m2_",
    "m3_",
    "m4_",
    "m5_",
    "m6_",
    "m7_",
    "m8_",
    "m9_",
)


TARGET_MODULES = {
    "signal_scorer",
    "decision_engine",
    "risk_engine",
    "feature_contract",
}

TARGET_CALLS = {
    "signal_scorer.load_scores",
    "signal_scorer.run",
    "decision_engine.load_scores",
    "decision_engine.build_decision_snapshot",
    "decision_engine.main",
    "risk_engine",
    "feature_contract.load_feature_snapshot",
    "feature_contract.build_feature_snapshot",
}

REAL_INPUTS = {
    "bars_by_asset",
    "indicators_by_asset",
    "structures_by_asset",
}


# =============================================================================
# DISCOVER FILES
# =============================================================================

def production_files():

    result = []

    for path in ROOT.glob("*.py"):

        name = path.name.lower()

        if any(
            token in name
            for token in SKIP_NAME_PARTS
        ):
            continue

        result.append(path)

    return sorted(result)


# =============================================================================
# HELPERS
# =============================================================================

def dotted(node):

    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):

        left = dotted(node.value)

        if left:
            return left + "." + node.attr

        return node.attr

    return ""


def call_name(node):

    if isinstance(node, ast.Call):
        return dotted(node.func)

    return ""


def arg_text(node):

    result = []

    for arg in node.args:

        result.append(
            ast.unparse(arg)
        )

    for kw in node.keywords:

        if kw.arg is None:

            result.append(
                "**" + ast.unparse(kw.value)
            )

        else:

            result.append(
                kw.arg
                + "="
                + ast.unparse(kw.value)
            )

    return result


# =============================================================================
# IMPORT GRAPH
# =============================================================================

def scan_imports(path):

    try:

        source = path.read_text(
            encoding="utf-8-sig",
            errors="ignore",
        )

        tree = ast.parse(
            source,
            filename=str(path),
        )

    except Exception:
        return []

    imports = []

    for node in ast.walk(tree):

        if isinstance(
            node,
            ast.Import,
        ):

            for alias in node.names:

                imports.append(
                    alias.name
                )

        elif isinstance(
            node,
            ast.ImportFrom,
        ):

            if node.module:
                imports.append(
                    node.module
                )

    return imports


# =============================================================================
# CALL GRAPH
# =============================================================================

def scan_calls(path):

    try:

        source = path.read_text(
            encoding="utf-8-sig",
            errors="ignore",
        )

        tree = ast.parse(
            source,
            filename=str(path),
        )

    except Exception:
        return []

    records = []

    stack = []

    class Visitor(ast.NodeVisitor):

        def visit_FunctionDef(self, node):

            stack.append(
                node.name
            )

            self.generic_visit(node)

            stack.pop()

        def visit_AsyncFunctionDef(self, node):

            stack.append(
                node.name
            )

            self.generic_visit(node)

            stack.pop()

        def visit_Call(self, node):

            name = call_name(node)

            args = arg_text(node)

            text = (
                name
                + "("
                + ", ".join(args)
                + ")"
            )

            interesting = (
                name in TARGET_CALLS
                or
                "load_scores" in name
                or
                "build_decision_snapshot" in name
                or
                "load_feature_snapshot" in name
                or
                any(
                    x in text
                    for x in REAL_INPUTS
                )
            )

            if interesting:

                records.append(
                    {
                        "file": path,
                        "line": node.lineno,
                        "caller": (
                            stack[-1]
                            if stack
                            else "<module>"
                        ),
                        "callee": name,
                        "args": args,
                    }
                )

            self.generic_visit(node)

    Visitor().visit(tree)

    return records


# =============================================================================
# FUNCTION SIGNATURES
# =============================================================================

def signatures(path):

    try:

        source = path.read_text(
            encoding="utf-8-sig",
            errors="ignore",
        )

        tree = ast.parse(
            source,
            filename=str(path),
        )

    except Exception:
        return []

    result = []

    wanted = {
        "main",
        "run",
        "load_scores",
        "build_decision_snapshot",
        "load_features",
        "load_feature_snapshot",
        "process_signals",
    }

    for node in ast.walk(tree):

        if not isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            continue

        if node.name not in wanted:
            continue

        positional = (
            node.args.posonlyargs
            + node.args.args
        )

        defaults = (
            [None]
            * (
                len(positional)
                - len(node.args.defaults)
            )
            + list(node.args.defaults)
        )

        params = []

        for arg, default in zip(
            positional,
            defaults,
        ):

            if default is None:
                params.append(arg.arg)
            else:
                params.append(
                    arg.arg
                    + "="
                    + ast.unparse(default)
                )

        result.append(
            {
                "file": path,
                "line": node.lineno,
                "name": node.name,
                "params": params,
            }
        )

    return result


# =============================================================================
# MAIN
# =============================================================================

def main():

    print("=" * 100)
    print(
        "ARUNDA DECISION ENGINE "
        "PRODUCTION BOUNDARY FORENSIC v0.2"
    )
    print("=" * 100)

    files = production_files()

    print()
    print(
        "Production candidate files:",
        len(files),
    )

    # -------------------------------------------------------------------------
    # IMPORTS
    # -------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("TARGET MODULE IMPORT GRAPH")
    print("=" * 100)

    imported_by = {
        module: []
        for module in TARGET_MODULES
    }

    for path in files:

        imports = scan_imports(path)

        for module in TARGET_MODULES:

            if module in imports:

                imported_by[module].append(
                    path
                )

    for module, paths in imported_by.items():

        print()
        print(
            f"MODULE : {module}"
        )

        if not paths:

            print(
                "  imported by : NONE"
            )

        else:

            for path in paths:

                print(
                    "  imported by :",
                    path.name,
                )

    # -------------------------------------------------------------------------
    # SIGNATURES
    # -------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("RUNTIME FUNCTION SIGNATURES")
    print("=" * 100)

    for path in files:

        for item in signatures(path):

            if item["name"] in {
                "run",
                "load_scores",
                "build_decision_snapshot",
                "process_signals",
            }:

                print()
                print(
                    "FILE :",
                    item["file"].name,
                )

                print(
                    "LINE :",
                    item["line"],
                )

                print(
                    "FUNC :",
                    item["name"]
                    + "("
                    + ", ".join(item["params"])
                    + ")",
                )

    # -------------------------------------------------------------------------
    # CALLS
    # -------------------------------------------------------------------------

    all_calls = []

    for path in files:

        all_calls.extend(
            scan_calls(path)
        )

    print()
    print("=" * 100)
    print("PRODUCTION CALL SITES")
    print("=" * 100)

    for item in all_calls:

        print()
        print(
            "FILE   :",
            item["file"].name,
        )

        print(
            "LINE   :",
            item["line"],
        )

        print(
            "CALLER :",
            item["caller"],
        )

        print(
            "CALLEE :",
            item["callee"],
        )

        print(
            "ARGS   :",
            ", ".join(item["args"])
            if item["args"]
            else "<ZERO ARGUMENTS>",
        )

    # -------------------------------------------------------------------------
    # SPECIAL TARGETS
    # -------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("DECISION BOUNDARY")
    print("=" * 100)

    scorer_calls = [
        x
        for x in all_calls
        if x["callee"]
        in {
            "signal_scorer.load_scores",
            "signal_scorer.run",
        }
    ]

    decision_loader_calls = [
        x
        for x in all_calls
        if x["callee"]
        == "decision_engine.load_scores"
    ]

    decision_build_calls = [
        x
        for x in all_calls
        if (
            "build_decision_snapshot"
            in x["callee"]
        )
    ]

    real_input_calls = [
        x
        for x in all_calls
        if any(
            name in x["args"]
            for name in REAL_INPUTS
        )
    ]

    print()
    print(
        "SCORER CALLS :",
        len(scorer_calls),
    )

    for x in scorer_calls:

        print(
            f"  {x['file'].name}:{x['line']} "
            f"{x['callee']}("
            + ", ".join(x["args"])
            + ")"
        )

    print()
    print(
        "DECISION load_scores CALLS :",
        len(decision_loader_calls),
    )

    for x in decision_loader_calls:

        print(
            f"  {x['file'].name}:{x['line']} "
            f"{x['callee']}("
            + ", ".join(x["args"])
            + ")"
        )

    print()
    print(
        "DECISION build CALLS :",
        len(decision_build_calls),
    )

    for x in decision_build_calls:

        print(
            f"  {x['file'].name}:{x['line']} "
            f"{x['callee']}("
            + ", ".join(x["args"])
            + ")"
        )

    print()
    print(
        "REAL INPUT REFERENCES :",
        len(real_input_calls),
    )

    for x in real_input_calls:

        print(
            f"  {x['file'].name}:{x['line']} "
            f"{x['callee']}("
            + ", ".join(x["args"])
            + ")"
        )

    # -------------------------------------------------------------------------
    # VERDICT
    # -------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("FINAL FORENSIC VERDICT")
    print("=" * 100)

    scorer_real = any(
        any(
            name in x["args"]
            for name in REAL_INPUTS
        )
        for x in scorer_calls
    )

    decision_gets_scores = any(
        any(
            name in x["args"]
            for name in {
                "scores",
                "score_snapshot",
                "signal_scores",
                "real_scores",
            }
        )
        for x in decision_build_calls
    )

    zero_arg_loader = any(
        len(x["args"]) == 0
        for x in decision_loader_calls
    )

    print(
        "REAL INPUT → SCORER :",
        "PROVEN"
        if scorer_real
        else "NOT PROVEN",
    )

    print(
        "SCORE → DECISION     :",
        "PROVEN"
        if decision_gets_scores
        else "NOT PROVEN",
    )

    print(
        "ZERO-ARG DECISION LOADER :",
        "FOUND"
        if zero_arg_loader
        else "NOT FOUND",
    )

    print()

    if (
        scorer_real
        and decision_gets_scores
        and not zero_arg_loader
    ):

        print(
            "STATUS : BRIDGE STRUCTURALLY CONNECTED"
        )

    elif zero_arg_loader:

        print(
            "STATUS : DECISION ENGINE BOUNDARY REPAIR REQUIRED"
        )

    else:

        print(
            "STATUS : PRODUCTION ENTRYPOINT STILL UNRESOLVED"
        )

    print()
    print("=" * 100)
    print("FORENSIC STATUS : COMPLETE")
    print("=" * 100)


if __name__ == "__main__":
    main()