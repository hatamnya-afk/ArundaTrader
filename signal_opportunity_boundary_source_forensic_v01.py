from __future__ import annotations

import ast
import inspect
import pathlib


FILES = [
    "opportunity_engine.py",
    "signal_engine.py",
    "signal_validator.py",
    "score_producer.py",
    "signal_scorer.py",
]


KEYWORDS = (
    "direction",
    "signal_state",
    "momentum",
    "confidence",
    "score",
    "ACTIVE",
    "NEUTRAL",
    "LONG",
    "SHORT",
    "NO_TRADE",
    "ELIGIBLE",
)


def function_names(source: str):

    tree = ast.parse(source)

    result = []

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):

            result.append(
                (
                    node.name,
                    node.lineno,
                    getattr(node, "end_lineno", node.lineno),
                )
            )

    return sorted(
        result,
        key=lambda x: x[1],
    )


def relevant_functions(source: str):

    tree = ast.parse(source)

    matches = []

    for node in ast.walk(tree):

        if not isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):

            continue

        segment = ast.get_source_segment(
            source,
            node,
        ) or ""

        upper = segment.upper()

        score = sum(
            1
            for keyword in KEYWORDS
            if keyword.upper() in upper
        )

        if score:

            matches.append(
                (
                    score,
                    node.name,
                    node.lineno,
                    getattr(
                        node,
                        "end_lineno",
                        node.lineno,
                    ),
                )
            )

    return sorted(
        matches,
        key=lambda x: (
            -x[0],
            x[2],
        ),
    )


print("=" * 100)
print(
    "ARUNDA SIGNAL <-> OPPORTUNITY "
    "BOUNDARY SOURCE FORENSIC v0.1"
)
print("=" * 100)

print("MODE=READ_ONLY")
print("FILES_CHANGED=0")
print("DB_WRITES=0")
print("EXECUTION=OFF")
print("ORDER_INTENTS=0")
print()

for filename in FILES:

    path = pathlib.Path(filename)

    if not path.exists():

        print()
        print(
            f"[MISSING] {filename}"
        )

        continue

    source = path.read_text(
        encoding="utf-8-sig"
    )

    print()
    print("=" * 100)
    print(
        f"FILE: {filename}"
    )
    print("=" * 100)

    print(
        f"SIZE={len(source)}"
    )

    print()
    print("FUNCTIONS")
    print("-" * 100)

    for name, start, end in function_names(
        source
    ):

        print(
            f"{name:<45} "
            f"L{start}-L{end}"
        )

    print()
    print("RELEVANT FUNCTIONS")
    print("-" * 100)

    matches = relevant_functions(
        source
    )

    for score, name, start, end in matches[:20]:

        print(
            f"HITS={score:<2} "
            f"{name:<45} "
            f"L{start}-L{end}"
        )

    # --------------------------------------------------------------
    # Print source of the strongest relevant functions only.
    # --------------------------------------------------------------

    tree = ast.parse(source)

    nodes = []

    for node in ast.walk(tree):

        if not isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):

            continue

        segment = ast.get_source_segment(
            source,
            node,
        ) or ""

        upper = segment.upper()

        score = sum(
            1
            for keyword in KEYWORDS
            if keyword.upper() in upper
        )

        if score >= 3:

            nodes.append(
                (
                    score,
                    node,
                )
            )

    nodes.sort(
        key=lambda x: (
            -x[0],
            x[1].lineno,
        )
    )

    print()
    print("STRONGEST SOURCE BLOCKS")
    print("-" * 100)

    shown = set()

    for score, node in nodes:

        key = (
            node.name,
            node.lineno,
        )

        if key in shown:

            continue

        shown.add(key)

        segment = ast.get_source_segment(
            source,
            node,
        )

        if not segment:

            continue

        print()
        print(
            f">>> {filename}::{node.name} "
            f"(keyword_hits={score})"
        )
        print(
            f">>> lines "
            f"{node.lineno}-"
            f"{getattr(node, 'end_lineno', node.lineno)}"
        )
        print()

        print(segment)

        # Do not flood the terminal.
        if len(shown) >= 6:

            break


print()
print("=" * 100)
print("FORENSIC_COMPLETE")
print("=" * 100)
print("NO_SOURCE_MUTATION=TRUE")
print("DB_WRITES=0")
print("STATUS=READY_FOR_BOUNDARY_REPAIR")
print("=" * 100)
