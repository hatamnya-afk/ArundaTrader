from pathlib import Path
import re

ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

CORE_FILES = [
    "arunda_pipeline.py",
    "market_snapshot_engine.py",
    "market_adapter.py",
]

FORBIDDEN_TERMS = [
    "BITPIN",
    "TOOBIT",
    "bitpin",
    "toobit",
    "HMAC",
    "hmac",
    "X-BB-APIKEY",
    "X-MBX-APIKEY",
    "recvWindow",
    "place_order",
    "cancel_order",
    "withdraw",
    "trading_adapter",
    "exchange_adapter",
]

FORBIDDEN_URLS = [
    r"https?://api\.toobit\.com",
    r"https?://.*bitpin.*",
    r"api-docs\.toobit\.com",
]

EXCHANGE_FIELDS = [
    "accountType",
    "canTrade",
    "filterType",
    "minQty",
    "maxQty",
    "stepSize",
    "minNotional",
]

EXCHANGE_SYMBOL = re.compile(
    r"\b(?:BTC|ETH|SOL|XRP|ADA|DOGE|SHIB|LINK|AVAX|DOT|LTC|UNI|AAVE|SUI|NEAR)USDT\b"
)

violations = []

print("=" * 80)
print("ARUNDA TRADER — EXCHANGE-AGNOSTIC CORE CHECK v0.2")
print("=" * 80)
print("MODE              : READ ONLY")
print("DATABASE WRITE    : NONE")
print("EXCHANGE REQUEST  : NONE")
print("EXECUTION         : NONE")
print()

for filename in CORE_FILES:
    path = ROOT / filename

    if not path.exists():
        violations.append(f"{filename}: FILE NOT FOUND")
        continue

    text = path.read_text(encoding="utf-8")

    for term in FORBIDDEN_TERMS:
        if term in text:
            violations.append(
                f"{filename}: forbidden exchange dependency -> {term}"
            )

    for pattern in FORBIDDEN_URLS:
        if re.search(pattern, text, re.IGNORECASE):
            violations.append(
                f"{filename}: forbidden exchange URL -> {pattern}"
            )

    for field in EXCHANGE_FIELDS:
        if re.search(
            rf"['\"]{re.escape(field)}['\"]",
            text
        ):
            violations.append(
                f"{filename}: exchange-specific response field -> {field}"
            )

    for match in EXCHANGE_SYMBOL.finditer(text):
        violations.append(
            f"{filename}: exchange-specific symbol literal -> {match.group(0)}"
        )

print("CORE FILES CHECKED :", len(CORE_FILES))
print()

print("CMC API KEY        : ALLOWED — MARKET DATA PROVIDER")
print("CMC HTTP SURFACE   : ALLOWED — MARKET DATA PROVIDER")
print()

if violations:
    print("RESULT            : FAIL")
    print()
    print("VIOLATIONS:")
    for item in sorted(set(violations)):
        print(" -", item)
else:
    print("BITPIN DEPENDENCY  : NONE")
    print("TOOBIT DEPENDENCY  : NONE")
    print("EXCHANGE ENDPOINT  : NONE")
    print("HMAC / SIGNATURE   : NONE")
    print("EXCHANGE AUTH      : NONE")
    print("EXCHANGE RESPONSE  : NONE")
    print("EXCHANGE SYMBOLS   : NONE")
    print("ORDER SUBMISSION   : NONE")
    print("ORDER CANCELLATION : NONE")
    print("WITHDRAWAL         : NONE")
    print()
    print("RESULT            : PASS")

print("=" * 80)
