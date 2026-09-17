from pathlib import Path
import re


ROOT = Path(r"C:\Users\ASUS\ArundaTrader")
TARGET = "risk_decisions"

FORENSIC_MARKERS = (
    "FORENSIC",
    "AUDIT",
    "RECONCILIATION",
    "SCAN",
    "BACKWARD_CHAIN",
    "SOURCE_OCCURRENCE",
    "WRITE_BACKWARD",
)


WRITE_PATTERNS = [
    re.compile(
        r"\bINSERT\s+INTO\s+[\"'`]?"
        + re.escape(TARGET)
        + r"[\"'`]?",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bUPDATE\s+[\"'`]?"
        + re.escape(TARGET)
        + r"[\"'`]?",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bDELETE\s+FROM\s+[\"'`]?"
        + re.escape(TARGET)
        + r"[\"'`]?",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bREPLACE\s+(?:INTO\s+)?[\"'`]?"
        + re.escape(TARGET)
        + r"[\"'`]?",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bUPSERT\s+(?:INTO\s+)?[\"'`]?"
        + re.escape(TARGET)
        + r"[\"'`]?",
        re.IGNORECASE,
    ),
]


def is_python_file(path: Path) -> bool:
    return (
        path.suffix.lower() == ".py"
        and path.name != Path(__file__).name
    )


def is_forensic_file(path: Path) -> bool:
    name = path.name.upper()

    return any(
        marker in name
        for marker in FORENSIC_MARKERS
    )


def print_context(lines, line_number, radius=4):
    start = max(0, line_number - radius - 1)
    end = min(len(lines), line_number + radius)

    for i in range(start, end):
        prefix = ">>>" if i == line_number - 1 else "   "
        print(
            f"{prefix} {i + 1:5d} | "
            f"{lines[i].rstrip()}"
        )


def scan_file(path: Path):
    try:
        text = path.read_text(
            encoding="utf-8",
            errors="replace",
        )
    except Exception:
        return []

    lines = text.splitlines()
    hits = []

    for line_number, line in enumerate(lines, start=1):

        for pattern in WRITE_PATTERNS:

            if pattern.search(line):

                hits.append(
                    {
                        "line": line_number,
                        "text": line,
                    }
                )

                break

    return hits


def main():

    print("=" * 110)
    print("ARUNDA — RISK_DECISIONS PRODUCTION WRITER SCAN v0.1")
    print("=" * 110)
    print(f"ROOT   : {ROOT}")
    print(f"TARGET : {TARGET}")
    print()
    print("MODE   : STATIC SOURCE ANALYSIS ONLY")
    print("DB     : NOT OPENED")
    print("IMPORT : NO PRODUCTION MODULE IMPORT")
    print("EXEC   : NO PRODUCTION EXECUTION")
    print("=" * 110)

    production_hits = []
    excluded_hits = []

    files = sorted(ROOT.glob("*.py"))

    for path in files:

        if not is_python_file(path):
            continue

        hits = scan_file(path)

        if not hits:
            continue

        if is_forensic_file(path):
            excluded_hits.append(
                (path, hits)
            )
        else:
            production_hits.append(
                (path, hits)
            )

    print()
    print("=" * 110)
    print("1) PRODUCTION CANDIDATE WRITERS")
    print("=" * 110)

    if not production_hits:
        print("NO DIRECT PRODUCTION risk_decisions WRITE FOUND.")
    else:

        for path, hits in production_hits:

            print()
            print("-" * 110)
            print(f"FILE : {path}")
            print(f"HITS : {len(hits)}")
            print("-" * 110)

            try:
                lines = path.read_text(
                    encoding="utf-8",
                    errors="replace",
                ).splitlines()
            except Exception:
                continue

            for hit in hits:

                print()
                print(
                    f"WRITE CANDIDATE : LINE {hit['line']}"
                )

                print_context(
                    lines,
                    hit["line"],
                    radius=5,
                )

    print()
    print("=" * 110)
    print("2) EXCLUDED FORENSIC / AUDIT MATCHES")
    print("=" * 110)

    excluded_count = 0

    for path, hits in excluded_hits:

        excluded_count += len(hits)

        print(
            f"{path.name} : {len(hits)} excluded matches"
        )

    print()
    print("=" * 110)
    print("3) FINAL RESULT")
    print("=" * 110)

    total_production = sum(
        len(hits)
        for _, hits in production_hits
    )

    print(
        f"PRODUCTION WRITE CANDIDATES : "
        f"{total_production}"
    )

    print(
        f"EXCLUDED FORENSIC/AUDIT     : "
        f"{excluded_count}"
    )

    if total_production == 0:

        print()
        print(
            "RESULT : NO DIRECT PRODUCTION "
            "risk_decisions WRITE PRIMITIVE FOUND."
        )

        print(
            "NEXT TARGET : DYNAMIC SQL BUILDER / "
            "TABLE-NAME PROPAGATION."
        )

    else:

        print()
        print(
            "RESULT : PRODUCTION WRITE CANDIDATE(S) FOUND."
        )

        print(
            "NEXT TARGET : INSPECT HIGHEST-CONFIDENCE "
            "WRITER CONTEXT."
        )

    print()
    print("=" * 110)
    print("SAFETY")
    print("=" * 110)
    print("STATIC SOURCE ANALYSIS ONLY")
    print("NO DATABASE CONNECTION")
    print("NO DATABASE READ")
    print("NO INSERT")
    print("NO UPDATE")
    print("NO DELETE")
    print("NO ALTER")
    print("NO CREATE")
    print("NO COMMIT")
    print("NO NETWORK")
    print("=" * 110)


if __name__ == "__main__":
    main()