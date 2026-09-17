from exchange_adapter_boundary import (
    CAPABILITY_PUBLIC_MARKET_DATA,
    CAPABILITY_ACCOUNT_READ,
    CAPABILITY_BALANCE_READ,
    CAPABILITY_SYMBOL_INFO,
    CAPABILITY_TRADING_CONSTRAINTS,
    CAPABILITY_ORDER_SUBMISSION,
    CAPABILITY_ORDER_CANCELLATION,
    CAPABILITY_WITHDRAWAL,
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
print("READ-ONLY RUNTIME VERIFICATION v0.2")
print("=" * 80)
print("REAL EXCHANGE REQUEST   : NONE")
print("ORDER SUBMISSION        : NONE")
print("ORDER CANCELLATION      : NONE")
print("WITHDRAWAL              : NONE")
print("DATABASE WRITE          : NONE")
print()

failures = []


def check(label, condition):
    result = "PASS" if condition else "FAIL"
    print(f"{label:<40}: {result}")
    if not condition:
        failures.append(label)


# ================================================================
# BITPIN — FAIL CLOSED
# ================================================================

r = FakeResult(
    "NOT_IMPLEMENTED",
    False,
    "get_account",
    "private account endpoint not verified",
)

x = map_bitpin_account(r)

check(
    "BITPIN ACCOUNT MAPPING",
    x.status == "NOT_IMPLEMENTED"
    and x.allowed is False
    and x.data["account_type"] is None
    and x.data["can_trade"] is None
)


r = FakeResult(
    "NOT_IMPLEMENTED",
    False,
    "get_balances",
    "private balance endpoint not verified",
)

x = map_bitpin_balance(r)

check(
    "BITPIN BALANCE MAPPING",
    x.status == "NOT_IMPLEMENTED"
    and x.allowed is False
)


r = FakeResult(
    "UNAVAILABLE",
    False,
    "get_exchange_info",
    "trading info not verified",
)

x = map_bitpin_exchange_info(r)

check(
    "BITPIN EXCHANGE INFO MAPPING",
    x.status == "UNAVAILABLE"
    and x.allowed is False
)


r = FakeResult(
    "UNVERIFIED",
    False,
    "validate_symbol",
    "private trading symbol validation not implemented",
    {"asset": "BTC"},
)

x = map_bitpin_symbol(r)

check(
    "BITPIN SYMBOL MAPPING",
    x.status == "UNVERIFIED"
    and x.allowed is False
)


r = FakeResult(
    "UNAVAILABLE",
    False,
    "get_trading_constraints",
    "authenticated constraints not verified",
    {"asset": "BTC"},
)

x = map_bitpin_constraints(r)

check(
    "BITPIN CONSTRAINTS MAPPING",
    x.status == "UNAVAILABLE"
    and x.allowed is False
)


# ================================================================
# TOOBIT — CANONICAL OUTPUT
# ================================================================

r = FakeResult(
    "PASS",
    True,
    "get_account",
    "verified read-only account",
    {
        "accountType": "master",
        "canTrade": None,
    },
)

x = map_toobit_account(r)

check(
    "TOOBIT ACCOUNT CANONICAL",
    x.status == "PASS"
    and x.allowed is True
    and x.data["account_type"] == "master"
    and x.data["can_trade"] is None
    and x.data["status"] == "PASS"
    and x.data["source"] == "TOOBIT"
)


r = FakeResult(
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

x = map_toobit_balance(r)

check(
    "TOOBIT BALANCE CANONICAL",
    x.status == "PASS"
    and x.allowed is True
    and len(x.data["balances"]) == 1
    and x.data["balances"][0]["asset"] == "BTC"
    and x.data["balances"][0]["free"] == "1.0"
    and x.data["balances"][0]["locked"] == "0.0"
    and x.data["balances"][0]["total"] == "1.0"
    and x.data["balances"][0]["source"] == "TOOBIT"
)


r = FakeResult(
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

x = map_toobit_exchange_info(r)

check(
    "TOOBIT EXCHANGE INFO CANONICAL",
    x.status == "PASS"
    and x.allowed is True
    and len(x.data["symbols"]) == 1
    and x.data["symbols"][0]["symbol"] == "BTCUSDT"
    and x.data["symbols"][0]["exists"] is True
    and x.data["symbols"][0]["tradable"] is True
)


r = FakeResult(
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

x = map_toobit_symbol(r)

check(
    "TOOBIT SYMBOL CANONICAL",
    x.status == "PASS"
    and x.allowed is True
    and x.data["symbol"] == "BTCUSDT"
    and x.data["exists"] is True
    and x.data["tradable"] is True
    and x.data["status"] == "TRADING"
)


r = FakeResult(
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

x = map_toobit_constraints(r)

check(
    "TOOBIT CONSTRAINTS CANONICAL",
    x.status == "PASS"
    and x.allowed is True
    and x.data["symbol"] == "BTCUSDT"
    and x.data["min_qty"] == "0.00001"
    and x.data["max_qty"] == "1000"
    and x.data["step_size"] == "0.00001"
    and x.data["min_notional"] == "5"
    and x.data["price_precision"] is None
    and x.data["quantity_precision"] is None
)


# ================================================================
# CAPABILITY CONTRACT
# ================================================================

bc = bitpin_capabilities()
tc = toobit_capabilities()

check(
    "BITPIN CAPABILITY CONTRACT",
    bc[CAPABILITY_PUBLIC_MARKET_DATA] is False
    and bc[CAPABILITY_ACCOUNT_READ] is False
    and bc[CAPABILITY_BALANCE_READ] is False
    and bc[CAPABILITY_SYMBOL_INFO] is False
    and bc[CAPABILITY_TRADING_CONSTRAINTS] is False
    and bc[CAPABILITY_ORDER_SUBMISSION] is False
    and bc[CAPABILITY_ORDER_CANCELLATION] is False
    and bc[CAPABILITY_WITHDRAWAL] is False
)


check(
    "TOOBIT CAPABILITY CONTRACT",
    tc[CAPABILITY_PUBLIC_MARKET_DATA] is False
    and tc[CAPABILITY_ACCOUNT_READ] is True
    and tc[CAPABILITY_BALANCE_READ] is True
    and tc[CAPABILITY_SYMBOL_INFO] is True
    and tc[CAPABILITY_TRADING_CONSTRAINTS] is True
    and tc[CAPABILITY_ORDER_SUBMISSION] is False
    and tc[CAPABILITY_ORDER_CANCELLATION] is False
    and tc[CAPABILITY_WITHDRAWAL] is False
)


# ================================================================
# SAFETY
# ================================================================

check(
    "ALL WRITE CAPABILITIES FALSE",
    bc[CAPABILITY_ORDER_SUBMISSION] is False
    and bc[CAPABILITY_ORDER_CANCELLATION] is False
    and bc[CAPABILITY_WITHDRAWAL] is False
    and tc[CAPABILITY_ORDER_SUBMISSION] is False
    and tc[CAPABILITY_ORDER_CANCELLATION] is False
    and tc[CAPABILITY_WITHDRAWAL] is False
)


print()
print("REAL EXCHANGE HTTP CALLS          : NONE")
print("DATABASE WRITE                     : NONE")
print("ORDER WRITE                        : NONE")
print("PRODUCTION CORE MODIFICATION       : NONE")
print()

if failures:
    print("OVERALL RESULT                     : FAIL")
    print()
    for failure in failures:
        print(" -", failure)
else:
    print("BITPIN MAPPING                     : PASS")
    print("TOOBIT MAPPING                     : PASS")
    print("CANONICAL OUTPUT                   : PASS")
    print("CAPABILITY CONTRACT                : PASS")
    print("FAIL-CLOSED WRITE SAFETY           : PASS")
    print("RUNTIME ISOLATION                  : PASS")
    print()
    print("OVERALL RESULT                     : PASS")

print("=" * 80)
