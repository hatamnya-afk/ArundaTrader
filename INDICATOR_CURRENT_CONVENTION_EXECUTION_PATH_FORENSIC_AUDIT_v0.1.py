from pathlib import Path
import ast
import re

BASE_DIR = Path(__file__).resolve().parent
ENGINE_PATH = BASE_DIR / "market_data_engine.py"

SEP = "=" * 100
SUB = "-" * 100


def section(title):
    print()
    print(SEP)
    print(title)
    print(SEP)


def subsection(title):
    print()
    print(SUB)
    print(title)
    print(SUB)


def get_source():
    if not ENGINE_PATH.exists():
        return None

    try:
        return ENGINE_PATH.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ENGINE_PATH.read_text(encoding="utf-8-sig")


def function_nodes(tree):
    result = {}

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            result[node.name] = node

    return result


def segment(source, node):
    try:
        return ast.get_source_segment(source, node) or ""
    except Exception:
        return ""


def lineno(node):
    return getattr(node, "lineno", "?") if node else "?"


def function_end(node):
    return getattr(node, "end_lineno", "?") if node else "?"


def normalize(text):
    return re.sub(r"\s+", " ", text.strip())


def contains(text, patterns):
    low = text.lower()
    return any(p.lower() in low for p in patterns)


def line_matches(source, patterns):
    result = []

    for number, line in enumerate(source.splitlines(), start=1):
        low = line.lower()

        if any(p.lower() in low for p in patterns):
            result.append((number, line.rstrip()))

    return result


def print_lines(label, lines, limit=40):
    print(label)

    if not lines:
        print("  [NONE]")
        return

    for number, line in lines[:limit]:
        print(f"  [LINE {number}] {line}")

    if len(lines) > limit:
        print(f"  ... {len(lines) - limit} additional matches")


def function_calls_in_node(node):
    calls = []

    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            calls.append(child)

    return calls


def call_name(call):
    func = call.func

    if isinstance(func, ast.Name):
        return func.id

    if isinstance(func, ast.Attribute):
        return func.attr

    return None


def find_return_nodes(node):
    return [
        child
        for child in ast.walk(node)
        if isinstance(child, ast.Return)
    ]


def print_function_body(name, node, source):
    subsection(f"FUNCTION BODY : {name}")

    body = segment(source, node)

    print(f"START LINE       : {lineno(node)}")
    print(f"END LINE         : {function_end(node)}")
    print(f"SOURCE SIZE      : {len(body)} characters")

    lines = body.splitlines()

    for i, line in enumerate(lines, start=lineno(node)):
        print(f"  [{i:04d}] {line}")

    return body


def analyze_function_execution(name, node, source):
    body = segment(source, node)

    subsection(f"EXECUTION TRACE : {name}")

    print(f"FUNCTION         : {name}")
    print(f"START LINE       : {lineno(node)}")
    print(f"END LINE         : {function_end(node)}")

    calls = function_calls_in_node(node)

    print()
    print("FUNCTION CALLS")
    if not calls:
        print("  [NONE]")
    else:
        seen = set()

        for call in calls:
            cname = call_name(call)

            if cname and cname not in seen:
                seen.add(cname)
                print(
                    f"  [CALL] {cname} "
                    f"(line {lineno(call)})"
                )

    print()
    print("RETURN PATHS")

    returns = find_return_nodes(node)

    if not returns:
        print("  [NO RETURN]")
    else:
        for ret in returns:
            value = ast.get_source_segment(source, ret.value)
            value = normalize(value or "")
            print(
                f"  [RETURN LINE {lineno(ret)}] "
                f"{value}"
            )

    print()
    print("ASSIGNMENT TARGETS")

    assignments = []

    for child in ast.walk(node):
        if isinstance(child, ast.Assign):
            value = ast.get_source_segment(source, child.value)
            value = normalize(value or "")

            for target in child.targets:
                target_text = normalize(
                    ast.get_source_segment(source, target) or ""
                )

                assignments.append(
                    (lineno(child), target_text, value)
                )

        elif isinstance(child, ast.AnnAssign):
            value = ast.get_source_segment(source, child.value)
            value = normalize(value or "")

            target_text = normalize(
                ast.get_source_segment(source, child.target) or ""
            )

            assignments.append(
                (lineno(child), target_text, value)
            )

    if not assignments:
        print("  [NONE]")
    else:
        for number, target, value in assignments:
            print(
                f"  [LINE {number}] "
                f"{target} = {value}"
            )

    print()
    print("CONVENTION SIGNALS INSIDE FUNCTION")

    alpha = contains(
        body,
        [
            "2 / (period + 1)",
            "2/(period+1)",
            "2.0 / (period + 1)",
            "2.0/(period+1)",
            "alpha",
        ],
    )

    seed = contains(
        body,
        [
            "mean(",
            "sum(",
            "seed",
            "initial",
            "[:period]",
        ],
    )

    recursive = contains(
        body,
        [
            "previous",
            "prev",
            "ema[-1]",
            "(1 - alpha)",
            "(1-alpha)",
            "alpha *",
        ],
    )

    ewm = contains(
        body,
        [
            ".ewm(",
            "ewm(",
        ],
    )

    gain_loss = contains(
        body,
        [
            "gain",
            "loss",
            "delta",
            "change",
        ],
    )

    wilder = contains(
        body,
        [
            "wilder",
            "1 / period",
            "1/period",
            "alpha=1 / period",
            "alpha = 1 / period",
        ],
    )

    rsi_formula = contains(
        body,
        [
            "100",
            "rs",
        ],
    )

    print(f"  EMA alpha signal       : {alpha}")
    print(f"  EMA seed signal        : {seed}")
    print(f"  EMA recursive signal   : {recursive}")
    print(f"  EMA EWM signal         : {ewm}")
    print(f"  RSI gain/loss signal   : {gain_loss}")
    print(f"  RSI Wilder signal      : {wilder}")
    print(f"  RSI formula signal     : {rsi_formula}")

    return {
        "alpha": alpha,
        "seed": seed,
        "recursive": recursive,
        "ewm": ewm,
        "gain_loss": gain_loss,
        "wilder": wilder,
        "rsi_formula": rsi_formula,
    }


def analyze_indicator_references(source):
    subsection("INDICATOR REFERENCE FORENSIC")

    targets = [
        "ema20",
        "ema50",
        "rsi14",
    ]

    lines = source.splitlines()

    for target in targets:
        print()
        print(f"TARGET : {target}")

        matches = []

        for number, line in enumerate(lines, start=1):
            if target.lower() in line.lower():
                matches.append((number, line.rstrip()))

        if not matches:
            print("  [NOT FOUND]")
            continue

        for number, line in matches:
            print(f"  [LINE {number}] {line}")


def analyze_global_calls(source, functions):
    subsection("GLOBAL CALL GRAPH CANDIDATES")

    interesting = {
        name.lower(): name
        for name in functions
    }

    call_lines = []

    for number, line in enumerate(source.splitlines(), start=1):
        stripped = line.strip()

        if "(" not in stripped:
            continue

        for low_name, original_name in interesting.items():
            pattern = rf"\b{re.escape(low_name)}\s*\("

            if re.search(pattern, stripped, re.IGNORECASE):
                call_lines.append(
                    (number, original_name, stripped)
                )

    if not call_lines:
        print("  [NONE]")
        return

    seen = set()

    for number, name, line in call_lines:
        key = (number, name)

        if key in seen:
            continue

        seen.add(key)

        print(
            f"  [LINE {number}] "
            f"CALL -> {name}()"
        )
        print(f"             {line}")


def identify_candidate_producer(functions):
    candidates = []

    for name, node in functions.items():
        low = name.lower()

        if (
            "indicator" in low
            or "technical" in low
            or "calculate" in low
            or "compute" in low
            or "market" in low
            or "snapshot" in low
            or "metric" in low
        ):
            candidates.append((name, node))

    return candidates


def trace_candidate_producers(source, candidates):
    subsection("CANDIDATE PRODUCER FUNCTIONS")

    if not candidates:
        print("  [NONE IDENTIFIED]")
        return

    for name, node in sorted(candidates):
        body = segment(source, node)

        hits = []

        for target in ["ema20", "ema50", "rsi14"]:
            if target in body.lower():
                hits.append(target)

        print()
        print(f"FUNCTION : {name}")
        print(f"START    : {lineno(node)}")
        print(f"END      : {function_end(node)}")

        if hits:
            print(
                "INDICATOR REFERENCES : "
                + ", ".join(hits)
            )
        else:
            print("INDICATOR REFERENCES : NONE")

        if hits:
            relevant = line_matches(
                body,
                [
                    "ema20",
                    "ema50",
                    "rsi14",
                    "ema",
                    "rsi",
                    "indicator",
                    "technical",
                ],
            )

            for number, line in relevant[:60]:
                absolute = lineno(node) + number - 1
                print(
                    f"  [LINE {absolute}] {line}"
                )


def main():
    section(
        "ARUNDA INDICATOR CURRENT CONVENTION "
        "EXECUTION PATH FORENSIC AUDIT v0.1"
    )

    print("MODE                    : READ ONLY")
    print("DATABASE WRITE          : NONE")
    print("FORMULA WRITE          : NONE")
    print("ENGINE MODIFICATIONS   : NONE")
    print("PRODUCTION RECALC      : NONE")
    print("PURPOSE                : EXACT CALL-PATH FORENSICS")

    section("ENGINE SOURCE")

    print(f"ENGINE PATH             : {ENGINE_PATH}")
    print(f"ENGINE FOUND            : {ENGINE_PATH.exists()}")

    if not ENGINE_PATH.exists():
        print()
        print("STATUS                  : BLOCKED")
        print("REASON                  : ENGINE SOURCE NOT FOUND")
        return

    source = get_source()

    if source is None:
        print()
        print("STATUS                  : BLOCKED")
        print("REASON                  : SOURCE READ FAILED")
        return

    print(f"SOURCE SIZE             : {len(source)} characters")
    print(f"SOURCE LINES            : {len(source.splitlines())}")

    section("AST RESOLUTION")

    try:
        tree = ast.parse(source)
        print("AST PARSE STATUS        : SUCCESS")
    except SyntaxError as exc:
        print("AST PARSE STATUS        : FAILED")
        print(f"ERROR LINE              : {exc.lineno}")
        print(f"ERROR COLUMN            : {exc.offset}")
        print(f"ERROR                   : {exc.msg}")

        print()
        print("STATUS                  : BLOCKED")
        print("REASON                  : INVALID PYTHON SOURCE")
        return

    functions = function_nodes(tree)

    print(f"FUNCTION COUNT          : {len(functions)}")

    section("TARGET FUNCTION INVENTORY")

    ema_functions = []

    for name, node in functions.items():
        low = name.lower()

        if "ema" in low:
            ema_functions.append((name, node))

    rsi_functions = []

    for name, node in functions.items():
        low = name.lower()

        if "rsi" in low:
            rsi_functions.append((name, node))

    print("EMA FUNCTIONS")
    if ema_functions:
        for name, node in sorted(ema_functions):
            print(
                f"  [FOUND] {name} "
                f"(lines {lineno(node)}-{function_end(node)})"
            )
    else:
        print("  [NONE]")

    print()
    print("RSI FUNCTIONS")
    if rsi_functions:
        for name, node in sorted(rsi_functions):
            print(
                f"  [FOUND] {name} "
                f"(lines {lineno(node)}-{function_end(node)})"
            )
    else:
        print("  [NONE]")

    section("TARGET REFERENCE SEARCH")

    analyze_indicator_references(source)

    section("EMA EXECUTION PATH")

    if not ema_functions:
        print("EMA EXECUTION PATH : NOT RESOLVED")
    else:
        for name, node in sorted(ema_functions):
            analyze_function_execution(
                name,
                node,
                source,
            )

    section("RSI EXECUTION PATH")

    if not rsi_functions:
        print("RSI EXECUTION PATH : NOT RESOLVED")
    else:
        for name, node in sorted(rsi_functions):
            analyze_function_execution(
                name,
                node,
                source,
            )

    section("GLOBAL CALL GRAPH")

    analyze_global_calls(
        source,
        functions,
    )

    section("PRODUCER FUNCTION FORENSICS")

    candidates = identify_candidate_producer(
        functions
    )

    trace_candidate_producers(
        source,
        candidates,
    )

    section("RAW SOURCE INDICATOR SIGNALS")

    print_lines(
        "EMA / RSI SOURCE MATCHES",
        line_matches(
            source,
            [
                "ema20",
                "ema50",
                "rsi14",
                "ema",
                "rsi",
                "gain",
                "loss",
                "mean(",
                "seed",
                "previous",
                "prev",
                ".ewm(",
                "alpha",
            ],
        ),
        limit=100,
    )

    section("PATH RESOLUTION RULE")

    print(
        "A convention cause is considered PROVEN only if all of the "
        "following are traceable:"
    )
    print("  1. TARGET FIELD")
    print("  2. PRODUCER FUNCTION")
    print("  3. INDICATOR FUNCTION CALL")
    print("  4. INDICATOR IMPLEMENTATION")
    print("  5. RETURN VALUE")
    print("  6. STORAGE ASSIGNMENT")
    print()
    print(
        "Presence of helper functions or keywords alone does NOT prove "
        "that they produced the stored value."
    )

    section("FORENSIC CONCLUSION")

    resolved_targets = 0

    for target in ["ema20", "ema50", "rsi14"]:
        if target.lower() in source.lower():
            resolved_targets += 1

    if resolved_targets == 3 and (
        ema_functions or rsi_functions
    ):
        print("STATUS                  : EXECUTION_PATH_EVIDENCE_FOUND")
        print(
            "REASON                  : "
            "TARGETS AND PRODUCER FUNCTIONS ARE TRACEABLE"
        )
        print(
            "NEXT STEP               : "
            "INSPECT EXACT ASSIGNMENT / RETURN CHAIN"
        )
    else:
        print("STATUS                  : EXECUTION_PATH_NOT_PROVEN")
        print(
            "REASON                  : "
            "CALL PATH REMAINS INCOMPLETE"
        )

    print()
    print("DATABASE WRITE OPERATIONS : NONE")
    print("ENGINE MODIFICATIONS      : NONE")
    print("FORMULA WRITE             : NONE")
    print("PRODUCTION RECALCULATION  : NONE")
    print("AUDIT COMPLETE")


if __name__ == "__main__":
    main()