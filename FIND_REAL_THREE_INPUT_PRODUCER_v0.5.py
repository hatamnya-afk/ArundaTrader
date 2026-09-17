# =============================================================================
# ARUNDA TRADER
# FIND REAL THREE-INPUT PRODUCER v0.5
# =============================================================================
#
# PURPOSE
# -------
# Find the REAL production code that constructs:
#
#     bars_by_asset
#     indicators_by_asset
#     structures_by_asset
#
# before they enter feature_contract.
#
# MODE
# ----
# READ ONLY
# NO IMPORTS
# NO EXECUTION
# NO DATABASE
# NO SOURCE MODIFICATION
#
# =============================================================================

from __future__ import annotations

import ast
import os
from pathlib import Path


# =============================================================================
# CONFIG
# =============================================================================

PROJECT_ROOT = Path(
    r"C:\Users\ASUS\ArundaTrader"
)

TARGETS = {
    "bars_by_asset",
    "indicators_by_asset",
    "structures_by_asset",
}

EXCLUDED_FILES = {
    "feature_contract.py",
    "decision_engine.py",
    "signal_scorer.py",
}

FORENSIC_MARKERS = (
    "FORENSIC",
    "AUDIT",
    "FINDER",
    "LOCATOR",
    "TRACE",
    "VERIFY",
    "DIAGNOSTIC",
    "SCAN",
    "REPAIR",
    "CHECK",
    "PROBE",
    "MINI",
)


# =============================================================================
# HELPERS
# =============================================================================

def is_python_file(path: Path) -> bool:

    return (
        path.suffix.lower() == ".py"
        and path.name not in EXCLUDED_FILES
    )


def is_forensic_file(path: Path) -> bool:

    name = path.name.upper()

    return any(
        marker in name
        for marker in FORENSIC_MARKERS
    )


def source_line(
    lines,
    lineno,
):

    if 1 <= lineno <= len(lines):

        return lines[lineno - 1].strip()

    return ""


def safe_unparse(node):

    try:

        return ast.unparse(node)

    except Exception:

        return "<unparseable>"


# =============================================================================
# AST PRODUCER ANALYSIS
# =============================================================================

class ProducerVisitor(ast.NodeVisitor):

    def __init__(
        self,
        filename,
        lines,
    ):

        self.filename = filename
        self.lines = lines
        self.function_stack = []
        self.results = []

    # -------------------------------------------------------------------------
    # Function tracking
    # -------------------------------------------------------------------------

    def visit_FunctionDef(
        self,
        node,
    ):

        self.function_stack.append(
            node.name
        )

        self.generic_visit(node)

        self.function_stack.pop()

    def visit_AsyncFunctionDef(
        self,
        node,
    ):

        self.function_stack.append(
            node.name
        )

        self.generic_visit(node)

        self.function_stack.pop()

    # -------------------------------------------------------------------------
    # Assignment
    # -------------------------------------------------------------------------

    def visit_Assign(
        self,
        node,
    ):

        targets = []

        for target in node.targets:

            if isinstance(
                target,
                ast.Name,
            ):

                targets.append(
                    target.id
                )

        matched = (
            TARGETS
            .intersection(targets)
        )

        if matched:

            self.results.append({

                "kind": "ASSIGNMENT",

                "line": node.lineno,

                "function": (
                    self.function_stack[-1]
                    if self.function_stack
                    else "<module>"
                ),

                "targets": sorted(matched),

                "value": safe_unparse(
                    node.value
                ),

                "source": source_line(
                    self.lines,
                    node.lineno,
                ),
            })

        self.generic_visit(node)

    # -------------------------------------------------------------------------
    # Named expression / annotated assignment
    # -------------------------------------------------------------------------

    def visit_AnnAssign(
        self,
        node,
    ):

        if isinstance(
            node.target,
            ast.Name,
        ):

            name = node.target.id

            if name in TARGETS:

                self.results.append({

                    "kind": "ANNOTATED_ASSIGNMENT",

                    "line": node.lineno,

                    "function": (
                        self.function_stack[-1]
                        if self.function_stack
                        else "<module>"
                    ),

                    "targets": [name],

                    "value": safe_unparse(
                        node.value
                    )
                    if node.value is not None
                    else "<NONE>",

                    "source": source_line(
                        self.lines,
                        node.lineno,
                    ),
                })

        self.generic_visit(node)

    # -------------------------------------------------------------------------
    # Dict construction
    #
    # Example:
    #
    # return {
    #     "bars_by_asset": bars,
    #     ...
    # }
    # -------------------------------------------------------------------------

    def visit_Dict(
        self,
        node,
    ):

        matched = []

        for key in node.keys:

            if isinstance(
                key,
                ast.Constant,
            ):

                if key.value in TARGETS:

                    matched.append(
                        key.value
                    )

        if matched:

            self.results.append({

                "kind": "DICT_KEY",

                "line": node.lineno,

                "function": (
                    self.function_stack[-1]
                    if self.function_stack
                    else "<module>"
                ),

                "targets": sorted(
                    set(matched)
                ),

                "value": safe_unparse(
                    node
                ),

                "source": source_line(
                    self.lines,
                    node.lineno,
                ),
            })

        self.generic_visit(node)

    # -------------------------------------------------------------------------
    # Function calls receiving target names
    # -------------------------------------------------------------------------

    def visit_Call(
        self,
        node,
    ):

        matched = []

        for arg in node.args:

            if isinstance(
                arg,
                ast.Name,
            ):

                if arg.id in TARGETS:

                    matched.append(
                        arg.id
                    )

        for keyword in node.keywords:

            if isinstance(
                keyword.value,
                ast.Name,
            ):

                if keyword.value.id in TARGETS:

                    matched.append(
                        keyword.value.id
                    )

        if matched:

            self.results.append({

                "kind": "CALL_INPUT",

                "line": node.lineno,

                "function": (
                    self.function_stack[-1]
                    if self.function_stack
                    else "<module>"
                ),

                "targets": sorted(
                    set(matched)
                ),

                "value": safe_unparse(
                    node
                ),

                "source": source_line(
                    self.lines,
                    node.lineno,
                ),
            })

        self.generic_visit(node)


# =============================================================================
# MAIN SCAN
# =============================================================================

def main():

    print("=" * 100)
    print(
        "ARUNDA TRADER — REAL THREE-INPUT PRODUCER v0.5"
    )
    print("=" * 100)

    print(
        "PROJECT ROOT :",
        PROJECT_ROOT
    )

    print(
        "MODE         : READ ONLY"
    )

    print(
        "IMPORTS      : NONE"
    )

    print(
        "EXECUTION    : NONE"
    )

    print(
        "DATABASE     : NOT TOUCHED"
    )

    print(
        "SOURCE EDIT  : NONE"
    )

    print("=" * 100)
    print()

    python_files = []

    for path in PROJECT_ROOT.rglob("*.py"):

        if not is_python_file(path):

            continue

        python_files.append(path)

    print(
        "PYTHON FILES SCANNED :",
        len(python_files)
    )

    print()

    all_results = []

    parse_errors = []

    for path in python_files:

        try:

            raw = path.read_text(
                encoding="utf-8-sig"
            )

            lines = raw.splitlines()

            tree = ast.parse(
                raw,
                filename=str(path)
            )

        except Exception as exc:

            parse_errors.append(
                (
                    path,
                    type(exc).__name__,
                    str(exc),
                )
            )

            continue

        visitor = ProducerVisitor(
            path,
            lines,
        )

        visitor.visit(tree)

        for result in visitor.results:

            result["file"] = str(path)

            result["forensic"] = (
                is_forensic_file(path)
            )

            all_results.append(
                result
            )

    # =========================================================================
    # REAL CANDIDATES
    # =========================================================================

    production_results = [
        item
        for item in all_results
        if not item["forensic"]
    ]

    forensic_results = [
        item
        for item in all_results
        if item["forensic"]
    ]

    print("=" * 100)
    print(
        "PRODUCTION CANDIDATES"
    )
    print("=" * 100)
    print()

    if not production_results:

        print(
            "NO PRODUCTION CANDIDATES FOUND."
        )

    else:

        for index, item in enumerate(
            production_results,
            1,
        ):

            print(
                "-" * 100
            )

            print(
                f"[{index}] {item['kind']}"
            )

            print(
                "FILE     :",
                item["file"]
            )

            print(
                "LINE     :",
                item["line"]
            )

            print(
                "FUNCTION :",
                item["function"]
            )

            print(
                "TARGETS  :",
                item["targets"]
            )

            print(
                "CODE     :",
                item["source"]
            )

            if item["kind"] in (
                "ASSIGNMENT",
                "ANNOTATED_ASSIGNMENT",
                "DICT_KEY",
            ):

                print(
                    "VALUE    :",
                    item["value"]
                )

            print()

    # =========================================================================
    # SCORE CANDIDATES
    # =========================================================================

    print("=" * 100)
    print(
        "THREE-INPUT PRODUCER CANDIDATES"
    )
    print("=" * 100)
    print()

    grouped = {}

    for item in production_results:

        key = (
            item["file"],
            item["function"],
        )

        grouped.setdefault(
            key,
            set(),
        ).update(
            item["targets"]
        )

    ranked = []

    for (
        file_name,
        function_name,
    ), targets in grouped.items():

        score = len(targets)

        ranked.append(
            (
                score,
                file_name,
                function_name,
                sorted(targets),
            )
        )

    ranked.sort(
        reverse=True
    )

    if not ranked:

        print(
            "NO CANDIDATE FUNCTIONS."
        )

    else:

        for (
            score,
            file_name,
            function_name,
            targets,
        ) in ranked:

            print(
                "SCORE     :",
                score,
            )

            print(
                "FILE      :",
                file_name,
            )

            print(
                "FUNCTION  :",
                function_name,
            )

            print(
                "TARGETS   :",
                targets,
            )

            print("-" * 100)

    # =========================================================================
    # FORENSIC NOISE SUMMARY
    # =========================================================================

    print()
    print("=" * 100)
    print(
        "FORENSIC / AUDIT NOISE"
    )
    print("=" * 100)
    print()

    print(
        "Forensic candidate records :",
        len(forensic_results)
    )

    print(
        "These are NOT treated as production producers."
    )

    # =========================================================================
    # PARSE ERRORS
    # =========================================================================

    print()
    print("=" * 100)
    print(
        "PARSE ERRORS"
    )
    print("=" * 100)
    print()

    print(
        "Parse errors :",
        len(parse_errors)
    )

    for (
        path,
        error_type,
        message,
    ) in parse_errors[:30]:

        print(
            path,
            "->",
            error_type,
            ":",
            message,
        )

    if len(parse_errors) > 30:

        print(
            "...",
            len(parse_errors) - 30,
            "additional parse errors omitted."
        )

    # =========================================================================
    # FINAL
    # =========================================================================

    print()
    print("=" * 100)
    print(
        "FORENSIC CONCLUSION"
    )
    print("=" * 100)
    print()

    three_input = [
        item
        for item in ranked
        if item[0] == 3
    ]

    if three_input:

        print(
            "REAL THREE-INPUT CANDIDATES FOUND :",
            len(three_input)
        )

        for (
            score,
            file_name,
            function_name,
            targets,
        ) in three_input:

            print()
            print(
                "FILE     :",
                file_name
            )

            print(
                "FUNCTION :",
                function_name
            )

            print(
                "TARGETS  :",
                targets
            )

    else:

        print(
            "NO SINGLE FUNCTION CURRENTLY SHOWS "
            "DIRECT CONSTRUCTION OF ALL THREE TARGETS."
        )

        print()
        print(
            "NEXT TRACE REQUIRED:"
        )

        print(
            "market data producer"
        )

        print(
            " -> bars producer"
        )

        print(
            " -> indicator producer"
        )

        print(
            " -> structure producer"
        )

        print(
            " -> runtime assembly"
        )

        print(
            " -> feature_contract"
        )

    print()
    print(
        "NO SOURCE FILES MODIFIED."
    )

    print(
        "NO DATABASE ACCESSED."
    )

    print(
        "NO PIPELINE EXECUTED."
    )

    print("=" * 100)


if __name__ == "__main__":
    main()