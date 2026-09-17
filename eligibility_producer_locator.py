# ARUNDA — ELIGIBILITY PRODUCER LOCATOR v0.1
# READ ONLY
# NO DB WRITE
# NO ARTIFACT WRITE
# NO CODE MODIFICATION

import ast
from pathlib import Path

ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

TARGET_WORDS = (
    "eligib",
    "eligible",
    "no_trade",
    "decision",
)

EXCLUDE_DIRS = {
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "backup",
    "backups",
}

def score_name(name):
    name = name.lower()
    score = 0

    for word in TARGET_WORDS:
        if word in name:
            score += 10

    return score


def inspect_file(path):

    try:
        source = path.read_text(
            encoding="utf-8",
            errors="ignore",
        )

        tree = ast.parse(source)

    except Exception:
        return []

    hits = []

    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):

            score = score_name(node.name)

            body_text = ast.get_source_segment(
                source,
                node,
            ) or ""

            lower_body = body_text.lower()

            for word in TARGET_WORDS:

                if word in lower_body:
                    score += 2

            if score > 0:

                hits.append(
                    (
                        score,
                        node.name,
                        node.lineno,
                        node.end_lineno,
                        body_text,
                    )
                )

    return hits


def main():

    print("=" * 100)
    print("ARUNDA — ELIGIBILITY PRODUCER LOCATOR v0.1")
    print("=" * 100)
    print("MODE : READ ONLY")
    print("ROOT :", ROOT)
    print()

    results = []

    for path in ROOT.rglob("*.py"):

        if any(
            part in EXCLUDE_DIRS
            for part in path.parts
        ):
            continue

        hits = inspect_file(path)

        for hit in hits:

            results.append(
                (
                    hit[0],
                    path,
                    hit[1],
                    hit[2],
                    hit[3],
                    hit[4],
                )
            )

    results.sort(
        key=lambda x: (
            -x[0],
            str(x[1]),
            x[3],
        )
    )

    print(
        "MATCHED FUNCTIONS:",
        len(results),
    )
    print()

    for (
        score,
        path,
        name,
        start,
        end,
        body,
    ) in results:

        print("=" * 100)
        print(
            "SCORE    :",
            score,
        )
        print(
            "FILE     :",
            path,
        )
        print(
            "FUNCTION :",
            name,
        )
        print(
            "LINES    :",
            f"{start}-{end}",
        )
        print("-" * 100)
        print(body)
        print()

    print("=" * 100)
    print("END")
    print("=" * 100)


if __name__ == "__main__":
    main()