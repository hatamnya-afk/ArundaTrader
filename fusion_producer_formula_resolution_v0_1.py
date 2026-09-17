from pathlib import Path
import ast

ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

TARGETS = {
    "MARKET": (
        "market_data_engine.py",
        "technical_score",
    ),
    "POSITIONING": (
        "coinalyze_positioning.py",
        "calculate_positioning_score",
    ),
    "NEWS": (
        "news_adapter.py",
        "calculate_news_score",
    ),
}

print("=" * 100)
print("ARUNDA FUSION PRODUCER FORMULA RESOLUTION v0.1")
print("=" * 100)

for arm, (filename, function_name) in TARGETS.items():

    path = ROOT / filename

    print()
    print("=" * 100)
    print(f"{arm} ARM")
    print(f"FILE     : {path}")
    print(f"FUNCTION : {function_name}")
    print("=" * 100)

    if not path.exists():
        print("STATUS=FILE_NOT_FOUND")
        continue

    source = path.read_text(
        encoding="utf-8-sig",
        errors="ignore"
    )

    try:
        tree = ast.parse(
            source,
            filename=str(path)
        )
    except Exception as exc:
        print(
            "AST_PARSE=FAIL",
            type(exc).__name__,
            str(exc)
        )
        continue

    target = None

    for node in tree.body:
        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef)
        ) and node.name == function_name:
            target = node
            break

    if target is None:
        print("FUNCTION_FOUND=FALSE")
        continue

    print(
        "FUNCTION_FOUND=TRUE"
    )

    try:
        print()
        print(ast.unparse(target))
    except Exception:
        lines = source.splitlines()

        start = target.lineno - 1

        end = (
            target.end_lineno
            if target.end_lineno
            else min(start + 200, len(lines))
        )

        print()
        print(
            "\n".join(
                lines[start:end]
            )
        )

print()
print("=" * 100)
print("DEPENDENCY FUNCTIONS")
print("=" * 100)

dependency_targets = {
    "MARKET": (
        "market_data_engine.py",
        [
            "ema",
            "ema_series",
            "rsi",
            "macd",
            "bollinger",
            "volume_metrics",
            "volatility",
            "calculate_analysis",
        ],
    ),
    "POSITIONING": (
        "coinalyze_positioning.py",
        [
            "calculate_oi_change",
            "parse_liquidations",
            "parse_long_short",
            "determine_quality",
        ],
    ),
    "NEWS": (
        "news_adapter.py",
        [
            "calculate_sentiment",
            "calculate_impact",
            "detect_asset",
        ],
    ),
}

for arm, (filename, names) in dependency_targets.items():

    path = ROOT / filename

    print()
    print("-" * 100)
    print(arm)

    if not path.exists():
        print("FILE_NOT_FOUND")
        continue

    source = path.read_text(
        encoding="utf-8-sig",
        errors="ignore"
    )

    try:
        tree = ast.parse(
            source,
            filename=str(path)
        )
    except Exception as exc:
        print(
            "AST_PARSE=FAIL",
            type(exc).__name__,
            str(exc)
        )
        continue

    found = {
        node.name: node
        for node in tree.body
        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef)
        )
    }

    for name in names:

        node = found.get(name)

        if node is None:
            continue

        print()
        print(
            f"FUNCTION: {name}"
        )

        try:
            print(
                ast.unparse(node)
            )
        except Exception:
            lines = source.splitlines()
            print(
                "\n".join(
                    lines[
                        node.lineno - 1:
                        node.end_lineno
                    ]
                )
            )

print()
print("=" * 100)
print("SAFETY")
print("=" * 100)
print("SOURCE_ONLY_INSPECTION=TRUE")
print("PRODUCERS_EXECUTED=FALSE")
print("PRODUCTION_DB_TOUCHED=FALSE")
print("DB_WRITES=0")
print("FABRIC_MODIFIED=FALSE")
print("FUSION_EXECUTED=FALSE")
print("SCORE=OFF")
print("DECISION=OFF")
print("ORDER_INTENTS=0")
print("EXECUTION=OFF")
print("=" * 100)
