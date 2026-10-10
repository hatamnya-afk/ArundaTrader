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
from decimal import Decimal, InvalidOperation
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional
from urllib.parse import urlencode

from exchange_execution_adapter_contract_v0_1 import AdapterOrderPreparation
from exchange_execution_contract import CanonicalExecutionResult, CanonicalOrderRequest, validate_order_request
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




def _format_provider_quantity(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text

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
            # Capability means an implemented provider path exists; the separate
            # execution/write gates still deny all real submission by default.
            order_submission=True,
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

            # A successful HTTP response is not proof that duplicate state is
            # known. Reject malformed collections or rows instead of silently
            # dropping them and returning an incomplete client-ID set.
            if not isinstance(open_orders, list) or not isinstance(recent_orders, list):
                raise RuntimeError("TOOBIT_FUTURES_ORDER_STATE_INVALID")

            def _client_ids(rows: list[Any]) -> frozenset[str]:
                identifiers: set[str] = set()
                for row in rows:
                    if not isinstance(row, dict):
                        raise RuntimeError("TOOBIT_FUTURES_ORDER_STATE_INVALID")
                    raw_id = row.get("clientOrderId", row.get("newClientOrderId"))
                    if not isinstance(raw_id, str) or not raw_id.strip():
                        raise RuntimeError("TOOBIT_FUTURES_ORDER_CLIENT_ID_UNAVAILABLE")
                    identifiers.add(raw_id.strip())
                return frozenset(identifiers)

            open_client_ids = _client_ids(open_orders)
            recent_client_ids = _client_ids(recent_orders)

            return ToobitAdapterResult(
                True,
                "OK",
                {
                    "state_known": True,
                    "open_order_client_ids": open_client_ids,
                    "recent_order_client_ids": recent_client_ids,
                },
            )
        except Exception as exc:
            return ToobitAdapterResult(False, str(exc))


    def prepare_order(
        self,
        request: Any,
        *,
        venue: str,
        execution_instrument: Any,
    ) -> AdapterOrderPreparation:
        """Translate a canonical request into an opaque Toobit order payload.

        This method is preparation only. It may read authoritative exchange
        metadata through the injected transport, but it never submits an order.
        Canonical quantity remains BASE_ASSET; provider-specific quantity
        semantics are translated here and never in Core.
        """
        normalized_venue = str(venue).strip().upper()
        adapter_name = self.adapter_name

        valid, reason = validate_order_request(request)
        if not valid:
            return AdapterOrderPreparation(
                ready=False,
                reason=reason,
                adapter_name=adapter_name,
                venue=normalized_venue,
            )

        if normalized_venue not in {"SPOT", "FUTURES"}:
            return AdapterOrderPreparation(
                ready=False,
                reason="VENUE_INVALID",
                adapter_name=adapter_name,
                venue=normalized_venue,
            )

        if not isinstance(
            execution_instrument,
            ExecutionInstrumentSpecification,
        ):
            return AdapterOrderPreparation(
                ready=False,
                reason="EXECUTION_INSTRUMENT_SPEC_INVALID",
                adapter_name=adapter_name,
                venue=normalized_venue,
            )

        if (
            execution_instrument.asset.strip().upper() != request.asset.strip().upper()
            or execution_instrument.venue.strip().upper() != normalized_venue
        ):
            return AdapterOrderPreparation(
                ready=False,
                reason="EXECUTION_INSTRUMENT_REQUEST_MISMATCH",
                adapter_name=adapter_name,
                venue=normalized_venue,
            )

        try:
            if normalized_venue == "FUTURES":
                resolved = self.resolve_futures_instrument(
                    execution_instrument
                )
                if not resolved.allowed or not isinstance(resolved.data, dict):
                    raise RuntimeError(resolved.reason)

                row = self.futures_trading_constraints(
                    request.asset,
                    execution_instrument=execution_instrument,
                )
                if not row.allowed or not isinstance(row.data, dict):
                    raise RuntimeError(row.reason)

                symbol = str(resolved.data["symbol"]).strip().upper()
                contract_row = row.data
                filters = self._filters(contract_row)

                base_quantity = Decimal(str(request.quantity))
                multiplier = Decimal(
                    str(contract_row.get("contractMultiplier", ""))
                )
                if base_quantity <= 0 or multiplier <= 0:
                    raise RuntimeError("FUTURES_QUANTITY_INVALID")

                provider_quantity = base_quantity / multiplier
                if provider_quantity != provider_quantity.to_integral_value():
                    raise RuntimeError(
                        "FUTURES_BASE_QUANTITY_NOT_CONTRACT_ALIGNED"
                    )

                lot = filters.get("LOT_SIZE") or filters.get("MARKET_LOT_SIZE")
                if isinstance(lot, dict):
                    minimum = Decimal(str(lot.get("minQty", "0")))
                    maximum = Decimal(str(lot.get("maxQty", "0")))
                    step = Decimal(str(lot.get("stepSize", "0")))
                    if minimum > 0 and provider_quantity < minimum:
                        raise RuntimeError("FUTURES_QUANTITY_BELOW_MIN")
                    if maximum > 0 and provider_quantity > maximum:
                        raise RuntimeError("FUTURES_QUANTITY_ABOVE_MAX")
                    if step > 0 and (
                        provider_quantity / step
                    ) != (
                        provider_quantity / step
                    ).to_integral_value():
                        raise RuntimeError("FUTURES_QUANTITY_STEP_INVALID")

                # This adapter currently binds to Toobit's v1 futures endpoint,
                # whose side is a combined open/close enum. This request opens a
                # position; closing semantics require a separate approved contract.
                # Toobit v1 Futures represents a market order as type=LIMIT
                # plus priceType=MARKET; type=MARKET is not valid on this endpoint.
                payload = {
                    "symbol": symbol,
                    "side": "BUY_OPEN" if request.direction == "LONG" else "SELL_OPEN",
                    "type": "LIMIT" if request.order_type == "MARKET" else request.order_type,
                    "priceType": "MARKET" if request.order_type == "MARKET" else "INPUT",
                    "newClientOrderId": request.intent_id,
                    "quantity": _format_provider_quantity(provider_quantity),
                }

                return AdapterOrderPreparation(
                    ready=True,
                    reason="READY",
                    adapter_name=adapter_name,
                    venue=normalized_venue,
                    request=payload,
                )

            row = self.trading_constraints(request.asset)
            if not row.allowed or not isinstance(row.data, dict):
                raise RuntimeError(row.reason)

            if str(row.data.get("status", "")).strip().upper() != "TRADING":
                raise RuntimeError("SPOT_INSTRUMENT_NOT_TRADING")

            symbol = (
                str(row.data.get("symbol", "")).strip().upper()
            )
            if not symbol:
                raise RuntimeError("SPOT_PROVIDER_SYMBOL_UNAVAILABLE")

            filters = self._filters(row.data)
            base_quantity = Decimal(str(request.quantity))
            if base_quantity <= 0:
                raise RuntimeError("SPOT_QUANTITY_INVALID")

            provider_quantity = base_quantity
            is_market_buy = (
                request.order_type == "MARKET"
                and request.direction == "LONG"
            )
            if is_market_buy:
                if request.reference_price is None:
                    raise RuntimeError(
                        "SPOT_MARKET_BUY_REFERENCE_PRICE_REQUIRED"
                    )
                reference_price = Decimal(str(request.reference_price))
                if not reference_price.is_finite() or reference_price <= 0:
                    raise RuntimeError(
                        "SPOT_MARKET_BUY_REFERENCE_PRICE_INVALID"
                    )
                # Toobit Spot v1 requires quote-asset amount for MARKET BUY.
                # Validate LOT_SIZE against canonical base quantity, not quote amount.
                provider_quantity = base_quantity * reference_price

            lot = filters.get("LOT_SIZE") or filters.get("MARKET_LOT_SIZE")
            if isinstance(lot, dict):
                minimum = Decimal(str(lot.get("minQty", "0")))
                maximum = Decimal(str(lot.get("maxQty", "0")))
                step = Decimal(str(lot.get("stepSize", "0")))
                filter_quantity = base_quantity if is_market_buy else provider_quantity
                if minimum > 0 and filter_quantity < minimum:
                    raise RuntimeError("SPOT_QUANTITY_BELOW_MIN")
                if maximum > 0 and filter_quantity > maximum:
                    raise RuntimeError("SPOT_QUANTITY_ABOVE_MAX")
                if step > 0 and (
                    filter_quantity / step
                ) != (
                    filter_quantity / step
                ).to_integral_value():
                    raise RuntimeError("SPOT_QUANTITY_STEP_INVALID")

            if is_market_buy:
                for filter_name in ("MIN_NOTIONAL", "NOTIONAL"):
                    notional_filter = filters.get(filter_name)
                    if not isinstance(notional_filter, dict):
                        continue
                    raw_minimum = notional_filter.get(
                        "minNotional",
                        notional_filter.get("minNotionalValue", "0"),
                    )
                    minimum_notional = Decimal(str(raw_minimum))
                    if minimum_notional > 0 and provider_quantity < minimum_notional:
                        raise RuntimeError("SPOT_NOTIONAL_BELOW_MIN")

            payload = {
                "symbol": symbol,
                "side": "BUY" if request.direction == "LONG" else "SELL",
                "type": request.order_type,
                "newClientOrderId": request.intent_id,
                "quantity": _format_provider_quantity(provider_quantity),
            }

            return AdapterOrderPreparation(
                ready=True,
                reason="READY",
                adapter_name=adapter_name,
                venue=normalized_venue,
                request=payload,
            )
        except (InvalidOperation, ValueError, TypeError) as exc:
            return AdapterOrderPreparation(
                ready=False,
                reason=f"ORDER_PREPARATION_INVALID:{exc}",
                adapter_name=adapter_name,
                venue=normalized_venue,
            )
        except Exception as exc:
            return AdapterOrderPreparation(
                ready=False,
                reason=str(exc),
                adapter_name=adapter_name,
                venue=normalized_venue,
            )

    def query_order_by_client_id(
        self,
        *,
        venue: str,
        symbol: str,
        client_order_id: str,
    ) -> ToobitAdapterResult:
        """Read provider order state by client ID; never submits or retries an order."""
        normalized_venue = str(venue).strip().upper()
        normalized_symbol = str(symbol).strip().upper()
        client_id = str(client_order_id).strip()
        if normalized_venue not in {"SPOT", "FUTURES"}:
            return ToobitAdapterResult(False, "VENUE_INVALID")
        if not normalized_symbol or not client_id:
            return ToobitAdapterResult(False, "ORDER_RECONCILIATION_IDENTITY_INVALID")
        params = {"symbol": normalized_symbol, "origClientOrderId": client_id}
        if normalized_venue == "FUTURES":
            params["category"] = "USDT"
        try:
            path = "/api/v1/spot/order" if normalized_venue == "SPOT" else "/api/v1/futures/order"
            response = self._unwrap(self._call("GET", path, params=params, signed=True))
            if not isinstance(response, dict):
                return ToobitAdapterResult(False, "PROVIDER_ORDER_RESPONSE_INVALID")
            observed_client_id = response.get("clientOrderId", response.get("newClientOrderId"))
            if str(observed_client_id or "") != client_id:
                return ToobitAdapterResult(False, "PROVIDER_ORDER_IDENTITY_UNCONFIRMED")
            if str(response.get("symbol", "")).strip().upper() != normalized_symbol:
                return ToobitAdapterResult(False, "PROVIDER_ORDER_SYMBOL_MISMATCH")
            if response.get("orderId") in (None, "") or not str(response.get("status", "")).strip():
                return ToobitAdapterResult(False, "PROVIDER_ORDER_STATE_INCOMPLETE")
            return ToobitAdapterResult(True, "PROVIDER_ORDER_STATE_CONFIRMED", response)
        except Exception as exc:
            return ToobitAdapterResult(False, f"ORDER_RECONCILIATION_FAILED:{exc}")

    def submit_prepared_order(
        self,
        preparation: AdapterOrderPreparation,
        *,
        canonical_request: CanonicalOrderRequest,
    ) -> CanonicalExecutionResult:
        """Submit one prepared order only when every independent write gate is open.

        No retries are performed. Any transport ambiguity is reported as
        UNKNOWN so callers must reconcile by client order ID before any retry.
        """
        import exchange_execution_contract as execution_contract

        valid, reason = validate_order_request(canonical_request)
        if not valid:
            return CanonicalExecutionResult(
                accepted=False, exchange_order_id=None, status="FAIL_CLOSED",
                asset=canonical_request.asset, direction=canonical_request.direction,
                executed_quantity=None, executed_price=None, timestamp=None,
                adapter=self.name, error_code=reason,
                error_message="Canonical order request rejected.",
                decision_id=canonical_request.decision_id,
            )

        if not isinstance(preparation, AdapterOrderPreparation) or not preparation.ready:
            return CanonicalExecutionResult(
                accepted=False, exchange_order_id=None, status="FAIL_CLOSED",
                asset=canonical_request.asset, direction=canonical_request.direction,
                executed_quantity=None, executed_price=None, timestamp=None,
                adapter=self.name, error_code="ORDER_PREPARATION_NOT_READY",
                error_message="Provider order preparation is not ready.",
                decision_id=canonical_request.decision_id,
            )
        if preparation.adapter_name != self.adapter_name or not isinstance(preparation.request, dict):
            return CanonicalExecutionResult(
                accepted=False, exchange_order_id=None, status="FAIL_CLOSED",
                asset=canonical_request.asset, direction=canonical_request.direction,
                executed_quantity=None, executed_price=None, timestamp=None,
                adapter=self.name, error_code="ORDER_PREPARATION_ADAPTER_MISMATCH",
                error_message="Prepared order does not belong to this adapter.",
                decision_id=canonical_request.decision_id,
            )
        payload = dict(preparation.request)
        if payload.get("newClientOrderId") != canonical_request.intent_id:
            return CanonicalExecutionResult(
                accepted=False, exchange_order_id=None, status="FAIL_CLOSED",
                asset=canonical_request.asset, direction=canonical_request.direction,
                executed_quantity=None, executed_price=None, timestamp=None,
                adapter=self.name, error_code="CLIENT_ORDER_ID_MISMATCH",
                error_message="Prepared client order identity does not match canonical intent.",
                decision_id=canonical_request.decision_id,
            )
        if preparation.venue not in {"SPOT", "FUTURES"}:
            return CanonicalExecutionResult(
                accepted=False, exchange_order_id=None, status="FAIL_CLOSED",
                asset=canonical_request.asset, direction=canonical_request.direction,
                executed_quantity=None, executed_price=None, timestamp=None,
                adapter=self.name, error_code="VENUE_INVALID",
                error_message="Prepared venue is invalid.",
                decision_id=canonical_request.decision_id,
            )

        gates = (
            execution_contract.EXECUTION_ENABLED,
            execution_contract.ORDER_SUBMISSION_ENABLED,
            execution_contract.EXCHANGE_WRITE_ENABLED,
        )
        if not all(gate is True for gate in gates):
            return CanonicalExecutionResult(
                accepted=False, exchange_order_id=None, status="FAIL_CLOSED",
                asset=canonical_request.asset, direction=canonical_request.direction,
                executed_quantity=None, executed_price=None, timestamp=None,
                adapter=self.name, error_code="EXECUTION_WRITE_GATES_CLOSED",
                error_message="Execution, order-submission, and exchange-write gates must all be explicitly enabled.",
                decision_id=canonical_request.decision_id,
            )
        if self._transport is None:
            return CanonicalExecutionResult(
                accepted=False, exchange_order_id=None, status="FAIL_CLOSED",
                asset=canonical_request.asset, direction=canonical_request.direction,
                executed_quantity=None, executed_price=None, timestamp=None,
                adapter=self.name, error_code="TOOBIT_TRANSPORT_NOT_CONFIGURED",
                error_message="No Toobit transport is configured.",
                decision_id=canonical_request.decision_id,
            )

        endpoint = "/api/v1/spot/order" if preparation.venue == "SPOT" else "/api/v1/futures/order"
        submission_error = None
        try:
            response = self._unwrap(self._call("POST", endpoint, params=payload, signed=True))
        except Exception as exc:
            # The POST is never retried. Perform exactly one read-only lookup
            # using the same provider symbol and client ID before declaring
            # the result unresolved.
            submission_error = str(exc)
            response = None

        if not isinstance(response, dict):
            if response is not None:
                submission_error = "Provider response is not an order object."
            reconciled = self.query_order_by_client_id(
                venue=preparation.venue,
                symbol=str(payload.get("symbol", "")),
                client_order_id=canonical_request.intent_id,
            )
            if reconciled.allowed and isinstance(reconciled.data, dict):
                response = reconciled.data
            else:
                detail = submission_error or "Provider response is not an order object."
                return CanonicalExecutionResult(
                    accepted=False, exchange_order_id=None, status="UNKNOWN",
                    asset=canonical_request.asset, direction=canonical_request.direction,
                    executed_quantity=None, executed_price=None, timestamp=None,
                    adapter=self.name,
                    error_code="PROVIDER_SUBMISSION_OUTCOME_UNKNOWN",
                    error_message=f"{detail}; reconciliation={reconciled.reason}",
                    decision_id=canonical_request.decision_id,
                    fill_outcome="UNKNOWN", fill_reason_code="RECONCILIATION_REQUIRED",
                )

        client_id = response.get("clientOrderId", response.get("newClientOrderId"))
        order_id = response.get("orderId")
        status = str(response.get("status", "")).strip().upper()
        if str(client_id or "") != canonical_request.intent_id or order_id in (None, "") or not status:
            return CanonicalExecutionResult(
                accepted=False, exchange_order_id=str(order_id) if order_id not in (None, "") else None,
                status="UNKNOWN", asset=canonical_request.asset, direction=canonical_request.direction,
                executed_quantity=None, executed_price=None, timestamp=None,
                adapter=self.name, error_code="PROVIDER_ORDER_IDENTITY_UNCONFIRMED",
                error_message="Provider response lacks matching client identity, order ID, or status.",
                decision_id=canonical_request.decision_id,
                fill_outcome="UNKNOWN", fill_reason_code="RECONCILIATION_REQUIRED",
            )

        try:
            raw_executed = response.get("executedQty")
            if raw_executed in (None, ""):
                raw_executed = response.get("executeQty", "0")
            executed = Decimal(str(raw_executed))

            # Some provider order payloads include avgPrice="0" alongside a
            # valid execution price. Select the first positive authoritative
            # price field rather than treating a present zero as final.
            price = None
            for raw_price in (
                response.get("avgPrice"),
                response.get("price"),
                response.get("dealPrice"),
            ):
                if raw_price in (None, ""):
                    continue
                candidate_price = Decimal(str(raw_price))
                if not candidate_price.is_finite() or candidate_price < 0:
                    raise InvalidOperation("invalid execution price")
                if candidate_price > 0:
                    price = candidate_price
                    break

            if not executed.is_finite() or executed < 0:
                raise InvalidOperation("invalid execution quantity")
        except (InvalidOperation, ValueError, TypeError):
            return CanonicalExecutionResult(
                accepted=False, exchange_order_id=str(order_id), status="UNKNOWN",
                asset=canonical_request.asset, direction=canonical_request.direction,
                executed_quantity=None, executed_price=None, timestamp=None,
                adapter=self.name, error_code="PROVIDER_EXECUTION_FIELDS_INVALID",
                error_message="Provider execution fields are invalid.",
                decision_id=canonical_request.decision_id,
                fill_outcome="UNKNOWN", fill_reason_code="RECONCILIATION_REQUIRED",
            )

        terminal_filled = status == "FILLED" and executed > 0 and price is not None
        fill_outcome = "FILLED" if terminal_filled else ("NOT_FILLED" if status in {"CANCELED", "REJECTED", "EXPIRED"} and executed == 0 else "UNKNOWN")
        fill_reason = "PROVIDER_CONFIRMED_FILLED" if terminal_filled else ("PROVIDER_TERMINAL_NO_FILL" if fill_outcome == "NOT_FILLED" else "PROVIDER_FILL_NOT_CONFIRMED")
        return CanonicalExecutionResult(
            accepted=status not in {"REJECTED", "ERROR"},
            exchange_order_id=str(order_id), status=status,
            asset=canonical_request.asset, direction=canonical_request.direction,
            executed_quantity=str(executed) if executed > 0 else None,
            executed_price=str(price) if price is not None and executed > 0 else None,
            timestamp=str(response.get("transactTime", response.get("time", response.get("updateTime", "")))) or None,
            adapter=self.name, error_code=None if status not in {"REJECTED", "ERROR"} else "PROVIDER_REJECTED_ORDER",
            error_message=None if status not in {"REJECTED", "ERROR"} else "Provider rejected the order.",
            decision_id=canonical_request.decision_id,
            fill_outcome=fill_outcome, fill_reason_code=fill_reason,
        )

    def submit_order(self, request: Any) -> CanonicalExecutionResult:
        return CanonicalExecutionResult(
            accepted=False, exchange_order_id=None, status="FAIL_CLOSED",
            asset=getattr(request, "asset", None), direction=getattr(request, "direction", None),
            executed_quantity=None, executed_price=None, timestamp=None,
            adapter=self.name, error_code="ORDER_PREPARATION_REQUIRED",
            error_message="Provider submission requires an explicit venue and resolved execution instrument.",
            decision_id=getattr(request, "decision_id", None),
        )

    def order_submission(self, *args: Any, **kwargs: Any) -> ToobitAdapterResult:
        del args, kwargs
        import exchange_execution_contract as execution_contract
        if not all((
            execution_contract.EXECUTION_ENABLED is True,
            execution_contract.ORDER_SUBMISSION_ENABLED is True,
            execution_contract.EXCHANGE_WRITE_ENABLED is True,
        )):
            return ToobitAdapterResult(False, "EXECUTION_WRITE_GATES_CLOSED")
        return ToobitAdapterResult(False, "PREPARED_ORDER_REQUIRED")

    def cancel_order(self, *, asset: str, exchange_order_id: str) -> CanonicalExecutionResult:
        return CanonicalExecutionResult(
            accepted=False, exchange_order_id=exchange_order_id, status="FAIL_CLOSED",
            asset=asset, direction=None, executed_quantity=None,
            executed_price=None, timestamp=None, adapter=self.name,
            error_code="EXECUTION_DISABLED_ORDER_CANCELLATION_NOT_IMPLEMENTED",
            error_message="Order cancellation is disabled by the current execution contract.",
        )


__all__ = ["BASE_URL", "ToobitAdapterResult", "ToobitExchangeAdapter"]
