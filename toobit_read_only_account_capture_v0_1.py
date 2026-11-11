"""Bounded read-only Toobit account evidence capture.

This script is intentionally independent of the trading pipeline and database.
It has a GET-only transport allowlist and never submits/cancels orders or changes
account settings. Raw responses are sensitive; keep the output directory private.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4

BASE_URL = "https://api.toobit.com"
RECV_WINDOW = 5000
PAGE_SIZE = 1000
MAX_PAGES = 100
RECENT_DAYS = 3

# Exact allowlist: every route used here is a documented GET/read endpoint.
PUBLIC_GETS = {"/api/v1/time", "/api/v1/exchangeInfo"}
SIGNED_GETS = {
    "/api/v1/account",
    "/api/v1/spot/openOrders",
    "/api/v1/spot/tradeOrders",
    "/api/v1/futures/balance",
    "/api/v1/futures/positions",
    "/api/v1/futures/openOrders",
    "/api/v1/futures/historyOrders",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def decimal_value(value: object, field: str, *, nonnegative: bool = True) -> Decimal:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise RuntimeError(f"INVALID_NUMERIC_FIELD:{field}") from exc
    if not number.is_finite() or (nonnegative and number < 0):
        raise RuntimeError(f"INVALID_NUMERIC_FIELD:{field}")
    return number


def _decode_response(response: object) -> object:
    if isinstance(response, dict) and "code" in response:
        code = response.get("code")
        if code not in (0, 200, "0", "200"):
            raise RuntimeError(f"PROVIDER_ERROR_CODE:{code}")
        if "data" in response:
            return response["data"]
    return response


class ReadOnlyToobitClient:
    """Minimal signed GET client. No non-GET method or non-allowlisted route exists."""

    def __init__(self, api_key: str, secret: str) -> None:
        self._api_key = api_key
        self._secret = secret.encode("utf-8")

    def get(self, path: str, params: dict[str, object] | None = None, *, signed: bool = True) -> object:
        allowlist = SIGNED_GETS if signed else PUBLIC_GETS
        if path not in allowlist:
            raise RuntimeError("ENDPOINT_NOT_ALLOWLISTED")
        query_params = dict(params or {})
        headers = {"Accept": "application/json", "User-Agent": "ArundaTrader-read-only-evidence/0.1"}
        if signed:
            query_params["timestamp"] = int(time.time() * 1000)
            query_params["recvWindow"] = RECV_WINDOW
            query = urlencode(query_params)
            signature = hmac.new(self._secret, query.encode("utf-8"), hashlib.sha256).hexdigest()
            query = f"{query}&signature={signature}"
            headers["X-BB-APIKEY"] = self._api_key
        else:
            query = urlencode(query_params)
        request = Request(f"{BASE_URL}{path}" + (f"?{query}" if query else ""), headers=headers, method="GET")
        try:
            with urlopen(request, timeout=15) as response:
                if response.status != 200:
                    raise RuntimeError(f"HTTP_STATUS:{response.status}")
                raw = response.read()
        except HTTPError as exc:
            # Do not echo request URLs, signatures, headers, or response bodies.
            raise RuntimeError(f"HTTP_ERROR:{exc.code}") from None
        except (URLError, TimeoutError, OSError) as exc:
            raise RuntimeError(f"TRANSPORT_ERROR:{type(exc).__name__}") from None
        try:
            return _decode_response(json.loads(raw.decode("utf-8")))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError("INVALID_JSON_RESPONSE") from exc


def require_list(payload: object, label: str) -> list[dict[str, object]]:
    if not isinstance(payload, list):
        raise RuntimeError(f"{label}_RESPONSE_NOT_LIST")
    rows: list[dict[str, object]] = []
    for row in payload:
        if not isinstance(row, dict):
            raise RuntimeError(f"{label}_ROW_INVALID")
        rows.append(row)
    return rows


def validate_spot_balances(payload: object) -> list[dict[str, object]]:
    if not isinstance(payload, dict) or not isinstance(payload.get("balances"), list):
        raise RuntimeError("SPOT_BALANCE_RESPONSE_INVALID")
    rows = require_list(payload["balances"], "SPOT_BALANCE")
    seen: set[str] = set()
    for row in rows:
        coin = str(row.get("coin", "")).strip().upper()
        if not coin or coin in seen:
            raise RuntimeError("SPOT_BALANCE_ASSET_MISSING_OR_DUPLICATE")
        seen.add(coin)
        for field in ("total", "free", "locked"):
            decimal_value(row.get(field), f"spot.{coin}.{field}")
    return rows


def validate_futures_balances(payload: object, category: str) -> list[dict[str, object]]:
    rows = require_list(payload, f"FUTURES_{category}_BALANCE")
    seen: set[str] = set()
    for row in rows:
        coin = str(row.get("coin", "")).strip().upper()
        if not coin or coin in seen:
            raise RuntimeError(f"FUTURES_{category}_BALANCE_ASSET_MISSING_OR_DUPLICATE")
        seen.add(coin)
        for field in ("balance", "availableBalance"):
            if field in row:
                decimal_value(row[field], f"futures.{category}.{coin}.{field}")
    return rows


def fetch_order_pages(
    client: ReadOnlyToobitClient, path: str, base_params: dict[str, object], label: str
) -> list[dict[str, object]]:
    cursor: int | None = None
    seen_ids: set[int] = set()
    collected: list[dict[str, object]] = []
    for _ in range(MAX_PAGES):
        params = dict(base_params)
        params["limit"] = PAGE_SIZE
        if cursor is not None:
            params["orderId"] = cursor
        rows = require_list(client.get(path, params), label)
        ids: list[int] = []
        for row in rows:
            raw_id = row.get("orderId")
            try:
                order_id = int(str(raw_id))
            except (ValueError, TypeError):
                raise RuntimeError(f"{label}_ORDER_ID_INVALID") from None
            if order_id <= 0 or order_id in seen_ids:
                raise RuntimeError(f"{label}_ORDER_ID_INVALID_OR_DUPLICATE")
            if cursor is not None and order_id >= cursor:
                raise RuntimeError(f"{label}_CURSOR_DID_NOT_ADVANCE")
            ids.append(order_id)
        seen_ids.update(ids)
        collected.extend(rows)
        if len(rows) < PAGE_SIZE:
            return collected
        next_cursor = min(ids)
        if cursor is not None and next_cursor >= cursor:
            raise RuntimeError(f"{label}_CURSOR_DID_NOT_ADVANCE")
        cursor = next_cursor
    raise RuntimeError(f"{label}_PAGE_LIMIT_EXCEEDED")


def capture(client: ReadOnlyToobitClient) -> dict[str, object]:
    cycle_id = str(uuid4())
    started = utc_now()
    result: dict[str, object] = {
        "schema": "arundatrader.toobit.read_only_evidence.v1",
        "cycle_id": cycle_id,
        "capture_started_utc": started,
        "venue": "TOOBIT",
        "mode": "READ_ONLY_GET_ONLY",
        "collections": {},
        "status": "BLOCKED",
        "blockers": [],
    }
    collections = result["collections"]
    assert isinstance(collections, dict)
    blockers: list[str] = result["blockers"]  # type: ignore[assignment]

    def run(name: str, fn) -> None:
        observed = utc_now()
        try:
            payload = fn()
            collections[name] = {
                "status": "VERIFIED",
                "retrieved_at_utc": observed,
                "payload": payload,
            }
        except Exception as exc:
            reason = str(exc)
            collections[name] = {
                "status": "BLOCKED",
                "retrieved_at_utc": observed,
                "error_code": reason[:120],
            }
            blockers.append(f"{name}:{reason[:120]}")

    run("server_time", lambda: client.get("/api/v1/time", signed=False))
    run("exchange_info", lambda: client.get("/api/v1/exchangeInfo", signed=False))

    def spot_account():
        payload = client.get("/api/v1/account")
        return {"balances": validate_spot_balances(payload)}

    run("spot_account", spot_account)
    for category in ("USDT", "USDC"):
        run(
            f"futures_{category.lower()}_balances",
            lambda category=category: {
                "category": category,
                "balances": validate_futures_balances(
                    client.get("/api/v1/futures/balance", {"category": category}), category
                ),
            },
        )
        def positions(category=category):
            rows = require_list(
                client.get("/api/v1/futures/positions", {"category": category}),
                f"FUTURES_{category}_POSITIONS",
            )
            for row in rows:
                if not str(row.get("symbol", "")).strip():
                    raise RuntimeError(f"FUTURES_{category}_POSITION_SYMBOL_MISSING")
                if str(row.get("side", "")).strip().upper() not in {"LONG", "SHORT"}:
                    raise RuntimeError(f"FUTURES_{category}_POSITION_SIDE_INVALID")
            return {"category": category, "positions": rows}
        run(f"futures_{category.lower()}_positions", positions)
        run(
            f"futures_{category.lower()}_open_orders",
            lambda category=category: {
                "category": category,
                "orders": fetch_order_pages(
                    client, "/api/v1/futures/openOrders", {"category": category},
                    f"FUTURES_{category}_OPEN_ORDERS",
                ),
            },
        )
        run(
            f"futures_{category.lower()}_recent_orders",
            lambda category=category: {
                "category": category,
                "window_days": RECENT_DAYS,
                "orders": fetch_order_pages(
                    client, "/api/v1/futures/historyOrders",
                    {
                        "category": category,
                        "startTime": int(time.time() * 1000) - RECENT_DAYS * 86400 * 1000,
                        "endTime": int(time.time() * 1000),
                    },
                    f"FUTURES_{category}_RECENT_ORDERS",
                ),
            },
        )

    run(
        "spot_open_orders",
        lambda: {
            "orders": fetch_order_pages(
                client, "/api/v1/spot/openOrders", {},
                "SPOT_OPEN_ORDERS",
            )
        },
    )
    start_ms = int(time.time() * 1000) - RECENT_DAYS * 86400 * 1000
    end_ms = int(time.time() * 1000)
    run(
        "spot_recent_orders",
        lambda: {
            "window_days": RECENT_DAYS,
            "orders": fetch_order_pages(
                client, "/api/v1/spot/tradeOrders",
                {"startTime": start_ms, "endTime": end_ms},
                "SPOT_RECENT_ORDERS",
            ),
        },
    )

    result["capture_finished_utc"] = utc_now()
    result["blockers"] = blockers
    result["status"] = "VERIFIED" if not blockers else "BLOCKED"
    result["raw_payload_sha256"] = hashlib.sha256(
        json.dumps(collections, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()
    return result


def default_output_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if not base:
        base = str(Path.home() / ".local" / "share")
    return Path(base) / "ArundaTrader" / "private_evidence"


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture Toobit account evidence using GET-only endpoints.")
    parser.add_argument("--output-dir", type=Path, default=default_output_dir())
    args = parser.parse_args()

    api_key = os.environ.get("TOOBIT_API_KEY", "").strip()
    secret = (os.environ.get("TOOBIT_SECRET_KEY") or os.environ.get("TOOBIT_API_SECRET") or "").strip()
    if not api_key or not secret:
        print("BLOCKED: TOOBIT_CREDENTIALS_UNAVAILABLE (configure environment variables locally; do not paste secrets)", file=sys.stderr)
        return 2

    output_dir = args.output_dir.expanduser().resolve()
    repo_root = Path(__file__).resolve().parent
    try:
        output_dir.relative_to(repo_root)
    except ValueError:
        pass
    else:
        print("BLOCKED: raw evidence output must be outside the repository", file=sys.stderr)
        return 2

    output_dir.mkdir(parents=True, exist_ok=True)
    report = capture(ReadOnlyToobitClient(api_key, secret))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_file = output_dir / f"toobit_read_only_capture_{stamp}_{report['cycle_id'][:8]}.json"
    encoded = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8")
    with output_file.open("xb") as handle:
        handle.write(encoded)
    # Console output is deliberately redacted: no balances, order rows, keys, signatures or raw responses.
    collections = report["collections"]
    statuses = {name: item["status"] for name, item in collections.items()}  # type: ignore[union-attr]
    print(json.dumps({
        "status": report["status"],
        "cycle_id": report["cycle_id"],
        "capture_started_utc": report["capture_started_utc"],
        "capture_finished_utc": report["capture_finished_utc"],
        "collections": statuses,
        "blocker_count": len(report["blockers"]),  # type: ignore[arg-type]
        "raw_artifact": str(output_file),
        "sha256": hashlib.sha256(encoded).hexdigest(),
        "warning": "Raw account evidence is sensitive; keep this local file private.",
    }, indent=2))
    return 0 if report["status"] == "VERIFIED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
