from pathlib import Path
import ast
import re

ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

CORE_FILES = [
    "arunda_pipeline.py",
    "market_snapshot_engine.py",
    "market_adapter.py",
]

FORBIDDEN_TERMS = {
    "BITPIN",
    "TOOBIT",
    "bitpin",
    "toobit",
    "HMAC",
    "hmac",
    "X-BB-APIKEY",
    "X-MBX-APIKEY",
    "api_key",
    "secret_key",
    "signature",
    "recvWindow",
    "place_order",
    "cancel_order",
    "withdraw",
    "trading_adapter",
    "exchange_adapter",
}

FORBIDDEN_URL_PATTERNS = [
    r"https?://api\.toobit\.com",
    r"https?://.*bitpin.*",
    r"api-docs\.toobit\.com",
]

EXCHANGE_SPECIFIC_FIELDS = {
    "accountType",
    "canTrade",
    "baseAsset",
    "quoteAsset",
    "filterType",
    "minQty",
    "maxQty",
    "stepSize",
    "minNotional",
}

EXCHANGE_SYMBOL_PATTERN = re.compile(
    r"\b(?:BTC|ETH|SOL|XRP|ADA|DOGE|SHIB|LINK|AVAX|DOT|LTC|UNI|AAVE|SUI|NEAR)USDT\b"
)

violations = []


def source_text(path):
    return path.read_text(encoding="utf-8")


def ast_check(path, text):
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError as exc:
        violations.append(
            f"{path.name}: SYNTAX ERROR: {exc}"
        )
        return

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name.lower()
                if "bitpin" in name or "toobit" in name:
                    violations.append(
                        f"{path.name}: exchange-specific import: {alias.name}"
                    )

        elif isinstance(node, ast.ImportFrom):
            module = (node.module or "").lower()
            if "bitpin" in module or "toobit" in module:
                violations.append(
                    f"{path.name}: exchange-specific import: {node.module}"
                )


print("=" * 80)
print("ARUNDA TRADER — EXCHANGE-AGNOSTIC CORE CHECK v0.1")
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

    text = source_text(path)
    ast_check(path, text)

    for term in FORBIDDEN_TERMS:
        if term in text:
            violations.append(
                f"{filename}: forbidden dependency -> {term}"
            )

    for pattern in FORBIDDEN_URL_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            violations.append(
                f"{filename}: exchange-specific URL -> {pattern}"
            )

    for field in EXCHANGE_SPECIFIC_FIELDS:
        if re.search(rf"['\"]{re.escape(field)}['\"]", text):
            violations.append(
                f"{filename}: exchange-specific response field -> {field}"
            )

    for match in EXCHANGE_SYMBOL_PATTERN.finditer(text):
        violations.append(
            f"{filename}: exchange-specific symbol literal -> {match.group(0)}"
        )

print("CORE FILES CHECKED :", len(CORE_FILES))
print()

if violations:
    print("RESULT            : FAIL")
    print()
    print("VIOLATIONS:")
    for item in sorted(set(violations)):
        print(" -", item)
else:
    print("BITPIN DEPENDENCY              : NONE")
    print("TOOBIT DEPENDENCY              : NONE")
    print("EXCHANGE ENDPOINT              : NONE")
    print("HMAC / SIGNATURE               : NONE")
    print("API KEY / AUTH HEADER          : NONE")
    print("EXCHANGE RESPONSE FIELDS       : NONE")
    print("EXCHANGE SYMBOL FORMAT         : NONE")
    print("ORDER SUBMISSION               : NONE")
    print("ORDER CANCELLATION             : NONE")
    print("WITHDRAWAL                     : NONE")
    print()
    print("RESULT            : PASS")

print("=" * 80)