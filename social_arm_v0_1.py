import json
import re
import time
import hashlib
from datetime import datetime, timezone

import websocket

from information_contract_v0_1 import validate_social


ENGINE_VERSION = "SOCIAL_ARM_v0.1"

RELAYS = [
    "wss://nos.lol",
    "wss://relay.snort.social",
    "wss://nostr.mom",
]

ASSETS = {
    "BTC": ["bitcoin", "$btc", "#btc", "btc", "₿"],
    "ETH": ["ethereum", "$eth", "#eth", "eth", "ether"],
    "SOL": ["solana", "$sol", "#sol", "sol"],
    "XRP": ["ripple", "$xrp", "#xrp", "xrp"],
}

POSITIVE = {
    "bullish", "bull", "buy", "bought", "long",
    "breakout", "surge", "rally", "pump", "growth",
    "上涨", "рост", "роста", "bullish",
}

NEGATIVE = {
    "bearish", "bear", "sell", "sold", "short",
    "dump", "crash", "drop", "fall", "decline",
    "下跌", "падение", "падает",
}

EVENT_TERMS = {
    "listing": ["listed", "listing", "launch"],
    "partnership": ["partnership", "partner", "collaboration"],
    "regulation": ["regulation", "sec", "ban", "legal"],
    "hack": ["hack", "hacked", "exploit", "stolen"],
    "upgrade": ["upgrade", "mainnet", "fork"],
    "price_move": ["surge", "rally", "crash", "dump", "breakout"],
}

MAX_EVENTS_PER_RELAY = 40
RECV_TIMEOUT = 7
MAX_OUTPUT_ITEMS = 100


def normalize_text(text):
    text = text or ""
    return re.sub(r"\s+", " ", text).strip()


def detect_assets(text):
    low = normalize_text(text).lower()
    found = []

    for asset, aliases in ASSETS.items():
        for alias in aliases:
            a = alias.lower()

            if alias in ("btc", "eth", "sol", "xrp"):
                if re.search(rf"(?<![a-z0-9]){re.escape(a)}(?![a-z0-9])", low):
                    found.append(asset)
                    break
            elif a in low:
                found.append(asset)
                break

    return sorted(set(found))


def sentiment_score(text):
    low = normalize_text(text).lower()

    pos = sum(
        1 for term in POSITIVE
        if re.search(rf"(?<!\w){re.escape(term)}(?!\w)", low)
    )

    neg = sum(
        1 for term in NEGATIVE
        if re.search(rf"(?<!\w){re.escape(term)}(?!\w)", low)
    )

    if pos > neg:
        return "BULLISH", min(1.0, 0.5 + 0.1 * (pos - neg))

    if neg > pos:
        return "BEARISH", min(1.0, 0.5 + 0.1 * (neg - pos))

    return "NEUTRAL", 0.35


def detect_event(text):
    low = normalize_text(text).lower()

    for event_type, terms in EVENT_TERMS.items():
        for term in terms:
            if re.search(rf"(?<!\w){re.escape(term)}(?!\w)", low):
                return event_type

    return "social_discussion"


def freshness(created_at):
    try:
        now = int(time.time())
        age = max(0, now - int(created_at))

        # Exponential decay; no synthetic timestamps.
        value = 2 ** (-age / 86400)

        return round(max(0.0, min(1.0, value)), 4)

    except Exception:
        return 0.0


def relevance(text, assets):
    if not assets:
        return 0.0

    low = normalize_text(text).lower()

    score = 0.45

    if len(low) >= 40:
        score += 0.10

    if len(low) >= 120:
        score += 0.10

    if any(
        term in low
        for term in [
            "price",
            "market",
            "trading",
            "crypto",
            "token",
            "coin",
            "exchange",
            "bitcoin",
            "ethereum",
            "solana",
            "ripple",
        ]
    ):
        score += 0.20

    if any(
        event in low
        for terms in EVENT_TERMS.values()
        for event in terms
    ):
        score += 0.10

    return round(min(1.0, score), 4)


def confidence(rel, fresh, sentiment_conf):
    value = (
        0.45 * rel
        + 0.30 * fresh
        + 0.25 * sentiment_conf
    )

    return round(max(0.0, min(1.0, value)), 4)


def source_id(relay, event_id):
    return f"{relay}:{event_id}"


def stable_id(relay, event):
    raw = f"{relay}|{event.get('id')}|{event.get('created_at')}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def build_record(relay, event):
    content = normalize_text(event.get("content", ""))
    assets = detect_assets(content)

    if not assets:
        return None

    asset = assets[0]

    sentiment, sent_conf = sentiment_score(content)

    rel = relevance(content, assets)
    fresh = freshness(event.get("created_at"))

    record = {
        "contract_version": "INFORMATION_CONTRACT_v0.1",
        "source": "NOSTR",
        "source_id": source_id(
            relay,
            event.get("id", ""),
        ),
        "asset": asset,
        "timestamp": datetime.fromtimestamp(
            int(event.get("created_at", 0)),
            tz=timezone.utc,
        ).isoformat(),
        "title": "",
        "text": content,
        "event_type": detect_event(content),
        "sentiment": sentiment,
        "relevance": rel,
        "confidence": confidence(
            rel,
            fresh,
            sent_conf,
        ),
        "freshness": fresh,
        "provenance": {
            "protocol": "NOSTR",
            "relay": relay,
            "event_id": event.get("id"),
            "pubkey": event.get("pubkey"),
            "kind": event.get("kind"),
            "created_at": event.get("created_at"),
        },
        "url": "",
        "author_id": event.get("pubkey"),
        "engagement": 0,
        "mention_count": 1,
        "momentum": 0.0,
    }

    return record


def read_relay(relay):
    ws = None
    events = []

    try:
        ws = websocket.create_connection(
            relay,
            timeout=RECV_TIMEOUT,
            origin="https://arundatrader.local",
        )

        sub_id = "ARUNDA_SOCIAL_01"

        request = [
            "REQ",
            sub_id,
            {
                "kinds": [1],
                "limit": MAX_EVENTS_PER_RELAY,
            },
        ]

        ws.send(json.dumps(request))

        deadline = time.time() + RECV_TIMEOUT

        while time.time() < deadline:

            try:
                raw = ws.recv()
            except Exception:
                break

            if not raw:
                continue

            try:
                message = json.loads(raw)
            except Exception:
                continue

            if not isinstance(message, list):
                continue

            if len(message) >= 3 and message[0] == "EVENT":
                event = message[2]

                if isinstance(event, dict):
                    events.append(event)

            elif message and message[0] == "EOSE":
                break

        return events

    finally:
        if ws:
            try:
                ws.close()
            except Exception:
                pass


def deduplicate(records):
    seen = set()
    output = []

    for record in records:
        key = (
            record["source"],
            record["source_id"],
        )

        if key in seen:
            continue

        seen.add(key)
        output.append(record)

    return output


def calculate_momentum(records):
    counts = {}

    now = time.time()

    for record in records:
        asset = record["asset"]

        try:
            ts = datetime.fromisoformat(
                record["timestamp"]
            ).timestamp()
        except Exception:
            continue

        age = max(0, now - ts)

        if age <= 3600:
            weight = 1.0
        elif age <= 21600:
            weight = 0.5
        elif age <= 86400:
            weight = 0.2
        else:
            weight = 0.05

        counts[asset] = counts.get(asset, 0.0) + weight

    max_value = max(counts.values(), default=0.0)

    for record in records:
        value = counts.get(record["asset"], 0.0)

        if max_value:
            record["momentum"] = round(
                value / max_value,
                4,
            )
        else:
            record["momentum"] = 0.0


def validate_records(records):
    valid = []
    invalid = []

    for record in records:
        try:
            result = validate_social(record)

            if result is True:
                valid.append(record)
            else:
                invalid.append({
                    "source_id": record["source_id"],
                    "error": str(result),
                })

        except Exception as exc:
            invalid.append({
                "source_id": record["source_id"],
                "error": str(exc),
            })

    return valid, invalid


def run():
    started = time.perf_counter()

    raw_records = []
    relay_results = []

    for relay in RELAYS:

        relay_started = time.perf_counter()

        try:
            events = read_relay(relay)

            relay_records = []

            for event in events:
                record = build_record(relay, event)

                if record is not None:
                    relay_records.append(record)

            raw_records.extend(relay_records)

            relay_results.append({
                "relay": relay,
                "status": "PASS",
                "events": len(events),
                "crypto_records": len(relay_records),
                "latency": round(
                    time.perf_counter() - relay_started,
                    3,
                ),
            })

        except Exception as exc:

            relay_results.append({
                "relay": relay,
                "status": "FAIL",
                "events": 0,
                "crypto_records": 0,
                "latency": round(
                    time.perf_counter() - relay_started,
                    3,
                ),
                "error": type(exc).__name__,
            })

    records = deduplicate(raw_records)

    records.sort(
        key=lambda x: (
            x["freshness"],
            x["confidence"],
        ),
        reverse=True,
    )

    records = records[:MAX_OUTPUT_ITEMS]

    calculate_momentum(records)

    valid, invalid = validate_records(records)

    return {
        "engine_version": ENGINE_VERSION,
        "status": (
            "PASS"
            if valid
            else "NO_DATA"
        ),
        "items": valid,
        "item_count": len(valid),
        "invalid_count": len(invalid),
        "relay_results": relay_results,
        "db_writes": 0,
        "lunarcrush": 0,
        "execution": "OFF",
        "elapsed": round(
            time.perf_counter() - started,
            3,
        ),
    }


def main():
    result = run()

    print("=" * 72)
    print("ARUNDA SOCIAL ARM v0.1")
    print("=" * 72)

    print(f"STATUS={result['status']}")
    print(f"ITEMS={result['item_count']}")
    print(f"INVALID={result['invalid_count']}")
    print(f"ENGINE={result['engine_version']}")

    for relay in result["relay_results"]:
        print(
            f"{relay['status']:5} | "
            f"{relay['relay']} | "
            f"EVENTS={relay['events']} | "
            f"CRYPTO={relay['crypto_records']} | "
            f"{relay['latency']}s"
        )

    print("-" * 72)
    print(f"CONTRACT={'PASS' if result['item_count'] > 0 else 'NO_DATA'}")
    print("DB_WRITE=0")
    print("LUNARCRUSH=0")
    print("EXECUTION=OFF")
    print("=" * 72)

    with open(
        "social_arm_v0_1_runtime_result.json",
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            result,
            f,
            ensure_ascii=False,
            indent=2,
        )


if __name__ == "__main__":
    main()