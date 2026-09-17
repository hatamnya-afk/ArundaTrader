import sqlite3
import math
import hashlib
from datetime import datetime, timezone


DB_PATH = "arunda.db"
ENGINE_VERSION = "FUSION_v0.5"

ASSETS = ["BTC", "ETH", "SOL", "XRP"]

BASE_WEIGHTS = {
    "market": 0.40,
    "positioning": 0.35,
    "news": 0.25,
}

# ---------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------

def clamp(value, low=-100.0, high=100.0):
    return max(low, min(high, value))


def normalize_market(score):
    """
    Market score in our current CMC adapter is approximately -15..+15.
    Convert to -100..+100.
    """
    if score is None:
        return None

    try:
        return clamp(float(score) / 15.0 * 100.0)
    except Exception:
        return None


def normalize_positioning(score):
    """
    Convert the native Coinalyze positioning score
    into Fusion signed directional space.

    Native positioning scale:
        35 = strong bearish
        50 = neutral
        70 = strong bullish

    Fusion scale:
        -100 = strong bearish
           0 = neutral
        +100 = strong bullish

    Piecewise calibration:
        35   -> -100
        42.5 -> -50
        50   -> 0
        60   -> +50
        70   -> +100
    """

    if score is None:
        return None

    try:
        score = float(score)
    except (TypeError, ValueError):
        return None

    # Lower positioning range: 35 -> -100, 50 -> 0
    if score <= 50.0:
        normalized = (score - 50.0) * (100.0 / 15.0)

    # Upper positioning range: 50 -> 0, 70 -> +100
    else:
        normalized = (score - 50.0) * (100.0 / 20.0)

    return clamp(normalized)

def normalize_news(score):
    """
    News score currently behaves approximately -5..+5.
    """
    if score is None:
        return None

    try:
        return clamp(float(score) / 5.0 * 100.0)
    except Exception:
        return None


# ---------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------

def connect_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_column(conn, table, column, definition):
    columns = {
        row["name"]
        for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
    }

    if column not in columns:
        conn.execute(
            f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
        )
        print(f"SCHEMA | ADDED | {column}")


def ensure_schema(conn):
    columns = {
        row["name"]
        for row in conn.execute(
            "PRAGMA table_info(fusion_signals)"
        ).fetchall()
    }

    required = {
        "snapshot_id": "TEXT",
        "missing_arm_penalty": "REAL",
        "news_confidence": "REAL",
        "signal_strength": "TEXT",
        "entry_price": "REAL",
        "direction": "TEXT",
    }

    for column, definition in required.items():
        if column not in columns:
            conn.execute(
                f"ALTER TABLE fusion_signals ADD COLUMN "
                f"{column} {definition}"
            )
            print(f"SCHEMA | ADDED | {column}")


# ---------------------------------------------------------------------
# Latest market data
# ---------------------------------------------------------------------

def get_latest_market(conn, asset):
    row = conn.execute(
        """
        SELECT *
        FROM market_data
        WHERE symbol = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (asset,),
    ).fetchone()

    return row


def get_latest_positioning(conn, asset):
    row = conn.execute(
        """
        SELECT *
        FROM positioning_data
        WHERE market = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (asset,),
    ).fetchone()

    return row


def get_latest_news(conn, asset):
    row = conn.execute(
        """
        SELECT *
        FROM news_signals
        WHERE asset = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (asset,),
    ).fetchone()

    return row


# ---------------------------------------------------------------------
# Signal calculations
# ---------------------------------------------------------------------

def calculate_news_confidence(news):
    if news is None:
        return 0.0

    try:
        confidence = float(news["confidence"])
        return clamp(confidence, 0.0, 1.0)
    except Exception:
        return 0.0


def calculate_dynamic_weights(
    market_available,
    positioning_available,
    news_available,
    news_confidence,
):
    weights = dict(BASE_WEIGHTS)

    # Remove unavailable arms.
    if not market_available:
        weights["market"] = 0.0

    if not positioning_available:
        weights["positioning"] = 0.0

    if not news_available:
        weights["news"] = 0.0
    else:
        # Weak news confidence should reduce its influence.
        weights["news"] *= max(0.25, news_confidence)

    total = sum(weights.values())

    if total <= 0:
        return {
            "market": 0.0,
            "positioning": 0.0,
            "news": 0.0,
        }

    return {
        key: value / total
        for key, value in weights.items()
    }


def calculate_agreement(values):
    """
    Agreement is based on directional coherence.

    Same direction -> high agreement.
    Opposite directions -> low agreement.
    Near-zero values are treated as neutral.
    """

    values = [
        float(v)
        for v in values
        if v is not None
    ]

    if len(values) <= 1:
        return 1.0

    directions = []

    for value in values:
        if value > 10:
            directions.append(1)
        elif value < -10:
            directions.append(-1)
        else:
            directions.append(0)

    non_neutral = [
        d for d in directions
        if d != 0
    ]

    if not non_neutral:
        return 1.0

    positive = non_neutral.count(1)
    negative = non_neutral.count(-1)

    total = len(non_neutral)

    return max(positive, negative) / total


def calculate_missing_penalty(
    market_available,
    positioning_available,
    news_available,
):
    available = sum(
        [
            market_available,
            positioning_available,
            news_available,
        ]
    )

    if available == 3:
        return 1.0

    if available == 2:
        return 0.82

    if available == 1:
        return 0.65

    return 0.0


def calculate_fused_score(
    market_norm,
    positioning_norm,
    news_norm,
    weights,
    missing_penalty,
):
    score = 0.0

    if market_norm is not None:
        score += weights["market"] * market_norm

    if positioning_norm is not None:
        score += weights["positioning"] * positioning_norm

    if news_norm is not None:
        score += weights["news"] * news_norm

    return clamp(score * missing_penalty)


def calculate_confidence(
    fused_score,
    agreement,
    available_weight,
    news_confidence,
    missing_penalty,
):
    strength = abs(fused_score) / 100.0

    confidence = (
        0.40 * strength
        + 0.25 * agreement
        + 0.20 * available_weight
        + 0.15 * news_confidence
    )

    confidence *= missing_penalty

    return max(
        0.0,
        min(1.0, confidence)
    )


def determine_regime(score):
    if score >= 60:
        return "STRONG_BULLISH"

    if score >= 25:
        return "BULLISH"

    if score <= -60:
        return "STRONG_BEARISH"

    if score <= -25:
        return "BEARISH"

    return "NEUTRAL"


def determine_direction(score):
    """
    Direction threshold is intentionally wider than zero.
    Weak signals become FLAT and won't create false trades.
    """

    if score >= 25:
        return "LONG"

    if score <= -25:
        return "SHORT"

    return "FLAT"


def determine_signal_strength(score, confidence):
    magnitude = abs(score)

    if confidence >= 0.75 and magnitude >= 60:
        return "STRONG"

    if confidence >= 0.55 and magnitude >= 30:
        return "MODERATE"

    return "WEAK"


def calculate_available_weight(
    market_available,
    positioning_available,
    news_available,
):
    total = 0.0

    if market_available:
        total += BASE_WEIGHTS["market"]

    if positioning_available:
        total += BASE_WEIGHTS["positioning"]

    if news_available:
        total += BASE_WEIGHTS["news"]

    return total


# ---------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------

def create_snapshot_id(timestamp):
    raw = f"{timestamp}|{ENGINE_VERSION}"

    digest = hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()[:16]

    compact_time = (
        timestamp
        .replace("-", "")
        .replace(":", "")
        .replace(".", "")
        .replace("+00:00", "")
    )

    return f"FUSION-{compact_time}-{digest}"


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main():

    print("=" * 78)
    print("             ARUNDA FUSION ENGINE v0.5")
    print("=" * 78)
    print("Sources : CMC + COINALYZE + NEWS")
    print("Database: arunda.db")
    print("Mode    : CALIBRATED MULTI-ARM FUSION + ENTRY PRICE")
    print("=" * 78)

    conn = connect_db()

    try:
        ensure_schema(conn)
        conn.commit()

        timestamp = datetime.now(
            timezone.utc
        ).isoformat()

        snapshot_id = create_snapshot_id(timestamp)

        results = []

        for asset in ASSETS:

            market = get_latest_market(
                conn,
                asset,
            )

            positioning = get_latest_positioning(
                conn,
                asset,
            )

            news = get_latest_news(
                conn,
                asset,
            )

            # ---------------------------------------------------------
            # Availability
            # ---------------------------------------------------------

            market_available = (
                market is not None
                and market["technical_score"] is not None
            )

            positioning_available = (
                positioning is not None
                and positioning["positioning_score"] is not None
            )

            news_available = (
                news is not None
                and news["news_score"] is not None
            )

            if not any(
                [
                    market_available,
                    positioning_available,
                    news_available,
                ]
            ):
                print()
                print(f"FUSION : {asset}")
                print("NO VERIFIED DATA AVAILABLE.")
                continue

            # ---------------------------------------------------------
            # Raw values
            # ---------------------------------------------------------

            market_raw = (
                float(market["technical_score"])
                if market_available
                else None
            )

            positioning_raw = (
                float(positioning["positioning_score"])
                if positioning_available
                else None
            )

            news_raw = (
                float(news["news_score"])
                if news_available
                else None
            )

            # ---------------------------------------------------------
            # Normalize
            # ---------------------------------------------------------

            market_norm = normalize_market(
                market_raw
            )

            positioning_norm = normalize_positioning(
                positioning_raw
            )

            news_norm = normalize_news(
                news_raw
            )

            # ---------------------------------------------------------
            # Confidence / weights
            # ---------------------------------------------------------

            news_confidence = (
                calculate_news_confidence(news)
                if news_available
                else 0.0
            )

            weights = calculate_dynamic_weights(
                market_available,
                positioning_available,
                news_available,
                news_confidence,
            )

            available_weight = calculate_available_weight(
                market_available,
                positioning_available,
                news_available,
            )

            agreement_values = [
                market_norm if market_available else None,
                positioning_norm if positioning_available else None,
                news_norm if news_available else None,
            ]

            agreement = calculate_agreement(
                agreement_values
            )

            missing_penalty = calculate_missing_penalty(
                market_available,
                positioning_available,
                news_available,
            )

            # ---------------------------------------------------------
            # Fusion
            # ---------------------------------------------------------

            fused_score = calculate_fused_score(
                market_norm,
                positioning_norm,
                news_norm,
                weights,
                missing_penalty,
            )

            confidence = calculate_confidence(
                fused_score,
                agreement,
                available_weight,
                news_confidence,
                missing_penalty,
            )

            regime = determine_regime(
                fused_score
            )

            direction = determine_direction(
                fused_score
            )

            signal_strength = determine_signal_strength(
                fused_score,
                confidence,
            )

            data_quality = (
                "VERIFIED"
                if (
                    market_available
                    and positioning_available
                    and news_available
                )
                else "PARTIAL"
            )

            # ---------------------------------------------------------
            # Entry price
            # ---------------------------------------------------------

            entry_price = None

            if market is not None:
                try:
                    entry_price = float(
                        market["close"]
                    )
                except Exception:
                    entry_price = None

            # ---------------------------------------------------------
            # Output
            # ---------------------------------------------------------

            print()
            print("=" * 78)
            print(f"FUSION : {asset}")
            print("=" * 78)

            print(
                f"MARKET RAW         : {market_raw}"
            )

            print(
                f"MARKET NORMALIZED  : {market_norm}"
            )

            print(
                f"POSITIONING RAW    : {positioning_raw}"
            )

            print(
                f"POSITIONING NORMAL : {positioning_norm}"
            )

            print(
                f"NEWS RAW           : {news_raw}"
            )

            print(
                f"NEWS NORMALIZED    : {news_norm}"
            )

            print("-" * 78)

            print(
                "DYNAMIC WEIGHTS    : "
                f"M={weights['market']:.3f} "
                f"P={weights['positioning']:.3f} "
                f"N={weights['news']:.3f}"
            )

            print(
                f"AVAILABLE WEIGHT   : {available_weight:.3f}"
            )

            print(
                f"NEWS CONFIDENCE    : {news_confidence:.3f}"
            )

            print(
                f"AGREEMENT          : {agreement:.3f}"
            )

            print(
                f"MISSING ARM PENALTY: {missing_penalty:.3f}"
            )

            print(
                f"FUSED SCORE        : {fused_score:.2f}"
            )

            print(
                f"CONFIDENCE         : {confidence:.3f}"
            )

            print(
                f"REGIME             : {regime}"
            )

            print(
                f"DIRECTION          : {direction}"
            )

            print(
                f"SIGNAL STRENGTH    : {signal_strength}"
            )

            print(
                f"ENTRY PRICE        : {entry_price}"
            )

            print(
                f"DATA QUALITY       : {data_quality}"
            )

            print("-" * 78)

            print(
                "AVAILABLE          : "
                f"Market={int(market_available)} "
                f"Positioning={int(positioning_available)} "
                f"News={int(news_available)}"
            )

            # ---------------------------------------------------------
            # Database insert
            # ---------------------------------------------------------

            conn.execute(
                """
                INSERT INTO fusion_signals (
                    timestamp,
                    asset,
                    market_score,
                    positioning_score,
                    news_score,
                    market_weight,
                    positioning_weight,
                    news_weight,
                    fused_score,
                    confidence,
                    regime,
                    data_quality,
                    market_available,
                    positioning_available,
                    news_available,
                    engine_version,
                    snapshot_id,
                    missing_arm_penalty,
                    news_confidence,
                    signal_strength,
                    entry_price,
                    direction,
                    market_score_norm,
                    positioning_score_norm,
                    news_score_norm,
                    agreement_score,
                    available_weight
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    timestamp,
                    asset,
                    market_raw,
                    positioning_raw,
                    news_raw,
                    weights["market"],
                    weights["positioning"],
                    weights["news"],
                    fused_score,
                    confidence,
                    regime,
                    data_quality,
                    int(market_available),
                    int(positioning_available),
                    int(news_available),
                    ENGINE_VERSION,
                    snapshot_id,
                    missing_penalty,
                    news_confidence,
                    signal_strength,
                    entry_price,
                    direction,
                    market_norm,
                    positioning_norm,
                    news_norm,
                    agreement,
                    available_weight,
                ),
            )

            results.append(
                {
                    "asset": asset,
                    "score": fused_score,
                    "confidence": confidence,
                    "regime": regime,
                    "direction": direction,
                    "entry_price": entry_price,
                    "quality": data_quality,
                }
            )

        conn.commit()

        # -------------------------------------------------------------
        # Summary
        # -------------------------------------------------------------

        print()
        print("=" * 78)
        print("                 FUSION ENGINE SUMMARY")
        print("=" * 78)

        print(
            "ASSET          SCORE      CONF              "
            "REGIME             DIRECTION    ENTRY"
        )

        print("-" * 78)

        for result in results:

            entry = result["entry_price"]

            if entry is None:
                entry_text = "N/A"
            else:
                entry_text = f"{entry:.6f}"

            print(
                f"{result['asset']:<14}"
                f"{result['score']:>7.2f}     "
                f"{result['confidence']:.3f}          "
                f"{result['regime']:<18}"
                f"{result['direction']:<12}"
                f"{entry_text}"
            )

        print()
        print("=" * 78)
        print("FUSION ENGINE COMPLETE")
        print("=" * 78)

        print(
            f"Signals generated : {len(results)}"
        )

        print(
            f"Snapshot ID       : {snapshot_id}"
        )

        print(
            f"Database           : {DB_PATH}"
        )

        print(
            "Table              : fusion_signals"
        )

        print(
            f"Engine             : {ENGINE_VERSION}"
        )

        print("=" * 78)

    except Exception as exc:

        conn.rollback()

        print()
        print("=" * 78)
        print("                 FUSION ENGINE ERROR")
        print("=" * 78)
        print(
            f"{type(exc).__name__}({str(exc)!r})"
        )
        print("=" * 78)

        raise

    finally:
        conn.close()


if __name__ == "__main__":
    main()

