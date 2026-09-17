from pathlib import Path
import ast


ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

SKIP_MARKERS = (
    "FORENSIC",
    "AUDIT",
    "RECONCILIATION",
    "SCAN",
    "BACKWARD_CHAIN",
    "SOURCE_OCCURRENCE",
    "WRITE_BACKWARD",
)

WRITE_WORDS = (
    "INSERT",
    "UPDATE",
    "DELETE",
    "REPLACE",
    "UPSERT",
    "MERGE",
)


class DynamicWriteVisitor(ast.NodeVisitor):

    def __init__(self, path, lines):
        self.path = path
        self.lines = lines
        self.hits = []

    def visit_Call(self, node):

        if not isinstance(node.func, ast.Attribute):
            self.generic_visit(node)
            return

        method = node.func.attr.lower()

        if method not in {
            "execute",
            "executemany",
            "executescript",
        }:
            self.generic_visit(node)
            return

        if not node.args:
            self.generic_visit(node)
            return

        sql_node = node.args[0]

        sql_text = self.extract_sql_text(sql_node)

        if sql_text is None:
            self.generic_visit(node)
            return

        normalized = sql_text.upper()

        if any(
            word in normalized
            for word in WRITE_WORDS
        ):

            self.hits.append(
                {
                    "line": node.lineno,
                    "method": method,
                    "sql_node": type(sql_node).__name__,
                    "sql": sql_text,
                }
            )

        self.generic_visit(node)

    def extract_sql_text(self, node):

        if isinstance(node, ast.Constant):

            if isinstance(node.value, str):
                return node.value

            return None

        if isinstance(node, ast.JoinedStr):

            parts = []

            for value in node.values:

                if isinstance(
                    value,
                    ast.Constant,
                ):
                    parts.append(
                        str(value.value)
                    )

                elif isinstance(
                    value,
                    ast.FormattedValue,
                ):
                    parts.append(
                        "{DYNAMIC}"
                    )

            return "".join(parts)

        if isinstance(node, ast.Name):

            return f"{{VARIABLE:{node.id}}}"

        if isinstance(node, ast.Attribute):

            return (
                "{ATTRIBUTE:"
                + ast.unparse(node)
                + "}"
            )

        if isinstance(node, ast.BinOp):

            try:
                return ast.unparse(node)
            except Exception:
                return "{BINOP}"

        if isinstance(node, ast.Call):

            try:
                return ast.unparse(node)
            except Exception:
                return "{CALL}"

        return None


def is_forensic(path):

    name = path.name.upper()

    return any(
        marker in name
        for marker in SKIP_MARKERS
    )


def show_context(
    lines,
    line,
    radius=8,
):

    start = max(
        0,
        line - radius - 1,
    )

    end = min(
        len(lines),
        line + radius,
    )

    for i in range(start, end):

        marker = (
            ">>>"
            if i == line - 1
            else "   "
        )

        print(
            f"{marker} "
            f"{i + 1:5d} | "
            f"{lines[i].rstrip()}"
        )


def main():

    print("=" * 110)
    print(
        "ARUNDA — DYNAMIC PRODUCTION WRITE "
        "PRIMITIVE SCAN v0.2"
    )
    print("=" * 110)

    print(f"ROOT : {ROOT}")
    print()
    print("MODE : STATIC SOURCE ANALYSIS ONLY")
    print("DATABASE : NOT OPENED")
    print("PRODUCTION IMPORT : NONE")
    print("PRODUCTION EXECUTION : NONE")
    print("=" * 110)

    total = 0

    for path in sorted(
        ROOT.glob("*.py")
    ):

        if path.name == Path(
            __file__
        ).name:
            continue

        if is_forensic(path):
            continue

        try:

            text = path.read_text(
                encoding="utf-8",
                errors="replace",
            )

            tree = ast.parse(text)

        except Exception:
            continue

        lines = text.splitlines()

        visitor = DynamicWriteVisitor(
            path,
            lines,
        )

        visitor.visit(tree)

        if not visitor.hits:
            continue

        print()
        print("=" * 110)
        print(f"FILE : {path}")
        print("=" * 110)

        for hit in visitor.hits:

            total += 1

            print()
            print(
                f"WRITE CANDIDATE #{total}"
            )

            print(
                f"METHOD   : {hit['method']}"
            )

            print(
                f"LINE     : {hit['line']}"
            )

            print(
                f"SQL NODE : {hit['sql_node']}"
            )

            print(
                f"SQL      : {hit['sql']}"
            )

            print()

            show_context(
                lines,
                hit["line"],
                radius=8,
            )

    print()
    print("=" * 110)
    print("FINAL RESULT")
    print("=" * 110)

    print(
        f"DYNAMIC WRITE CANDIDATES : {total}"
    )

    print()

    if total == 0:

        print(
            "RESULT : NO DYNAMIC WRITE "
            "PRIMITIVE FOUND."
        )

        print(
            "NEXT TARGET : "
            "CALL-SITE / BUILDER DISCOVERY."
        )

    else:

        print(
            "RESULT : DYNAMIC WRITE "
            "CANDIDATE(S) FOUND."
        )

        print(
            "NEXT TARGET : "
            "TRACE TABLE-NAME ARGUMENT "
            "FOR EACH WRITE CANDIDATE."
        )

    print()
    print("=" * 110)
    print("SAFETY")
    print("=" * 110)
    print("STATIC SOURCE ANALYSIS ONLY")
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