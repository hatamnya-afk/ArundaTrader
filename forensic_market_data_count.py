import sqlite3
import market_regime_engine as mr


print("=" * 78)
print("MARKET DATA RAW COUNT FORENSIC")
print("=" * 78)
print("MODE : READ ONLY")
print()


conn = sqlite3.connect(mr.DB_PATH)
conn.row_factory = sqlite3.Row

try:

    columns = mr._get_columns(
        conn,
        "market_data",
    )

    print("COLUMNS:")
    print(columns)
    print()

    symbol_col = mr._find_column(
        columns,
        ["symbol"],
    )

    open_col = mr._find_column(
        columns,
        ["open", "open_price", "openPrice"],
    )

    high_col = mr._find_column(
        columns,
        ["high", "high_price", "highPrice"],
    )

    low_col = mr._find_column(
        columns,
        ["low", "low_price", "lowPrice"],
    )

    close_col = mr._find_column(
        columns,
        ["close", "close_price", "closePrice"],
    )

    print("RESOLVED COLUMNS")
    print("SYMBOL :", symbol_col)
    print("OPEN   :", open_col)
    print("HIGH   :", high_col)
    print("LOW    :", low_col)
    print("CLOSE  :", close_col)
    print()

    query = f"""
        SELECT
            "{symbol_col}" AS symbol,
            COUNT(*) AS total,
            SUM(
                CASE
                    WHEN "{open_col}" IS NULL
                      OR "{high_col}" IS NULL
                      OR "{low_col}" IS NULL
                      OR "{close_col}" IS NULL
                    THEN 1
                    ELSE 0
                END
            ) AS null_ohlc
        FROM market_data
        GROUP BY "{symbol_col}"
        ORDER BY "{symbol_col}"
    """

    rows = conn.execute(query).fetchall()

    print("EXPECTED ASSET COUNTS")
    print("-" * 78)

    for asset in mr.EXPECTED_ASSETS:

        matches = [
            row
            for row in rows
            if str(row["symbol"]).strip().upper() == asset
        ]

        if not matches:
            print(
                f"{asset:<6} | NOT FOUND"
            )
            continue

        row = matches[0]

        print(
            f"{asset:<6} | "
            f"RAW={row['total']:<6} | "
            f"NULL_OHLC={row['null_ohlc']}"
        )

    print()
    print("=" * 78)
    print("LOADER COUNTS")
    print("=" * 78)

    history = mr.load_market_data_by_symbol()

    for asset in mr.EXPECTED_ASSETS:

        print(
            f"{asset:<6} | "
            f"LOADER={len(history.get(asset, []))}"
        )

finally:

    conn.close()