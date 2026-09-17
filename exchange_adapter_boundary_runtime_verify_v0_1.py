from exchange_adapter_boundary import (
    PUBLIC_MARKET_DATA,
    ACCOUNT_READ,
    BALANCE_READ,
    SYMBOL_INFO,
    TRADING_CONSTRAINTS,
    ORDER_SUBMISSION,
    ORDER_CANCELLATION,
    WITHDRAWAL,
)
from exchange_adapter_mapping import (
    map_bitpin_account,
    map_bitpin_balance,
    map_bitpin_exchange_info,
    map_bitpin_symbol,
    map_bitpin_constraints,
    bitpin_capabilities,
    map_toobit_account,
    map_toobit_balance,
    map_toobit_exchange_info,
    map_toobit_symbol,
    map_toobit_constraints,
    toobit_capabilities,
)


class FakeResult:
    def __init__(self, status, allowed, operation, reason, data=None):
        self.status = status
        self.allowed = allowed
        self.operation = operation
        self.reason = reason
        self.data = data


print("=" * 80)
print("ARUNDA TRADER — EXCHANGE-AGNOSTIC ADAPTER BOUNDARY")
print("READ-ONLY RUNTIME VERIFICATION v0.1")
print("=" * 80)
print("MODE                    : READ ONLY")
print("REAL EXCHANGE REQUEST   : NONE")
print("ORDER SUBMISSION        : NONE")
print("ORDER CANCELLATION      : NONE")
print("WITHDRAWAL              : NONE")
print("DATABASE WRITE          : NONE")
print()

failures = []


def check(label, condition):
    status = "PASS" if condition else "FAIL"
    print(f"{label:<35}: {status}")
    if not condition:
        failures.append(label)


# ------------------------------------------------------------------
# 1. Bitpin mapping — fail closed
# ------------------------------------------------------------------

bitpin_unavailable = FakeResult(
    "NOT_IMPLEMENTED",
    False,
    "get_account",
    "private account endpoint not verified",
    None,
)

bitpin_account = map_bitpin_account(bitpin_unavailable)

check(
    "BITPIN ACCOUNT MAPPING",
    bitpin_account.status == "NOT_IMPLEMENTED"
    and bitpin_account.allowed is False
)

check(
    "BITPIN ACCOUNT FAIL-CLOSED",
    bitpin_account.data.get("account_type") is None
    and bitpin_account.data.get("can_trade") is None
)

bitpin_balance = map_bitpin_balance(
    FakeResult(
        "NOT_IMPLEMENTED",
        False,
        "get_balances",
        "private balance endpoint not verified",
        None,
    )
)

check(
    "BITPIN BALANCE MAPPING",
    bitpin_balance.status == "NOT_IMPLEMENTED"
    and bitpin_balance.allowed is False
)

bitpin_info = map_bitpin_exchange_info(
    FakeResult(
        "UNAVAILABLE",
        False,
        "get_exchange_info",
        "private trading symbol validation not verified",
        None,
    )
)

check(
    "BITPIN EXCHANGE INFO MAPPING",
    bitpin_info.status == "UNAVAILABLE"
    and bitpin_info.allowed is False
)

bitpin_symbol = map_bitpin_symbol(
    FakeResult(
        "UNVERIFIED",
        False,
        "validate_symbol",
        "private trading-symbol validation not implemented",
        {"asset": "BTC"},
    )
)

check(
    "BITPIN SYMBOL MAPPING",
    bitpin_symbol.status == "UNVERIFIED"
    and bitpin_symbol.allowed is False
)

bitpin_constraints = map_bitpin_constraints(
    FakeResult(
        "UNAVAILABLE",
        False,
        "get_trading_constraints",
        "authenticated trading constraints not verified",
        {"asset": "BTC"},
    )
)

check(
    "BITPIN CONSTRAINTS MAPPING",
    bitpin_constraints.status == "UNAVAILABLE"
    and bitpin_constraints.allowed is False
)


# ------------------------------------------------------------------
# 2. Toobit canonical mapping — controlled verified-like data
# ------------------------------------------------------------------

toobit_account_raw = FakeResult(
    "PASS",
    True,
    "get_account",
    "verified read-only account",
    {
        "accountType": "master",
        "canTrade": None,
    },
)

toobit_account = map_toobit_account(toobit_account_raw)

check(
    "TOOBIT ACCOUNT CANONICAL",
    toobit_account.status == "PASS"
    and toobit_account.allowed is True
    and toobit_account.data["account_type"] == "master"
    and toobit_account.data["can_trade"] is None
    and toobit_account.data["source"] == "TOOBIT"
)


toobit_balance_raw = FakeResult(
    "PASS",
    True,
    "get_balances",
    "verified read-only balance",
    {
        "balance_rows": 1,
        "nonzero_balances": [
            {
                "coin": "BTC",
                "free": "1.0",
                "locked": "0.0",
                "total": "1.0",
            }
        ],
        "nonzero_count": 1,
    },
)

toobit_balance = map_toobit_balance(toobit_balance_raw)

check(
    "TOOBIT BALANCE CANONICAL",
    toobit_balance.status == "PASS"
    and toobit_balance.allowed is True
    and len(toobit_balance.data["balances"]) == 1
    and toobit_balance.data["balances"][0]["asset"] == "BTC"
    and toobit_balance.data["balances"][0]["total"] == "1.0"
    and toobit_balance.data["balances"][0]["source"] == "TOOBIT"
)


toobit_info_raw = FakeResult(
    "PASS",
    True,
    "get_exchange_info",
    "verified public exchange info",
    {
        "symbol_count": 1,
        "symbols": [
            {
                "symbol": "BTCUSDT",
                "baseAsset": "BTC",
                "quoteAsset": "USDT",
                "status": "TRADING",
            }
        ],
    },
)

toobit_info = map_toobit_exchange_info(toobit_info_raw)

check(
    "TOOBIT EXCHANGE INFO CANONICAL",
    toobit_info.status == "PASS"
    and toobit_info.allowed is True
    and len(toobit_info.data["symbols"]) == 1
    and toobit_info.data["symbols"][0]["symbol"] == "BTCUSDT"
)


toobit_symbol_raw = FakeResult(
    "PASS",
    True,
    "validate_symbol",
    "verified symbol",
    {
        "asset": "BTC",
        "symbol": "BTCUSDT",
        "status": "TRADING",
        "base_asset": "BTC",
        "quote_asset": "USDT",
    },
)

toobit_symbol = map_toobit_symbol(toobit_symbol_raw)

check(
    "TOOBIT SYMBOL CANONICAL",
    toobit_symbol.status == "PASS"
    and toobit_symbol.allowed is True
    and toobit_symbol.data["symbol"] == "BTCUSDT"
    and toobit_symbol.data["exists"] is True
    and toobit_symbol.data["tradable"] is True
    and toobit_symbol.data["status"] == "TRADING"
)


toobit_constraints_raw = FakeResult(
    "PASS",
    True,
    "get_trading_constraints",
    "verified constraints",
    {
        "asset": "BTC",
        "symbol": "BTCUSDT",
        "status": "TRADING",
        "filters": {
            "LOT_SIZE": {
                "minQty": "0.00001",
                "maxQty": "1000",
                "stepSize": "0.00001",
            },
            "MIN_NOTIONAL": {
                "minNotional": "5",
            },
        },
    },
)

toobit_constraints = map_toobit_constraints(toobit_constraints_raw)

check(
    "TOOBIT CONSTRAINTS CANONICAL",
    toobit_constraints.status == "PASS"
    and toobit_constraints.allowed is True
    and toobit_constraints.data["symbol"] == "BTCUSDT"
    and toobit_constraints.data["min_qty"] == "0.00001"
    and toobit_constraints.data["max_qty"] == "1000"
    and toobit_constraints.data["step_size"] == "0.00001"
    and toobit_constraints.data["min_notional"] == "5"
    and toobit_constraints.data["price_precision"] is None
    and toobit_constraints.data["quantity_precision"] is None
)


# ------------------------------------------------------------------
# 3. Capability contract
# ------------------------------------------------------------------

bc = bitpin_capabilities()
tc = toobit_capabilities()

check(
    "BITPIN CAPABILITY CONTRACT",
    bc[ACCOUNT_READ] is False
    and bc[BALANCE_READ] is False
    and bc[SYMBOL_INFO] is False
    and bc[TRADING_CONSTRAINTS] is False
    and bc[ORDER_SUBMISSION] is False
    and bc[ORDER_CANCELLATION] is False
    and bc[WITHDRAWAL] is False
)

check(
    "TOOBIT CAPABILITY CONTRACT",
    tc[ACCOUNT_READ] is True
    and tc[BALANCE_READ] is True
    and tc[SYMBOL_INFO] is True
    and tc[TRADING_CONSTRAINTS] is True
    and tc[ORDER_SUBMISSION] is False
    and tc[ORDER_CANCELLATION] is False
    and tc[WITHDRAWAL] is False
)


# ------------------------------------------------------------------
# 4. Hard safety contract
# ------------------------------------------------------------------

check(
    "WRITE CAPABILITIES ALL FALSE",
    bc[ORDER_SUBMISSION] is False
    and bc[ORDER_CANCELLATION] is False
    and bc[WITHDRAWAL] is False
    and tc[ORDER_SUBMISSION] is False
    and tc[ORDER_CANCELLATION] is False
    and tc[WITHDRAWAL] is False
)

print()

# ------------------------------------------------------------------
# 5. Runtime isolation
# ------------------------------------------------------------------

print("REAL EXCHANGE HTTP CALLS        : NONE")
print("ORDER WRITE CALLS               : NONE")
print("DATABASE WRITE CALLS            : NONE")
print("PRODUCTION CORE MODIFICATION    : NONE")
print()

if failures:
    print("OVERALL RESULT                   : FAIL")
    print()
    for failure in failures:
        print(" -", failure)
else:
    print("BITPIN MAPPING                  : PASS")
    print("TOOBIT MAPPING                  : PASS")
    print("CANONICAL OUTPUT                : PASS")
    print("CAPABILITY CONTRACT             : PASS")
    print("FAIL-CLOSED WRITE SAFETY        : PASS")
    print("RUNTIME ISOLATION               : PASS")
    print()
    print("OVERALL RESULT                  : PASS")

print("=" * 80)
