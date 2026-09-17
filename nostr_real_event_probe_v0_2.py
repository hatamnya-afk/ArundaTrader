import json
import time
import websocket

RELAYS = [
    "wss://nos.lol",
    "wss://relay.damus.io",
    "wss://relay.primal.net",
    "wss://nostr.wine",
    "wss://relay.snort.social",
    "wss://nostr.mom",
    "wss://relay.nostr.bg",
    "wss://relay.orangepill.dev",
]

ASSETS = {
    "BTC": ["btc", "bitcoin", "₿"],
    "ETH": ["eth", "ethereum", "ether"],
    "SOL": ["sol", "solana"],
    "XRP": ["xrp", "ripple"],
}

TIMEOUT = 7
MAX_EVENTS = 30


def detect_assets(text):
    text = (text or "").lower()
    found = []

    for asset, aliases in ASSETS.items():
        if any(alias.lower() in text for alias in aliases):
            found.append(asset)

    return sorted(set(found))


def probe(relay):
    ws = None
    started = time.perf_counter()
    events = []

    try:
        ws = websocket.create_connection(
            relay,
            timeout=TIMEOUT,
            origin="https://arundatrader.local",
        )

        sub_id = "ARUNDA_CRYPTO_02"

        # Recent kind-1 notes.
        # Asset relevance is validated locally from real event content.
        req = [
            "REQ",
            sub_id,
            {
                "kinds": [1],
                "limit": MAX_EVENTS,
            },
        ]

        ws.send(json.dumps(req))

        deadline = time.time() + TIMEOUT

        while time.time() < deadline:
            try:
                raw = ws.recv()
            except Exception:
                break

            if not raw:
                continue

            try:
                msg = json.loads(raw)
            except Exception:
                continue

            if not isinstance(msg, list) or len(msg) < 3:
                continue

            if msg[0] == "EVENT":
                event = msg[2]

                if not isinstance(event, dict):
                    continue

                content = event.get("content", "")
                assets = detect_assets(content)

                if assets:
                    events.append({
                        "id": event.get("id"),
                        "pubkey": event.get("pubkey"),
                        "created_at": event.get("created_at"),
                        "kind": event.get("kind"),
                        "assets": assets,
                        "content": content[:300],
                    })

                    if len(events) >= 5:
                        break

            elif msg[0] == "EOSE":
                break

        latency = round(time.perf_counter() - started, 3)

        if events:
            status = "PASS"
        else:
            status = "NO_CRYPTO_DATA"

        return {
            "relay": relay,
            "status": status,
            "crypto_events": len(events),
            "latency": latency,
            "events": events,
        }

    except Exception as e:
        latency = round(time.perf_counter() - started, 3)

        return {
            "relay": relay,
            "status": "FAIL",
            "crypto_events": 0,
            "latency": latency,
            "error": type(e).__name__,
        }

    finally:
        if ws:
            try:
                ws.close()
            except Exception:
                pass


def main():
    print("=" * 72)
    print("ARUNDA NOSTR CRYPTO + REDUNDANCY PROBE v0.2")
    print("=" * 72)

    results = []

    for relay in RELAYS:
        result = probe(relay)
        results.append(result)

        print(
            f"{result['status']:15} | "
            f"{relay} | "
            f"CRYPTO_EVENTS={result['crypto_events']} | "
            f"{result['latency']}s"
        )

        if result.get("events"):
            for event in result["events"][:2]:
                print(
                    f"    {event['assets']} | "
                    f"{event['content'][:140]!r}"
                )

        if result.get("error"):
            print(f"    ERROR={result['error']}")

    crypto_pass = sum(
        r["status"] == "PASS"
        for r in results
    )

    # Minimum two independent usable relays.
    redundancy_pass = crypto_pass >= 2
    crypto_relevance_pass = crypto_pass >= 1

    overall = (
        crypto_relevance_pass
        and redundancy_pass
    )

    print("-" * 72)
    print(f"CRYPTO_RELEVANCE={'PASS' if crypto_relevance_pass else 'FAIL'}")
    print(f"CRYPTO_RELAY_COUNT={crypto_pass}")
    print(f"REDUNDANCY={'PASS' if redundancy_pass else 'FAIL'}")
    print(f"NOSTR_PRODUCTION={'PASS' if overall else 'BLOCKED'}")
    print("DB_WRITE=0")
    print("LUNARCRUSH=0")
    print("EXECUTION=OFF")
    print("=" * 72)

    with open(
        "nostr_crypto_redundancy_probe_result_v0_2.json",
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            {
                "version": "NOSTR_CRYPTO_REDUNDANCY_PROBE_v0.2",
                "results": results,
                "crypto_relevance": (
                    "PASS"
                    if crypto_relevance_pass
                    else "FAIL"
                ),
                "crypto_relay_count": crypto_pass,
                "redundancy": (
                    "PASS"
                    if redundancy_pass
                    else "FAIL"
                ),
                "nostr_production": (
                    "PASS"
                    if overall
                    else "BLOCKED"
                ),
                "db_write": 0,
                "lunarcrush": 0,
                "execution": "OFF",
            },
            f,
            ensure_ascii=False,
            indent=2,
        )


if __name__ == "__main__":
    main()