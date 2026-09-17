import ast
import os
from pathlib import Path

ROOT = Path(r"C:\Users\ASUS\ArundaTrader")
TARGET = "risk_decisions"

WRITE_METHODS = {
    "execute",
    "executemany",
    "executescript",
}

WRITE_KEYWORDS = (
    "INSERT",
    "UPDATE",
    "REPLACE",
    "UPSERT",
    "DELETE",
)


def is_write_sql(text):
    if not isinstance(text, str):
        return False

    upper = text.upper()

    return any(
        keyword in upper
        for keyword in WRITE_KEYWORDS
    )


def get_constant_string(node):
    if isinstance(node, ast.Constant):
        if isinstance(node.value, str):
            return node.value

    return None


def trace_node(node):
    """
    Recursively collect every Name / Attribute / Call / JoinedStr
    participating in a dynamic SQL argument.
    """

    results = []

    for child in ast.walk(node):

        if isinstance(child, ast.Name):
            results.append(
                ("NAME", child.id)
            )

        elif isinstance(child, ast.Attribute):
            results.append(
                (
                    "ATTRIBUTE",
                    ast.unparse(child)
                )
            )

        elif isinstance(child, ast.Call):
            results.append(
                (
                    "CALL",
                    ast.unparse(child)
                )
            )

        elif isinstance(child, ast.JoinedStr):
            results.append(
                (
                    "FSTRING",
                    ast.unparse(child)
                )
            )

    return results


def scan_file(path):

    try:
        source = path.read_text(
            encoding="utf-8",
            errors="ignore",
        )

        tree = ast.parse(
            source,
            filename=str(path),
        )

    except Exception:
        return []

    findings = []

    for node in ast.walk(tree):

        if not isinstance(node, ast.Call):
            continue

        if not isinstance(node.func, ast.Attribute):
            continue

        if node.func.attr not in WRITE_METHODS:
            continue

        if not node.args:
            continue

        sql_node = node.args[0]

        sql_text = get_constant_string(sql_node)

        dynamic = isinstance(
            sql_node,
            (
                ast.JoinedStr,
                ast.Name,
                ast.Call,
                ast.BinOp,
            ),
        )

        if sql_text is not None:

            if not is_write_sql(sql_text):
                continue

            if TARGET.lower() not in sql_text.lower():
                continue

            findings.append(
                {
                    "line": node.lineno,
                    "method": node.func.attr,
                    "kind": "STATIC_TARGET_HIT",
                    "sql": sql_text.strip(),
                    "trace": [],
                }
            )

            continue

        if not dynamic:
            continue

        trace = trace_node(sql_node)

        trace_text = " | ".join(
            f"{kind}:{value}"
            for kind, value in trace
        )

        findings.append(
            {
                "line": node.lineno,
                "method": node.func.attr,
                "kind": "DYNAMIC_WRITE",
                "sql": ast.unparse(sql_node),
                "trace": trace,
                "trace_text": trace_text,
            }
        )

    return findings


def main():

    print("=" * 110)
    print("ARUNDA — RISK_DECISIONS TARGET WRITER ARGUMENT TRACE v0.1")
    print("=" * 110)
    print(f"ROOT   : {ROOT}")
    print(f"TARGET : {TARGET}")
    print()
    print("MODE   : STATIC SOURCE ANALYSIS ONLY")
    print("DB     : NOT OPENED")
    print("IMPORT : NONE")
    print("EXEC   : NO PRODUCTION EXECUTION")
    print("=" * 110)

    total = 0

    for path in sorted(ROOT.glob("*.py")):

        # خود اسکریپت را بررسی نکن
        if path.name == Path(__file__).name:
            continue

        findings = scan_file(path)

        if not findings:
            continue

        for item in findings:

            total += 1

            print()
            print("-" * 110)

            print(
                f"FILE   : {path}"
            )

            print(
                f"LINE   : {item['line']}"
            )

            print(
                f"METHOD : {item['method']}"
            )

            print(
                f"KIND   : {item['kind']}"
            )

            print(
                f"SQL    : {item['sql']}"
            )

            if item["trace"]:

                print(
                    "ARGUMENT TRACE:"
                )

                for kind, value in item["trace"]:

                    print(
                        f"    {kind:<12} : {value}"
                    )

    print()
    print("=" * 110)
    print("FINAL RESULT")
    print("=" * 110)

    print(
        f"TARGET WRITER TRACE HITS : {total}"
    )

    if total == 0:

        print(
            "RESULT : NO risk_decisions TARGET WRITER ARGUMENT HIT FOUND."
        )

        print(
            "NEXT TARGET : TABLE-NAME / SQL BUILDER PROPAGATION."
        )

    else:

        print(
            "RESULT : RISK_DECISIONS WRITER ARGUMENT PATH(S) FOUND."
        )

        print(
            "NEXT TARGET : INSPECT ONLY THE REPORTED FILE/LINE ARGUMENT CHAIN."
        )

    print()
    print("=" * 110)
    print("SAFETY")
    print("=" * 110)
    print("STATIC SOURCE ANALYSIS ONLY")
    print("NO PRODUCTION MODULE IMPORT")
    print("NO DATABASE CONNECTION")
    print("NO DATABASE READ")
    print("NO SELECT EXECUTION")
    print("NO INSERT")
    print("NO UPDATE")
    print("NO DELETE")
    print("NO ALTER")
    print("NO CREATE")
    print("NO COMMIT")
    print("NO NETWORK")
    print("NO ORDER")
    print("NO TRADE")
    print("=" * 110)


if __name__ == "__main__":
    main()