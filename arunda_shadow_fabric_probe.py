from __future__ import annotations

import sqlite3
from pathlib import Path


PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

FABRIC_DB = (
    PROJECT_ROOT
    / "public_market_data_fabric"
    / "canonical_store_v0.1.sqlite"
)

LAUNCH_TIMESTAMP = 1788134400


def main():

    if not FABRIC_DB.exists():
        raise RuntimeError(
            f"FABRIC_MISSING={FABRIC_DB}"
        )

    conn = sqlite3.connect(
        f"file:{FABRIC_DB}?mode=ro",
        uri=True,
    )

    try:

        tables = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            ORDER BY name
            """
        ).fetchall()

        print(f"FABRIC_DB={FABRIC_DB}")
        print(f"TABLE_COUNT={len(tables)}")

        for (table,) in tables:

            print()
            print(f"TABLE={table}")

            cols = conn.execute(
                f'PRAGMA table_info("{table}")'
            ).fetchall()

            print(
                "COLUMNS="
                + ",".join(
                    str(row[1])
                    for row in cols
                )
            )

            try:
                count = conn.execute(
                    f'SELECT COUNT(*) FROM "{table}"'
                ).fetchone()[0]

                print(f"ROWS={count}")

            except Exception as exc:
                print(
                    f"ROWS_ERROR={type(exc).__name__}"
                )
                continue

            try:
                sample = conn.execute(
                    f'''
                    SELECT *
                    FROM "{table}"
                    LIMIT 5
                    '''
                ).fetchall()

                for index, row in enumerate(
                    sample,
                    start=1,
                ):
                    print(
                        f"SAMPLE_{index}="
                        + repr(row)
                    )

            except Exception as exc:
                print(
                    f"SAMPLE_ERROR={type(exc).__name__}"
                )

        print()
        print("=== POST_LAUNCH_TIMESTAMP_PROBE ===")

        for (table,) in tables:

            cols = [
                row[1]
                for row in conn.execute(
                    f'PRAGMA table_info("{table}")'
                ).fetchall()
            ]

            timestamp_candidates = [
                c for c in cols
                if c.lower() in {
                    "timestamp",
                    "ts",
                    "time",
                    "open_time",
                    "open_timestamp",
                    "source_timestamp",
                }
            ]

            if not timestamp_candidates:
                continue

            for timestamp_col in timestamp_candidates:

                try:
                    result = conn.execute(
                        f'''
                        SELECT
                            COUNT(*),
                            MIN("{timestamp_col}"),
                            MAX("{timestamp_col}")
                        FROM "{table}"
                        WHERE "{timestamp_col}" >= ?
                        ''',
                        (LAUNCH_TIMESTAMP,),
                    ).fetchone()

                    print(
                        f"TABLE={table} "
                        f"TIMESTAMP_COLUMN={timestamp_col} "
                        f"POST_LAUNCH_ROWS={result[0]} "
                        f"MIN={result[1]} "
                        f"MAX={result[2]}"
                    )

                except Exception as exc:
                    print(
                        f"TIMESTAMP_PROBE_ERROR="
                        f"{table}.{timestamp_col} "
                        f"{type(exc).__name__}"
                    )

        print()
        print("=== PROVENANCE_PROBE ===")

        provenance_terms = (
            "source",
            "provider",
            "provenance",
            "engine",
        )

        for (table,) in tables:

            cols = [
                row[1]
                for row in conn.execute(
                    f'PRAGMA table_info("{table}")'
                ).fetchall()
            ]

            interesting = [
                c for c in cols
                if any(
                    term in c.lower()
                    for term in provenance_terms
                )
            ]

            if not interesting:
                continue

            print(
                f"TABLE={table} "
                f"PROVENANCE_COLUMNS="
                + ",".join(interesting)
            )

            try:
                select_cols = ",".join(
                    f'"{c}"'
                    for c in interesting
                )

                rows = conn.execute(
                    f'''
                    SELECT {select_cols}
                    FROM "{table}"
                    LIMIT 10
                    '''
                ).fetchall()

                for row in rows:
                    print(
                        "PROVENANCE_SAMPLE="
                        + repr(row)
                    )

            except Exception as exc:
                print(
                    f"PROVENANCE_ERROR="
                    f"{type(exc).__name__}"
                )

    finally:
        conn.close()


if __name__ == "__main__":
    main()