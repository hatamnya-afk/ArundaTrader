from pathlib import Path
import ast
import re

BASE_DIR = Path(__file__).resolve().parent
ENGINE_PATH = BASE_DIR / "market_data_engine.py"

TARGETS = {
    "EMA20": {
        "field": "ema20",
        "functions": ["ema", "ema_series"],
    },
    "EMA50": {
        "field": "ema50",
        "functions": ["ema", "ema_series"],
    },
    "RSI14": {
        "field": "rsi14",
        "functions": ["rsi"],
    },
}

WIDTH = 100


def banner(text):
    print("=" * WIDTH)
    print(text)
    print("=" * WIDTH)


def section(text):
    print()
    print("=" * WIDTH)
    print(text)
    print("-" * WIDTH)


def load_source():
    if not ENGINE_PATH.exists():
        return None, None

    source = ENGINE_PATH.read_text(
        encoding="utf-8",
        errors="replace",
    )

    return source, source.splitlines()


def parse_source(source):
    try:
        return ast.parse(source)
    except SyntaxError as exc:
        print(f"AST PARSE ERROR : {exc}")
        return None


def function_inventory(tree):
    result = {}

    if tree is None:
        return result

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            result[node.name] = node

    return result


def function_source(node, lines):
    if node is None:
        return ""

    start = max(0, node.lineno - 1)
    end = getattr(node, "end_lineno", node.lineno)

    return "\n".join(lines[start:end])


def contains_call(text, function_name):
    return re.search(
        rf"\b{re.escape(function_name)}\s*\(",
        text,
        re.IGNORECASE,
    ) is not None


def find_target_assignments(source, field):
    patterns = [
        rf"""["']{re.escape(field)}["']\s*:""",
        rf"""["']{re.escape(field)}["']\s*\]""",
        rf"""\.{re.escape(field)}\s*=""",
        rf"""\b{re.escape(field)}\s*=""",
    ]

    matches = []

    for number, line in enumerate(
        source.splitlines(),
        start=1,
    ):
        for pattern in patterns:
            if re.search(
                pattern,
                line,
                re.IGNORECASE,
            ):
                matches.append(
                    (number, line.strip())
                )
                break

    return matches


def find_ast_assignments(tree, lines, field):
    results = []

    if tree is None:
        return results

    normalized = field.lower()

    for node in ast.walk(tree):

        if isinstance(node, ast.Assign):
            targets = node.targets

            for target in targets:

                try:
                    target_text = ast.unparse(target)
                except Exception:
                    target_text = ""

                if normalized in target_text.lower():

                    try:
                        value_text = ast.unparse(
                            node.value
                        )
                    except Exception:
                        value_text = ""

                    results.append(
                        {
                            "line": node.lineno,
                            "target": target_text,
                            "value": value_text,
                            "full": ast.unparse(node),
                        }
                    )

        elif isinstance(node, ast.AnnAssign):

            try:
                target_text = ast.unparse(
                    node.target
                )
            except Exception:
                target_text = ""

            if normalized in target_text.lower():

                try:
                    value_text = ast.unparse(
                        node.value
                    ) if node.value else ""
                except Exception:
                    value_text = ""

                results.append(
                    {
                        "line": node.lineno,
                        "target": target_text,
                        "value": value_text,
                        "full": (
                            f"{target_text} = "
                            f"{value_text}"
                        ),
                    }
                )

    return results


def find_producer_functions(
    tree,
    lines,
    target_functions,
):
    found = []

    if tree is None:
        return found

    inventory = function_inventory(tree)

    for name in target_functions:

        if name in inventory:

            node = inventory[name]

            found.append(
                {
                    "name": name,
                    "line": node.lineno,
                    "end_line": getattr(
                        node,
                        "end_lineno",
                        node.lineno,
                    ),
                    "source": function_source(
                        node,
                        lines,
                    ),
                }
            )

    return found


def find_calls_to_producer(
    tree,
    lines,
    target_functions,
):
    results = []

    if tree is None:
        return results

    inventory = function_inventory(tree)

    for caller_name, caller_node in inventory.items():

        caller_text = function_source(
            caller_node,
            lines,
        )

        for producer in target_functions:

            if contains_call(
                caller_text,
                producer,
            ):

                results.append(
                    {
                        "caller": caller_name,
                        "producer": producer,
                        "line": caller_node.lineno,
                        "end_line": getattr(
                            caller_node,
                            "end_lineno",
                            caller_node.lineno,
                        ),
                    }
                )

    return results


def find_returns(producer):
    results = []

    if producer is None:
        return results

    for node in ast.walk(producer):

        if isinstance(node, ast.Return):

            try:
                text = (
                    ast.unparse(node.value)
                    if node.value is not None
                    else "None"
                )
            except Exception:
                text = ""

            results.append(
                {
                    "line": node.lineno,
                    "value": text,
                }
            )

    return results


def inspect_assignment_chain(
    target_name,
    target_config,
    tree,
    lines,
    source,
):
    field = target_config["field"]
    producers = target_config["functions"]

    print()
    print("=" * WIDTH)
    print(f"TARGET : {target_name}")
    print("=" * WIDTH)

    # --------------------------------------------------------
    # 1. TARGET FIELD
    # --------------------------------------------------------

    print()
    print("1. TARGET FIELD")
    print("-" * WIDTH)

    ast_assignments = find_ast_assignments(
        tree,
        lines,
        field,
    )

    text_assignments = find_target_assignments(
        source,
        field,
    )

    target_found = bool(
        ast_assignments or text_assignments
    )

    if ast_assignments:

        for item in ast_assignments:
            print(
                f"  [FOUND] LINE {item['line']} : "
                f"{item['full']}"
            )

    elif text_assignments:

        for line, text in text_assignments:
            print(
                f"  [TEXT EVIDENCE] "
                f"LINE {line} : {text}"
            )

    else:
        print("  [MISSING] TARGET FIELD")

    # --------------------------------------------------------
    # 2. PRODUCER FUNCTION
    # --------------------------------------------------------

    print()
    print("2. PRODUCER FUNCTION")
    print("-" * WIDTH)

    producer_info = find_producer_functions(
        tree,
        lines,
        producers,
    )

    producer_found = bool(producer_info)

    if producer_info:

        for item in producer_info:
            print(
                f"  [FOUND] : {item['name']}() "
                f"LINES {item['line']}-"
                f"{item['end_line']}"
            )

    else:
        print("  [MISSING] PRODUCER FUNCTION")

    # --------------------------------------------------------
    # 3. INDICATOR FUNCTION CALL
    # --------------------------------------------------------

    print()
    print("3. INDICATOR FUNCTION CALL")
    print("-" * WIDTH)

    call_info = find_calls_to_producer(
        tree,
        lines,
        producers,
    )

    relevant_calls = [
        x
        for x in call_info
        if x["producer"] in producers
    ]

    call_found = bool(relevant_calls)

    if relevant_calls:

        seen = set()

        for item in relevant_calls:

            key = (
                item["caller"],
                item["producer"],
            )

            if key in seen:
                continue

            seen.add(key)

            print(
                f"  [FOUND] : "
                f"{item['producer']}() "
                f"inside {item['caller']}() "
                f"LINES {item['line']}-"
                f"{item['end_line']}"
            )

    else:
        print("  [MISSING] INDICATOR FUNCTION CALL")

    # --------------------------------------------------------
    # 4. INDICATOR IMPLEMENTATION
    # --------------------------------------------------------

    print()
    print("4. INDICATOR IMPLEMENTATION")
    print("-" * WIDTH)

    implementation_found = bool(
        producer_info
    )

    if implementation_found:

        for item in producer_info:

            print(
                f"  [FOUND] : {item['name']}()"
            )

            source_lines = item["source"].splitlines()

            for number, line in enumerate(
                source_lines,
                start=item["line"],
            ):

                lowered = line.lower()

                interesting = (
                    "return " in lowered
                    or "alpha" in lowered
                    or "seed" in lowered
                    or "rolling" in lowered
                    or "ewm" in lowered
                    or "rsi" in lowered
                    or "gain" in lowered
                    or "loss" in lowered
                    or "avg" in lowered
                )

                if interesting:
                    print(
                        f"      {number:4d}: "
                        f"{line.strip()}"
                    )

    else:
        print(
            "  [MISSING] "
            "INDICATOR IMPLEMENTATION"
        )

    # --------------------------------------------------------
    # 5. RETURN VALUE
    # --------------------------------------------------------

    print()
    print("5. RETURN VALUE")
    print("-" * WIDTH)

    return_found = False

    if producer_info:

        inventory = function_inventory(tree)

        for item in producer_info:

            node = inventory.get(
                item["name"]
            )

            returns = find_returns(node)

            if returns:

                return_found = True

                for ret in returns:
                    print(
                        f"  [FOUND] "
                        f"{item['name']}() "
                        f"LINE {ret['line']} "
                        f"RETURN {ret['value']}"
                    )

            else:
                print(
                    f"  [MISSING] "
                    f"{item['name']}() RETURN"
                )

    if not return_found:
        print("  [MISSING] RETURN VALUE")

    # --------------------------------------------------------
    # 6. STORAGE ASSIGNMENT
    # --------------------------------------------------------

    print()
    print("6. STORAGE ASSIGNMENT")
    print("-" * WIDTH)

    storage_found = False

    for item in ast_assignments:

        value = item["value"]

        if any(
            contains_call(
                value,
                producer,
            )
            for producer in producers
        ):
            storage_found = True

            print(
                f"  [FOUND] LINE {item['line']} : "
                f"{item['full']}"
            )

    if not storage_found:

        print(
            "  [NO DIRECT PRODUCER→FIELD "
            "ASSIGNMENT PROVEN]"
        )

        if ast_assignments:

            print(
                "  TARGET FIELD EXISTS, "
                "BUT DIRECT CALL CHAIN IS NOT PROVEN."
            )

    # --------------------------------------------------------
    # VERDICT
    # --------------------------------------------------------

    print()
    print("CHAIN VERDICT")
    print("-" * WIDTH)

    print(
        f"  [{'FOUND' if target_found else 'MISSING':7}] "
        f": TARGET FIELD"
    )

    print(
        f"  [{'FOUND' if producer_found else 'MISSING':7}] "
        f": PRODUCER FUNCTION"
    )

    print(
        f"  [{'FOUND' if call_found else 'MISSING':7}] "
        f": INDICATOR FUNCTION CALL"
    )

    print(
        f"  [{'FOUND' if implementation_found else 'MISSING':7}] "
        f": INDICATOR IMPLEMENTATION"
    )

    print(
        f"  [{'FOUND' if return_found else 'MISSING':7}] "
        f": RETURN VALUE"
    )

    print(
        f"  [{'FOUND' if storage_found else 'MISSING':7}] "
        f": STORAGE ASSIGNMENT"
    )

    complete = all(
        [
            target_found,
            producer_found,
            call_found,
            implementation_found,
            return_found,
            storage_found,
        ]
    )

    print()
    print(
        "CHAIN STATUS : "
        + (
            "COMPLETE"
            if complete
            else "INCOMPLETE"
        )
    )

    print(
        "CAUSE STATUS : "
        + (
            "CAUSE_PATH_READY_FOR_DETERMINATION"
            if complete
            else "CAUSE_NOT_PROVEN"
        )
    )

    return {
        "target": target_name,
        "target_found": target_found,
        "producer_found": producer_found,
        "call_found": call_found,
        "implementation_found": implementation_found,
        "return_found": return_found,
        "storage_found": storage_found,
        "complete": complete,
    }


def main():

    banner(
        "ARUNDA INDICATOR CURRENT CONVENTION "
        "COMPLETE EXECUTION CHAIN FORENSIC AUDIT v0.1"
    )

    print("MODE                  : READ ONLY")
    print("DATABASE WRITE        : NONE")
    print("FORMULA WRITE        : NONE")
    print("PRODUCTION RECALCULATION : NONE")
    print(
        "PURPOSE               : "
        "EXACT TARGET → PRODUCER → CALL → "
        "IMPLEMENTATION → RETURN → STORAGE"
    )

    section("PATH RESOLUTION RULE")

    print(
        "A convention cause is considered PROVEN only if "
        "all six execution-chain components are traceable:"
    )

    print("  1. TARGET FIELD")
    print("  2. PRODUCER FUNCTION")
    print("  3. INDICATOR FUNCTION CALL")
    print("  4. INDICATOR IMPLEMENTATION")
    print("  5. RETURN VALUE")
    print("  6. STORAGE ASSIGNMENT")

    print()
    print(
        "Presence of helper functions or keywords alone "
        "does NOT prove that they produced the stored value."
    )

    section("ENGINE SOURCE INVENTORY")

    print(f"ENGINE PATH             : {ENGINE_PATH}")
    print(
        f"ENGINE FOUND            : "
        f"{ENGINE_PATH.exists()}"
    )

    source, lines = load_source()

    if source is None:
        print()
        print("FORENSIC CONCLUSION")
        print("-" * WIDTH)
        print("STATUS                  : BLOCKED")
        print(
            "REASON                  : "
            "ENGINE SOURCE NOT FOUND"
        )
        print("AUDIT COMPLETE")
        return

    print(
        f"SOURCE SIZE             : "
        f"{len(source)} characters"
    )

    print(
        f"SOURCE LINES            : "
        f"{len(lines)}"
    )

    section("AST SOURCE RESOLUTION")

    tree = parse_source(source)

    if tree is None:
        print(
            "AST STATUS              : FAILED"
        )
        print(
            "FORENSIC STATUS         : BLOCKED"
        )
        print(
            "REASON                  : "
            "SOURCE COULD NOT BE PARSED"
        )
        print()
        print(
            "DATABASE WRITE OPERATIONS : NONE"
        )
        print(
            "ENGINE MODIFICATIONS      : NONE"
        )
        print(
            "FORMULA WRITE             : NONE"
        )
        print(
            "PRODUCTION RECALCULATION  : NONE"
        )
        print("AUDIT COMPLETE")
        return

    print(
        "AST STATUS              : SUCCESS"
    )

    inventory = function_inventory(tree)

    section("FUNCTION INVENTORY")

    for name in [
        "ema",
        "ema_series",
        "rsi",
    ]:

        if name in inventory:

            node = inventory[name]

            print(
                f"  [FOUND] : {name}() "
                f"LINE {node.lineno}-"
                f"{getattr(node, 'end_lineno', node.lineno)}"
            )

        else:
            print(
                f"  [NOT FOUND] : {name}()"
            )

    results = []

    for target_name, config in TARGETS.items():

        result = inspect_assignment_chain(
            target_name,
            config,
            tree,
            lines,
            source,
        )

        results.append(result)

    section(
        "FINAL COMPLETE EXECUTION CHAIN FORENSIC SUMMARY"
    )

    targets_checked = len(results)

    complete_chains = sum(
        1
        for result in results
        if result["complete"]
    )

    incomplete_chains = (
        targets_checked - complete_chains
    )

    print(
        f"TARGETS CHECKED        : "
        f"{targets_checked}"
    )

    print(
        f"COMPLETE CHAINS        : "
        f"{complete_chains}"
    )

    print(
        f"INCOMPLETE CHAINS      : "
        f"{incomplete_chains}"
    )

    print()
    print("TARGET MATRIX")
    print("-" * WIDTH)

    for result in results:

        status = (
            "COMPLETE"
            if result["complete"]
            else "INCOMPLETE"
        )

        print(
            f"  [{status:10}] : "
            f"{result['target']}"
        )

    section("FORENSIC CONCLUSION")

    if complete_chains == targets_checked:

        print(
            "STATUS                  : "
            "EXECUTION_PATH_COMPLETE"
        )

        print(
            "REASON                  : "
            "ALL SIX CHAIN COMPONENTS ARE "
            "TRACEABLE FOR ALL TARGETS"
        )

        print(
            "NEXT STEP               : "
            "DETERMINE EXACT CURRENT CONVENTION "
            "FROM PROVEN EXECUTION PATH"
        )

    else:

        print(
            "STATUS                  : "
            "EXECUTION_PATH_INCOMPLETE"
        )

        print(
            "REASON                  : "
            "ONE OR MORE EXECUTION CHAINS "
            "REMAIN INCOMPLETE"
        )

        print(
            "NEXT STEP               : "
            "INSPECT ONLY THE REMAINING "
            "MISSING CHAIN COMPONENTS"
        )

    print()
    print(
        "DATABASE WRITE OPERATIONS : NONE"
    )
    print(
        "ENGINE MODIFICATIONS      : NONE"
    )
    print(
        "FORMULA WRITE             : NONE"
    )
    print(
        "PRODUCTION RECALCULATION  : NONE"
    )
    print("AUDIT COMPLETE")


if __name__ == "__main__":
    main()