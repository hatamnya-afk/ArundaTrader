from pathlib import Path
import ast

ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

INPUTS = {
    "bars_by_asset",
    "indicators_by_asset",
    "structures_by_asset",
}

EXCLUDE = {
    "signal_scorer.py",
    "decision_engine.py",
    "risk_engine.py",
    "execution_engine.py",
    "signal_score_contract.py",
}


def dotted(node):

    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):

        left = dotted(node.value)

        if left:
            return left + "." + node.attr

        return node.attr

    return ""


def expr(node):

    try:
        return ast.unparse(node)
    except Exception:
        return "?"


print("=" * 90)
print("ARUNDA REAL RUNTIME INPUT PRODUCER LOCATOR v0.1")
print("=" * 90)

results = []

for path in sorted(ROOT.glob("*.py")):

    if path.name in EXCLUDE:
        continue

    try:

        source = path.read_text(
            encoding="utf-8-sig"
        )

        tree = ast.parse(
            source,
            filename=str(path)
        )

    except Exception:
        continue

    hits = []

    for node in ast.walk(tree):

        # -------------------------------------------------------------
        # Function definitions containing real input names
        # -------------------------------------------------------------

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):

            args = []

            for arg in node.args.args:

                if arg.arg in INPUTS:
                    args.append(arg.arg)

            if args:

                hits.append(
                    (
                        node.lineno,
                        "FUNCTION_INPUT",
                        node.name,
                        ", ".join(args),
                    )
                )

        # -------------------------------------------------------------
        # Calls whose arguments contain real input names
        # -------------------------------------------------------------

        elif isinstance(node, ast.Call):

            names = set()

            for child in ast.walk(node):

                if isinstance(
                    child,
                    ast.Name,
                ):

                    if child.id in INPUTS:
                        names.add(child.id)

            if names:

                hits.append(
                    (
                        node.lineno,
                        "CALL_WITH_INPUT",
                        dotted(node),
                        ", ".join(
                            sorted(names)
                        ),
                    )
                )

        # -------------------------------------------------------------
        # Assignments involving real input names
        # -------------------------------------------------------------

        elif isinstance(
            node,
            ast.Assign,
        ):

            names = set()

            for child in ast.walk(node.value):

                if isinstance(
                    child,
                    ast.Name,
                ):

                    if child.id in INPUTS:
                        names.add(child.id)

            if names:

                targets = []

                for target in node.targets:

                    targets.append(
                        expr(target)
                    )

                hits.append(
                    (
                        node.lineno,
                        "ASSIGNMENT",
                        " = ".join(targets),
                        ", ".join(
                            sorted(names)
                        ),
                    )
                )

    if hits:

        results.append(
            (
                path,
                hits,
            )
        )


print()
print(
    "FILES WITH REAL INPUT REFERENCES :",
    len(results)
)

print()

for path, hits in results:

    print("-" * 90)
    print("FILE :", path.name)

    # فقط حداکثر 15 hit مهم از هر فایل
    for (
        line,
        kind,
        name,
        inputs,
    ) in hits[:15]:

        print(
            f"L{line:<5} "
            f"{kind:<18} "
            f"{name:<45} "
            f"[{inputs}]"
        )


print()
print("=" * 90)
print("HIGH-VALUE CANDIDATES")
print("=" * 90)

for path, hits in results:

    for (
        line,
        kind,
        name,
        inputs,
    ) in hits:

        if kind == "CALL_WITH_INPUT":

            print(
                f"{path.name}:L{line} "
                f"{name} "
                f"<{inputs}>"
            )


print()
print("=" * 90)
print("END")
print("=" * 90)