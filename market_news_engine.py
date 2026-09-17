import sqlite3
import time
import hashlib
import re
import html
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

DB_PATH = "arunda.db"
ENGINE_VERSION = "MARKET_NEWS_MULTI_SOURCE_v0.2"
TIMEOUT = 20
MAX_ITEMS = 100

RSS_SOURCES = {
    "COINDESK": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "COINTELEGRAPH": "https://cointelegraph.com/rss",
    "DECRYPT": "https://decrypt.co/feed",
    "BITCOIN_MAGAZINE": "https://bitcoinmagazine.com/.rss/full/",
}

ALIASES = {
    "BTC": ["bitcoin", "btc"],
    "ETH": ["ethereum", "eth"],
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


def clean_text(value):
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def normalize_url(url):
    url = (url or "").strip()

    url = re.sub(
        r"([?&])(utm_[^=&]+|fbclid|gclid)=[^&]*",
        "",
        url,
        flags=re.IGNORECASE,
    )

    return url.rstrip("?&")


def parse_date(value):
    if not value:
        return utc_now()

    try:
        dt = parsedate_to_datetime(value)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.astimezone(timezone.utc).isoformat()

    except Exception:
        pass

    try:
        dt = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.astimezone(timezone.utc).isoformat()

    except Exception:
        return utc_now()


def content_hash(source, title, url):
    raw = (
        source.strip().lower()
        + "|"
        + title.strip().lower()
        + "|"
        + normalize_url(url).lower()
    )

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()


def detect_symbol(title, description):
    text = (
        (title or "")
        + " "
        + (description or "")
    ).lower()

    candidates = []

    for symbol, aliases in ALIASES.items():
        for alias in aliases:
            candidates.append(
                (len(alias), symbol, alias)
            )

    candidates.sort(reverse=True)

    for _, symbol, alias in candidates:

        if len(alias) <= 4:
            pattern = (
                r"(?<![a-z0-9])"
                + re.escape(alias)
                + r"(?![a-z0-9])"
            )

            if re.search(pattern, text):
                return symbol

        elif alias in text:
            return symbol

    return None


def connect_database():
    return sqlite3.connect(DB_PATH)


def ensure_schema(conn):

    conn.execute("""
        CREATE TABLE IF NOT EXISTS market_news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            published_at TEXT,
            collected_at TEXT,
            source TEXT,
            title TEXT,
            description TEXT,
            url TEXT,
            symbol TEXT,
            content_hash TEXT UNIQUE,
            source_timestamp TEXT,
            engine_version TEXT
        )
    """)

    existing = {
        row[1]
        for row in conn.execute(
            "PRAGMA table_info(market_news)"
        ).fetchall()
    }

    required = {
        "published_at": "TEXT",
        "collected_at": "TEXT",
        "source": "TEXT",
        "title": "TEXT",
        "description": "TEXT",
        "url": "TEXT",
        "symbol": "TEXT",
        "content_hash": "TEXT",
        "source_timestamp": "TEXT",
        "engine_version": "TEXT",
    }

    added = []

    for column, datatype in required.items():

        if column not in existing:

            try:
                conn.execute(
                    f"ALTER TABLE market_news "
                    f"ADD COLUMN {column} {datatype}"
                )

                added.append(column)

            except sqlite3.OperationalError:
                pass

    conn.commit()

    count = conn.execute(
        "SELECT COUNT(*) FROM market_news"
    ).fetchone()[0]

    print("News Table           : READY")
    print(
        "Schema Columns Added : {}".format(
            len(added)
        )
    )

    if added:
        print(
            "Added Columns        : {}".format(
                ", ".join(added)
            )
        )

    print(
        "Existing News Records : {}".format(
            count
        )
    )


def parse_rss(source, xml_data):

    root = ET.fromstring(xml_data)

    results = []

    for item in root.iter():

        tag = item.tag.lower()

        if not (
            tag.endswith("item")
            or tag.endswith("entry")
        ):
            continue

        title = ""
        description = ""
        url = ""
        published = ""

        for child in list(item):

            child_tag = child.tag.lower()
            text = child.text or ""

            if child_tag.endswith("title"):
                title = text

            elif (
                child_tag.endswith("description")
                or child_tag.endswith("summary")
                or child_tag.endswith("content")
            ):
                description = text

            elif (
                child_tag.endswith("pubdate")
                or child_tag.endswith("published")
                or child_tag.endswith("updated")
            ):
                published = text

            elif child_tag.endswith("link"):

                url = (
                    child.attrib.get("href")
                    or text
                )

        title = clean_text(title)
        description = clean_text(description)
        url = normalize_url(url)

        if not title:
            continue

        results.append({
            "source": source,
            "title": title,
            "description": description[:4000],
            "url": url,
            "published_at": parse_date(published),
        })

    unique = {}

    for item in results:

        key = content_hash(
            item["source"],
            item["title"],
            item["url"],
        )

        unique[key] = item

    return list(unique.values())[:MAX_ITEMS]


def fetch_source(source, url):

    headers = {
        "User-Agent":
            "Mozilla/5.0 "
            "ArundaTrader/0.2",
        "Accept":
            "application/rss+xml,"
            "application/xml,"
            "text/xml,"
            "*/*",
    }

    start = time.time()

    response = requests.get(
        url,
        headers=headers,
        timeout=TIMEOUT,
    )

    latency = int(
        (time.time() - start) * 1000
    )

    response.raise_for_status()

    items = parse_rss(
        source,
        response.text
    )

    return items, latency


def insert_news(conn, item):

    digest = content_hash(
        item["source"],
        item["title"],
        item["url"],
    )

    symbol = detect_symbol(
        item["title"],
        item["description"],
    )

    try:

        cursor = conn.execute("""
            INSERT INTO market_news (
                published_at,
                collected_at,
                source,
                title,
                description,
                url,
                symbol,
                content_hash,
                source_timestamp,
                engine_version
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item["published_at"],
            utc_now(),
            item["source"],
            item["title"],
            item["description"],
            item["url"],
            symbol,
            digest,
            item["published_at"],
            ENGINE_VERSION,
        ))

        return cursor.rowcount > 0

    except sqlite3.IntegrityError:
        return False


def print_recent_news(conn):

    print()
    print("=" * 120)
    print("RECENT MARKET NEWS")
    print("=" * 120)

    rows = conn.execute("""
        SELECT
            source,
            published_at,
            symbol,
            title
        FROM market_news
        ORDER BY id DESC
        LIMIT 20
    """).fetchall()

    if not rows:
        print("NO NEWS RECORDS")
        return

    for source, published, symbol, title in rows:

        source = (source or "UNKNOWN")[:16]
        published = (published or "NONE")[:28]
        symbol = (symbol or "NONE")[:8]
        title = clean_text(title)

        if len(title) > 70:
            title = title[:67] + "..."

        print(
            "{:<16} | {:<28} | {:<8} | {}".format(
                source,
                published,
                symbol,
                title,
            )
        )


def main():

    print("=" * 82)
    print("        ARUNDA MARKET NEWS ENGINE v0.2")
    print("=" * 82)
    print("Sources        : MULTI-SOURCE RSS")
    print("CMC Content    : DISABLED")
    print("CoinMarketCal  : RESERVED FOR EVENT ARM")
    print("Database       : arunda.db")
    print("Mode           : NEWS COLLECTION")
    print("Normalization  : ENABLED")
    print("Deduplication  : ENABLED")
    print("Asset Mapping  : BASIC")
    print("Sentiment      : NOT USED")
    print("Ranking        : NOT USED")
    print("Opportunity    : NOT USED")
    print("Signal         : NOT USED")
    print("Prediction     : NOT USED")
    print("Risk           : NOT USED")
    print("Execution      : NOT USED")
    print("Writes         : market_news")
    print("=" * 82)

    start_time = time.time()

    conn = connect_database()

    print()
    print("Database           : CONNECTED")
    print("Checking news schema...")

    ensure_schema(conn)

    total_items = 0
    total_inserted = 0
    total_duplicates = 0
    successful_sources = 0
    failed_sources = 0

    print()
    print("Starting multi-source collection...")

    for source, url in RSS_SOURCES.items():

        print()
        print("-" * 82)
        print("SOURCE :", source)
        print("URL    :", url)

        try:

            items, latency = fetch_source(
                source,
                url
            )

            successful_sources += 1

            inserted = 0
            duplicates = 0

            for item in items:

                if insert_news(conn, item):
                    inserted += 1
                else:
                    duplicates += 1

            conn.commit()

            total_items += len(items)
            total_inserted += inserted
            total_duplicates += duplicates

            print(
                "STATUS : SUCCESS"
            )

            print(
                "Items              : {}"
                .format(len(items))
            )

            print(
                "Inserted           : {}"
                .format(inserted)
            )

            print(
                "Duplicates         : {}"
                .format(duplicates)
            )

            print(
                "Latency            : {} ms"
                .format(latency)
            )

        except Exception as error:

            failed_sources += 1

            print(
                "STATUS : FAILED"
            )

            print(
                "Error  : {}: {}"
                .format(
                    type(error).__name__,
                    error
                )
            )

    total_records = conn.execute(
        "SELECT COUNT(*) FROM market_news"
    ).fetchone()[0]

    mapped_assets = conn.execute("""
        SELECT COUNT(*)
        FROM market_news
        WHERE symbol IS NOT NULL
        AND symbol != ''
    """).fetchone()[0]

    runtime = time.time() - start_time

    print()
    print("=" * 82)
    print("             MARKET NEWS SUMMARY")
    print("=" * 82)

    print(
        "Sources Successful : {}"
        .format(successful_sources)
    )

    print(
        "Sources Failed     : {}"
        .format(failed_sources)
    )

    print(
        "Items Collected    : {}"
        .format(total_items)
    )

    print(
        "Inserted           : {}"
        .format(total_inserted)
    )

    print(
        "Duplicates         : {}"
        .format(total_duplicates)
    )

    print(
        "News Records       : {}"
        .format(total_records)
    )

    print(
        "Assets Identified  : {}"
        .format(mapped_assets)
    )

    print(
        "Runtime            : {:.2f} sec"
        .format(runtime)
    )

    print(
        "Engine             : {}"
        .format(ENGINE_VERSION)
    )

    print("=" * 82)

    print_recent_news(conn)

    print()
    print("=" * 82)
    print("       ARUNDA MARKET NEWS ENGINE v0.2 COMPLETE")
    print("=" * 82)

    if successful_sources > 0:
        print("NEWS STATUS : SUCCESS")
    else:
        print("NEWS STATUS : FAILED")

    print("Sentiment     : NOT USED")
    print("Ranking       : NOT USED")
    print("Opportunity   : NOT USED")
    print("Signal        : NOT USED")
    print("Prediction    : NOT USED")
    print("Risk          : NOT USED")
    print("Execution     : NOT USED")

    conn.close()


if __name__ == "__main__":
    main()
