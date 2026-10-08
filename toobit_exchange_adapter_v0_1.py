"""ARUNDA TRADER — TOOBIT EXCHANGE ADAPTER v0.1

Phase B / Toobit Binding.

This adapter is intentionally READ-ONLY at the current checkpoint.
It exposes the provider-native read surface required by the existing
CP46-C / CP46-D preflight contracts and contains NO order, cancel,
withdrawal, or database-write operation.

Transport is injected so the adapter boundary can be verified without
calling Toobit. A live transport may be supplied only at the later
authorized controlled-test gate.

Toobit's documented REST base is https://api.toobit.com.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional
from urllib.parse import urlencode

from exchange_execution_contract import CanonicalExecutionResult
from execution_instrument_contract_v0_1 import (
    ExecutionInstrumentSpecification,
    InstrumentResolutionStatus,
    resolve_provider_instrument,
)

BASE_URL = "https://api.toobit.com"
DEFAULT_RECV_WINDOW = 5000


@dataclass(frozen=True)
class ToobitAdapterResult:
    allowed: bool
    reason: str
    data: Optional[dict[str, Any]] = None


Transport = Callable[..., Mapping[str, Any] | list[Any]]


class ToobitExchangeAdapter:
    """Provider-specific, read-only Toobit adapter.

    The adapter never performs order submission/cancellation/withdrawal.
    HTTP is not performed unless a transport callable is explicitly
    injected by a later authorized runtime boundary.
    """

    name = "TOOBIT"

    @property
    def adapter_name(self) -> str:
        return self.name

    def capabilities(self):
        from exchange_execution_adapter_contract_v0_1 import ExchangeAdapterCapabilities
        return ExchangeAdapterCapabilities(
            venue_discovery=True,
            instrument_resolution=True,
            constraint_read=True,
            account_read=True,
            order_state_read=True,
            order_submission=False,
            order_cancellation=False,
        )

    def __init__(
        self,
        *,
        transport: Optional[Transport] = None,
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        recv_window: int = DEFAULT_RECV_WINDOW,
    ) -> None:
        self._transport = transport
        self._api_key = api_key or os.getenv("TOOBIT_API_KEY")
        self._secret_key = secret_key or os.getenv("TOOBIT_SECRET_KEY") or os.getenv("TOOBIT_API_SECRET")
        self._recv_window = int(recv_window)

    def _call(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        signed: bool = False,
    ) -> Any:
        if self._transport is None:
            raise RuntimeError("TOOBIT_TRANSPORT_NOT_CONFIGURED")

        payload = dict(params or {})
        headers: dict[str, str] = {}

        if signed:
            if not self._api_key or not self._secret_key:
                raise RuntimeError("TOOBIT_CREDENTIALS_UNAVAILABLE")
            payload["timestamp"] = int(time.time() * 1000)
            payload["recvWindow"] = self._recv_window
            query = urlencode(payload)
            signature = hmac.new(
                self._secret_key.encode("utf-8"),
                query.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            payload["signature"] = signature
            headers["X-BB-APIKEY"] = self._api_key

        return self._transport(
            method=method,
            path=path,
            params=payload,
            headers=headers,
            base_url=BASE_URL,
        )

    @staticmethod
    def _unwrap(response: Any) -> Any:
        if isinstance(response, dict) and "code" in response:
            code = response.get("code")
            if code not in (0, 200, "0", "200"):
                raise RuntimeError(
                    f"TOOBIT_PROVIDER_ERROR:{code}:{response.get('msg', '')}"
                )
            if "data" in response:
                return response["data"]
        return response

    @staticmethod
    def _find_asset(rows: Any, asset: str, *, futures: bool) -> dict[str, Any]:
        if not isinstance(rows, list):
            raise RuntimeError("TOOBIT_EXCHANGE_INFO_INVALID")

        target = asset.strip().upper()
        matches: list[dict[str, Any]] = []

        for row in rows:
            if not isinstance(row, dict):
                continue
            if futures:
                underlying = str(row.get("underlying", "")).strip().upper()
                if underlying == target:
                    matches.append(row)
            else:
                base = str(row.get("baseAsset", "")).strip().upper()
                quote = str(row.get("quoteAsset", "")).strip().upper()
                if base == target and quote == "USDT":
                    matches.append(row)

        if len(matches) != 1:
            raise RuntimeError(
                "AUTHORITATIVE_PROVIDER_SYMBOL_UNAVAILABLE:"
                f"{target}:matches={len(matches)}"
            )

        return matches[0]

    @staticmethod
    def _filters(row: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
        raw = row.get("filters")
        if not isinstance(raw, list):
            raise RuntimeError("TOOBIT_CONTRACT_FILTERS_INVALID")
        result: dict[str, dict[str, Any]] = {}
        for item in raw:
            if isinstance(item, dict) and isinstance(item.get("filterType"), str):
                result[item["filterType"]] = item
        return result

    def get_server_time(self) -> ToobitAdapterResult:
        try:
            data = self._unwrap(self._call("GET", "/api/v1/time"))
            if not isinstance(data, dict):
                raise RuntimeError("TOOBIT_SERVER_TIME_INVALID")
            raw = data.get("serverTime")
            timestamp = int(raw)
            if timestamp <= 0:
                raise RuntimeError("TOOBIT_SERVER_TIME_INVALID")
            return ToobitAdapterResult(True, "OK", {"serverTime": timestamp})
        except Exception as exc:
            return ToobitAdapterResult(False, str(exc))

    def _exchange_info(self) -> dict[str, Any]:
        data = self._unwrap(self._call("GET", "/api/v1/exchangeInfo"))
        if not isinstance(data, dict):
            raise RuntimeError("TOOBIT_EXCHANGE_INFO_INVALID")
        return data

    def discover_tradable_assets(self, *, venue: str) -> ToobitAdapterResult:
        """Return the current provider-reported tradable asset universe.

        Discovery is metadata-only. No static coin list is maintained here;
        Core remains asset-agnostic and exact instrument selection is handled
        separately by the execution instrument resolver.
        """
        try:
            normalized_venue = str(venue).strip().upper()
            if normalized_venue not in {"SPOT", "FUTURES"}:
                raise RuntimeError("EXECUTION_INSTRUMENT_VENUE_INVALID")

            info = self._exchange_info()
            assets: set[str] = set()
            rows_key = "symbols" if normalized_venue == "SPOT" else "contracts"
            rows = info.get(rows_key)
            if not isinstance(rows, list):
                raise RuntimeError("TOOBIT_EXCHANGE_INFO_INVALID")

            for row in rows:
                if not isinstance(row, dict):
                    continue
                if str(row.get("status", "")).strip().upper() != "TRADING":
                    continue
                if normalized_venue == "SPOT":
                    asset = str(row.get("baseAsset", "")).strip().upper()
                    quote = str(row.get("quoteAsset", "")).strip().upper()
                    if asset and quote == "USDT":
                        assets.add(asset)
                else:
                    asset = str(row.get("underlying", "")).strip().upper()
                    if asset:
                        assets.add(asset)

            return ToobitAdapterResult(
                True,
                "OK",
                {"venue": normalized_venue, "assets": sorted(assets)},
            )
        except Exception as exc:
            return ToobitAdapterResult(False, str(exc))

    def trading_constraints(self, asset: str) -> ToobitAdapterResult:
        try:
            row = self._find_asset(
                self._exchange_info().get("symbols"),
                asset,
                futures=False,
            )
            return ToobitAdapterResult(True, "OK", row)
        except Exception as exc:
            return ToobitAdapterResult(False, str(exc))

    def futures_trading_constraints(
        self,
        asset: str,
        *,
        execution_instrument: Optional[ExecutionInstrumentSpecification] = None,
    ) -> ToobitAdapterResult:
        try:
            if execution_instrument is not None:
                resolved = self.resolve_futures_instrument(
                    execution_instrument
                )
                if (
                    not resolved.allowed
                    or not isinstance(resolved.data, dict)
                ):
                    raise RuntimeError(
                        getattr(
                            resolved,
                            "reason",
                            "FUTURES_INSTRUMENT_UNAVAILABLE",
                        )
                    )

                symbol = str(
                    resolved.data["symbol"]
                ).strip().upper()

                contracts = self._exchange_info().get("contracts")
                if not isinstance(contracts, list):
                    raise RuntimeError("TOOBIT_EXCHANGE_INFO_INVALID")

                matches = [
                    row
                    for row in contracts
                    if (
                        isinstance(row, dict)
                        and str(row.get("symbol", "")).strip().upper()
                        == symbol
                    )
                ]

                if len(matches) != 1:
                    raise RuntimeError(
                        "AUTHORITATIVE_PROVIDER_SYMBOL_UNAVAILABLE:"
                        f"{asset}:symbol={symbol}:matches={len(matches)}"
                    )

                return ToobitAdapterResult(True, "OK", matches[0])

            row = self._find_asset(
                self._exchange_info().get("contracts"),
                asset,
                futures=True,
            )
            return ToobitAdapterResult(True, "OK", row)
        except Exception as exc:
            return ToobitAdapterResult(False, str(exc))

    def resolve_futures_instrument(
        self,
        specification: ExecutionInstrumentSpecification,
    ) -> ToobitAdapterResult:
        """Resolve a provider-neutral Futures instrument specification.

        Provider-specific metadata interpretation remains inside this adapter.
        The Core never sees or reconstructs the provider symbol.
        """
        try:
            if not isinstance(
                specification,
                ExecutionInstrumentSpecification,
            ):
                raise RuntimeError("EXECUTION_INSTRUMENT_SPEC_INVALID")

            if specification.venue.strip().upper() != "FUTURES":
                raise RuntimeError("EXECUTION_INSTRUMENT_VENUE_INVALID")

            contracts = self._exchange_info().get("contracts")
            if not isinstance(contracts, list):
                raise RuntimeError("TOOBIT_EXCHANGE_INFO_INVALID")

            candidates: list[dict[str, Any]] = []
            for row in contracts:
                if not isinstance(row, dict):
                    continue

                symbol = row.get("symbol")
                underlying = row.get("underlying")
                status = row.get("status")

                if not all(
                    isinstance(value, str) and value.strip()
                    for value in (symbol, underlying, status)
                ):
                    continue

                # Toobit exposes settlement/margin identity as provider
                # metadata. Never derive it from the provider symbol.
                settlement_asset = row.get("marginToken")
                if not isinstance(settlement_asset, str) or not settlement_asset.strip():
                    settlement_asset = row.get("quoteAsset")

                if not isinstance(settlement_asset, str) or not settlement_asset.strip():
                    continue

                # Toobit uses SWAP contracts for perpetual futures.
                # This provider-specific interpretation stays in the adapter.
                instrument_type = (
                    "PERPETUAL"
                    if "-SWAP" in symbol.upper()
                    else None
                )

                candidates.append(
                    {
                        "asset": underlying.strip().upper(),
                        "venue": "FUTURES",
                        "settlement_asset": settlement_asset.strip().upper(),
                        "instrument_type": instrument_type,
                        "provider_symbol": symbol.strip().upper(),
                        "status": status.strip().upper(),
                    }
                )

            resolved = resolve_provider_instrument(
                specification,
                candidates,
            )

            if resolved.status != InstrumentResolutionStatus.RESOLVED:
                return ToobitAdapterResult(
                    False,
                    resolved.reason,
                    {"candidate_count": len(candidates)},
                )

            return ToobitAdapterResult(
                True,
                "OK",
                {
                    "symbol": resolved.provider_symbol,
                    "instrument": dict(resolved.observation or {}),
                },
            )
        except Exception as exc:
            return ToobitAdapterResult(False, str(exc))

    def account_check(self) -> ToobitAdapterResult:
        try:
            data = self._unwrap(self._call("GET", "/api/v1/account", signed=True))
            if not isinstance(data, dict) or not isinstance(data.get("balances"), list):
                raise RuntimeError("TOOBIT_ACCOUNT_STATE_INVALID")
            return ToobitAdapterResult(True, "OK", {"state_known": True})
        except Exception as exc:
            return ToobitAdapterResult(False, str(exc))

    def futures_account_state(
        self,
        asset: str,
        *,
        execution_instrument: Optional[ExecutionInstrumentSpecification] = None,
    ) -> ToobitAdapterResult:
        try:
            if execution_instrument is not None:
                resolved = self.resolve_futures_instrument(
                    execution_instrument
                )
                if (
                    not resolved.allowed
                    or not isinstance(resolved.data, dict)
                ):
                    raise RuntimeError(
                        getattr(
                            resolved,
                            "reason",
                            "FUTURES_INSTRUMENT_UNAVAILABLE",
                        )
                    )
                symbol = str(
                    resolved.data["symbol"]
                ).strip().upper()
            else:
                constraints = self.futures_trading_constraints(asset)
                if (
                    not constraints.allowed
                    or not isinstance(constraints.data, dict)
                ):
                    raise RuntimeError(constraints.reason)
                symbol = str(
                    constraints.data["symbol"]
                ).strip().upper()

            balance = self._unwrap(
                self._call(
                    "GET",
                    "/api/v1/futures/balance",
                    signed=True,
                )
            )
            leverage = self._unwrap(
                self._call(
                    "GET",
                    "/api/v1/futures/accountLeverage",
                    params={
                        "symbol": symbol,
                        "category": "USDT",
                    },
                    signed=True,
                )
            )
            if not isinstance(balance, list):
                raise RuntimeError(
                    "TOOBIT_FUTURES_BALANCE_INVALID"
                )
            if not isinstance(leverage, list):
                raise RuntimeError(
                    "TOOBIT_FUTURES_LEVERAGE_STATE_INVALID"
                )
            leverage_rows = [
                row
                for row in leverage
                if (
                    isinstance(row, dict)
                    and str(
                        row.get("symbolId", "")
                    ).strip().upper()
                    == symbol
                )
            ]

            if len(leverage_rows) != 1:
                raise RuntimeError(
                    "TOOBIT_FUTURES_LEVERAGE_STATE_UNAVAILABLE"
                )

            margin_type = leverage_rows[0].get("marginType")
            if str(margin_type).strip().upper() not in {"CROSS", "ISOLATED"}:
                raise RuntimeError(
                    "TOOBIT_FUTURES_MARGIN_STATE_UNAVAILABLE"
                )

            positions = self._unwrap(
                self._call(
                    "GET",
                    "/api/v1/futures/positions",
                    params={
                        "symbol": symbol,
                        "category": "USDT",
                    },
                    signed=True,
                )
            )

            if not isinstance(positions, list):
                raise RuntimeError(
                    "TOOBIT_FUTURES_POSITION_STATE_INVALID"
                )

            for row in positions:
                if not isinstance(row, dict):
                    raise RuntimeError(
                        "TOOBIT_FUTURES_POSITION_STATE_INVALID"
                    )
                if (
                    str(row.get("symbol", ""))
                    .strip()
                    .upper()
                    != symbol
                ):
                    raise RuntimeError(
                        "TOOBIT_FUTURES_POSITION_SYMBOL_INVALID"
                    )
                if (
                    str(row.get("side", "")).upper()
                    not in {"LONG", "SHORT"}
                ):
                    raise RuntimeError(
                        "TOOBIT_FUTURES_POSITION_SIDE_INVALID"
                    )

            return ToobitAdapterResult(
                True,
                "OK",
                {
                    "state_known": True,
                    # Toobit accountLeverage returns the provider-native
                    # margin mode (CROSS/ISOLATED). Presence of that
                    # authoritative enum is the only basis for knowing
                    # margin state here; balance presence is not used.
                    "margin_state_known": True,
                    "margin_type": str(margin_type).strip().upper(),
                    "leverage_state_known": True,
                    "position_state_known": True,
                    "positions": positions,
                },
            )
        except Exception as exc:
            return ToobitAdapterResult(False, str(exc))

    def futures_duplicate_check(
        self,
        asset: str,
        *,
        execution_instrument: Optional[ExecutionInstrumentSpecification] = None,
    ) -> ToobitAdapterResult:
        try:
            if execution_instrument is not None:
                resolved = self.resolve_futures_instrument(
                    execution_instrument
                )
                if (
                    not resolved.allowed
                    or not isinstance(resolved.data, dict)
                ):
                    raise RuntimeError(
                        getattr(
                            resolved,
                            "reason",
                            "FUTURES_INSTRUMENT_UNAVAILABLE",
                        )
                    )
                symbol = str(
                    resolved.data["symbol"]
                ).strip().upper()
            else:
                constraints = self.futures_trading_constraints(asset)
                if (
                    not constraints.allowed
                    or not isinstance(constraints.data, dict)
                ):
                    raise RuntimeError(constraints.reason)
                symbol = str(
                    constraints.data["symbol"]
                ).strip().upper()

            open_orders = self._unwrap(
                self._call(
                    "GET",
                    "/api/v2/futures/open-orders",
                    params={
                        "symbol": symbol,
                        "category": "USDT",
                        "limit": 1000,
                    },
                    signed=True,
                )
            )
            recent_orders = self._unwrap(
                self._call(
                    "GET",
                    "/api/v1/futures/historyOrders",
                    params={
                        "symbol": symbol,
                        "category": "USDT",
                        "limit": 1000,
                    },
                    signed=True,
                )
            )

            return ToobitAdapterResult(
                True,
                "OK",
                {
                    "state_known": True,
                    "open_order_client_ids": frozenset(
                        str(row["clientOrderId"])
                        for row in open_orders
                        if (
                            isinstance(row, dict)
                            and row.get("clientOrderId") is not None
                        )
                    ),
                    "recent_order_client_ids": frozenset(
                        str(row["clientOrderId"])
                        for row in recent_orders
                        if (
                            isinstance(row, dict)
                            and row.get("clientOrderId") is not None
                        )
                    ),
                },
            )
        except Exception as exc:
            return ToobitAdapterResult(False, str(exc))


    def submit_order(self, request: Any) -> CanonicalExecutionResult:
        del request
        return CanonicalExecutionResult(
            accepted=False, exchange_order_id=None, status="FAIL_CLOSED",
            asset=None, direction=None, executed_quantity=None,
            executed_price=None, timestamp=None, adapter=self.name,
            error_code="EXECUTION_DISABLED_ORDER_SUBMISSION_NOT_IMPLEMENTED",
            error_message="Order submission is disabled by the current execution contract.",
        )

    def order_submission(self, *args: Any, **kwargs: Any) -> ToobitAdapterResult:
        del args, kwargs
        return ToobitAdapterResult(
            False,
            "EXECUTION_DISABLED_ORDER_SUBMISSION_NOT_IMPLEMENTED",
        )

    def cancel_order(self, *, asset: str, exchange_order_id: str) -> CanonicalExecutionResult:
        return CanonicalExecutionResult(
            accepted=False, exchange_order_id=exchange_order_id, status="FAIL_CLOSED",
            asset=asset, direction=None, executed_quantity=None,
            executed_price=None, timestamp=None, adapter=self.name,
            error_code="EXECUTION_DISABLED_ORDER_CANCELLATION_NOT_IMPLEMENTED",
            error_message="Order cancellation is disabled by the current execution contract.",
        )


__all__ = ["BASE_URL", "ToobitAdapterResult", "ToobitExchangeAdapter"]
