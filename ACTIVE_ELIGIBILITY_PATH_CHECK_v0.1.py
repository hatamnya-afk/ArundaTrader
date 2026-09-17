import os
import sqlite3
import inspect
import importlib


PROJECT_ROOT = r"C:\Users\ASUS\ArundaTrader"
DB_PATH = os.path.join(PROJECT_ROOT, "arunda.db")

TARGET_TABLE = "opportunity_signals"


def line(char="=", n=100):
    print(char * n)


def table_exists(conn, table):
    row = conn.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type='table'
          AND name=?
        LIMIT 1
        """,
        (table,),
    ).fetchone()

    return row is not None


def get_columns(conn, table):
    return [
        row[1]
        for row in conn.execute(
            f'PRAGMA table_info("{table}")'
        ).fetchall()
    ]


def load_latest_rows(conn):
    columns = get_columns(conn, TARGET_TABLE)

    if "id" in columns:
        order_column = "id"
    elif "created_at" in columns:
        order_column = "created_at"
    else:
        order_column = columns[0]

    rows = conn.execute(
        f'''
        SELECT *
        FROM "{TARGET_TABLE}"
        ORDER BY "{order_column}" DESC
        LIMIT 48
        '''
    ).fetchall()

    return columns, rows


def print_rows(columns, rows):
    line()
    print("EXISTING REAL PRODUCTION SIGNAL ROWS")
    line()

    print("Columns:")
    print(", ".join(columns))
    print()

    print(f"Rows captured : {len(rows)}")
    print()

    for index, row in enumerate(rows, 1):
        print(f"--- ROW {index} ---")

        for column, value in zip(columns, row):
            print(f"{column:<30} : {value}")

        print()


def discover_eligibility_files():
    print()
    line()
    print("ELIGIBILITY EXECUTION PATH DISCOVERY")
    line()

    matches = []

    keywords = (
        "eligib",
        "evaluate",
        "eligible",
        "no_trade",
        "no-trade",
        "eligibility",
    )

    for root, dirs, files in os.walk(PROJECT_ROOT):

        dirs[:] = [
            d for d in dirs
            if d not in {
                ".git",
                "__pycache__",
                ".venv",
                "venv",
                "env",
                "node_modules",
                "_backups",
            }
        ]

        for filename in files:

            if not filename.endswith(".py"):
                continue

            path = os.path.join(root, filename)

            try:
                with open(
                    path,
                    "r",
                    encoding="utf-8",
                    errors="ignore",
                ) as f:
                    text = f.read()

            except Exception:
                continue

            lower = text.lower()

            if (
                "opportunity_signals" in lower
                and
                any(k in lower for k in keywords)
            ):
                matches.append(path)

    for path in sorted(set(matches)):
        print(path)

    print()
    print(f"Candidate files : {len(set(matches))}")

    return sorted(set(matches))


def inspect_file(path):
    print()
    line()
    print("FILE")
    line()
    print(path)

    try:
        with open(
            path,
            "r",
            encoding="utf-8",
            errors="ignore",
        ) as f:
            lines = f.readlines()

    except Exception as exc:
        print(f"READ ERROR : {exc}")
        return

    found = []

    for number, text in enumerate(lines, 1):

        lower = text.lower()

        if (
            "opportunity_signals" in lower
            or "eligible" in lower
            or "eligibility" in lower
            or "no_trade" in lower
        ):
            found.append(number)

    if not found:
        return

    print()
    print("RELEVANT LOCATIONS")
    print()

    shown = set()

    for number in found:

        start = max(1, number - 5)
        end = min(len(lines), number + 5)

        block = range(start, end + 1)

        if any(n in shown for n in block):
            continue

        for n in block:
            print(
                f"{n:5d} | {lines[n - 1].rstrip()}"
            )
            shown.add(n)

        print("-" * 100)


def main():

    line()
    print("ARUNDA TRADER — ACTIVE ELIGIBILITY PATH CHECK")
    line()

    print(f"PROJECT : {PROJECT_ROOT}")
    print(f"DATABASE: {DB_PATH}")
    print(f"TARGET  : {TARGET_TABLE}")
    print("MODE    : READ ONLY")
    print("WRITE   : NONE")

    if not os.path.exists(DB_PATH):
        raise RuntimeError(
            f"Database not found: {DB_PATH}"
        )

    conn = sqlite3.connect(DB_PATH)

    try:

        if not table_exists(
            conn,
            TARGET_TABLE,
        ):
            raise RuntimeError(
                f"Table does not exist: {TARGET_TABLE}"
            )

        columns, rows = load_latest_rows(
            conn
        )

        print()
        print(
            f"TARGET TABLE : {TARGET_TABLE}"
        )

        print(
            f"TOTAL COLUMNS: {len(columns)}"
        )

        print_rows(
            columns,
            rows,
        )

    finally:
        conn.close()

    files = discover_eligibility_files()

    for path in files:
        inspect_file(path)

    print()
    line()
    print("NEXT STEP")
    line()

    print(
        "Use the output above to identify the EXISTING "
        "production eligibility entry point."
    )

    print(
        "Do NOT modify strategy."
    )

    print(
        "Do NOT create synthetic signals."
    )

    print(
        "Do NOT write to the production database."
    )

    line()


if __name__ == "__main__":
    main()