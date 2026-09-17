import json
import time

try:
    import websocket
except ImportError:
    print("ERROR: websocket-client نصب نیست")
    print("RUN: python -m pip install websocket-client")
    raise SystemExit(1)


RELAYS = [
    "wss://relay.damus.io",
    "wss://nos.lol",
    "wss://relay.primal.net",
    "wss://nostr.wine",
]

TIMEOUT = 8
QUERY_TERMS = ["bitcoin", "ethereum", "solana", "xrp"]


def probe(relay):
    ws = None
    started = time.perf_counter()

    try:
        ws = websocket.create_connection(
            relay,
            timeout=TIMEOUT,
            origin="https://arundatrader.local",
        )

        sub_id = "ARUNDA01"

        # kind=1 = short-form social notes
        req = [
            "REQ",
            sub_id,
            {
                "kinds": [1],
                "limit": 5,
            },
        ]

        ws.send(json.dumps(req))

        events = []
        eose = False

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

            if not isinstance(msg, list) or not msg:
                continue

            if msg[0] == "EVENT" and len(msg) >= 3:
                event = msg[2]

                if isinstance(event, dict):
                    events.append({
                        "id": event.get("id"),
                        "pubkey": event.get("pubkey"),
                        "created_at": event.get("created_at"),
                        "kind": event.get("kind"),
                        "content": event.get("content", "")[:300],
                    })

            elif msg[0] == "EOSE":
                eose = True
                break

        elapsed = round(time.perf_counter() - started, 3)

        return {
            "relay": relay,
            "status": "PASS" if events else "NO_DATA",
            "events": len(events),
            "eose": eose,
            "latency": elapsed,
            "samples": events[:3],
        }

    except Exception as e:
        elapsed = round(time.perf_counter() - started, 3)

        return {
            "relay": relay,
            "status": "FAIL",
            "events": 0,
            "eose": False,
            "latency": elapsed,
            "error": type(e).__name__,
        }

    finally:
        if ws:
            try:
                ws.close()
            except Exception:
                pass


def main():
    print("=" * 68)
    print("ARUNDA NOSTR REAL-EVENT PROBE v0.1")
    print("=" * 68)

    results = []

    for relay in RELAYS:
        result = probe(relay)
        results.append(result)

        status = result["status"]

        print(
            f"{status:8} | "
            f"{relay} | "
            f"EVENTS={result['events']} | "
            f"EOSE={result['eose']} | "
            f"{result['latency']}s"
        )

        if result.get("samples"):
            sample = result["samples"][0]
            print(
                f"         EVENT kind={sample['kind']} "
                f"content={sample['content'][:120]!r}"
            )

        if result.get("error"):
            print(f"         ERROR={result['error']}")

    passed = sum(r["status"] == "PASS" for r in results)

    print("-" * 68)
    print(f"REAL_EVENT_PASS={passed}/{len(RELAYS)}")
    print(f"REAL_EVENT_RUNTIME={'PASS' if passed >= 2 else 'FAIL'}")
    print("DB_WRITE=0")
    print("LUNARCRUSH=0")
    print("EXECUTION=OFF")
    print("=" * 68)

    with open(
        "nostr_real_event_probe_result_v0_1.json",
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            {
                "version": "NOSTR_REAL_EVENT_PROBE_v0.1",
                "results": results,
                "real_event_pass": passed,
                "runtime": "PASS" if passed >= 2 else "FAIL",
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