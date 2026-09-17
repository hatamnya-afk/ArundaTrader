CANONICAL_OHLCV_FIELDS = (
    "asset", "symbol", "timestamp", "timeframe",
    "open", "high", "low", "close", "volume",
)

PROVENANCE_FIELDS = (
    "source_id", "source_type",
    "source_timestamp", "retrieved_at",
)

SOURCE_TYPES = (
    "CEX_PUBLIC_API",
    "DEX_ONCHAIN",
)

PRODUCTION_TIMEFRAME = "1h"

FORBIDDEN = (
    "SYNTHETIC",
    "INTERPOLATION",
    "FILL",
    "BACKFILL",
    "PADDING",
    "BLENDING",
)

ONE_CANDLE_ONE_SOURCE = True
FAIL_CLOSED = True
