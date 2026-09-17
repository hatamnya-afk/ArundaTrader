from pathlib import Path
import sqlite3
import json
import csv
from datetime import datetime, timezone

ENGINE = "PUBLIC_CANONICAL_OHLCV_v0.1"
ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

# فقط برای کشف artifactهای PDF-03؛ هیچ چیزی نوشته نمی‌شود.
SEARCH_DIRS = [
    ROOT,
    ROOT / "data",
    ROOT / "artifacts",
    ROOT / "runtime",
    ROOT / "output",
    ROOT / "outputs",
    ROOT / "pdf03",
]

KEYWORDS = (
    "pdf03",
    "dex",
    "raydium",
    "observation",
    "observations",
    "onchain",
    "solana",
)

SUPPORTED = {".json", ".jsonl", ".csv", ".db", ".sqlite", ".sqlite3"}


def is_candidate(p: Path):
    if not p.is_file() or p.suffix.lower() not in SUPPORTED:
        return False
    name = p.name.lower()
    return any(k in name for k in KEYWORDS)


def discover():
    found = set()
    for d in SEARCH_DIRS:
        if not d.exists():
            continue
        try:
            for p in d.rglob("*"):
                if is_candidate(p):
                    found.add(p.resolve())
        except Exception:
            pass
    return sorted(found)


def inspect_json(path):
    try:
        text = path.read_text(encoding="utf-8")
        obj = json.loads(text)
        return obj
    except Exception:
        return None


def inspect_jsonl(path):
    rows = []
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        return rows
    except Exception:
        return []


def inspect_csv(path):
    try:
        with path.open("r", encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))
    except Exception:
        return []


def flatten(obj):
    if isinstance(obj, list):
        for x in obj:
            yield x
    elif isinstance(obj, dict):
        # Common observation containers
        for key in (
            "observations",
            "observation",
            "data",
            "transactions",
            "swaps",
            "records",
            "items",
            "results",
        ):
            if key in obj and isinstance(obj[key], list):
                for x in obj[key]:
                    yield x
        else:
            yield obj


def get_value(row, names):
    if not isinstance(row, dict):
        return None

    lowered = {str(k).lower(): v for k, v in row.items()}

    for name in names:
        if name.lower() in lowered:
            return lowered[name.lower()]

    return None


def valid_observation(row):
    if not isinstance(row, dict):
        return False

    timestamp = get_value(
        row,
        ["timestamp", "time", "ts", "block_time", "block_timestamp"],
    )

    source = get_value(
        row,
        ["source_id", "source", "sourceId"],
    )

    tx = get_value(
        row,
        ["signature", "tx_signature", "transaction_signature", "tx"],
    )

    price = get_value(
        row,
        ["price", "execution_price", "unit_price"],
    )

    if timestamp is None:
        return False

    if source is None:
        return False

    if tx is None:
        return False

    if price is None:
        return False

    try:
        float(price)
    except Exception:
        return False

    return True


def hour_key(value):
    try:
        if isinstance(value, (int, float)):
            dt = datetime.fromtimestamp(float(value), tz=timezone.utc)
        else:
            s = str(value).replace("Z", "+00:00")
            dt = datetime.fromisoformat(s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)

        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:00:00Z")
    except Exception:
        return None


def main():
    print(f"ENGINE={ENGINE}")
    print("MODE=READ_ONLY")
    print("DB_WRITE=DISABLED")
    print()

    candidates = discover()

    print(f"ARTIFACTS_DISCOVERED={len(candidates)}")

    if not candidates:
        print("STATUS=BLOCKED")
        print("REASON=NO_PDF03_ARTIFACT_DISCOVERED")
        return

    all_valid = []
    artifact_count = 0

    for path in candidates:
        print(f"ARTIFACT={path}")

        try:
            if path.suffix.lower() == ".json":
                obj = inspect_json(path)
            elif path.suffix.lower() == ".jsonl":
                obj = inspect_jsonl(path)
            elif path.suffix.lower() == ".csv":
                obj = inspect_csv(path)
            else:
                print("ARTIFACT_TYPE=DATABASE")
                print("DB_INSPECTION=SKIPPED")
                continue

            rows = list(flatten(obj))

            if not rows:
                print("OBSERVATIONS=0")
                continue

            artifact_count += 1

            valid = [r for r in rows if valid_observation(r)]

            print(f"ROWS_FOUND={len(rows)}")
            print(f"VALID_OBSERVATIONS={len(valid)}")

            for r in valid:
                all_valid.append((path, r))

        except Exception as exc:
            print(f"ARTIFACT_ERROR={type(exc).__name__}:{exc}")

    print()
    print("===== PDF-04 OBSERVATION PROBE =====")

    if not all_valid:
        print("STATUS=BLOCKED")
        print("REASON=NO_VALID_REAL_OBSERVATIONS")
        print("OBSERVATIONS_FOUND=0")
        print("OBSERVATIONS_VALID=0")
        return

    hours = {}

    for path, row in all_valid:
        hk = hour_key(
            get_value(
                row,
                ["timestamp", "time", "ts", "block_time", "block_timestamp"],
            )
        )

        if hk is None:
            continue

        hours.setdefault(hk, []).append((path, row))

    sources = set()
    pairs = set()

    for _, row in all_valid:
        src = get_value(row, ["source_id", "source", "sourceId"])
        pair = get_value(
            row,
            ["pair", "symbol", "market", "pool", "trading_pair"],
        )

        if src is not None:
            sources.add(str(src))

        if pair is not None:
            pairs.add(str(pair))

    complete = []
    incomplete = []

    # IMPORTANT:
    # We DO NOT decide that one observation is enough for OHLCV.
    # We only report hour buckets and their observations.
    for hk, rows in sorted(hours.items()):
        if len(rows) >= 1:
            complete.append(hk)

    print(f"SOURCE={','.join(sorted(sources))}")
    print(f"PAIR={','.join(sorted(pairs))}")
    print(f"OBSERVATIONS_FOUND={sum(len(v) for v in hours.values())}")
    print(f"OBSERVATIONS_VALID={len(all_valid)}")
    print(f"HOURS_DISCOVERED={len(hours)}")

    # At this stage completeness is intentionally NOT asserted.
    # PDF-04 contract must define minimum transaction/observation
    # requirements before a candle can be committed.
    print(f"COMPLETE_HOURS=UNDEFINED_PENDING_CONTRACT")
    print(f"INCOMPLETE_HOURS=UNDEFINED_PENDING_CONTRACT")

    print("SYNTHETIC=0")
    print("INTERPOLATION=0")
    print("FILL=0")
    print("BACKFILL=0")
    print("PADDING=0")
    print("BLENDING=0")
    print("DB_WRITES=0")
    print("CANONICAL_OHLCV_COMMITTED=0")

    print()
    print("STATUS=READY_FOR_MANAGER_REVIEW")


if __name__ == "__main__":
    main()