# ================================================================
# ARUNDA NEWS ADAPTER v0.2
# GDELT + CRYPTO RSS
# ================================================================

import sqlite3
import hashlib
import json
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime


DB = "arunda.db"

ENGINE_VERSION = "NEWS_RSS_v0.2"

RSS_SOURCES = {
    "COINDESK": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "COINTELEGRAPH": "https://cointelegraph.com/rss",
    "DECRYPT": "https://decrypt.co/feed",
    "BITCOIN_MAGAZINE": "https://bitcoinmagazine.com/.rss/full/",
}


# ------------------------------------------------
# KEYWORDS
# ------------------------------------------------

BULLISH = {
    "etf approval": 5,
    "etf inflow": 5,
    "institutional buying": 5,
    "institutional adoption": 4,
    "adoption": 3,
    "bullish": 3,
    "breakout": 4,
    "accumulation": 3,
    "inflow": 3,
    "buying": 2,
    "surge": 2,
    "rally": 3,
    "approval": 4,
    "positive": 2,
    "upgrade": 2,
    "partnership": 2,
    "record high": 4,
}

BEARISH = {
    "etf outflow": -5,
    "hack": -6,
    "hacked": -6,
    "exploit": -6,
    "bankruptcy": -6,
    "fraud": -6,
    "lawsuit": -4,
    "sec lawsuit": -5,
    "regulation": -2,
    "ban": -5,
    "banned": -5,
    "liquidation": -4,
    "liquidations": -4,
    "outflow": -3,
    "selling": -2,
    "sell-off": -4,
    "selloff": -4,
    "bearish": -3,
    "crash": -6,
    "collapse": -6,
    "recession": -4,
    "negative": -2,
}

HIGH_IMPACT = {
    "fed": 5,
    "federal reserve": 5,
    "interest rate": 4,
    "rate cut": 5,
    "rate hike": 5,
    "cpi": 4,
    "inflation": 4,
    "employment": 3,
    "nonfarm payroll": 5,
    "sec": 4,
    "etf": 5,
    "hack": 6,
    "exploit": 6,
    "bankruptcy": 6,
    "liquidation": 5,
    "whale": 3,
}


# ------------------------------------------------
# DATABASE
# ------------------------------------------------

def db_connect():
    return sqlite3.connect(DB)


def ensure_schema():

    conn = db_connect()
    cur = conn.cursor()

    # Existing news table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS news_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            source TEXT,
            title TEXT,
            url TEXT,
            asset TEXT,
            category TEXT,
            sentiment_score REAL,
            impact_score REAL,
            news_score REAL,
            fingerprint TEXT,
            engine_version TEXT
        )
    """)

    # Add missing columns safely
    columns = {
        "timestamp": "TEXT",
        "source": "TEXT",
        "title": "TEXT",
        "url": "TEXT",
        "asset": "TEXT",
        "category": "TEXT",
        "sentiment_score": "REAL",
        "impact_score": "REAL",
        "news_score": "REAL",
        "fingerprint": "TEXT",
        "engine_version": "TEXT",
    }

    existing = {
        row[1]
        for row in cur.execute("PRAGMA table_info(news_data)").fetchall()
    }

    for name, dtype in columns.items():
        if name not in existing:
            cur.execute(
                f"ALTER TABLE news_data ADD COLUMN {name} {dtype}"
            )

    cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_news_fingerprint
        ON news_data(fingerprint)
    """)

    # Aggregated signal table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS news_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            asset TEXT NOT NULL,
            news_score REAL,
            bullish_pressure REAL,
            bearish_pressure REAL,
            neutral_pressure REAL,
            article_count INTEGER,
            confidence REAL,
            regime TEXT,
            engine_version TEXT
        )
    """)

    conn.commit()
    conn.close()


# ------------------------------------------------
# HTTP
# ------------------------------------------------

def fetch_url(url, timeout=12):

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent":
                "Mozilla/5.0 ArundaTrader/NewsAdapter"
        }
    )

    start = time.time()

    try:
        with urllib.request.urlopen(
            request,
            timeout=timeout
        ) as response:

            data = response.read()

            latency = round(
                (time.time() - start) * 1000,
                2
            )

            return data, latency, None

    except Exception as e:

        return None, round(
            (time.time() - start) * 1000,
            2
        ), str(e)


# ------------------------------------------------
# RSS PARSER
# ------------------------------------------------

def parse_rss(data):

    root = ET.fromstring(data)

    articles = []

    # RSS
    for item in root.findall(".//item"):

        title = item.findtext("title", "")
        link = item.findtext("link", "")
        pubdate = item.findtext("pubDate", "")
        description = item.findtext("description", "")

        articles.append({
            "title": clean_text(title),
            "url": clean_text(link),
            "published": parse_date(pubdate),
            "description": clean_text(description),
        })

    # Atom fallback
    if not articles:

        ns = {
            "atom": "http://www.w3.org/2005/Atom"
        }

        for entry in root.findall(
            ".//atom:entry",
            ns
        ):

            title = entry.findtext(
                "atom:title",
                "",
                ns
            )

            link_element = entry.find(
                "atom:link",
                ns
            )

            link = ""

            if link_element is not None:
                link = link_element.attrib.get(
                    "href",
                    ""
                )

            published = entry.findtext(
                "atom:published",
                "",
                ns
            )

            summary = entry.findtext(
                "atom:summary",
                "",
                ns
            )

            articles.append({
                "title": clean_text(title),
                "url": clean_text(link),
                "published": parse_date(published),
                "description": clean_text(summary),
            })

    return articles


def clean_text(text):

    if not text:
        return ""

    text = re.sub(
        r"<[^>]+>",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def parse_date(value):

    if not value:
        return datetime.now(
            timezone.utc
        ).isoformat()

    try:

        dt = parsedate_to_datetime(value)

        if dt.tzinfo is None:
            dt = dt.replace(
                tzinfo=timezone.utc
            )

        return dt.astimezone(
            timezone.utc
        ).isoformat()

    except Exception:

        try:
            return datetime.fromisoformat(
                value.replace("Z", "+00:00")
            ).astimezone(
                timezone.utc
            ).isoformat()

        except Exception:

            return datetime.now(
                timezone.utc
            ).isoformat()


# ------------------------------------------------
# FINGERPRINT
# ------------------------------------------------

def fingerprint(title, url):

    raw = (
        title.strip().lower()
        + "|"
        + url.strip().lower()
    )

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()


# ------------------------------------------------
# ASSET DETECTION
# ------------------------------------------------

def detect_asset(title, description):

    text = (
        title + " " + description
    ).lower()

    if re.search(
        r"\bbitcoin\b|\bbtc\b",
        text
    ):
        return "BTC"

    if re.search(
        r"\bethereum\b|\beth\b",
        text
    ):
        return "ETH"

    if re.search(
        r"\bsolana\b|\bsol\b",
        text
    ):
        return "SOL"

    if re.search(
        r"\bxrp\b|\bripple\b",
        text
    ):
        return "XRP"

    if re.search(
        r"\bbnb\b|\bbinance coin\b",
        text
    ):
        return "BNB"

    return "CRYPTO"


# ------------------------------------------------
# SENTIMENT
# ------------------------------------------------

def calculate_sentiment(text):

    text = text.lower()

    score = 0.0

    for keyword, value in BULLISH.items():

        if keyword in text:
            score += value

    for keyword, value in BEARISH.items():

        if keyword in text:
            score += value

    return max(
        -10.0,
        min(10.0, score)
    )


# ------------------------------------------------
# IMPACT
# ------------------------------------------------

def calculate_impact(text):

    text = text.lower()

    impact = 1.0

    for keyword, value in HIGH_IMPACT.items():

        if keyword in text:
            impact += value

    return min(
        10.0,
        impact
    )


# ------------------------------------------------
# NEWS SCORE
# ------------------------------------------------

def calculate_news_score(
    sentiment,
    impact
):

    # sentiment: -10 ... +10
    # impact: 1 ... 10

    score = sentiment * (
        impact / 10.0
    )

    return round(
        max(-10.0, min(10.0, score)),
        4
    )


# ------------------------------------------------
# INSERT
# ------------------------------------------------

def insert_article(article):

    conn = db_connect()
    cur = conn.cursor()

    title = article["title"]
    url = article["url"]

    fp = fingerprint(
        title,
        url
    )

    # Dedup
    exists = cur.execute(
        """
        SELECT 1
        FROM news_data
        WHERE fingerprint = ?
        LIMIT 1
        """,
        (fp,)
    ).fetchone()

    if exists:

        conn.close()
        return False

    text = (
        title
        + " "
        + article["description"]
    )

    asset = detect_asset(
        title,
        article["description"]
    )

    sentiment = calculate_sentiment(
        text
    )

    impact = calculate_impact(
        text
    )

    news_score = calculate_news_score(
        sentiment,
        impact
    )

    cur.execute(
        """
        INSERT INTO news_data (
            timestamp,
            source,
            title,
            url,
            asset,
            category,
            sentiment_score,
            impact_score,
            news_score,
            fingerprint,
            engine_version
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            article["published"],
            article["source"],
            title,
            url,
            asset,
            "CRYPTO",
            sentiment,
            impact,
            news_score,
            fp,
            ENGINE_VERSION,
        )
    )

    conn.commit()
    conn.close()

    return True


# ------------------------------------------------
# AGGREGATE SIGNAL
# ------------------------------------------------

def generate_signal(asset):

    conn = db_connect()
    cur = conn.cursor()

    rows = cur.execute(
        """
        SELECT news_score
        FROM news_data
        WHERE asset = ?
        ORDER BY timestamp DESC
        LIMIT 50
        """,
        (asset,)
    ).fetchall()

    conn.close()

    if not rows:

        return None

    scores = [
        float(row[0])
        for row in rows
        if row[0] is not None
    ]

    if not scores:
        return None

    total = len(scores)

    bullish = sum(
        1 for x in scores
        if x > 0.5
    )

    bearish = sum(
        1 for x in scores
        if x < -0.5
    )

    neutral = total - bullish - bearish

    avg = sum(scores) / total

    bullish_pressure = (
        bullish / total
    ) * 100

    bearish_pressure = (
        bearish / total
    ) * 100

    neutral_pressure = (
        neutral / total
    ) * 100

    # Confidence grows with article count
    confidence = min(
        1.0,
        0.35 + (
            total / 50.0
        ) * 0.65
    )

    if avg >= 2.0:
        regime = "STRONG_BULLISH"

    elif avg >= 0.5:
        regime = "BULLISH"

    elif avg <= -2.0:
        regime = "STRONG_BEARISH"

    elif avg <= -0.5:
        regime = "BEARISH"

    else:
        regime = "NEUTRAL"

    timestamp = datetime.now(
        timezone.utc
    ).isoformat()

    conn = db_connect()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO news_signals (
            timestamp,
            asset,
            news_score,
            bullish_pressure,
            bearish_pressure,
            neutral_pressure,
            article_count,
            confidence,
            regime,
            engine_version
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            timestamp,
            asset,
            round(avg, 4),
            round(bullish_pressure, 2),
            round(bearish_pressure, 2),
            round(neutral_pressure, 2),
            total,
            round(confidence, 3),
            regime,
            ENGINE_VERSION,
        )
    )

    conn.commit()
    conn.close()

    return {
        "asset": asset,
        "news_score": round(avg, 4),
        "bullish_pressure": round(
            bullish_pressure,
            2
        ),
        "bearish_pressure": round(
            bearish_pressure,
            2
        ),
        "neutral_pressure": round(
            neutral_pressure,
            2
        ),
        "article_count": total,
        "confidence": round(
            confidence,
            3
        ),
        "regime": regime,
    }


# ------------------------------------------------
# SOURCE RUNNER
# ------------------------------------------------

def run_sources():

    print()
    print("=" * 78)
    print(
        "             ARUNDA NEWS ADAPTER v0.2"
    )
    print("=" * 78)
    print(
        "Sources : Crypto RSS"
    )
    print(
        "Database: arunda.db"
    )
    print("=" * 78)
    print()

    total_articles = 0
    inserted_articles = 0

    for source, url in RSS_SOURCES.items():

        data, latency, error = fetch_url(
            url
        )

        if error:

            print(
                f"{source:<16} | OFFLINE | "
                f"{error}"
            )

            continue

        try:

            articles = parse_rss(
                data
            )

            for article in articles:

                article["source"] = source

            total_articles += len(
                articles
            )

            inserted = 0

            for article in articles:

                if insert_article(
                    article
                ):
                    inserted += 1
                    inserted_articles += 1

            print(
                f"{source:<16} | ONLINE  | "
                f"{len(articles):>3} articles | "
                f"{latency:>7.0f} ms | "
                f"NEW {inserted:>3}"
            )

        except Exception as e:

            print(
                f"{source:<16} | ERROR   | "
                f"{str(e)}"
            )

    print()
    print(
        f"TOTAL ARTICLES : {total_articles}"
    )

    print(
        f"NEW INSERTS    : {inserted_articles}"
    )

    print()

    # Generate signals
    print("=" * 78)
    print(
        "                    NEWS SIGNALS"
    )
    print("=" * 78)

    for asset in [
        "BTC",
        "ETH",
        "SOL",
        "XRP",
        "BNB",
        "CRYPTO",
    ]:

        signal = generate_signal(
            asset
        )

        if signal:

            print()
            print(
                f"{asset:<8} | "
                f"Score {signal['news_score']:>7.2f} | "
                f"Regime {signal['regime']:<16} | "
                f"Confidence {signal['confidence']:.2f}"
            )

            print(
                f"         | "
                f"Bull {signal['bullish_pressure']:>6.1f}% | "
                f"Bear {signal['bearish_pressure']:>6.1f}% | "
                f"Neutral {signal['neutral_pressure']:>6.1f}% | "
                f"N={signal['article_count']}"
            )

    print()
    print("=" * 78)
    print(
        "                 NEWS ADAPTER COMPLETE"
    )
    print("=" * 78)
    print(
        f"Database : {DB}"
    )
    print(
        "Tables   : news_data + news_signals"
    )
    print(
        f"Engine   : {ENGINE_VERSION}"
    )
    print("=" * 78)


# ------------------------------------------------
# MAIN
# ------------------------------------------------

if __name__ == "__main__":

    try:

        ensure_schema()
        run_sources()

    except Exception as e:

        print()
        print("=" * 78)
        print(
            "NEWS ADAPTER FATAL ERROR"
        )
        print("=" * 78)
        print(
            repr(e)
        )