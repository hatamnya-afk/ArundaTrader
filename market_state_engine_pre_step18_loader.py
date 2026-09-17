# ==============================================================================
# ARUNDA MARKET STATE ENGINE v0.2.1
# ==============================================================================
# NORMALIZED UNIFIED MARKET STATE CONTRACT
#
# Layers:
#   market_history
#   market_technical
#   market_news_intelligence
#   market_whale
#   market_microstructure
#
# This layer DOES NOT:
#   Ranking
#   Opportunity
#   Signal
#   Prediction
#   Risk
#   Execution
# ==============================================================================

import sqlite3
import math
import traceback
from datetime import datetime, timezone


DB_PATH = "arunda.db"
ENGINE_VERSION = "MARKET_STATE_UNIFIED_v0.2.1"


# ==============================================================================
# UTILITIES
# ==============================================================================

def utc_now():
    return datetime.now(timezone.utc).isoformat()


def safe_float(value):
    try:
        if value is None:
            return None

        value = float(value)

        if not math.isfinite(value):
            return None

        return value

    except Exception:
        return None


def clamp(value, low=-1.0, high=1.0):
    value = safe_float(value)

    if value is None:
        return None

    return max(low, min(high, value))


def normalize_percent(value, scale=10.0):
    """
    Converts a percentage-like value into approximately [-1, +1].
    Example:
        +10% -> +1
        -10% -> -1
    """
    value = safe_float(value)

    if value is None:
        return None

    return clamp(value / scale)


def inverse_normalize(value, scale=10.0):
    value = safe_float(value)

    if value is None:
        return None

    return clamp(-(value / scale))


def table_exists(conn, table_name):
    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
          AND name=?
        """,
        (table_name,),
    ).fetchone()

    return row is not None


def get_columns(conn, table_name):
    if not table_exists(conn, table_name):
        return []

    rows = conn.execute(
        f'PRAGMA table_info("{table_name}")'
    ).fetchall()

    return [row[1] for row in rows]


def get_table_info(conn, table_name):
    if not table_exists(conn, table_name):
        return []

    return conn.execute(
        f'PRAGMA table_info("{table_name}")'
    ).fetchall()


def find_column(columns, candidates):
    lower_map = {c.lower(): c for c in columns}

    for candidate in candidates:
        if candidate.lower() in lower_map:
            return lower_map[candidate.lower()]

    return None


def ensure_column(conn, table_name, column_name, column_type):
    columns = get_columns(conn, table_name)

    if column_name in columns:
        return False

    conn.execute(
        f'ALTER TABLE "{table_name}" ADD COLUMN "{column_name}" {column_type}'
    )

    return True


# ==============================================================================
# SCHEMA
# ==============================================================================

def ensure_market_state_schema(conn):

    if not table_exists(conn, "market_state"):

        conn.execute(
            """
            CREATE TABLE market_state (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                name TEXT,
                rank REAL,
                price REAL,
                market_cap REAL,
                volume_24h REAL,
                change_1h REAL,
                change_24h REAL,
                change_7d REAL,

                return_5 REAL,
                return_10 REAL,
                return_20 REAL,

                sma_3 REAL,
                sma_5 REAL,
                sma_10 REAL,
                sma_20 REAL,

                ema_5 REAL,
                ema_10 REAL,
                ema_20 REAL,

                momentum_5 REAL,
                momentum_10 REAL,
                momentum_20 REAL,

                volatility_5 REAL,
                volatility_10 REAL,
                volatility_20 REAL,

                rsi_14 REAL,

                volume_change_1 REAL,
                volume_change_3 REAL,

                news_event TEXT,
                news_sentiment REAL,
                news_score REAL,
                news_importance REAL,
                news_freshness REAL,
                news_confidence REAL,

                whale_count REAL,
                whale_volume REAL,
                whale_available INTEGER,

                microstructure_score REAL,
                microstructure_liquidity REAL,
                microstructure_volatility REAL,
                microstructure_momentum REAL,
                microstructure_pressure REAL,

                technical_score REAL,
                technical_available INTEGER,
                news_available INTEGER,
                whale_score REAL,
                microstructure_available INTEGER,

                state_score REAL,
                state_confidence REAL,
                data_completeness REAL,
                state_sources TEXT,
                state_version TEXT,

                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        conn.commit()

    added = []

    additions = [
        ("technical_score", "REAL"),
        ("technical_available", "INTEGER"),
        ("news_available", "INTEGER"),
        ("whale_score", "REAL"),
        ("microstructure_available", "INTEGER"),
        ("state_score", "REAL"),
        ("state_confidence", "REAL"),
        ("data_completeness", "REAL"),
        ("state_sources", "TEXT"),
        ("state_version", "TEXT"),
        ("updated_at", "TEXT"),
    ]

    for column, column_type in additions:
        if ensure_column(
            conn,
            "market_state",
            column,
            column_type
        ):
            added.append(column)

    # IMPORTANT:
    # Existing installations may already have created_at as NOT NULL.
    # We deliberately DO NOT drop or alter it.
    # Every new INSERT below explicitly supplies created_at.

    conn.commit()

    return added


# ==============================================================================
# SOURCE LAYER LOADING
# ==============================================================================

def load_latest_by_symbol(
    conn,
    table_name,
    symbol_candidates=("symbol",),
    timestamp_candidates=("timestamp", "published_at", "created_at"),
):

    if not table_exists(conn, table_name):
        return {}, []

    columns = get_columns(conn, table_name)

    symbol_col = find_column(
        columns,
        symbol_candidates
    )

    timestamp_col = find_column(
        columns,
        timestamp_candidates
    )

    if symbol_col is None:
        return {}, columns

    if timestamp_col is None:

        rows = conn.execute(
            f'SELECT * FROM "{table_name}"'
        ).fetchall()

    else:

        rows = conn.execute(
            f'''
            SELECT *
            FROM "{table_name}"
            ORDER BY "{timestamp_col}" DESC
            '''
        ).fetchall()

    column_index = {
        column: i
        for i, column in enumerate(columns)
    }

    result = {}

    for row in rows:

        symbol = row[column_index[symbol_col]]

        if symbol is None:
            continue

        symbol = str(symbol).strip()

        if not symbol:
            continue

        symbol_upper = symbol.upper()

        if symbol_upper in result:
            continue

        item = {}

        for column, index in column_index.items():
            item[column] = row[index]

        result[symbol_upper] = item

    return result, columns


def load_universe(conn):

    if not table_exists(conn, "market_history"):
        raise RuntimeError(
            "market_history table does not exist."
        )

    columns = get_columns(conn, "market_history")

    symbol_col = find_column(
        columns,
        ["symbol"]
    )

    if symbol_col is None:
        raise RuntimeError(
            "market_history has no symbol column."
        )

    timestamp_col = find_column(
        columns,
        ["timestamp", "source_timestamp"]
    )

    if timestamp_col is None:
        raise RuntimeError(
            "market_history has no timestamp column."
        )

    rows = conn.execute(
        f'''
        SELECT *
        FROM market_history
        ORDER BY "{timestamp_col}" DESC
        '''
    ).fetchall()

    index = {
        column: i
        for i, column in enumerate(columns)
    }

    universe = {}

    for row in rows:

        symbol = row[index[symbol_col]]

        if symbol is None:
            continue

        symbol = str(symbol).strip()

        if not symbol:
            continue

        key = symbol.upper()

        if key in universe:
            continue

        item = {}

        for column, i in index.items():
            item[column] = row[i]

        universe[key] = item

    return universe


# ==============================================================================
# TECHNICAL INTERPRETATION
# ==============================================================================

def calculate_technical_score(t):

    if not t:
        return None

    components = []

    # Short-term returns
    for column, scale in [
        ("return_5", 10.0),
        ("return_10", 15.0),
        ("return_20", 20.0),
    ]:

        value = normalize_percent(
            t.get(column),
            scale
        )

        if value is not None:
            components.append(value)

    # Momentum
    for column, scale in [
        ("momentum_5", 10.0),
        ("momentum_10", 10.0),
        ("momentum_20", 10.0),
    ]:

        value = normalize_percent(
            t.get(column),
            scale
        )

        if value is not None:
            components.append(value)

    # Price vs SMA
    price = safe_float(t.get("price"))

    for sma_col in [
        "sma_5",
        "sma_10",
        "sma_20",
    ]:

        sma = safe_float(t.get(sma_col))

        if price is None or sma is None or sma == 0:
            continue

        relative = ((price / sma) - 1.0) * 100.0

        components.append(
            normalize_percent(relative, 10.0)
        )

    # RSI contribution
    rsi = safe_float(t.get("rsi_14"))

    if rsi is not None:
        # RSI 50 = neutral
        rsi_component = (rsi - 50.0) / 50.0
        components.append(
            clamp(rsi_component)
        )

    if not components:
        return None

    return sum(components) / len(components)


# ==============================================================================
# NEWS INTERPRETATION
# ==============================================================================

def calculate_news_score(n):

    if not n:
        return None

    direct = safe_float(
        n.get("news_score")
    )

    if direct is not None:
        return clamp(direct)

    sentiment = safe_float(
        n.get("sentiment")
    )

    if sentiment is None:
        sentiment = safe_float(
            n.get("news_sentiment")
        )

    if sentiment is None:
        return None

    return clamp(sentiment)


def get_news_value(n, candidates):

    if not n:
        return None

    for candidate in candidates:

        if candidate in n:
            value = n.get(candidate)

            if value is not None:
                return value

    return None


# ==============================================================================
# WHALE INTERPRETATION
# ==============================================================================

def calculate_whale_score(w):

    if not w:
        return None

    count = safe_float(
        w.get("whale_count")
    )

    volume = safe_float(
        w.get("whale_volume")
    )

    if count is None and volume is None:
        return None

    components = []

    if count is not None:
        components.append(
            clamp(count / 10.0)
        )

    if volume is not None:
        # Logarithmic normalization.
        # Does not assign direction by itself.
        try:
            if volume > 0:
                score = math.log10(
                    max(volume, 1.0)
                ) / 12.0

                components.append(
                    clamp(score)
                )
        except Exception:
            pass

    if not components:
        return None

    return sum(components) / len(components)


# ==============================================================================
# MICROSTRUCTURE
# ==============================================================================

def calculate_micro_score(m):

    if not m:
        return None

    direct = safe_float(
        m.get("microstructure_score")
    )

    if direct is not None:
        return clamp(direct)

    components = []

    momentum = safe_float(
        m.get("microstructure_momentum")
    )

    pressure = safe_float(
        m.get("microstructure_pressure")
    )

    liquidity = safe_float(
        m.get("microstructure_liquidity")
    )

    if momentum is not None:
        components.append(
            clamp(momentum)
        )

    if pressure is not None:
        components.append(
            clamp(pressure)
        )

    if liquidity is not None:
        # Liquidity itself is not bullish/bearish.
        # It contributes only weakly to state confidence.
        pass

    if not components:
        return None

    return sum(components) / len(components)


# ==============================================================================
# VALUE HELPERS
# ==============================================================================

def copy_value(source, candidates):

    if not source:
        return None

    for candidate in candidates:

        if candidate in source:
            return source.get(candidate)

    return None


def detect_news_event(news):

    if not news:
        return None

    event = copy_value(
        news,
        [
            "event",
            "news_event",
            "event_type",
        ]
    )

    if event is None:
        return None

    return str(event)


# ==============================================================================
# STATE CALCULATION
# ==============================================================================

def build_state(
    universe_item,
    technical,
    news,
    whale,
    micro,
):

    state = {}

    # --------------------------------------------------------------------------
    # BASE MARKET DATA
    # --------------------------------------------------------------------------

    for column in [
        "name",
        "rank",
        "price",
        "market_cap",
        "volume_24h",
        "change_1h",
        "change_24h",
        "change_7d",
    ]:

        value = universe_item.get(column)

        if value is None:
            value = copy_value(
                technical,
                [column]
            )

        state[column] = value

    # --------------------------------------------------------------------------
    # TECHNICAL
    # --------------------------------------------------------------------------

    technical_columns = [
        "return_5",
        "return_10",
        "return_20",
        "sma_3",
        "sma_5",
        "sma_10",
        "sma_20",
        "ema_5",
        "ema_10",
        "ema_20",
        "momentum_5",
        "momentum_10",
        "momentum_20",
        "volatility_5",
        "volatility_10",
        "volatility_20",
        "rsi_14",
        "volume_change_1",
        "volume_change_3",
    ]

    for column in technical_columns:
        state[column] = copy_value(
            technical,
            [column]
        )

    technical_score = calculate_technical_score(
        {
            **universe_item,
            **(technical or {}),
        }
    )

    state["technical_score"] = technical_score
    state["technical_available"] = (
        1 if technical_score is not None else 0
    )

    # --------------------------------------------------------------------------
    # NEWS
    # --------------------------------------------------------------------------

    news_score = calculate_news_score(news)

    news_sentiment = get_news_value(
        news,
        [
            "news_sentiment",
            "sentiment",
        ]
    )

    news_importance = get_news_value(
        news,
        [
            "news_importance",
            "importance",
        ]
    )

    news_freshness = get_news_value(
        news,
        [
            "news_freshness",
            "freshness",
        ]
    )

    news_confidence = get_news_value(
        news,
        [
            "news_confidence",
            "confidence",
        ]
    )

    state["news_event"] = detect_news_event(news)
    state["news_sentiment"] = safe_float(news_sentiment)
    state["news_score"] = news_score
    state["news_importance"] = safe_float(news_importance)
    state["news_freshness"] = safe_float(news_freshness)
    state["news_confidence"] = safe_float(news_confidence)

    state["news_available"] = (
        1 if news_score is not None else 0
    )

    # --------------------------------------------------------------------------
    # WHALE
    # --------------------------------------------------------------------------

    whale_count = copy_value(
        whale,
        [
            "whale_count",
            "count",
        ]
    )

    whale_volume = copy_value(
        whale,
        [
            "whale_volume",
            "volume",
            "amount_usd",
            "usd_value",
        ]
    )

    whale_score = calculate_whale_score(
        {
            "whale_count": whale_count,
            "whale_volume": whale_volume,
        }
    )

    state["whale_count"] = safe_float(
        whale_count
    )

    state["whale_volume"] = safe_float(
        whale_volume
    )

    state["whale_available"] = (
        1 if whale_score is not None else 0
    )

    state["whale_score"] = whale_score

    # --------------------------------------------------------------------------
    # MICROSTRUCTURE
    # --------------------------------------------------------------------------

    micro_score = calculate_micro_score(
        micro
    )

    state["microstructure_score"] = micro_score

    state["microstructure_liquidity"] = safe_float(
        copy_value(
            micro,
            [
                "microstructure_liquidity",
                "liquidity",
            ]
        )
    )

    state["microstructure_volatility"] = safe_float(
        copy_value(
            micro,
            [
                "microstructure_volatility",
                "volatility",
            ]
        )
    )

    state["microstructure_momentum"] = safe_float(
        copy_value(
            micro,
            [
                "microstructure_momentum",
                "momentum",
            ]
        )
    )

    state["microstructure_pressure"] = safe_float(
        copy_value(
            micro,
            [
                "microstructure_pressure",
                "pressure",
            ]
        )
    )

    state["microstructure_available"] = (
        1 if micro_score is not None else 0
    )

    # --------------------------------------------------------------------------
    # UNIFIED STATE
    # --------------------------------------------------------------------------

    layers = []

    weighted_sum = 0.0
    weight_sum = 0.0

    if technical_score is not None:
        weighted_sum += technical_score * 0.40
        weight_sum += 0.40
        layers.append("technical")

    if news_score is not None:
        weighted_sum += news_score * 0.25
        weight_sum += 0.25
        layers.append("news")

    if whale_score is not None:
        weighted_sum += whale_score * 0.15
        weight_sum += 0.15
        layers.append("whale")

    if micro_score is not None:
        weighted_sum += micro_score * 0.20
        weight_sum += 0.20
        layers.append("microstructure")

    if weight_sum > 0:
        state_score = weighted_sum / weight_sum
    else:
        state_score = None

    available_layers = len(layers)

    total_layers = 4

    data_completeness = (
        available_layers / total_layers
    )

    # Confidence is deliberately conservative.
    # It represents quality/completeness of state data,
    # NOT probability of price movement.
    state_confidence = data_completeness

    if news_score is not None:

        freshness = safe_float(
            news_freshness
        )

        confidence = safe_float(
            news_confidence
        )

        if freshness is not None:
            state_confidence *= (
                0.75 + 0.25 * clamp(
                    freshness,
                    0.0,
                    1.0
                )
            )

        if confidence is not None:
            state_confidence *= (
                0.75 + 0.25 * clamp(
                    confidence,
                    0.0,
                    1.0
                )
            )

    state["state_score"] = (
        clamp(state_score)
        if state_score is not None
        else None
    )

    state["data_completeness"] = round(
        data_completeness,
        6
    )

    state["state_confidence"] = round(
        clamp(
            state_confidence,
            0.0,
            1.0
        ),
        6
    )

    state["state_sources"] = (
        ",".join(layers)
        if layers
        else "universe"
    )

    state["state_version"] = ENGINE_VERSION

    return state


# ==============================================================================
# UPSERT
# ==============================================================================

def upsert_state(
    conn,
    table_columns,
    symbol,
    timestamp,
    state,
    existing_created_at=None,
):

    now = utc_now()

    values = dict(state)

    values["symbol"] = symbol
    values["timestamp"] = timestamp

    # CRITICAL FIX:
    # market_state.created_at is NOT NULL in the existing database.
    # Always provide it explicitly.
    values["created_at"] = (
        existing_created_at
        if existing_created_at
        else now
    )

    values["updated_at"] = now

    values["state_version"] = ENGINE_VERSION

    insert_columns = [
        column
        for column in table_columns
        if column in values
    ]

    # Make absolutely sure the required columns are present.
    required = [
        "timestamp",
        "symbol",
        "created_at",
        "updated_at",
    ]

    for column in required:
        if column not in insert_columns:
            raise RuntimeError(
                f"market_state is missing required column: {column}"
            )

    # Preserve an existing created_at.
    # Remove an existing record for the same symbol+timestamp.
    conn.execute(
        """
        DELETE FROM market_state
        WHERE symbol = ?
          AND timestamp = ?
        """,
        (
            symbol,
            timestamp,
        )
    )

    placeholders = ",".join(
        ["?"] * len(insert_columns)
    )

    column_sql = ",".join(
        f'"{column}"'
        for column in insert_columns
    )

    params = [
        values.get(column)
        for column in insert_columns
    ]

    conn.execute(
        f'''
        INSERT INTO market_state (
            {column_sql}
        )
        VALUES (
            {placeholders}
        )
        ''',
        params
    )


# ==============================================================================
# MAIN
# ==============================================================================

def main():

    print("=" * 80)
    print("             ARUNDA MARKET STATE ENGINE v0.2.1")
    print("=" * 80)
    print("Source          : UNIFIED MARKET LAYERS")
    print("Database        : arunda.db")
    print("Mode            : NORMALIZED STATE CONTRACT")
    print("Universe        : ACTIVE MARKET UNIVERSE")
    print("Historical      : MARKET HISTORY")
    print("Technical       : MARKET TECHNICAL")
    print("News            : NEWS INTELLIGENCE")
    print("Whale           : PROVIDER AGNOSTIC")
    print("Microstructure  : MARKET MICROSTRUCTURE")
    print("Ranking         : NOT USED")
    print("Opportunity     : NOT USED")
    print("Signal          : NOT USED")
    print("Prediction      : NOT USED")
    print("Risk            : NOT USED")
    print("Execution       : NOT USED")
    print("Writes          : market_state")
    print("=" * 80)

    conn = sqlite3.connect(DB_PATH)

    conn.row_factory = None

    try:

        print()
        print("Checking database...")

        universe = load_universe(conn)

        print(
            f"Universe Assets : {len(universe)}"
        )

        print()
        print("Checking market-state schema...")

        added = ensure_market_state_schema(
            conn
        )

        print(
            "Market State Table : EXISTING"
        )

        print(
            f"Schema Columns Added : {len(added)}"
        )

        if added:
            print(
                "Added Columns        : "
                + ", ".join(added)
            )

        table_columns = get_columns(
            conn,
            "market_state"
        )

        # ----------------------------------------------------------------------
        # LOAD LAYERS
        # ----------------------------------------------------------------------

        print()
        print("Loading source layers...")

        technical, _ = load_latest_by_symbol(
            conn,
            "market_technical"
        )

        news, _ = load_latest_by_symbol(
            conn,
            "market_news_intelligence",
            timestamp_candidates=(
                "published_at",
                "timestamp",
                "created_at",
            )
        )

        whale, _ = load_latest_by_symbol(
            conn,
            "market_whale"
        )

        micro, _ = load_latest_by_symbol(
            conn,
            "market_microstructure"
        )

        print(
            f"Technical Assets       : {len(technical)}"
        )

        print(
            f"News Assets            : {len(news)}"
        )

        print(
            f"Whale Assets           : {len(whale)}"
        )

        print(
            f"Microstructure Assets  : {len(micro)}"
        )

        # ----------------------------------------------------------------------
        # BUILD
        # ----------------------------------------------------------------------

        print()
        print(
            "Building normalized market state..."
        )

        inserted = 0
        errors = 0

        timestamp = utc_now()

        # Prefer the latest market_history timestamp
        # when available, so all universe assets share
        # the same state snapshot.
        history_columns = get_columns(
            conn,
            "market_history"
        )

        history_timestamp_col = find_column(
            history_columns,
            [
                "timestamp",
                "source_timestamp",
            ]
        )

        if history_timestamp_col:

            row = conn.execute(
                f'''
                SELECT "{history_timestamp_col}"
                FROM market_history
                ORDER BY "{history_timestamp_col}" DESC
                LIMIT 1
                '''
            ).fetchone()

            if row and row[0]:
                timestamp = str(row[0])

        # ----------------------------------------------------------------------
        # Process each asset
        # ----------------------------------------------------------------------

        for symbol, universe_item in universe.items():

            try:

                t = technical.get(symbol)
                n = news.get(symbol)
                w = whale.get(symbol)
                m = micro.get(symbol)

                state = build_state(
                    universe_item,
                    t,
                    n,
                    w,
                    m,
                )

                # Existing created_at, if this exact snapshot exists.
                existing = conn.execute(
                    """
                    SELECT created_at
                    FROM market_state
                    WHERE symbol = ?
                      AND timestamp = ?
                    LIMIT 1
                    """,
                    (
                        symbol,
                        timestamp,
                    )
                ).fetchone()

                existing_created_at = (
                    existing[0]
                    if existing
                    else None
                )

                upsert_state(
                    conn,
                    table_columns,
                    symbol,
                    timestamp,
                    state,
                    existing_created_at,
                )

                inserted += 1

            except Exception as exc:

                errors += 1

                print(
                    f"STATE ERROR [{symbol}] : {exc}"
                )

        conn.commit()

        # ----------------------------------------------------------------------
        # SUMMARY
        # ----------------------------------------------------------------------

        total_records = conn.execute(
            "SELECT COUNT(*) FROM market_state"
        ).fetchone()[0]

        total_assets = conn.execute(
            """
            SELECT COUNT(DISTINCT symbol)
            FROM market_state
            """
        ).fetchone()[0]

        print()
        print("=" * 80)
        print("             MARKET STATE SUMMARY")
        print("=" * 80)
        print(
            f"Universe Assets        : {len(universe)}"
        )
        print(
            f"Technical Assets       : {len(technical)}"
        )
        print(
            f"News Assets            : {len(news)}"
        )
        print(
            f"Whale Assets           : {len(whale)}"
        )
        print(
            f"Microstructure Assets  : {len(micro)}"
        )
        print(
            f"States Generated       : {inserted}"
        )
        print(
            f"Errors                 : {errors}"
        )
        print(
            f"Market State Records   : {total_records}"
        )
        print(
            f"Market State Assets    : {total_assets}"
        )
        print("=" * 80)

        # ----------------------------------------------------------------------
        # RECENT STATE PREVIEW
        # ----------------------------------------------------------------------

        print()
        print(
            "RECENT NORMALIZED MARKET STATE"
        )

        print("-" * 150)

        print(
            f"{'SYMBOL':<12}"
            f"{'STATE':>10}"
            f"{'CONF':>10}"
            f"{'COMP':>10}"
            f"{'TECH':>10}"
            f"{'NEWS':>10}"
            f"{'WHALE':>10}"
            f"{'MICRO':>10}"
            f"  SOURCES"
        )

        print("-" * 150)

        rows = conn.execute(
            """
            SELECT
                symbol,
                state_score,
                state_confidence,
                data_completeness,
                technical_score,
                news_score,
                whale_score,
                microstructure_score,
                state_sources
            FROM market_state
            WHERE timestamp = ?
            ORDER BY symbol
            LIMIT 30
            """,
            (timestamp,)
        ).fetchall()

        for row in rows:

            (
                symbol,
                state_score,
                confidence,
                completeness,
                technical_score,
                news_score,
                whale_score,
                micro_score,
                sources,
            ) = row

            def fmt(value):
                if value is None:
                    return "NONE"

                try:
                    return f"{float(value):.3f}"
                except Exception:
                    return "NONE"

            print(
                f"{str(symbol):<12}"
                f"{fmt(state_score):>10}"
                f"{fmt(confidence):>10}"
                f"{fmt(completeness):>10}"
                f"{fmt(technical_score):>10}"
                f"{fmt(news_score):>10}"
                f"{fmt(whale_score):>10}"
                f"{fmt(micro_score):>10}"
                f"  {sources or 'NONE'}"
            )

        print()
        print("=" * 80)
        print(
            "       ARUNDA MARKET STATE ENGINE v0.2.1 COMPLETE"
        )
        print("=" * 80)
        print(
            "STATE STATUS     : SUCCESS"
        )
        print(
            "Unified Layer    : ACTIVE"
        )
        print(
            "Ranking          : NOT USED"
        )
        print(
            "Opportunity      : NOT USED"
        )
        print(
            "Signal           : NOT USED"
        )
        print(
            "Prediction       : NOT USED"
        )
        print(
            "Risk             : NOT USED"
        )
        print(
            "Execution        : NOT USED"
        )

    except Exception as exc:

        conn.rollback()

        print()
        print("=" * 80)
        print(
            "             MARKET STATE ENGINE ERROR"
        )
        print("=" * 80)
        print(
            f"{type(exc).__name__}: {exc}"
        )
        print("=" * 80)

        traceback.print_exc()

        raise

    finally:
        conn.close()


if __name__ == "__main__":
    main()
