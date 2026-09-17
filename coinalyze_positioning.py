import os
import sqlite3
import time
from datetime import datetime, timezone

import requests


# ============================================================
# ARUNDA COINALYZE POSITIONING ADAPTER v0.2
# ============================================================

DB = "arunda.db"

BASE_URL = "https://api.coinalyze.net/v1"

API_KEY = os.getenv("COINALYZE_API_KEY")

SYMBOL = "BTCUSDT_PERP.A"

INTERVAL = "5min"

# Historical window
HISTORY_MINUTES = 30

ENGINE_VERSION = "POSITIONING_COINALYZE_v0.2"


# ============================================================
# DATABASE
# ============================================================

def get_connection():

    return sqlite3.connect(DB)


def create_table(conn):

    conn.execute("""
        CREATE TABLE IF NOT EXISTS positioning_data (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            timestamp TEXT NOT NULL,

            market TEXT NOT NULL,

            source TEXT NOT NULL,

            symbol TEXT NOT NULL,

            interval TEXT,

            open_interest REAL,
            open_interest_change_pct REAL,

            funding_rate REAL,

            liquidation_long REAL,
            liquidation_short REAL,
            liquidation_total REAL,

            long_short_ratio REAL,
            long_position_pct REAL,
            short_position_pct REAL,

            positioning_score REAL,

            data_quality TEXT,

            api_status TEXT,

            engine_version TEXT,

            UNIQUE(
                market,
                timestamp,
                source,
                symbol
            )
        )
    """)

    conn.commit()


# ============================================================
# HTTP CLIENT
# ============================================================

class CoinalyzeClient:

    def __init__(self):

        if not API_KEY:

            raise RuntimeError(
                "COINALYZE_API_KEY is missing."
            )

        self.session = requests.Session()

        self.session.headers.update({
            "api_key": API_KEY,
            "Accept": "application/json"
        })

    def get(self, endpoint, params):

        url = BASE_URL + endpoint

        start = time.time()

        try:

            response = self.session.get(
                url,
                params=params,
                timeout=15
            )

        except requests.RequestException as e:

            raise RuntimeError(
                f"NETWORK ERROR: {e}"
            )

        latency = int(
            (time.time() - start) * 1000
        )

        if response.status_code == 429:

            retry_after = response.headers.get(
                "Retry-After",
                "unknown"
            )

            raise RuntimeError(
                f"RATE_LIMIT | "
                f"Retry-After={retry_after}"
            )

        if response.status_code != 200:

            raise RuntimeError(
                f"HTTP {response.status_code} | "
                f"{response.text[:500]}"
            )

        try:

            data = response.json()

        except Exception:

            raise RuntimeError(
                "Invalid JSON response"
            )

        return data, latency


# ============================================================
# TIME
# ============================================================

def now_unix():

    return int(
        time.time()
    )


def unix_to_iso(ts):

    if ts is None:
        return None

    return datetime.fromtimestamp(
        int(ts),
        tz=timezone.utc
    ).isoformat()


# ============================================================
# API FUNCTIONS
# ============================================================

def get_open_interest(client):

    data, latency = client.get(
        "/open-interest",
        {
            "symbols": SYMBOL,
            "convert_to_usd": "false"
        }
    )

    if not data:

        return None, latency

    return data[0], latency


def get_funding_rate(client):

    data, latency = client.get(
        "/funding-rate",
        {
            "symbols": SYMBOL
        }
    )

    if not data:

        return None, latency

    return data[0], latency


def get_open_interest_history(client):

    now = now_unix()

    start = now - (
        HISTORY_MINUTES * 60
    )

    data, latency = client.get(
        "/open-interest-history",
        {
            "symbols": SYMBOL,
            "interval": INTERVAL,
            "from": start,
            "to": now,
            "convert_to_usd": "false"
        }
    )

    if not data:

        return None, latency

    return data[0], latency


def get_liquidation_history(client):

    now = now_unix()

    start = now - (
        HISTORY_MINUTES * 60
    )

    data, latency = client.get(
        "/liquidation-history",
        {
            "symbols": SYMBOL,
            "interval": INTERVAL,
            "from": start,
            "to": now,
            "convert_to_usd": "false"
        }
    )

    if not data:

        return None, latency

    return data[0], latency


def get_long_short_history(client):

    now = now_unix()

    start = now - (
        HISTORY_MINUTES * 60
    )

    data, latency = client.get(
        "/long-short-ratio-history",
        {
            "symbols": SYMBOL,
            "interval": INTERVAL,
            "from": start,
            "to": now
        }
    )

    if not data:

        return None, latency

    return data[0], latency


# ============================================================
# HISTORY HELPERS
# ============================================================

def get_history_values(container):

    if not container:

        return []

    history = container.get(
        "history"
    )

    if not isinstance(
        history,
        list
    ):

        return []

    return history


def latest_value(container):

    history = get_history_values(
        container
    )

    if not history:

        return None

    return history[-1]


def previous_value(container):

    history = get_history_values(
        container
    )

    if len(history) < 2:

        return None

    return history[-2]


# ============================================================
# OI CHANGE
# ============================================================

def calculate_oi_change(
    latest,
    previous
):

    if not latest or not previous:

        return None

    latest_close = latest.get("c")
    previous_close = previous.get("c")

    if (
        latest_close is None
        or previous_close is None
        or previous_close == 0
    ):

        return None

    return (
        (
            latest_close
            - previous_close
        )
        / previous_close
        * 100
    )


# ============================================================
# LIQUIDATIONS
# ============================================================

def parse_liquidations(
    latest
):

    if not latest:

        return None, None, None

    long_liquidation = latest.get(
        "l"
    )

    short_liquidation = latest.get(
        "s"
    )

    total = None

    if (
        long_liquidation is not None
        and short_liquidation is not None
    ):

        total = (
            long_liquidation
            + short_liquidation
        )

    return (
        long_liquidation,
        short_liquidation,
        total
    )


# ============================================================
# LONG / SHORT
# ============================================================

def parse_long_short(
    latest
):

    if not latest:

        return (
            None,
            None,
            None
        )

    ratio = latest.get(
        "r"
    )

    long_pct = latest.get(
        "l"
    )

    short_pct = latest.get(
        "s"
    )

    return (
        ratio,
        long_pct,
        short_pct
    )


# ============================================================
# POSITIONING SCORE
# ============================================================

def calculate_positioning_score(
    funding_rate,
    oi_change_pct,
    liquidation_long,
    liquidation_short,
    long_short_ratio
):

    components = []

    # --------------------------------------------------------
    # FUNDING
    # --------------------------------------------------------

    if funding_rate is not None:

        if funding_rate >= 0.001:

            components.append(35)

        elif funding_rate >= 0.0005:

            components.append(45)

        elif funding_rate >= 0:

            components.append(55)

        elif funding_rate > -0.0005:

            components.append(55)

        elif funding_rate > -0.001:

            components.append(65)

        else:

            components.append(70)

    # --------------------------------------------------------
    # OI
    # --------------------------------------------------------

    if oi_change_pct is not None:

        if oi_change_pct >= 5:

            components.append(65)

        elif oi_change_pct >= 2:

            components.append(60)

        elif oi_change_pct > -2:

            components.append(50)

        elif oi_change_pct > -5:

            components.append(45)

        else:

            components.append(40)

    # --------------------------------------------------------
    # LIQUIDATIONS
    # --------------------------------------------------------

    if (
        liquidation_long is not None
        and liquidation_short is not None
    ):

        total = (
            liquidation_long
            + liquidation_short
        )

        if total > 0:

            short_share = (
                liquidation_short
                / total
            )

            long_share = (
                liquidation_long
                / total
            )

            if short_share >= 0.65:

                components.append(65)

            elif long_share >= 0.65:

                components.append(35)

            else:

                components.append(50)

    # --------------------------------------------------------
    # LONG / SHORT
    # --------------------------------------------------------

    if long_short_ratio is not None:

        if long_short_ratio >= 1.5:

            components.append(40)

        elif long_short_ratio >= 1.1:

            components.append(45)

        elif long_short_ratio >= 0.9:

            components.append(50)

        elif long_short_ratio >= 0.67:

            components.append(55)

        else:

            components.append(60)

    if len(components) == 0:

        return None

    return round(
        sum(components)
        / len(components),
        2
    )


# ============================================================
# QUALITY
# ============================================================

def determine_quality(
    oi,
    funding,
    oi_history,
    liquidation,
    long_short
):

    core = [
        oi,
        funding,
        oi_history,
        long_short
    ]

    available = sum(
        x is not None
        for x in core
    )

    if available == 4:

        if liquidation is not None:

            return "COMPLETE"

        return "PARTIAL"

    if available >= 2:

        return "DEGRADED"

    return "INSUFFICIENT"


# ============================================================
# SAVE
# ============================================================

def save_positioning(
    conn,
    timestamp,
    oi,
    oi_change_pct,
    funding,
    liquidation_long,
    liquidation_short,
    liquidation_total,
    long_short_ratio,
    long_position_pct,
    short_position_pct,
    score,
    quality
):

    conn.execute("""
        INSERT OR REPLACE INTO positioning_data (

            timestamp,
            market,
            source,
            symbol,
            interval,

            open_interest,
            open_interest_change_pct,

            funding_rate,

            liquidation_long,
            liquidation_short,
            liquidation_total,

            long_short_ratio,
            long_position_pct,
            short_position_pct,

            positioning_score,

            data_quality,

            api_status,

            engine_version
        )

        VALUES (
            ?, ?, ?, ?, ?,

            ?, ?,

            ?,

            ?, ?, ?,

            ?, ?, ?,

            ?,

            ?,

            ?,

            ?
        )
    """, (

        timestamp,

        "BTC",

        "COINALYZE",

        SYMBOL,

        INTERVAL,

        oi,

        oi_change_pct,

        funding,

        liquidation_long,

        liquidation_short,

        liquidation_total,

        long_short_ratio,

        long_position_pct,

        short_position_pct,

        score,

        quality,

        "OK",

        ENGINE_VERSION
    ))

    conn.commit()


# ============================================================
# MAIN PROCESS
# ============================================================

def process():

    print()
    print("=" * 82)
    print("             ARUNDA POSITIONING ADAPTER v0.2")
    print("=" * 82)

    print(
        f"Source   : COINALYZE"
    )

    print(
        f"Symbol   : {SYMBOL}"
    )

    print(
        f"Interval : {INTERVAL}"
    )

    print(
        f"History  : {HISTORY_MINUTES} minutes"
    )

    print()

    client = CoinalyzeClient()

    # --------------------------------------------------------
    # OPEN INTEREST
    # --------------------------------------------------------

    oi_data, oi_latency = (
        get_open_interest(client)
    )

    print(
        f"Open Interest       : {oi_data}"
    )

    print(
        f"OI Latency          : {oi_latency} ms"
    )

    # --------------------------------------------------------
    # FUNDING
    # --------------------------------------------------------

    funding_data, funding_latency = (
        get_funding_rate(client)
    )

    print(
        f"Funding Rate        : {funding_data}"
    )

    print(
        f"Funding Latency     : {funding_latency} ms"
    )

    # --------------------------------------------------------
    # OI HISTORY
    # --------------------------------------------------------

    oi_history, oi_hist_latency = (
        get_open_interest_history(client)
    )

    oi_latest = latest_value(
        oi_history
    )

    oi_previous = previous_value(
        oi_history
    )

    oi_change_pct = calculate_oi_change(
        oi_latest,
        oi_previous
    )

    print(
        f"OI Latest           : {oi_latest}"
    )

    print(
        f"OI Previous         : {oi_previous}"
    )

    print(
        f"OI Change %         : {oi_change_pct}"
    )

    # --------------------------------------------------------
    # LIQUIDATIONS
    # --------------------------------------------------------

    liquidation_data, liquidation_latency = (
        get_liquidation_history(client)
    )

    liquidation_latest = latest_value(
        liquidation_data
    )

    (
        liquidation_long,
        liquidation_short,
        liquidation_total
    ) = parse_liquidations(
        liquidation_latest
    )

    print(
        f"Liquidation Latest  : "
        f"{liquidation_latest}"
    )

    print(
        f"Liquidation Long    : "
        f"{liquidation_long}"
    )

    print(
        f"Liquidation Short   : "
        f"{liquidation_short}"
    )

    print(
        f"Liquidation Total   : "
        f"{liquidation_total}"
    )

    # --------------------------------------------------------
    # LONG / SHORT
    # --------------------------------------------------------

    long_short_data, ls_latency = (
        get_long_short_history(client)
    )

    long_short_latest = latest_value(
        long_short_data
    )

    (
        long_short_ratio,
        long_position_pct,
        short_position_pct
    ) = parse_long_short(
        long_short_latest
    )

    print(
        f"Long/Short Latest   : "
        f"{long_short_latest}"
    )

    print(
        f"Long/Short Ratio    : "
        f"{long_short_ratio}"
    )

    print(
        f"Long %              : "
        f"{long_position_pct}"
    )

    print(
        f"Short %             : "
        f"{short_position_pct}"
    )

    # --------------------------------------------------------
    # FUNDING VALUE
    # --------------------------------------------------------

    funding_value = None

    if funding_data:

        funding_value = funding_data.get(
            "value"
        )

    # --------------------------------------------------------
    # SCORE
    # --------------------------------------------------------

    score = calculate_positioning_score(
        funding_value,
        oi_change_pct,
        liquidation_long,
        liquidation_short,
        long_short_ratio
    )

    # --------------------------------------------------------
    # QUALITY
    # --------------------------------------------------------

    quality = determine_quality(
        oi_data,
        funding_data,
        oi_history,
        liquidation_data,
        long_short_data
    )

    # --------------------------------------------------------
    # TIMESTAMP
    # --------------------------------------------------------

    # Prefer Coinalyze timestamp when available.

    timestamp_unix = None

    if oi_data:

        timestamp_unix = oi_data.get(
            "update"
        )

    if timestamp_unix is not None:

        timestamp = unix_to_iso(
            timestamp_unix / 1000
        )

    elif oi_latest:

        timestamp = unix_to_iso(
            oi_latest.get("t")
        )

    else:

        timestamp = datetime.now(
            timezone.utc
        ).isoformat()

    # --------------------------------------------------------
    # DATABASE
    # --------------------------------------------------------

    conn = get_connection()

    create_table(conn)

    save_positioning(
        conn,

        timestamp,

        oi_data.get("value")
        if oi_data
        else None,

        oi_change_pct,

        funding_value,

        liquidation_long,

        liquidation_short,

        liquidation_total,

        long_short_ratio,

        long_position_pct,

        short_position_pct,

        score,

        quality
    )

    conn.close()

    # --------------------------------------------------------
    # FINAL REPORT
    # --------------------------------------------------------

    print()
    print("=" * 82)
    print("POSITIONING RESULT")
    print("=" * 82)

    print(
        f"OI                  : "
        f"{oi_data.get('value') if oi_data else None}"
    )

    print(
        f"OI Change           : "
        f"{oi_change_pct}"
    )

    print(
        f"Funding             : "
        f"{funding_value}"
    )

    print(
        f"Long Liquidation    : "
        f"{liquidation_long}"
    )

    print(
        f"Short Liquidation   : "
        f"{liquidation_short}"
    )

    print(
        f"Long/Short Ratio    : "
        f"{long_short_ratio}"
    )

    print(
        f"Long %              : "
        f"{long_position_pct}"
    )

    print(
        f"Short %             : "
        f"{short_position_pct}"
    )

    print(
        f"Positioning Score   : "
        f"{score}"
    )

    print(
        f"Data Quality        : "
        f"{quality}"
    )

    print()

    print(
        "Database            : arunda.db"
    )

    print(
        "Table               : positioning_data"
    )

    print(
        f"Engine              : "
        f"{ENGINE_VERSION}"
    )

    print("=" * 82)


# ============================================================
# ENTRY
# ============================================================

if __name__ == "__main__":

    try:

        process()

    except Exception as e:

        print()
        print("=" * 82)
        print("POSITIONING ADAPTER ERROR")
        print("=" * 82)

        print(
            repr(e)
        )

        print("=" * 82)