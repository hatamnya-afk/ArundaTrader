from pathlib import Path
import ast


PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")
TARGET = PROJECT_ROOT / "technical_engine.py"

TARGET_FIELDS = {
    "trend",
    "momentum",
    "acceleration",
    "volatility",
}


def read_source(path):
    return path.read_text(
        encoding="utf-8-sig"
    )


def source_segment(source, node):
    lines = source.splitlines()

    start = node.lineno
    end = getattr(
        node,
        "end_lineno",
        node.lineno,
    )

    return "\n".join(
        f"{i:5} | {lines[i - 1]}"
        for i in range(
            start,
            end + 1,
        )
    )


def value_summary(node):
    try:
        return ast.dump(
            node,
            indent=2,
        )
    except Exception:
        return repr(node)


def dict_fields(node):
    result = []

    if not isinstance(
        node,
        ast.Dict,
    ):
        return result

    for key in node.keys:
        if isinstance(
            key,
            ast.Constant,
        ):
            result.append(
                repr(key.value)
            )

    return result


def main():

    print("=" * 100)
    print(
        "ARUNDA TRADER — TECHNICAL SEMANTIC PRODUCER LINEAGE FORENSIC v0.1"
    )
    print("=" * 100)

    print(
        f"PROJECT ROOT : {PROJECT_ROOT}"
    )
    print(
        f"TARGET       : {TARGET}"
    )
    print(
        "MODE         : READ ONLY STATIC SOURCE INSPECTION"
    )
    print(
        "DATABASE     : NONE"
    )
    print(
        "WRITE        : NONE"
    )
    print(
        "SOURCE MUTATION : NONE"
    )
    print(
        "BOM HANDLING : UTF-8-SIG / IN MEMORY ONLY"
    )

    print("=" * 100)

    if not TARGET.exists():
        raise FileNotFoundError(
            TARGET
        )

    source = read_source(TARGET)

    tree = ast.parse(
        source,
        filename=str(TARGET),
    )

    functions = [
        node
        for node in ast.walk(tree)
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        )
    ]

    print("\n")
    print("=" * 100)
    print("A) TARGET SEMANTIC FIELD ASSIGNMENTS")
    print("=" * 100)

    found_assignments = []

    for function in functions:

        for node in ast.walk(function):

            if isinstance(
                node,
                ast.Assign,
            ):

                for target in node.targets:

                    if (
                        isinstance(
                            target,
                            ast.Name,
                        )
                        and target.id
                        in TARGET_FIELDS
                    ):

                        found_assignments.append(
                            (
                                function.name,
                                node,
                                target.id,
                            )
                        )

            elif isinstance(
                node,
                ast.AnnAssign,
            ):

                target = node.target

                if (
                    isinstance(
                        target,
                        ast.Name,
                    )
                    and target.id
                    in TARGET_FIELDS
                ):

                    found_assignments.append(
                        (
                            function.name,
                            node,
                            target.id,
                        )
                    )

    if not found_assignments:
        print(
            "NO DIRECT SIMPLE-NAME ASSIGNMENTS FOUND"
        )

    else:

        for (
            function_name,
            node,
            field,
        ) in found_assignments:

            print("\n")
            print(
                "DIRECT VARIABLE PRODUCER"
            )
            print(
                f"FUNCTION : {function_name}"
            )
            print(
                f"LINE     : {node.lineno}"
            )
            print(
                f"FIELD    : {field}"
            )

            print(
                "\nSOURCE"
            )
            print(
                "-" * 100
            )

            print(
                source_segment(
                    source,
                    node,
                )
            )

            print(
                "\nVALUE AST"
            )
            print(
                "-" * 100
            )

            value = (
                node.value
                if isinstance(
                    node,
                    ast.Assign,
                )
                else node.value
            )

            print(
                value_summary(
                    value
                )
            )

    print("\n")
    print("=" * 100)
    print("B) TARGET FIELD REFERENCES")
    print("=" * 100)

    reference_map = {
        field: []
        for field in TARGET_FIELDS
    }

    for function in functions:

        for node in ast.walk(function):

            if isinstance(
                node,
                ast.Name,
            ):

                if (
                    isinstance(
                        node.ctx,
                        ast.Load,
                    )
                    and node.id
                    in TARGET_FIELDS
                ):

                    reference_map[
                        node.id
                    ].append(
                        (
                            function.name,
                            node.lineno,
                        )
                    )

    for field in sorted(
        TARGET_FIELDS
    ):

        print(
            f"\nFIELD : {field}"
        )

        refs = reference_map[
            field
        ]

        if not refs:
            print(
                "  NO LOAD REFERENCES"
            )
            continue

        for (
            function_name,
            line,
        ) in refs:

            print(
                f"  {function_name} : line {line}"
            )

    print("\n")
    print("=" * 100)
    print(
        "C) RETURN-LEVEL CONSUMPTION"
    )
    print("=" * 100)

    for function in functions:

        for node in ast.walk(function):

            if not isinstance(
                node,
                ast.Return,
            ):
                continue

            value = node.value

            if value is None:
                continue

            fields = set()

            if isinstance(
                value,
                ast.Dict,
            ):

                for key in value.keys:

                    if (
                        isinstance(
                            key,
                            ast.Constant,
                        )
                        and key.value
                        in TARGET_FIELDS
                    ):

                        fields.add(
                            key.value
                        )

            elif isinstance(
                value,
                ast.Call,
            ):

                for keyword in value.keywords:

                    if (
                        keyword.arg
                        in TARGET_FIELDS
                    ):

                        fields.add(
                            keyword.arg
                        )

            if fields:

                print("\n")
                print(
                    "RETURN-LEVEL FIELD PRODUCER / CONSUMER"
                )
                print(
                    f"FUNCTION : {function.name}"
                )
                print(
                    f"LINE     : {node.lineno}"
                )
                print(
                    f"FIELDS   : {sorted(fields)}"
                )

                print(
                    "\nRETURN AST"
                )
                print(
                    "-" * 100
                )

                print(
                    value_summary(
                        value
                    )
                )

    print("\n")
    print("=" * 100)
    print(
        "D) FUNCTIONS CALLING / PRODUCING TARGET FIELDS"
    )
    print("=" * 100)

    for function in functions:

        called = []

        for node in ast.walk(function):

            if isinstance(
                node,
                ast.Call,
            ):

                if isinstance(
                    node.func,
                    ast.Name,
                ):

                    if (
                        node.func.id
                        in {
                            "calculate_asset",
                            "calculate_structure",
                            "build_structural_state",
                            "load_structural_state",
                        }
                    ):

                        called.append(
                            (
                                node.func.id,
                                node.lineno,
                            )
                        )

        if called:

            print(
                f"\nFUNCTION : {function.name}"
            )

            for (
                callee,
                line,
            ) in called:

                print(
                    f"  CALL : {callee}()"
                    f" @ line {line}"
                )

    print("\n")
    print("=" * 100)
    print("E) FIELD PRODUCER SUMMARY")
    print("=" * 100)

    for field in sorted(
        TARGET_FIELDS
    ):

        producers = [
            (
                function_name,
                node.lineno,
            )
            for (
                function_name,
                node,
                produced_field,
            ) in found_assignments
            if produced_field == field
        ]

        print(
            f"{field:15}"
            f" producers={len(producers)}"
        )

        for (
            function_name,
            line,
        ) in producers:

            print(
                f"    {function_name}"
                f" @ line {line}"
            )

    print("\n")
    print("=" * 100)
    print("F) FORENSIC DECISION")
    print("=" * 100)

    print(
        "PURPOSE : Identify actual source-level producers of "
        "trend, momentum, acceleration, volatility."
    )

    print(
        "NO REPAIR WAS PERFORMED."
    )
    print(
        "NO MAPPING WAS CREATED."
    )
    print(
        "NO SYNTHETIC FIELD WAS CREATED."
    )
    print(
        "NO PRODUCTION SOURCE WAS MODIFIED."
    )

    print("\n")
    print("=" * 100)
    print("G) SAFETY ASSERTION")
    print("=" * 100)

    print(
        "DATABASE ACCESS : False"
    )
    print(
        "DATABASE WRITE  : False"
    )
    print(
        "FILE WRITE      : False"
    )
    print(
        "PRODUCTION EXECUTION : False"
    )
    print(
        "NETWORK         : False"
    )
    print(
        "SOURCE MUTATION : False"
    )

    print("=" * 100)
    print(
        "END — TECHNICAL SEMANTIC PRODUCER LINEAGE FORENSIC v0.1"
    )
    print("=" * 100)


if __name__ == "__main__":
    main()