import os
import sqlite3
from collections import Counter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "arunda.db")
TABLE = "market_technical"

def main():
    print("=" * 100)
    print("ARUNDA MARKET TECHNICAL PERSISTENCE ORIGIN FORENSIC v0.1")
    print("=" * 100)
    print("MODE : READ ONLY")
    print("EXECUTION : NO")
    print("DB WRITE : NO")
    print("SOURCE MODIFY : NO")
    print(f"DATABASE : {DB_PATH}")
    print()

    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.execute("PRAGMA query_only=1")

    exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (TABLE,)
    ).fetchone()

    if not exists:
        print("market_technical : NOT FOUND")
        conn.close()
        return

    print("=" * 100)
    print("SCHEMA")
    print("=" * 100)

    columns = conn.execute(
        f"PRAGMA table_info({TABLE})"
    ).fetchall()

    for c in columns:
        print(
            f"{c[0]:3} | {c[1]:35} | "
            f"type={c[2]:15} | notnull={c[3]} | pk={c[5]}"
        )

    names = [c[1] for c in columns]

    print()
    print("=" * 100)
    print("ROW COUNT")
    print("=" * 100)

    count = conn.execute(
        f"SELECT COUNT(*) FROM {TABLE}"
    ).fetchone()[0]

    print(f"ROWS : {count}")

    print()
    print("=" * 100)
    print("TIMESTAMP / ORIGIN CANDIDATES")
    print("=" * 100)

    candidates = [
        n for n in names
        if any(x in n.lower() for x in (
            "time", "date", "created", "updated",
            "source", "engine", "batch", "snapshot",
            "version", "origin"
        ))
    ]

    print("CANDIDATE COLUMNS:")
    for n in candidates:
        print(f"  {n}")

    if candidates:
        for n in candidates:
            try:
                rows = conn.execute(
                    f"""
                    SELECT {n}, COUNT(*)
                    FROM {TABLE}
                    GROUP BY {n}
                    ORDER BY COUNT(*) DESC
                    LIMIT 20
                    """
                ).fetchall()

                print()
                print(f"--- {n} ---")
                for value, cnt in rows:
                    print(f"{repr(value):45} : {cnt}")
            except Exception as e:
                print(f"{n} : ERROR {e}")

    print()
    print("=" * 100)
    print("PRIMARY KEY / ID DISTRIBUTION")
    print("=" * 100)

    pk_cols = [c[1] for c in columns if c[5]]

    for n in pk_cols:
        try:
            result = conn.execute(
                f"""
                SELECT MIN({n}), MAX({n}), COUNT(DISTINCT {n})
                FROM {TABLE}
                """
            ).fetchone()

            print(
                f"{n} -> MIN={result[0]} | "
                f"MAX={result[1]} | "
                f"DISTINCT={result[2]}"
            )
        except Exception as e:
            print(f"{n} : ERROR {e}")

    print()
    print("=" * 100)
    print("SYMBOL DISTRIBUTION")
    print("=" * 100)

    if "symbol" in names:
        rows = conn.execute(
            f"""
            SELECT symbol, COUNT(*)
            FROM {TABLE}
            GROUP BY symbol
            ORDER BY COUNT(*) DESC
            LIMIT 30
            """
        ).fetchall()

        for symbol, cnt in rows:
            print(f"{str(symbol):30} : {cnt}")

    print()
    print("=" * 100)
    print("NULL DENSITY")
    print("=" * 100)

    for n in names:
        try:
            nonnull, nulls = conn.execute(
                f"""
                SELECT
                    COUNT({n}),
                    COUNT(*) - COUNT({n})
                FROM {TABLE}
                """
            ).fetchone()

            print(
                f"{n:35} "
                f"NON_NULL={nonnull:8} "
                f"NULL={nulls:8}"
            )
        except Exception:
            pass

    print()
    print("=" * 100)
    print("FIRST 10 ROWS")
    print("=" * 100)

    rows = conn.execute(
        f"SELECT * FROM {TABLE} LIMIT 10"
    ).fetchall()

    for row in rows:
        print(row)

    print()
    print("=" * 100)
    print("LAST 10 ROWS")
    print("=" * 100)

    order_col = None

    for preferred in ("id", "timestamp", "created_at", "updated_at", "time"):
        if preferred in names:
            order_col = preferred
            break

    if order_col:
        rows = conn.execute(
            f"""
            SELECT *
            FROM {TABLE}
            ORDER BY {order_col} DESC
            LIMIT 10
            """
        ).fetchall()
    else:
        rows = conn.execute(
            f"SELECT * FROM {TABLE} LIMIT 10 OFFSET MAX(0, {count}-10)"
        ).fetchall()

    for row in rows:
        print(row)

    print()
    print("=" * 100)
    print("DATABASE OBJECTS REFERENCING market_technical")
    print("=" * 100)

    objects = conn.execute(
        """
        SELECT type, name, sql
        FROM sqlite_master
        WHERE sql IS NOT NULL
        AND lower(sql) LIKE '%market_technical%'
        ORDER BY type, name
        """
    ).fetchall()

    for typ, name, sql in objects:
        print()
        print(f"TYPE : {typ}")
        print(f"NAME : {name}")
        print("SQL  :")
        print(sql)

    print()
    print("=" * 100)
    print("FINAL PERSISTENCE ORIGIN FORENSIC")
    print("=" * 100)
    print("READ ONLY       : YES")
    print("SQLITE MODE     : mode=ro")
    print("QUERY ONLY      : 1")
    print("INSERT          : NONE")
    print("UPDATE          : NONE")
    print("DELETE          : NONE")
    print("ALTER           : NONE")
    print("CREATE          : NONE")
    print("DROP            : NONE")
    print("REPLACE         : NONE")
    print("COMMIT          : NONE")
    print("SOURCE MODIFY   : NONE")
    print("EXECUTION       : NONE")
    print("SYNTHETIC DATA  : NONE")
    print()
    print("FORENSIC STATUS : COMPLETE")
    print("=" * 100)

    conn.close()


if __name__ == "__main__":
    main()