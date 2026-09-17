from pathlib import Path
import ast

FILES = [
    "public_dex_onchain.py",
    "public_dex_observation.py",
    "public_dex_final_swap_pair_proof.py",
    "public_dex_price_observation.py",
    "public_dex_raydium_decode.py",
    "public_dex_swap_proof.py",
]

print("ENGINE=PUBLIC_CANONICAL_OHLCV_OBSERVATION_RECOVERY_v0.1")
print("STATUS=READ_ONLY_ARTIFACT_PROBE")

for name in FILES:

    path = Path(name)

    print("\n=== FILE ===")
    print(name)

    if not path.exists():
        print("EXISTS=False")
        continue

    print("EXISTS=True")
    print("SIZE=", path.stat().st_size)

    text = path.read_text(encoding="utf-8", errors="replace")

    try:
        tree = ast.parse(text)
    except Exception as e:
        print("AST_PARSE=FAILED")
        print("ERROR=", repr(e))
        continue

    print("AST_PARSE=OK")

    names = []
    calls = []
    strings = []

    for node in ast.walk(tree):

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names.append(node.name)

        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.append(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.append(node.func.attr)

        elif isinstance(node, ast.Constant):
            if isinstance(node.value, str):
                value = node.value.strip()
                if value:
                    strings.append(value)

    print("FUNCTIONS=", sorted(set(names)))

    interesting_calls = sorted({
        x for x in calls
        if any(k in x.lower() for k in (
            "rpc",
            "transaction",
            "signature",
            "balance",
            "observation",
            "price",
            "program",
            "account",
            "instruction",
        ))
    })

    print("INTERESTING_CALLS=", interesting_calls)

    keywords = (
        "observation",
        "price",
        "timestamp",
        "source_id",
        "source_type",
        "input_amount",
        "output_amount",
        "signature",
        "slot",
        "block_time",
        "SOL/USDC",
        "USDC",
        "WSOL",
    )

    hits = []

    for value in strings:
        low = value.lower()

        if any(k.lower() in low for k in keywords):
            hits.append(value)

    print("INTERESTING_STRINGS_COUNT=", len(hits))

    for value in hits[:80]:
        print("STRING=", value)

print("\n=== CONTRACT ===")
print("READ_ONLY=True")
print("DB_WRITES=0")
print("SYNTHETIC=False")
print("INTERPOLATION=False")
print("FILL=False")
print("BACKFILL=False")
print("PADDING=False")
print("BLENDING=False")
print("CANONICAL_OHLCV_COMMITTED=False")

print("\nSTATUS=PROBE_COMPLETE")
