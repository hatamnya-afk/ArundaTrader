import sqlite3
import re
import math
import hashlib
from datetime import datetime, timezone

DB_PATH = "arunda.db"
ENGINE_VERSION = "MARKET_NEWS_INTELLIGENCE_v0.1"

SOURCE_WEIGHT = {
    "COINDESK": 1.00,
    "COINTELEGRAPH": 0.95,
    "DECRYPT": 0.90,
    "BITCOIN_MAGAZINE": 0.90,
}

POSITIVE_TERMS = [
    "approved", "approval", "adoption", "accumulate", "accumulation",
    "bullish", "buy", "bought", "buying", "breakthrough", "partnership",
    "launch", "launched", "growth", "surge", "rally", "record",
    "inflow", "outflow", "institutional", "investment", "invest",
    "upgrade", "etf", "legal clarity", "clarity act", "support",
    "integration", "expands", "expansion", "treasury", "holdings"
]

NEGATIVE_TERMS = [
    "hack", "hacked", "exploit", "exploited", "breach", "stolen",
    "lawsuit", "ban", "banned", "fraud", "scam", "collapse",
    "liquidation", "liquidated", "sell", "selling", "sold",
    "outflow", "shutdown", "shut down", "warning", "risk",
    "investigation", "illegal", "sanction", "sanctions", "attack",
    "bearish", "decline", "drop", "crash", "loss", "losses"
]

EVENT_RULES = [
    ("REGULATION", [
        "sec", "regulator", "regulation", "regulatory",
        "law", "legislation", "clarity act", "fca",
        "government", "congress", "senate"
    ]),
    ("ETF", [
        "etf", "spot etf", "fund", "exchange traded"
    ]),
    ("SECURITY", [
        "hack", "hacked", "exploit", "breach", "stolen",
        "attack", "vulnerability"
    ]),
    ("EXCHANGE", [
        "exchange", "listing", "delisting", "trading platform"
    ]),
    ("INSTITUTIONAL", [
        "institutional", "bank", "banks", "fund",
        "asset manager", "treasury", "sovereign",
        "investment firm"
    ]),
    ("ADOPTION", [
        "adoption", "adopt", "integrates", "integration",
        "payment", "payments", "merchant", "partnership"
    ]),
    ("MARKET", [
        "rally", "surge", "crash", "market", "price",
        "volume", "liquidation"
    ]),
    ("TECHNOLOGY", [
        "upgrade", "mainnet", "protocol", "network",
        "scaling", "layer 2", "layer-2", "launch"
    ]),
]

ASSET_ALIASES = {
    "BTC": ["bitcoin", "btc"],
    "ETH": ["ethereum", "ether", "eth"],
    "SOL": ["solana", "sol"],
    "XRP": ["ripple", "xrp"],
    "ADA": ["cardano", "ada"],
    "DOGE": ["dogecoin", "doge"],
    "SHIB": ["shiba inu", "shib"],
    "LINK": ["chainlink", "link"],
    "AVAX": ["avalanche", "avax"],
    "DOT": ["polkadot", "dot"],
    "LTC": ["litecoin", "ltc"],
    "UNI": ["uniswap", "uni"],
    "AAVE": ["aave"],
    "SUI": ["sui"],
    "NEAR": ["near protocol", "near"],
}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def clean_text(text):
    text = text or ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_columns(conn, table):
    rows = conn.execute(
        f"PRAGMA table_info({table})"
    ).fetchall()

    return {
        row[1].lower(): row[1]
        for row in rows
    }


def find_column(columns, candidates):
    for candidate in candidates:
        if candidate.lower() in columns:
            return columns[candidate.lower()]
    return None


def ensure_intelligence_schema(conn):

    conn.execute("""
        CREATE TABLE IF NOT EXISTS market_news_intelligence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            news_id INTEGER,
            published_at TEXT,
            source TEXT,
            symbol TEXT,
            title TEXT,
            event_type TEXT,
            sentiment TEXT,
            sentiment_score REAL,
            importance_score REAL,
            freshness_score REAL,
            confidence_score REAL,
            asset_relevance REAL,
            is_duplicate INTEGER DEFAULT 0,
            intelligence_hash TEXT UNIQUE,
            engine_version TEXT,
            created_at TEXT
        )
    """)

    columns = normalize_columns(
        conn,
        "market_news_intelligence"
    )

    required = {
        "news_id": "INTEGER",
        "published_at": "TEXT",
        "source": "TEXT",
        "symbol": "TEXT",
        "title": "TEXT",
        "event_type": "TEXT",
        "sentiment": "TEXT",
        "sentiment_score": "REAL",
        "importance_score": "REAL",
        "freshness_score": "REAL",
        "confidence_score": "REAL",
        "asset_relevance": "REAL",
        "is_duplicate": "INTEGER DEFAULT 0",
        "intelligence_hash": "TEXT",
        "engine_version": "TEXT",
        "created_at": "TEXT",
    }

    added = []

    for name, datatype in required.items():

        if name.lower() not in columns:

            try:
                conn.execute(
                    f"ALTER TABLE market_news_intelligence "
                    f"ADD COLUMN {name} {datatype}"
                )
                added.append(name)

            except sqlite3.OperationalError:
                pass

    conn.commit()

    count = conn.execute(
        "SELECT COUNT(*) "
        "FROM market_news_intelligence"
    ).fetchone()[0]

    print(
        "Technical Intelligence Table : READY"
    )

    print(
        "Schema Columns Added         : {}"
        .format(len(added))
    )

    if added:
        print(
            "Added Columns                : {}"
            .format(", ".join(added))
        )

    print(
        "Existing Intelligence Records: {}"
        .format(count)
    )


def tokenize(text):
    return set(
        re.findall(
            r"[a-zA-Z0-9\-]+",
            text.lower()
        )
    )


def count_terms(text, terms):

    text = text.lower()

    count = 0

    for term in terms:

        if term in text:
            count += 1

    return count


def detect_event_type(text):

    text = text.lower()

    scores = []

    for event_type, terms in EVENT_RULES:

        score = count_terms(
            text,
            terms
        )

        if score > 0:
            scores.append(
                (score, event_type)
            )

    if not scores:
        return "GENERAL"

    scores.sort(
        key=lambda x: x[0],
        reverse=True
    )

    return scores[0][1]


def detect_symbol(title, description, existing_symbol):

    if existing_symbol:
        return existing_symbol.upper()

    text = (
        (title or "")
        + " "
        + (description or "")
    ).lower()

    matches = []

    for symbol, aliases in ASSET_ALIASES.items():

        for alias in aliases:

            if len(alias) <= 4:

                pattern = (
                    r"(?<![a-z0-9])"
                    + re.escape(alias)
                    + r"(?![a-z0-9])"
                )

                if re.search(pattern, text):
                    matches.append(symbol)

            elif alias in text:
                matches.append(symbol)

    if not matches:
        return None

    counts = {}

    for symbol in matches:
        counts[symbol] = (
            counts.get(symbol, 0) + 1
        )

    return max(
        counts,
        key=counts.get
    )


def calculate_sentiment(text):

    positive = count_terms(
        text,
        POSITIVE_TERMS
    )

    negative = count_terms(
        text,
        NEGATIVE_TERMS
    )

    total = positive + negative

    if total == 0:
        return "NEUTRAL", 0.0

    raw = (
        positive - negative
    ) / total

    score = max(
        -1.0,
        min(1.0, raw)
    )

    if score > 0.15:
        sentiment = "POSITIVE"

    elif score < -0.15:
        sentiment = "NEGATIVE"

    else:
        sentiment = "NEUTRAL"

    return sentiment, score


def calculate_freshness(published_at):

    if not published_at:
        return 0.25

    try:

        value = published_at

        if value.endswith("Z"):
            value = value[:-1] + "+00:00"

        dt = datetime.fromisoformat(
            value
        )

        if dt.tzinfo is None:
            dt = dt.replace(
                tzinfo=timezone.utc
            )

        now = datetime.now(
            timezone.utc
        )

        age_hours = (
            now - dt
        ).total_seconds() / 3600.0

        if age_hours < 0:
            age_hours = 0

        if age_hours <= 1:
            return 1.00

        if age_hours <= 6:
            return 0.90

        if age_hours <= 24:
            return 0.75

        if age_hours <= 72:
            return 0.50

        if age_hours <= 168:
            return 0.25

        return 0.10

    except Exception:
        return 0.25


def calculate_importance(
    source,
    event_type,
    sentiment_score,
    title
):

    source_weight = SOURCE_WEIGHT.get(
        source.upper(),
        0.70
    )

    event_weight = {
        "SECURITY": 1.00,
        "REGULATION": 0.95,
        "ETF": 0.95,
        "INSTITUTIONAL": 0.90,
        "EXCHANGE": 0.85,
        "ADOPTION": 0.80,
        "TECHNOLOGY": 0.70,
        "MARKET": 0.65,
        "GENERAL": 0.35,
    }.get(
        event_type,
        0.35
    )

    sentiment_magnitude = abs(
        sentiment_score
    )

    title_bonus = 0.05 if (
        len(title or "") > 45
    ) else 0.0

    score = (
        0.40 * source_weight
        + 0.40 * event_weight
        + 0.15 * sentiment_magnitude
        + title_bonus
    )

    return round(
        min(1.0, score),
        4
    )


def calculate_confidence(
    source,
    symbol,
    event_type,
    title
):

    score = SOURCE_WEIGHT.get(
        source.upper(),
        0.70
    )

    if symbol:
        score += 0.10

    if event_type != "GENERAL":
        score += 0.10

    if title and len(title) >= 30:
        score += 0.05

    return round(
        min(1.0, score),
        4
    )


def intelligence_hash(
    news_id,
    title,
    symbol,
    event_type
):

    raw = (
        str(news_id)
        + "|"
        + (title or "")
        + "|"
        + str(symbol)
        + "|"
        + event_type
    )

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()


def process_news(conn):

    news_columns = normalize_columns(
        conn,
        "market_news"
    )

    id_col = find_column(
        news_columns,
        ["id"]
    )

    title_col = find_column(
        news_columns,
        ["title", "headline"]
    )

    description_col = find_column(
        news_columns,
        ["description", "summary", "content"]
    )

    source_col = find_column(
        news_columns,
        ["source", "publisher"]
    )

    published_col = find_column(
        news_columns,
        ["published_at", "published", "timestamp"]
    )

    symbol_col = find_column(
        news_columns,
        ["symbol", "asset"]
    )

    if not id_col or not title_col:

        raise RuntimeError(
            "market_news schema missing "
            "required id/title columns."
        )

    print()
    print(
        "Detected News Schema"
    )
    print("-" * 82)
    print(
        "ID Column          : {}"
        .format(id_col)
    )
    print(
        "Title Column       : {}"
        .format(title_col)
    )
    print(
        "Description Column : {}"
        .format(description_col or "NONE")
    )
    print(
        "Source Column      : {}"
        .format(source_col or "NONE")
    )
    print(
        "Published Column   : {}"
        .format(published_col or "NONE")
    )
    print(
        "Symbol Column      : {}"
        .format(symbol_col or "NONE")
    )

    select_parts = [
        f"{id_col} AS news_id",
        f"{title_col} AS title",
    ]

    select_parts.append(
        f"{description_col} AS description"
        if description_col
        else "'' AS description"
    )

    select_parts.append(
        f"{source_col} AS source"
        if source_col
        else "'UNKNOWN' AS source"
    )

    select_parts.append(
        f"{published_col} AS published_at"
        if published_col
        else "NULL AS published_at"
    )

    select_parts.append(
        f"{symbol_col} AS symbol"
        if symbol_col
        else "NULL AS symbol"
    )

    query = (
        "SELECT "
        + ", ".join(select_parts)
        + " FROM market_news "
        + f"ORDER BY {id_col} ASC"
    )

    rows = conn.execute(
        query
    ).fetchall()

    return rows


def insert_intelligence(
    conn,
    row
):

    (
        news_id,
        title,
        description,
        source,
        published_at,
        existing_symbol,
    ) = row

    title = clean_text(title)
    description = clean_text(
        description
    )

    combined = (
        title
        + " "
        + description
    )

    source = (
        source or "UNKNOWN"
    ).upper()

    symbol = detect_symbol(
        title,
        description,
        existing_symbol
    )

    event_type = detect_event_type(
        combined
    )

    sentiment, sentiment_score = (
        calculate_sentiment(combined)
    )

    freshness = calculate_freshness(
        published_at
    )

    importance = calculate_importance(
        source,
        event_type,
        sentiment_score,
        title
    )

    confidence = calculate_confidence(
        source,
        symbol,
        event_type,
        title
    )

    asset_relevance = (
        1.0 if symbol else 0.25
    )

    digest = intelligence_hash(
        news_id,
        title,
        symbol,
        event_type
    )

    try:

        conn.execute("""
            INSERT INTO market_news_intelligence (
                news_id,
                published_at,
                source,
                symbol,
                title,
                event_type,
                sentiment,
                sentiment_score,
                importance_score,
                freshness_score,
                confidence_score,
                asset_relevance,
                is_duplicate,
                intelligence_hash,
                engine_version,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            news_id,
            published_at,
            source,
            symbol,
            title,
            event_type,
            sentiment,
            sentiment_score,
            importance,
            freshness,
            confidence,
            asset_relevance,
            0,
            digest,
            ENGINE_VERSION,
            utc_now(),
        ))

        return "INSERTED"

    except sqlite3.IntegrityError:

        return "DUPLICATE"


def print_recent_intelligence(conn):

    print()
    print("=" * 130)
    print("RECENT NEWS INTELLIGENCE")
    print("=" * 130)

    rows = conn.execute("""
        SELECT
            symbol,
            event_type,
            sentiment,
            sentiment_score,
            importance_score,
            freshness_score,
            confidence_score,
            title
        FROM market_news_intelligence
        ORDER BY id DESC
        LIMIT 20
    """).fetchall()

    if not rows:
        print("NO INTELLIGENCE RECORDS")
        return

    print(
        "{:<8} {:<14} {:<10} {:>7} {:>7} {:>7} {:>7} | {}".format(
            "SYMBOL",
            "EVENT",
            "SENTIMENT",
            "SCORE",
            "IMP",
            "FRESH",
            "CONF",
            "TITLE"
        )
    )

    print("-" * 130)

    for row in rows:

        (
            symbol,
            event_type,
            sentiment,
            sentiment_score,
            importance,
            freshness,
            confidence,
            title,
        ) = row

        title = clean_text(title)

        if len(title) > 65:
            title = title[:62] + "..."

        print(
            "{:<8} {:<14} {:<10} {:>7.2f} {:>7.2f} {:>7.2f} {:>7.2f} | {}".format(
                (symbol or "NONE")[:8],
                (event_type or "GENERAL")[:14],
                (sentiment or "NEUTRAL")[:10],
                sentiment_score or 0.0,
                importance or 0.0,
                freshness or 0.0,
                confidence or 0.0,
                title
            )
        )


def main():

    print("=" * 82)
    print("        ARUNDA MARKET NEWS INTELLIGENCE ENGINE v0.1")
    print("=" * 82)
    print("Source          : market_news")
    print("Database        : arunda.db")
    print("Mode            : NEWS INTELLIGENCE EXTRACTION")
    print("Sentiment       : RULE-BASED FEATURE")
    print("Event Detection : ENABLED")
    print("Asset Mapping   : ENABLED")
    print("Freshness       : ENABLED")
    print("Importance      : ENABLED")
    print("Confidence      : ENABLED")
    print("Ranking         : NOT USED")
    print("Opportunity     : NOT USED")
    print("Signal          : NOT USED")
    print("Prediction      : NOT USED")
    print("Risk            : NOT USED")
    print("Execution       : NOT USED")
    print("Writes          : market_news_intelligence")
    print("=" * 82)

    conn = sqlite3.connect(
        DB_PATH
    )

    try:

        print()
        print(
            "Database           : CONNECTED"
        )

        print(
            "Checking intelligence schema..."
        )

        ensure_intelligence_schema(
            conn
        )

        print()
        print(
            "Reading market news..."
        )

        rows = process_news(
            conn
        )

        print()
        print(
            "News Records Read  : {}"
            .format(len(rows))
        )

        inserted = 0
        duplicates = 0
        errors = 0

        print()
        print(
            "Calculating intelligence features..."
        )

        for row in rows:

            try:

                result = insert_intelligence(
                    conn,
                    row
                )

                if result == "INSERTED":
                    inserted += 1

                else:
                    duplicates += 1

            except Exception as error:

                errors += 1

                print(
                    "ROW ERROR | News ID={} | {}: {}".format(
                        row[0],
                        type(error).__name__,
                        error
                    )
                )

        conn.commit()

        total_records = conn.execute(
            "SELECT COUNT(*) "
            "FROM market_news_intelligence"
        ).fetchone()[0]

        assets = conn.execute("""
            SELECT COUNT(DISTINCT symbol)
            FROM market_news_intelligence
            WHERE symbol IS NOT NULL
            AND symbol != ''
        """).fetchone()[0]

        print()
        print("=" * 82)
        print(
            "             NEWS INTELLIGENCE SUMMARY"
        )
        print("=" * 82)

        print(
            "News Rows Read       : {}"
            .format(len(rows))
        )

        print(
            "Inserted              : {}"
            .format(inserted)
        )

        print(
            "Duplicates            : {}"
            .format(duplicates)
        )

        print(
            "Errors                : {}"
            .format(errors)
        )

        print(
            "Intelligence Records  : {}"
            .format(total_records)
        )

        print(
            "Assets Identified     : {}"
            .format(assets)
        )

        print("=" * 82)

        print_recent_intelligence(
            conn
        )

        print()
        print("=" * 82)
        print(
            "       ARUNDA MARKET NEWS INTELLIGENCE ENGINE v0.1 COMPLETE"
        )
        print("=" * 82)
        print(
            "INTELLIGENCE STATUS : {}"
            .format(
                "SUCCESS"
                if errors == 0
                else "PARTIAL"
            )
        )
        print(
            "Sentiment           : FEATURE ONLY"
        )
        print(
            "Ranking             : NOT USED"
        )
        print(
            "Opportunity         : NOT USED"
        )
        print(
            "Signal              : NOT USED"
        )
        print(
            "Prediction          : NOT USED"
        )
        print(
            "Risk                : NOT USED"
        )
        print(
            "Execution           : NOT USED"
        )

    except Exception as error:

        print()
        print("=" * 82)
        print(
            "       MARKET NEWS INTELLIGENCE ENGINE ERROR"
        )
        print("=" * 82)

        print(
            "{}: {}".format(
                type(error).__name__,
                error
            )
        )

    finally:

        conn.close()


if __name__ == "__main__":
    main()
