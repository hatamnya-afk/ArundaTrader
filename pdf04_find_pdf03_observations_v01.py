from pathlib import Path

ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

KEYWORDS = (
    "raydium",
    "solana",
    "swapbaseinv2",
    "swap",
    "observation",
    "onchain",
    "dex",
    "pdf03",
    "public_market",
)

EXTENSIONS = {
    ".py", ".json", ".jsonl", ".csv", ".txt",
    ".db", ".sqlite", ".sqlite3", ".log"
}

SKIP_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
}


def main():
    print("ENGINE=PUBLIC_CANONICAL_OHLCV_v0.1")
    print("MODE=READ_ONLY")
    print("DB_WRITE=DISABLED")
    print()

    matches = []

    for path in ROOT.rglob("*"):

        if not path.is_file():
            continue

        if any(part in SKIP_DIRS for part in path.parts):
            continue

        if path.suffix.lower() not in EXTENSIONS:
            continue

        name = path.name.lower()

        if any(keyword in name for keyword in KEYWORDS):
            matches.append(path)

    print(f"FILES_MATCHED_BY_NAME={len(matches)}")

    for path in sorted(matches):
        print(f"FILE={path}")

    print()

    # Search file contents for known PDF-03 identifiers.
    content_matches = []

    needles = (
        "RAYDIUM_AMM_V4",
        "SOLANA_MAINNET_RAYDIUM_AMM_V4",
        "SwapBaseInV2",
        "2zwC7mMv",
        "1.892593",
        "0.018123314",
        "104.4286381618726023",
        "USDC",
        "WSOL",
    )

    for path in sorted(matches):

        try:
            if path.stat().st_size > 20_000_000:
                continue

            text = path.read_text(
                encoding="utf-8",
                errors="ignore"
            )

            found = [
                needle
                for needle in needles
                if needle.lower() in text.lower()
            ]

            if found:
                content_matches.append((path, found))

        except Exception:
            continue

    print(f"CONTENT_MATCHED_FILES={len(content_matches)}")

    for path, found in content_matches:
        print(f"CONTENT_FILE={path}")
        print("MATCHES=" + ",".join(found))

    print()

    if content_matches:
        print("STATUS=FOUND_PDF03_EVIDENCE")
    else:
        print("STATUS=NOT_FOUND")
        print("REASON=PDF03_ARTIFACT_LOCATION_UNKNOWN")

    print("DB_WRITES=0")
    print("CANONICAL_OHLCV_COMMITTED=0")


if __name__ == "__main__":
    main()