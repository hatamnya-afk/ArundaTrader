import ast
import inspect
from pathlib import Path


# =============================================================================
# ARUNDA TRADER
# M2 — PRODUCTION SCORER DEPENDENCY LOCATOR
# v0.1
# =============================================================================
#
# PURPOSE
# -------
# Locate the REAL production sources used to construct:
#
#     feature_record
#     structural_state
#     regime_data
#
# required by:
#
#     signal_scorer.calculate_score()
#
# RULES
# -----
# READ ONLY
# NO DATABASE
# NO WRITE
# NO IMPORT SIDE EFFECTS
# NO SYNTHETIC DATA
# NO PRODUCTION MODIFICATION
# =============================================================================


PROJECT_ROOT = Path(__file__).resolve().parent
SCORER_FILE = PROJECT_ROOT / "signal_scorer.py"


TARGETS = {
    "feature_record",
    "features",
    "feature_snapshot",
    "regime_data",
    "regime",
    "market_regime",
    "structural_state",
    "structure",
    "market_structure",
}


def line(char="=", length=100):
    print(char * length)


def read_source():
    if not SCORER_FILE.exists():
        raise RuntimeError(
            f"signal_scorer.py not found: {SCORER_FILE}"
        )

    return SCORER_FILE.read_text(
        encoding="utf-8-sig"
    )


def collect_functions(tree):
    functions = {}

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):

            functions[node.name] = node

    return functions


def names_in_node(node):
    result = set()

    for child in ast.walk(node):

        if isinstance(child, ast.Name):
            result.add(child.id)

        elif isinstance(child, ast.Attribute):
            result.add(child.attr)

    return result


def call_targets(node):
    result = []

    for child in ast.walk(node):

        if not isinstance(
            child,
            ast.Call,
        ):
            continue

        func = child.func

        if isinstance(
            func,
            ast.Name,
        ):

            result.append(
                func.id
            )

        elif isinstance(
            func,
            ast.Attribute,
        ):

            result.append(
                func.attr
            )

    return result


def source_context(source, lineno, radius=8):

    lines = source.splitlines()

    start = max(
        0,
        lineno - radius - 1
    )

    end = min(
        len(lines),
        lineno + radius
    )

    output = []

    for index in range(
        start,
        end
    ):

        output.append(
            f"{index + 1:>6} | {lines[index]}"
        )

    return "\n".join(output)


def find_target_references(source, tree):

    lines = source.splitlines()

    hits = []

    for index, text in enumerate(
        lines,
        start=1
    ):

        lower = text.lower()

        if any(
            target.lower() in lower
            for target in TARGETS
        ):

            hits.append(
                (
                    index,
                    text,
                )
            )

    return hits


def find_score_call(tree):

    results = []

    for node in ast.walk(tree):

        if not isinstance(
            node,
            ast.Call,
        ):
            continue

        func = node.func

        if isinstance(
            func,
            ast.Name,
        ):

            if func.id == "calculate_score":
                results.append(node)

        elif isinstance(
            func,
            ast.Attribute,
        ):

            if func.attr == "calculate_score":
                results.append(node)

    return results


def describe_call(node):

    positional = []

    for arg in node.args:

        try:
            positional.append(
                ast.unparse(arg)
            )
        except Exception:
            positional.append(
                "<unparseable>"
            )

    keywords = []

    for keyword in node.keywords:

        try:
            value = ast.unparse(
                keyword.value
            )
        except Exception:
            value = "<unparseable>"

        keywords.append(
            f"{keyword.arg}={value}"
        )

    return positional, keywords


def main():

    print("=" * 100)
    print(
        "ARUNDA TRADER — M2"
    )
    print(
        "PRODUCTION_SCORER_DEPENDENCY_LOCATOR_v0.1"
    )
    print("=" * 100)

    print(
        f"PROJECT : {PROJECT_ROOT}"
    )

    print(
        f"SCORER  : {SCORER_FILE}"
    )

    print(
        "MODE    : READ ONLY"
    )

    print(
        "DATABASE: NOT USED"
    )

    print(
        "WRITE   : NONE"
    )

    print(
        "PRODUCTION MODIFIED : NO"
    )

    print("=" * 100)

    if not SCORER_FILE.exists():

        print(
            "STATUS : BLOCKED"
        )

        print(
            "ERROR  : signal_scorer.py not found"
        )

        return 1

    source = read_source()

    try:

        tree = ast.parse(
            source
        )

    except SyntaxError as exc:

        print(
            "STATUS : BLOCKED"
        )

        print(
            f"SYNTAX ERROR : {exc}"
        )

        return 1

    functions = collect_functions(
        tree
    )

    # =========================================================================
    # PRODUCTION SCORER
    # =========================================================================

    print()
    line("-")

    print(
        "PRODUCTION SCORER"
    )

    line("-")

    scorer = functions.get(
        "calculate_score"
    )

    if scorer is None:

        print(
            "calculate_score : NOT FOUND"
        )

        return 1

    print(
        f"calculate_score : FOUND"
    )

    print(
        f"Line            : {scorer.lineno}"
    )

    print(
        "Arguments       : "
        + ", ".join(
            arg.arg
            for arg in scorer.args.args
        )
    )

    # =========================================================================
    # TARGET REFERENCES
    # =========================================================================

    print()
    line("-")

    print(
        "SCORER DEPENDENCY REFERENCES"
    )

    line("-")

    hits = find_target_references(
        source,
        tree
    )

    for lineno, text in hits:

        print(
            f"{lineno:>6} | {text}"
        )

    if not hits:

        print(
            "NO DIRECT TARGET REFERENCES FOUND"
        )

    # =========================================================================
    # SCORE CALL SITES
    # =========================================================================

    print()
    line("-")

    print(
        "CALCULATE_SCORE CALL SITES"
    )

    line("-")

    score_calls = find_score_call(
        tree
    )

    if not score_calls:

        print(
            "NO CALL SITES FOUND"
        )

    else:

        for number, node in enumerate(
            score_calls,
            start=1
        ):

            positional, keywords = describe_call(
                node
            )

            print()
            print(
                f"[CALL {number}] LINE {node.lineno}"
            )

            print(
                "POSITIONAL:"
            )

            for item in positional:
                print(
                    f"    {item}"
                )

            print(
                "KEYWORDS:"
            )

            for item in keywords:
                print(
                    f"    {item}"
                )

            print()
            print(
                source_context(
                    source,
                    node.lineno,
                    radius=12
                )
            )

    # =========================================================================
    # FUNCTION DEPENDENCY GRAPH
    # =========================================================================

    print()
    line("-")

    print(
        "FUNCTION DEPENDENCY GRAPH"
    )

    line("-")

    for name, node in functions.items():

        names = names_in_node(
            node
        )

        relevant = (
            names
            &
            TARGETS
        )

        calls = call_targets(
            node
        )

        if relevant or (
            name == "load_scores"
        ):

            print()
            print(
                f"FUNCTION : {name}"
            )

            print(
                f"LINE     : {node.lineno}"
            )

            if relevant:

                print(
                    "TARGET REFERENCES:"
                )

                for item in sorted(
                    relevant
                ):

                    print(
                        f"    {item}"
                    )

            if calls:

                print(
                    "CALLS:"
                )

                for item in sorted(
                    set(calls)
                ):

                    print(
                        f"    {item}"
                    )

    # =========================================================================
    # LOAD_SCORES
    # =========================================================================

    print()
    line("-")

    print(
        "LOAD_SCORES PRODUCTION PATH"
    )

    line("-")

    load_scores = functions.get(
        "load_scores"
    )

    if load_scores is None:

        print(
            "load_scores : NOT FOUND"
        )

    else:

        print(
            f"load_scores : FOUND"
        )

        print(
            f"Line        : {load_scores.lineno}"
        )

        print()

        print(
            source_context(
                source,
                load_scores.lineno,
                radius=30
            )
        )

    # =========================================================================
    # FINAL
    # =========================================================================

    print()
    line("=")

    print(
        "LOCATOR STATUS : COMPLETE"
    )

    print(
        "NEXT ACTION     : IDENTIFY REAL FEATURE/REGIME "
        "PRODUCTION SOURCES"
    )

    print(
        "NO REPAIR PERFORMED"
    )

    print(
        "NO DATABASE ACCESS"
    )

    print(
        "NO PRODUCTION MODIFICATION"
    )

    line("=")

    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )