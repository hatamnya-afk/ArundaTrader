# ARUNDA_TRADER_LIVE_SIGNAL_ORDER_INTENT_BINDING_FORENSIC_v0.1.py

from pathlib import Path
import ast


PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

TARGET = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_LIVE_SIGNAL_ORDER_INTENT_RELEASE_PREFLIGHT_v0.2.py"
)


def source_segment(lines, start, end):
    return "".join(
        f"{i + 1:04d}: {lines[i]}"
        for i in range(start, min(end, len(lines)))
    )


def find_function(tree, name):
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == name:
                return node
    return None


def collect_reads(node):
    reads = []

    for item in ast.walk(node):
        if isinstance(item, ast.Subscript):
            try:
                text = ast.unparse(item)
            except Exception:
                text = "<unparse-failed>"

            reads.append(
                (
                    getattr(item, "lineno", None),
                    text,
                )
            )

    return reads


def collect_assignments(node):
    assignments = []

    for item in ast.walk(node):
        if isinstance(item, ast.Assign):
            try:
                target = ast.unparse(item.targets[0])
                value = ast.unparse(item.value)
            except Exception:
                target = "<unparse-failed>"
                value = "<unparse-failed>"

            assignments.append(
                (
                    getattr(item, "lineno", None),
                    target,
                    value,
                )
            )

    return assignments


def collect_calls(node):
    calls = []

    for item in ast.walk(node):
        if isinstance(item, ast.Call):
            try:
                text = ast.unparse(item)
            except Exception:
                text = "<unparse-failed>"

            calls.append(
                (
                    getattr(item, "lineno", None),
                    text,
                )
            )

    return calls


def main():
    print("=" * 100)
    print("ARUNDA TRADER — RELEASE PREFLIGHT v0.2")
    print("CANONICAL ARTIFACT → RELEASE DECISION BINDING FORENSIC v0.1")
    print("=" * 100)
    print(f"TARGET : {TARGET}")
    print("MODE   : READ ONLY")
    print("WRITE  : NONE")
    print("DB     : NOT ACCESSED")
    print("=" * 100)

    if not TARGET.exists():
        raise FileNotFoundError(f"Target not found: {TARGET}")

    text = TARGET.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)

    tree = ast.parse(text, filename=str(TARGET))

    validate_replay = find_function(tree, "validate_replay")
    build_report = find_function(tree, "build_report")

    print("\nFUNCTION DISCOVERY")
    print("-" * 100)

    print(
        f"validate_replay : "
        f"{'FOUND' if validate_replay else 'MISSING'}"
    )

    print(
        f"build_report    : "
        f"{'FOUND' if build_report else 'MISSING'}"
    )

    if not validate_replay:
        raise RuntimeError("validate_replay() not found.")

    if not build_report:
        raise RuntimeError("build_report() not found.")

    # ------------------------------------------------------------------
    # validate_replay
    # ------------------------------------------------------------------

    print("\n" + "=" * 100)
    print("A) validate_replay() — RELEVANT READS")
    print("=" * 100)

    replay_reads = collect_reads(validate_replay)

    relevant_replay_reads = [
        item
        for item in replay_reads
        if any(
            key in item[1]
            for key in (
                "artifact",
                "eligible_rows",
                "eligible_signals",
                "order_intents",
                "decision",
                "snapshot_id",
                "replay_path",
                "replay_verification",
            )
        )
    ]

    for lineno, expr in sorted(
        relevant_replay_reads,
        key=lambda x: (x[0] or 0, x[1]),
    ):
        print(f"LINE {lineno:04d} : {expr}")

    print("\n" + "-" * 100)
    print("validate_replay() — RELEVANT ASSIGNMENTS")
    print("-" * 100)

    replay_assignments = collect_assignments(validate_replay)

    for lineno, target, value in sorted(
        replay_assignments,
        key=lambda x: (x[0] or 0, x[1]),
    ):
        if any(
            key in f"{target} = {value}"
            for key in (
                "artifact",
                "eligible_rows",
                "eligible_signals",
                "order_intents",
                "decision",
                "snapshot_id",
            )
        ):
            print(
                f"LINE {lineno:04d} : "
                f"{target} = {value}"
            )

    # ------------------------------------------------------------------
    # build_report
    # ------------------------------------------------------------------

    print("\n" + "=" * 100)
    print("B) build_report() — RELEVANT READS")
    print("=" * 100)

    build_reads = collect_reads(build_report)

    relevant_build_reads = [
        item
        for item in build_reads
        if any(
            key in item[1]
            for key in (
                "gate",
                "preflight",
                "replay",
                "artifact",
                "eligible_rows",
                "eligible_signals",
                "order_intents",
                "decision",
                "snapshot_id",
                "release_allowed",
                "status",
                "verdict",
                "next_stage",
            )
        )
    ]

    for lineno, expr in sorted(
        relevant_build_reads,
        key=lambda x: (x[0] or 0, x[1]),
    ):
        print(f"LINE {lineno:04d} : {expr}")

    print("\n" + "-" * 100)
    print("build_report() — RELEVANT ASSIGNMENTS")
    print("-" * 100)

    build_assignments = collect_assignments(build_report)

    for lineno, target, value in sorted(
        build_assignments,
        key=lambda x: (x[0] or 0, x[1]),
    ):
        if any(
            key in f"{target} = {value}"
            for key in (
                "artifact",
                "eligible_rows",
                "eligible_signals",
                "order_intents",
                "decision",
                "snapshot_id",
                "release_allowed",
                "status",
                "verdict",
                "next_stage",
            )
        ):
            print(
                f"LINE {lineno:04d} : "
                f"{target} = {value}"
            )

    # ------------------------------------------------------------------
    # Calls
    # ------------------------------------------------------------------

    print("\n" + "=" * 100)
    print("C) build_report() — FUNCTION CALLS")
    print("=" * 100)

    build_calls = collect_calls(build_report)

    for lineno, expr in sorted(
        build_calls,
        key=lambda x: (x[0] or 0, x[1]),
    ):
        if any(
            key in expr
            for key in (
                "validate",
                "compare",
                "get_dict",
                "get_int",
                "get_bool",
            )
        ):
            print(f"LINE {lineno:04d} : {expr}")

    # ------------------------------------------------------------------
    # Exact source windows
    # ------------------------------------------------------------------

    print("\n" + "=" * 100)
    print("D) EXACT SOURCE — validate_replay()")
    print("=" * 100)

    if validate_replay.end_lineno:
        print(
            source_segment(
                lines,
                validate_replay.lineno - 1,
                validate_replay.end_lineno,
            )
        )

    print("\n" + "=" * 100)
    print("E) EXACT SOURCE — build_report()")
    print("=" * 100)

    if build_report.end_lineno:
        print(
            source_segment(
                lines,
                build_report.lineno - 1,
                build_report.end_lineno,
            )
        )

    # ------------------------------------------------------------------
    # Static conclusion
    # ------------------------------------------------------------------

    print("\n" + "=" * 100)
    print("STATIC BINDING CHECK")
    print("=" * 100)

    build_text = ast.get_source_segment(text, build_report) or ""

    has_canonical_artifact = (
        "artifact" in build_text
        and "artifact_contract" in build_text
    )

    uses_duplicate_eligible = (
        "eligible_signals" in build_text
    )

    uses_duplicate_intents = (
        "order_intents" in build_text
    )

    print(
        "build_report references artifact_contract : "
        f"{has_canonical_artifact}"
    )

    print(
        "build_report references eligible_signals  : "
        f"{uses_duplicate_eligible}"
    )

    print(
        "build_report references order_intents     : "
        f"{uses_duplicate_intents}"
    )

    print("\n" + "=" * 100)
    print("END — NO DECISION GENERATED")
    print("=" * 100)


if __name__ == "__main__":
    raise SystemExit(main())