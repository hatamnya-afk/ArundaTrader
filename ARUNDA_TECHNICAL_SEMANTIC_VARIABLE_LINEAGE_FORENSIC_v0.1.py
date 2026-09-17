from pathlib import Path
import ast


PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

TECHNICAL_ENGINE = PROJECT_ROOT / "technical_engine.py"
MARKET_REGIME_ENGINE = PROJECT_ROOT / "market_regime_engine.py"
MARKET_REGIME = PROJECT_ROOT / "market_regime.py"

TARGET_FIELDS = {
    "trend",
    "momentum",
    "acceleration",
    "position",
    "volatility",
}

TARGET_VARIABLES = {
    "trend",
    "trend_direction",
    "trend_strength",
    "trend_alignment",

    "momentum",
    "momentum_state",

    "acceleration",
    "acceleration_state",

    "position",

    "volatility",
    "volatility_state",
}


def read_source(path):
    return path.read_text(
        encoding="utf-8-sig"
    )


def parse_source(path):
    source = read_source(path)

    return (
        source,
        ast.parse(
            source,
            filename=str(path),
        ),
    )


def node_source(source, node):
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


def ast_text(node):
    return ast.dump(
        node,
        indent=2,
    )


def is_target_name(node):
    return (
        isinstance(
            node,
            ast.Name,
        )
        and node.id in TARGET_VARIABLES
    )


def collect_assignments(tree):
    result = []

    for function in ast.walk(tree):

        if not isinstance(
            function,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            continue

        for node in ast.walk(function):

            if isinstance(
                node,
                ast.Assign,
            ):

                for target in node.targets:

                    if is_target_name(
                        target
                    ):

                        result.append(
                            {
                                "function":
                                    function.name,
                                "line":
                                    node.lineno,
                                "field":
                                    target.id,
                                "node":
                                    node,
                            }
                        )

            elif isinstance(
                node,
                ast.AnnAssign,
            ):

                if is_target_name(
                    node.target
                ):

                    result.append(
                        {
                            "function":
                                function.name,
                            "line":
                                node.lineno,
                            "field":
                                node.target.id,
                            "node":
                                node,
                        }
                    )

    return result


def collect_returns(tree):
    result = []

    for function in ast.walk(tree):

        if not isinstance(
            function,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            continue

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

                result.append(
                    {
                        "function":
                            function.name,
                        "line":
                            node.lineno,
                        "fields":
                            sorted(fields),
                        "node":
                            node,
                    }
                )

    return result


def collect_calls(tree):
    result = []

    for function in ast.walk(tree):

        if not isinstance(
            function,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            continue

        for node in ast.walk(function):

            if not isinstance(
                node,
                ast.Call,
            ):
                continue

            if isinstance(
                node.func,
                ast.Name,
            ):

                name = node.func.id

            elif isinstance(
                node.func,
                ast.Attribute,
            ):

                name = node.func.attr

            else:
                continue

            if name in {
                "calculate_asset",
                "calculate_structure",
                "build_structural_state",
                "load_structural_state",
                "build_structure",
            }:

                result.append(
                    {
                        "function":
                            function.name,
                        "callee":
                            name,
                        "line":
                            node.lineno,
                    }
                )

    return result


def print_header(title):
    print("\n")
    print("=" * 100)
    print(title)
    print("=" * 100)


def inspect_file(path):

    if not path.exists():

        print(
            f"\nFILE NOT FOUND : {path}"
        )

        return None

    source, tree = parse_source(
        path
    )

    print_header(
        f"FILE : {path.name}"
    )

    assignments = collect_assignments(
        tree
    )

    returns = collect_returns(
        tree
    )

    calls = collect_calls(
        tree
    )

    print("\n")
    print(
        "TARGET VARIABLE ASSIGNMENTS"
    )
    print("-" * 100)

    if not assignments:

        print(
            "NONE"
        )

    else:

        for item in assignments:

            print(
                f"\nFIELD    : {item['field']}"
            )

            print(
                f"FUNCTION : {item['function']}"
            )

            print(
                f"LINE     : {item['line']}"
            )

            print(
                "\nSOURCE"
            )

            print(
                node_source(
                    source,
                    item["node"],
                )
            )

            print(
                "\nVALUE AST"
            )

            value = (
                item["node"].value
                if hasattr(
                    item["node"],
                    "value",
                )
                else None
            )

            if value is not None:

                print(
                    ast_text(
                        value
                    )
                )

    print_header(
        "RETURN-LEVEL SEMANTIC FIELDS"
    )

    if not returns:

        print(
            "NONE"
        )

    else:

        for item in returns:

            print(
                f"\nFUNCTION : {item['function']}"
            )

            print(
                f"LINE     : {item['line']}"
            )

            print(
                f"FIELDS   : {item['fields']}"
            )

            print(
                "\nRETURN AST"
            )

            print(
                ast_text(
                    item["node"].value
                )
            )

    print_header(
        "IMPORTANT CALLS"
    )

    if not calls:

        print(
            "NONE"
        )

    else:

        for item in calls:

            print(
                f"{item['function']}"
                f" -> {item['callee']}()"
                f" @ line {item['line']}"
            )

    return {
        "source": source,
        "tree": tree,
        "assignments": assignments,
        "returns": returns,
        "calls": calls,
    }


def field_producers(results):

    producers = {
        field: []
        for field in TARGET_FIELDS
    }

    for result in results:

        if result is None:
            continue

        for item in result[
            "assignments"
        ]:

            field = item["field"]

            if field in producers:

                producers[field].append(
                    (
                        item["function"],
                        item["line"],
                    )
                )

    return producers


def detect_existing_acceleration(
    results
):

    candidates = []

    for result in results:

        if result is None:
            continue

        for item in result[
            "assignments"
        ]:

            field = item["field"]

            if (
                field == "acceleration"
                or
                field == "acceleration_state"
            ):

                candidates.append(
                    (
                        item["function"],
                        item["line"],
                        field,
                        item["node"],
                    )
                )

    return candidates


def detect_contract_mismatch(
    market_regime_result,
    market_regime_engine_result,
    technical_result,
):

    print_header(
        "CONTRACT CONSISTENCY"
    )

    problems = []

    if (
        market_regime_result
        is not None
    ):

        for item in (
            market_regime_result[
                "calls"
            ]
        ):

            if (
                item["callee"]
                == "build_structure"
            ):

                print(
                    "\nmarket_regime.py "
                    "calls build_structure()."
                )

    if (
        market_regime_engine_result
        is not None
    ):

        structural_returns = (
            market_regime_engine_result[
                "returns"
            ]
        )

        for item in structural_returns:

            if (
                "trend" not in item[
                    "fields"
                ]
                and
                "momentum" not in item[
                    "fields"
                ]
            ):

                continue

    if (
        technical_result
        is not None
    ):

        technical_fields = set()

        for item in technical_result[
            "assignments"
        ]:

            if item["field"] in {
                "trend",
                "momentum",
                "volatility",
            }:

                technical_fields.add(
                    item["field"]
                )

        missing = (
            TARGET_FIELDS
            - technical_fields
        )

        if missing:

            print(
                "\nTECHNICAL SEMANTIC "
                "FIELDS NOT DIRECTLY PRODUCED:"
            )

            for field in sorted(
                missing
            ):

                print(
                    f"  - {field}"
                )

            problems.extend(
                sorted(missing)
            )

    return problems


def repair_existing_producer_only(
    technical_path,
    technical_result,
):

    print_header(
        "REPAIR GATE"
    )

    acceleration_candidates = (
        detect_existing_acceleration(
            [technical_result]
        )
    )

    if not acceleration_candidates:

        print(
            "\nNO EXISTING ACCELERATION "
            "PRODUCER FOUND."
        )

        print(
            "\nREPAIR ABORTED."
        )

        print(
            "REASON:"
        )

        print(
            "An acceleration value cannot "
            "be invented safely."
        )

        print(
            "No synthetic field was inserted."
        )

        return False

    print(
        "\nEXISTING ACCELERATION "
        "PRODUCER(S):"
    )

    for (
        function,
        line,
        field,
        node,
    ) in acceleration_candidates:

        print(
            f"  {function}"
            f" @ line {line}"
            f" -> {field}"
        )

    print(
        "\nREPAIR STATUS:"
    )

    print(
        "Existing producer detected."
    )

    print(
        "However, automatic mutation is "
        "blocked until the producer's "
        "semantic contract is explicit."
    )

    print(
        "\nNO SOURCE MODIFICATION PERFORMED."
    )

    return False


def final_decision(
    producers,
    problems,
):

    print_header(
        "FINAL DECISION"
    )

    print(
        "ACTUAL PRODUCERS"
    )

    for field in sorted(
        TARGET_FIELDS
    ):

        values = producers.get(
            field,
            [],
        )

        print(
            f"\n{field}:"
        )

        if not values:

            print(
                "  MISSING"
            )

        else:

            for (
                function,
                line,
            ) in values:

                print(
                    f"  {function}"
                    f" @ line {line}"
                )

    print("\n")

    if "acceleration" in problems:

        print(
            "CRITICAL:"
        )

        print(
            "acceleration has no confirmed "
            "source-level producer."
        )

        print(
            "Therefore it MUST NOT be "
            "synthesized during repair."
        )

    print(
        "\nNO DATABASE ACCESS."
    )

    print(
        "NO DATABASE WRITE."
    )

    print(
        "NO SYNTHETIC DATA."
    )

    print(
        "NO FORWARD/BACK FILL."
    )

    print(
        "NO SOURCE MUTATION."
    )


def main():

    print("=" * 100)
    print(
        "ARUNDA TRADER — "
        "TECHNICAL SEMANTIC VARIABLE "
        "LINEAGE AND REPAIR v0.1"
    )
    print("=" * 100)

    print(
        f"PROJECT ROOT : {PROJECT_ROOT}"
    )

    print(
        "MODE         : READ + "
        "CONTRACT-GATED REPAIR"
    )

    print(
        "DATABASE     : NONE"
    )

    print(
        "WRITE        : BLOCKED "
        "UNTIL PRODUCER CONTRACT "
        "IS PROVEN"
    )

    print(
        "BOM HANDLING : UTF-8-SIG"
    )

    technical = inspect_file(
        TECHNICAL_ENGINE
    )

    market_regime_engine = (
        inspect_file(
            MARKET_REGIME_ENGINE
        )
    )

    market_regime = inspect_file(
        MARKET_REGIME
    )

    results = [
        technical,
        market_regime_engine,
        market_regime,
    ]

    producers = field_producers(
        results
    )

    problems = detect_contract_mismatch(
        market_regime,
        market_regime_engine,
        technical,
    )

    repair_existing_producer_only(
        TECHNICAL_ENGINE,
        technical,
    )

    final_decision(
        producers,
        problems,
    )

    print("\n")
    print("=" * 100)
    print(
        "END — "
        "TECHNICAL SEMANTIC VARIABLE "
        "LINEAGE AND REPAIR v0.1"
    )
    print("=" * 100)


if __name__ == "__main__":
    main()