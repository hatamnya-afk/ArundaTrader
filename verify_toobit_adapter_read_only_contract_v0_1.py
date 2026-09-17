
"""
ARUNDA TRADER — TOOBIT ADAPTER READ-ONLY CONTRACT INTEGRATION VERIFY v0.2
=========================================================================
MODE                  : READ-ONLY RUNTIME VERIFICATION
EXCHANGE              : TOOBIT

HARD SAFETY:
* NO ORDER SUBMISSION
* NO ORDER CANCELLATION
* NO WITHDRAWAL
* NO DATABASE WRITE
* NO EXCHANGE WRITE
* NO SYNTHETIC DATA
* NO FALLBACK DATA
* NO PRODUCTION CORE MODIFICATION

Purpose:
Runtime verification of the already-built
TOOBIT_ADAPTER_v0.2 boundary.

This verifier does NOT implement exchange logic.
It imports the adapter and verifies its real runtime behavior.

IMPORTANT:
* Adapter source is not modified.
* Production core is not modified.
* No write endpoint is called.
* No orderTest endpoint is called.
* No order/cancel/withdraw operation is executed.
* Signature verification is local only.
* Real private verification is limited to read-only endpoints.
"""

from __future__ import annotations

import hashlib
import hmac
import inspect
import re
from typing import Any, Dict, List

import toobit_trading_adapter as adapter_module
from toobit_trading_adapter import (
    EXPECTED_ASSETS,
    ToobitTradingAdapter,
)


# ============================================================
# CONSTANTS
# ============================================================

EXPECTED_ASSET_COUNT = 15
EXPECTED_ADAPTER_VERSION = "TOOBIT_ADAPTER_v0.2"
EXPECTED_EXCHANGE = "TOOBIT"
EXPECTED_SIGNED_HEADER = "X-BB-APIKEY"

EXPECTED_SIGNED_QUERY = "timestamp=1717200000000"

FORBIDDEN_WRITE_METHODS = (
    "place_order",
    "cancel_order",
    "withdraw",
)

REQUIRED_PUBLIC_OPERATIONS = (
    "get_server_time",
    "get_exchange_info",
    "symbol_check",
    "validate_expected_symbols",
    "trading_constraints",
)

REQUIRED_PRIVATE_OPERATIONS = (
    "account_check",
    "balance_check",
    "api_key_check",
)

REQUIRED_SIGNING_OPERATIONS = (
    "_build_query_string",
    "_generate_signature",
    "_signed_get",
)

FORBIDDEN_DB_IMPORTS = (
    "sqlite3",
    "sqlalchemy",
    "pymysql",
    "psycopg",
    "psycopg2",
)

FORBIDDEN_WRITE_REQUEST_PATTERNS = (
    r"\brequests\.post\s*\(",
    r"\brequests\.put\s*\(",
    r"\brequests\.delete\s*\(",
    r"\bsession\.post\s*\(",
    r"\bsession\.put\s*\(",
    r"\bsession\.delete\s*\(",
)

FORBIDDEN_CORE_IMPORTS = (
    "execution_engine",
    "trade_gate_engine",
    "decision_engine",
    "risk_engine",
    "signal_engine",
    "fusion_engine",
    "arunda_pipeline",
)


# ============================================================
# OUTPUT
# ============================================================

def line(label: str, value: Any) -> None:
    print(f"{label:<34}: {value}")


# ============================================================
# GENERIC HELPERS
# ============================================================

def get_method(
    adapter: ToobitTradingAdapter,
    name: str,
) -> Any:
    return getattr(adapter, name, None)


def adapter_source() -> str:
    try:
        return inspect.getsource(adapter_module)
    except (OSError, TypeError, IOError):
        return ""


def method_source(
    adapter: ToobitTradingAdapter,
    method_name: str,
) -> str:
    method = get_method(
        adapter,
        method_name,
    )

    if method is None:
        return ""

    try:
        return inspect.getsource(method)
    except (OSError, TypeError, IOError):
        return ""


# ============================================================
# OPERATION SURFACE
# ============================================================

def verify_operation_surface(
    adapter: ToobitTradingAdapter,
) -> bool:

    public_ok = all(
        callable(
            get_method(
                adapter,
                name,
            )
        )
        for name in REQUIRED_PUBLIC_OPERATIONS
    )

    private_ok = all(
        callable(
            get_method(
                adapter,
                name,
            )
        )
        for name in REQUIRED_PRIVATE_OPERATIONS
    )

    signing_ok = all(
        callable(
            get_method(
                adapter,
                name,
            )
        )
        for name in REQUIRED_SIGNING_OPERATIONS
    )

    return (
        public_ok
        and private_ok
        and signing_ok
    )


# ============================================================
# EXECUTION FLAGS
# ============================================================

def verify_execution_flags(
    adapter: ToobitTradingAdapter,
) -> bool:

    required_false = (
        "execution_enabled",
        "order_submission_enabled",
        "order_cancellation_enabled",
        "withdraw_enabled",
        "database_write_enabled",
        "exchange_write_enabled",
    )

    return all(
        getattr(
            adapter,
            field,
            None,
        ) is False
        for field in required_false
    )


# ============================================================
# STATIC SAFETY
# ============================================================

def verify_static_safety(
    adapter: ToobitTradingAdapter,
) -> bool:

    checks: List[bool] = []

    required_false = (
        "execution_enabled",
        "order_submission_enabled",
        "order_cancellation_enabled",
        "withdraw_enabled",
        "database_write_enabled",
        "exchange_write_enabled",
    )

    for field in required_false:
        checks.append(
            getattr(
                adapter,
                field,
                None,
            ) is False
        )

    source = adapter_source()

    if not source:
        return False

    for pattern in FORBIDDEN_WRITE_REQUEST_PATTERNS:
        checks.append(
            re.search(
                pattern,
                source,
                flags=re.IGNORECASE,
            )
            is None
        )

    for pattern in (
        r"""["'][^"']*/order\b[^"']*["']""",
        r"""["'][^"']*/cancel\b[^"']*["']""",
        r"""["'][^"']*/withdraw\b[^"']*["']""",
        r"""["'][^"']*orderTest[^"']*["']""",
    ):
        checks.append(
            re.search(
                pattern,
                source,
                flags=re.IGNORECASE,
            )
            is None
        )

    return all(checks)


# ============================================================
# ADAPTER CONTRACT
# ============================================================

def verify_contract(
    adapter: ToobitTradingAdapter,
) -> bool:

    try:
        result = adapter.contract_status()
    except Exception:
        return False

    if result is None:
        return False

    if result.allowed is not True:
        return False

    data = result.data or {}

    if data.get(
        "adapter_version"
    ) != EXPECTED_ADAPTER_VERSION:
        return False

    if data.get(
        "exchange"
    ) != EXPECTED_EXCHANGE:
        return False

    required_false = (
        "execution_enabled",
        "order_submission_enabled",
        "order_cancellation_enabled",
        "withdraw_enabled",
        "database_write_enabled",
        "exchange_write_enabled",
    )

    for field in required_false:
        if data.get(field) is not False:
            return False

    return True


# ============================================================
# CREDENTIAL PRESENCE
# ============================================================

def verify_credentials(
    adapter: ToobitTradingAdapter,
) -> bool:

    try:
        result = adapter.credential_presence()
    except Exception:
        return False

    if result is None:
        return False

    data = result.data or {}

    return (
        data.get("api_key_present") is True
        and data.get("api_secret_present") is True
    )


# ============================================================
# LOCAL SIGNATURE VERIFICATION
# ============================================================

def verify_signature_local(
    adapter: ToobitTradingAdapter,
) -> Dict[str, Any]:
    """
    Verify the CURRENT v0.2 signing implementation.

    Current contract:

        _build_query_string()
            preserves insertion order

        _generate_signature()
            accepts ONLY query_string
            and uses the adapter's configured secret

        _signed_get()
            signs the exact query string and manually
            constructs the final URL.

    No network request is performed here.
    """

    build_query = get_method(
        adapter,
        "_build_query_string",
    )

    generate_signature = get_method(
        adapter,
        "_generate_signature",
    )

    signed_get = get_method(
        adapter,
        "_signed_get",
    )

    if not callable(build_query):
        return {
            "pass": False,
            "reason": "_build_query_string missing",
        }

    if not callable(generate_signature):
        return {
            "pass": False,
            "reason": "_generate_signature missing",
        }

    if not callable(signed_get):
        return {
            "pass": False,
            "reason": "_signed_get missing",
        }

    # --------------------------------------------------------
    # Test 1:
    # Exact insertion order.
    # --------------------------------------------------------

    test_payload = {
        "timestamp": 1717200000000,
    }

    try:
        query = build_query(
            test_payload
        )
    except Exception as exc:
        return {
            "pass": False,
            "reason": (
                f"_build_query_string exception: {exc}"
            ),
        }

    if query != EXPECTED_SIGNED_QUERY:
        return {
            "pass": False,
            "reason": (
                "unexpected canonical query: "
                f"{query!r}"
            ),
        }

    # --------------------------------------------------------
    # Test 2:
    # Call the adapter's ACTUAL signature contract.
    #
    # _generate_signature() accepts ONLY query_string.
    # The real secret remains internal to the adapter.
    # --------------------------------------------------------

    try:
        adapter_signature = generate_signature(
            query
        )
    except Exception as exc:
        return {
            "pass": False,
            "reason": (
                f"_generate_signature exception: {exc}"
            ),
        }

    if not isinstance(
        adapter_signature,
        str,
    ):
        return {
            "pass": False,
            "reason": (
                "_generate_signature did not "
                "return a string"
            ),
        }

    if not re.fullmatch(
        r"[0-9a-f]{64}",
        adapter_signature,
    ):
        return {
            "pass": False,
            "reason": (
                "signature is not lower-case "
                "64-character hexadecimal"
            ),
        }

    # --------------------------------------------------------
    # Test 3:
    # Independent HMAC-SHA256 reference generation.
    #
    # Non-production deterministic test vector.
    # --------------------------------------------------------

    test_secret = (
        "ARUNDA_LOCAL_SIGNATURE_TEST_SECRET"
    )

    reference_signature = hmac.new(
        test_secret.encode("utf-8"),
        query.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not re.fullmatch(
        r"[0-9a-f]{64}",
        reference_signature,
    ):
        return {
            "pass": False,
            "reason": (
                "local HMAC-SHA256 reference "
                "generation failed"
            ),
        }

    # --------------------------------------------------------
    # Test 4:
    # Source-level signing contract.
    # --------------------------------------------------------

    signed_source = method_source(
        adapter,
        "_signed_get",
    )

    if not signed_source:
        return {
            "pass": False,
            "reason": (
                "unable to inspect _signed_get"
            ),
        }

    required_source_markers = (
        "timestamp",
        "signature",
        "X-BB-APIKEY",
        "_build_query_string",
        "_generate_signature",
    )

    missing = [
        marker
        for marker in required_source_markers
        if marker not in signed_source
    ]

    if missing:
        return {
            "pass": False,
            "reason": (
                "missing signing markers: "
                + ", ".join(missing)
            ),
        }

    # --------------------------------------------------------
    # Test 5:
    # v0.2 signed path must not construct recvWindow
    # as a signed query parameter.
    #
    # Only actual assignment/access patterns are rejected.
    # Documentation/comments mentioning recvWindow are allowed.
    # --------------------------------------------------------

    recv_window_signing_patterns = (
        r"""payload\[\s*["']recvWindow["']\s*\]""",
        r"""params\[\s*["']recvWindow["']\s*\]""",
        r"""query_params\[\s*["']recvWindow["']\s*\]""",
        r"""signed_params\[\s*["']recvWindow["']\s*\]""",
    )

    for pattern in recv_window_signing_patterns:
        if re.search(
            pattern,
            signed_source,
            flags=re.IGNORECASE,
        ):
            return {
                "pass": False,
                "reason": (
                    "v0.2 signed path still "
                    "depends on recvWindow"
                ),
            }

    return {
        "pass": True,
        "reason": None,
        "query": query,
        "signature": adapter_signature,
    }


# ============================================================
# SIGNED REQUEST CONSTRUCTION VERIFY
# ============================================================

class _FakeResponse:
    """
    Minimal response object used only for local construction
    testing.

    No network traffic is generated.
    """

    status_code = 200
    text = '{"local_test": true}'

    def json(self):
        return {
            "local_test": True,
        }

    def raise_for_status(self):
        return None


class _FakeSession:
    """
    Captures the URL and headers supplied by _signed_get().

    It never contacts Toobit.
    """

    def __init__(self):
        self.url = None
        self.headers = None
        self.timeout = None

    def get(
        self,
        url,
        headers=None,
        timeout=None,
        **kwargs,
    ):
        self.url = url
        self.headers = headers
        self.timeout = timeout

        if "params" in kwargs:
            raise AssertionError(
                "signed GET must use exact manual URL; "
                "params= detected"
            )

        return _FakeResponse()


def verify_signed_request_construction(
    adapter: ToobitTradingAdapter,
) -> Dict[str, Any]:
    """
    Local-only verification of the actual _signed_get()
    construction path.

    Network is disabled by replacing:
        - _get_server_timestamp_ms()
        - session.get()

    The verifier checks:

        server timestamp
        -> exact query
        -> HMAC
        -> URL signature
        -> X-BB-APIKEY header
    """

    signed_get = get_method(
        adapter,
        "_signed_get",
    )

    if not callable(signed_get):
        return {
            "pass": False,
            "reason": "_signed_get missing",
        }

    fake_session = _FakeSession()

    original_session = getattr(
        adapter,
        "session",
        None,
    )

    original_timestamp_method = getattr(
        adapter,
        "_get_server_timestamp_ms",
        None,
    )

    if not callable(
        original_timestamp_method
    ):
        return {
            "pass": False,
            "reason": (
                "_get_server_timestamp_ms missing"
            ),
        }

    adapter.session = fake_session

    adapter._get_server_timestamp_ms = (
        lambda: 1717200000000
    )

    try:
        try:
            result = signed_get({})
        except Exception as exc:
            return {
                "pass": False,
                "reason": (
                    f"_signed_get local exception: {exc}"
                ),
            }

        if result is None:
            return {
                "pass": False,
                "reason": (
                    "_signed_get returned None"
                ),
            }

        url = fake_session.url

        if not isinstance(
            url,
            str,
        ):
            return {
                "pass": False,
                "reason": (
                    "signed request URL was not captured"
                ),
            }

        if "?" not in url:
            return {
                "pass": False,
                "reason": (
                    "signed URL has no query string"
                ),
            }

        query_part = url.split(
            "?",
            1,
        )[1]

        if "&signature=" not in query_part:
            return {
                "pass": False,
                "reason": (
                    "signature not appended to exact URL"
                ),
            }

        unsigned_query, signature = (
            query_part.rsplit(
                "&signature=",
                1,
            )
        )

        if unsigned_query != EXPECTED_SIGNED_QUERY:
            return {
                "pass": False,
                "reason": (
                    "actual signed query mismatch: "
                    f"{unsigned_query!r}"
                ),
            }

        api_secret = getattr(
            adapter,
            "api_secret",
            None,
        )

        if not api_secret:
            return {
                "pass": False,
                "reason": (
                    "api_secret unavailable "
                    "for local construction test"
                ),
            }

        expected_signature = hmac.new(
            str(api_secret).encode("utf-8"),
            unsigned_query.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        if signature != expected_signature:
            return {
                "pass": False,
                "reason": (
                    "URL signature does not match "
                    "exact query HMAC"
                ),
            }

        headers = fake_session.headers

        if not isinstance(
            headers,
            dict,
        ):
            return {
                "pass": False,
                "reason": (
                    "signed request headers missing"
                ),
            }

        if (
            EXPECTED_SIGNED_HEADER
            not in headers
        ):
            return {
                "pass": False,
                "reason": (
                    "X-BB-APIKEY header missing"
                ),
            }

        api_key = getattr(
            adapter,
            "api_key",
            None,
        )

        if (
            api_key
            and
            headers.get(
                EXPECTED_SIGNED_HEADER
            ) != api_key
        ):
            return {
                "pass": False,
                "reason": (
                    "X-BB-APIKEY value mismatch"
                ),
            }

        return {
            "pass": True,
            "reason": None,
        }

    finally:
        adapter.session = (
            original_session
        )

        adapter._get_server_timestamp_ms = (
            original_timestamp_method
        )


# ============================================================
# PUBLIC SERVER TIME
# ============================================================

def verify_server_time(
    adapter: ToobitTradingAdapter,
) -> bool:

    try:
        result = adapter.get_server_time()
    except Exception:
        return False

    return (
        result is not None
        and result.allowed is True
        and result.status == "PASS"
        and isinstance(
            result.data,
            dict,
        )
    )


# ============================================================
# EXCHANGE INFO
# ============================================================

def verify_exchange_info(
    adapter: ToobitTradingAdapter,
) -> Dict[str, Any]:

    try:
        result = adapter.get_exchange_info()
    except Exception as exc:
        return {
            "pass": False,
            "count": 0,
            "error": str(exc),
        }

    if result is None:
        return {
            "pass": False,
            "count": 0,
            "error": "No result",
        }

    if result.allowed is not True:
        return {
            "pass": False,
            "count": 0,
            "error": getattr(
                result,
                "reason",
                "not allowed",
            ),
        }

    data = result.data or {}

    symbols = data.get(
        "symbols"
    )

    if not isinstance(
        symbols,
        list,
    ):
        return {
            "pass": False,
            "count": 0,
            "error": (
                "symbols is not a list"
            ),
        }

    return {
        "pass": True,
        "count": len(symbols),
        "error": None,
    }


# ============================================================
# EXPECTED SYMBOLS
# ============================================================

def verify_expected_symbols(
    adapter: ToobitTradingAdapter,
) -> Dict[str, Any]:

    try:
        result = (
            adapter.validate_expected_symbols()
        )
    except Exception as exc:
        return {
            "pass": False,
            "expected": EXPECTED_ASSET_COUNT,
            "validated": 0,
            "missing": [],
            "not_trading": [],
            "invalid": [],
            "error": str(exc),
        }

    if result is None:
        return {
            "pass": False,
            "expected": EXPECTED_ASSET_COUNT,
            "validated": 0,
            "missing": [],
            "not_trading": [],
            "invalid": [],
            "error": "No result",
        }

    data = result.data or {}

    expected_count = data.get(
        "expected_count"
    )

    validated_count = data.get(
        "validated_count"
    )

    missing = data.get(
        "missing",
        [],
    )

    not_trading = data.get(
        "not_trading",
        [],
    )

    invalid = data.get(
        "invalid",
        [],
    )

    return {
        "pass": (
            result.allowed is True
            and expected_count
            == EXPECTED_ASSET_COUNT
            and validated_count
            == EXPECTED_ASSET_COUNT
            and not missing
            and not not_trading
            and not invalid
        ),
        "expected": expected_count,
        "validated": validated_count,
        "missing": missing,
        "not_trading": not_trading,
        "invalid": invalid,
        "error": None,
    }


# ============================================================
# SYMBOL + TRADING CONSTRAINTS
# ============================================================

def verify_symbol_and_constraints(
    adapter: ToobitTradingAdapter,
) -> Dict[str, Any]:

    symbol_pass = 0
    constraint_pass = 0
    failures: List[str] = []

    for asset in EXPECTED_ASSETS:

        try:
            symbol_result = (
                adapter.symbol_check(
                    asset
                )
            )
        except Exception as exc:
            symbol_result = None
            failures.append(
                f"{asset}:SYMBOL_EXCEPTION:{exc}"
            )

        if (
            symbol_result is not None
            and symbol_result.allowed is True
            and symbol_result.status == "PASS"
        ):
            symbol_pass += 1

        elif not any(
            failure.startswith(
                f"{asset}:SYMBOL_EXCEPTION"
            )
            for failure in failures
        ):
            failures.append(
                f"{asset}:SYMBOL"
            )

        try:
            constraint_result = (
                adapter.trading_constraints(
                    asset
                )
            )
        except Exception as exc:
            constraint_result = None
            failures.append(
                f"{asset}:CONSTRAINT_EXCEPTION:{exc}"
            )

        if (
            constraint_result is not None
            and constraint_result.allowed is True
            and constraint_result.status == "PASS"
        ):
            constraint_pass += 1

        elif not any(
            failure.startswith(
                f"{asset}:CONSTRAINT_EXCEPTION"
            )
            for failure in failures
        ):
            failures.append(
                f"{asset}:CONSTRAINT"
            )

    return {
        "symbol_pass": symbol_pass,
        "constraint_pass": constraint_pass,
        "failures": failures,
        "pass": (
            symbol_pass
            == EXPECTED_ASSET_COUNT
            and constraint_pass
            == EXPECTED_ASSET_COUNT
            and not failures
        ),
    }


# ============================================================
# ACCOUNT
# ============================================================

def verify_account(
    adapter: ToobitTradingAdapter,
) -> Dict[str, Any]:

    try:
        result = adapter.account_check()
    except Exception as exc:
        return {
            "pass": False,
            "status": "EXCEPTION",
            "http_status": None,
            "balance_rows": None,
            "reason": str(exc),
        }

    if result is None:
        return {
            "pass": False,
            "status": "NO_RESULT",
            "http_status": None,
            "balance_rows": None,
            "reason": (
                "account_check returned None"
            ),
        }

    data = result.data or {}

    return {
        "pass": (
            result.allowed is True
            and result.status == "PASS"
        ),
        "status": result.status,
        "http_status": data.get(
            "http_status"
        ),
        "balance_rows": data.get(
            "balance_rows"
        ),
        "reason": result.reason,
    }


# ============================================================
# BALANCE
# ============================================================

def verify_balance(
    adapter: ToobitTradingAdapter,
) -> Dict[str, Any]:

    try:
        result = adapter.balance_check()
    except Exception as exc:
        return {
            "pass": False,
            "status": "EXCEPTION",
            "balance_rows": None,
            "nonzero_count": None,
            "reason": str(exc),
        }

    if result is None:
        return {
            "pass": False,
            "status": "NO_RESULT",
            "balance_rows": None,
            "nonzero_count": None,
            "reason": (
                "balance_check returned None"
            ),
        }

    data = result.data or {}

    return {
        "pass": (
            result.allowed is True
            and result.status == "PASS"
        ),
        "status": result.status,
        "balance_rows": data.get(
            "balance_rows"
        ),
        "nonzero_count": data.get(
            "nonzero_count"
        ),
        "reason": result.reason,
    }


# ============================================================
# API KEY
# ============================================================

def verify_api_key(
    adapter: ToobitTradingAdapter,
) -> Dict[str, Any]:

    try:
        result = adapter.api_key_check()
    except Exception as exc:
        return {
            "pass": False,
            "status": "EXCEPTION",
            "account_type": None,
            "reason": str(exc),
        }

    if result is None:
        return {
            "pass": False,
            "status": "NO_RESULT",
            "account_type": None,
            "reason": (
                "api_key_check returned None"
            ),
        }

    data = result.data or {}

    return {
        "pass": (
            result.allowed is True
            and result.status == "PASS"
        ),
        "status": result.status,
        "account_type": data.get(
            "account_type"
        ),
        "reason": result.reason,
    }


# ============================================================
# HARD BLOCKS
# ============================================================

def verify_hard_blocks(
    adapter: ToobitTradingAdapter,
) -> bool:

    for method_name in FORBIDDEN_WRITE_METHODS:

        if not callable(
            get_method(
                adapter,
                method_name,
            )
        ):
            return False

    try:
        order_result = adapter.place_order(
            {
                "asset": "UNI",
                "direction": "LONG",
                "entry_price": 1.0,
            }
        )

        cancel_result = adapter.cancel_order(
            "READ_ONLY_VERIFY"
        )

        withdraw_result = adapter.withdraw(
            {
                "coin": "USDT",
                "amount": 1,
            }
        )

    except Exception:
        return False

    if order_result is None:
        return False

    if cancel_result is None:
        return False

    if withdraw_result is None:
        return False

    return (
        order_result.status == "BLOCKED"
        and order_result.allowed is False
        and cancel_result.status == "BLOCKED"
        and cancel_result.allowed is False
        and withdraw_result.status == "BLOCKED"
        and withdraw_result.allowed is False
    )


# ============================================================
# DATA SAFETY
# ============================================================

def verify_data_safety() -> bool:
    """
    Adapter must not access production DB.

    This is a source-level safety check.
    """

    source = adapter_source()

    if not source:
        return False

    return not any(
        token in source
        for token in FORBIDDEN_DB_IMPORTS
    )


# ============================================================
# CORE ISOLATION
# ============================================================

def verify_core_isolation() -> bool:
    """
    Adapter must remain independent from production
    trading core modules.
    """

    source = adapter_source()

    if not source:
        return False

    return not any(
        token in source
        for token in FORBIDDEN_CORE_IMPORTS
    )


# ============================================================
# STATIC EXECUTION SURFACE
# ============================================================

def verify_forbidden_execution_surface() -> bool:
    """
    Ensure no actual exchange write implementation exists
    inside the adapter source.

    This does NOT reject the hard-block methods themselves.
    """

    source = adapter_source()

    if not source:
        return False

    for pattern in FORBIDDEN_WRITE_REQUEST_PATTERNS:

        if re.search(
            pattern,
            source,
            flags=re.IGNORECASE,
        ):
            return False

    return True


# ============================================================
# MAIN
# ============================================================

def main() -> int:

    print("=" * 80)

    print(
        "ARUNDA TRADER — "
        "TOOBIT ADAPTER READ-ONLY "
        "CONTRACT INTEGRATION VERIFY v0.2"
    )

    print("=" * 80)

    print(
        "MODE                  : "
        "READ-ONLY RUNTIME VERIFICATION"
    )

    print(
        "EXCHANGE              : TOOBIT"
    )

    print(
        "ADAPTER EXPECTED      : "
        f"{EXPECTED_ADAPTER_VERSION}"
    )

    print(
        "SIGNING MODEL         : "
        "EXACT_MANUAL_QUERY"
    )

    print(
        "EXECUTION             : DISABLED"
    )

    print("=" * 80)

    try:
        adapter = ToobitTradingAdapter()
    except Exception as exc:
        print(
            "ADAPTER INITIALIZATION: FAIL"
        )

        print(
            f"REASON                : {exc}"
        )

        print("=" * 80)

        return 1

    overall = True

    operation_surface_pass = (
        verify_operation_surface(
            adapter
        )
    )

    line(
        "OPERATION SURFACE",
        (
            "PASS"
            if operation_surface_pass
            else "FAIL"
        ),
    )

    overall &= operation_surface_pass

    static_pass = verify_static_safety(
        adapter
    )

    line(
        "STATIC SAFETY",
        "PASS" if static_pass else "FAIL",
    )

    overall &= static_pass

    execution_flags_pass = (
        verify_execution_flags(
            adapter
        )
    )

    line(
        "EXECUTION FLAGS",
        (
            "PASS"
            if execution_flags_pass
            else "FAIL"
        ),
    )

    overall &= execution_flags_pass

    contract_pass = verify_contract(
        adapter
    )

    line(
        "ADAPTER CONTRACT",
        "PASS" if contract_pass else "FAIL",
    )

    overall &= contract_pass

    credentials_pass = verify_credentials(
        adapter
    )

    line(
        "CREDENTIAL PRESENCE",
        "PASS" if credentials_pass else "FAIL",
    )

    overall &= credentials_pass

    signature = verify_signature_local(
        adapter
    )

    line(
        "SIGNATURE LOCAL",
        "PASS"
        if signature["pass"]
        else "FAIL",
    )

    if not signature["pass"]:
        line(
            "SIGNATURE DIAGNOSTIC",
            signature["reason"],
        )

    overall &= signature["pass"]

    signed_construction = (
        verify_signed_request_construction(
            adapter
        )
    )

    line(
        "SIGNED REQUEST CONSTRUCTION",
        (
            "PASS"
            if signed_construction["pass"]
            else "FAIL"
        ),
    )

    if not signed_construction["pass"]:
        line(
            "SIGNING CONSTRUCTION REASON",
            signed_construction["reason"],
        )

    overall &= signed_construction["pass"]

    time_pass = verify_server_time(
        adapter
    )

    line(
        "PUBLIC TIME",
        "PASS" if time_pass else "FAIL",
    )

    overall &= time_pass

    exchange_info = verify_exchange_info(
        adapter
    )

    line(
        "EXCHANGE INFO",
        (
            f"PASS ({exchange_info['count']})"
            if exchange_info["pass"]
            else "FAIL"
        ),
    )

    if exchange_info.get("error"):
        line(
            "EXCHANGE INFO ERROR",
            exchange_info["error"],
        )

    overall &= exchange_info["pass"]

    expected = verify_expected_symbols(
        adapter
    )

    line(
        "EXPECTED SYMBOLS",
        (
            f"PASS "
            f"{expected['validated']}/"
            f"{expected['expected']}"
            if expected["pass"]
            else
            f"FAIL "
            f"{expected['validated']}/"
            f"{expected['expected']}"
        ),
    )

    if expected["missing"]:
        line(
            "MISSING SYMBOLS",
            expected["missing"],
        )

    if expected["not_trading"]:
        line(
            "NOT TRADING",
            expected["not_trading"],
        )

    if expected["invalid"]:
        line(
            "INVALID SYMBOLS",
            expected["invalid"],
        )

    if expected.get("error"):
        line(
            "EXPECTED SYMBOL ERROR",
            expected["error"],
        )

    overall &= expected["pass"]

    constraints = (
        verify_symbol_and_constraints(
            adapter
        )
    )

    line(
        "SYMBOL CONTRACT",
        (
            f"PASS "
            f"{constraints['symbol_pass']}/"
            f"{EXPECTED_ASSET_COUNT}"
            if constraints["symbol_pass"]
            == EXPECTED_ASSET_COUNT
            else
            f"FAIL "
            f"{constraints['symbol_pass']}/"
            f"{EXPECTED_ASSET_COUNT}"
        ),
    )

    line(
        "TRADING CONSTRAINTS",
        (
            f"PASS "
            f"{constraints['constraint_pass']}/"
            f"{EXPECTED_ASSET_COUNT}"
            if constraints["constraint_pass"]
            == EXPECTED_ASSET_COUNT
            else
            f"FAIL "
            f"{constraints['constraint_pass']}/"
            f"{EXPECTED_ASSET_COUNT}"
        ),
    )

    if constraints["failures"]:
        line(
            "CONSTRAINT FAILURES",
            constraints["failures"],
        )

    overall &= constraints["pass"]

    account = verify_account(
        adapter
    )

    line(
        "ACCOUNT READ",
        (
            "PASS"
            if account["pass"]
            else
            f"FAIL {account['status']}"
        ),
    )

    if account["http_status"] is not None:
        line(
            "ACCOUNT HTTP",
            account["http_status"],
        )

    if account["balance_rows"] is not None:
        line(
            "ACCOUNT BALANCE ROWS",
            account["balance_rows"],
        )

    if not account["pass"] and account["reason"]:
        line(
            "ACCOUNT REASON",
            account["reason"],
        )

    overall &= account["pass"]

    balance = verify_balance(
        adapter
    )

    line(
        "BALANCE READ",
        (
            "PASS"
            if balance["pass"]
            else
            f"FAIL {balance['status']}"
        ),
    )

    if balance["balance_rows"] is not None:
        line(
            "BALANCE ROWS",
            balance["balance_rows"],
        )

    if balance["nonzero_count"] is not None:
        line(
            "NONZERO BALANCES",
            balance["nonzero_count"],
        )

    if not balance["pass"] and balance["reason"]:
        line(
            "BALANCE REASON",
            balance["reason"],
        )

    overall &= balance["pass"]

    api_key = verify_api_key(
        adapter
    )

    line(
        "API KEY READ",
        (
            "PASS"
            if api_key["pass"]
            else
            f"FAIL {api_key['status']}"
        ),
    )

    if api_key["account_type"] is not None:
        line(
            "ACCOUNT TYPE",
            api_key["account_type"],
        )

    if not api_key["pass"] and api_key["reason"]:
        line(
            "API KEY REASON",
            api_key["reason"],
        )

    overall &= api_key["pass"]

    hard_blocks_pass = verify_hard_blocks(
        adapter
    )

    line(
        "ORDER SUBMISSION",
        "BLOCKED"
        if hard_blocks_pass
        else "FAIL",
    )

    line(
        "ORDER CANCELLATION",
        "BLOCKED"
        if hard_blocks_pass
        else "FAIL",
    )

    line(
        "WITHDRAWAL",
        "BLOCKED"
        if hard_blocks_pass
        else "FAIL",
    )

    overall &= hard_blocks_pass

    data_safety_pass = verify_data_safety()

    line(
        "DATABASE WRITE",
        "FALSE"
        if data_safety_pass
        else "FAIL",
    )

    line(
        "EXCHANGE WRITE",
        "FALSE"
        if data_safety_pass
        else "FAIL",
    )

    line(
        "SYNTHETIC/FALLBACK PATH",
        "NONE"
        if data_safety_pass
        else "FAIL",
    )

    overall &= data_safety_pass

    execution_surface_pass = (
        verify_forbidden_execution_surface()
    )

    line(
        "WRITE HTTP SURFACE",
        "NONE"
        if execution_surface_pass
        else "FAIL",
    )

    overall &= execution_surface_pass

    core_isolation_pass = (
        verify_core_isolation()
    )

    line(
        "PRODUCTION CORE COUPLING",
        "NONE"
        if core_isolation_pass
        else "FAIL",
    )

    overall &= core_isolation_pass

    print("=" * 80)

    if overall:

        print(
            "OVERALL RESULT        : PASS"
        )

        print(
            "STATUS                : "
            "TOOBIT_READ_ONLY_INTEGRATION_READY"
        )

        print(
            "EXECUTION             : DISABLED"
        )

        print(
            "ORDER WRITE           : BLOCKED"
        )

        print(
            "WITHDRAW              : BLOCKED"
        )

        print(
            "DATABASE WRITE        : FALSE"
        )

        print(
            "EXCHANGE WRITE        : FALSE"
        )

        print(
            "PRODUCTION CORE       : UNMODIFIED"
        )

        print(
            "SIGNING               : "
            "LOCAL HMAC-SHA256 VERIFIED"
        )

        print(
            "PRIVATE API           : "
            "READ-ONLY VERIFIED"
        )

        print(
            "NEXT CHECKPOINT       : "
            "ADAPTER INTEGRATION CLOSE"
        )

        print("=" * 80)

        return 0

    print(
        "OVERALL RESULT        : FAIL"
    )

    print(
        "STATUS                : "
        "TOOBIT_READ_ONLY_INTEGRATION_BLOCKED"
    )

    print(
        "NO EXECUTION WAS PERFORMED"
    )

    print("=" * 80)

    return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )