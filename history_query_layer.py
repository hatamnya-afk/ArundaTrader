import sqlite3
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any


# =============================================================================
# ARUNDA TRADER
# HISTORY QUERY LAYER v0.1
# =============================================================================
#
# PURPOSE:
#   Read-only access layer for verified market_history.
#
# ARCHITECTURE:
#   DATABASE
#       ↓
#   HISTORY QUERY LAYER
#       ↓
#   FUTURE CONSUMERS
#       ├── Technical Engine
#       ├── Pattern Engine
#       ├── Opportunity Engine
#       ├── Prediction Engine
#       └── Signal Engine
#
# IMPORTANT:
#   - READ ONLY
#   - NO INSERT
#   - NO UPDATE
#   - NO DELETE
#   - NO ALTER
#   - NO CREATE
#   - CMC_ID is the primary historical identity
#   - SYMBOL is display/filter information only
# =============================================================================


DB_PATH = "arunda.db"

ENGINE_NAME = "ARUNDA HISTORY QUERY LAYER"
ENGINE_VERSION = "HISTORY_QUERY_v0.1"


# =============================================================================
# EXCEPTIONS
# =============================================================================

class HistoryQueryError(Exception):
    """Base exception for the History Query Layer."""
    pass


class HistorySchemaError(HistoryQueryError):
    """Raised when the active history schema is incompatible."""
    pass


class HistoryReadError(HistoryQueryError):
    """Raised when a read operation fails."""
    pass


# =============================================================================
# REQUIRED SCHEMA
# =============================================================================

REQUIRED_HISTORY_COLUMNS = {
    "id",
    "timestamp",
    "cmc_id",
    "symbol",
    "name",
    "rank",
    "price",
    "market_cap",
    "volume_24h",
    "change_1h",
    "change_24h",
    "change_7d",
    "source",
    "source_timestamp",
    "engine_version",
    "created_at",
}


# =============================================================================
# HELPERS
# =============================================================================

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def row_to_dict(cursor: sqlite3.Cursor, row: tuple) -> Dict[str, Any]:
    columns = [description[0] for description in cursor.description]
    return dict(zip(columns, row))


# =============================================================================
# HISTORY QUERY LAYER
# =============================================================================

class HistoryQueryLayer:
    """
    Read-only query interface for the verified market_history table.

    Historical identity:
        (timestamp, cmc_id)

    Symbol is NEVER used as the unique identity.
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None

    # -------------------------------------------------------------------------
    # CONNECTION
    # -------------------------------------------------------------------------

    def connect(self) -> None:
        if self.conn is not None:
            return

        try:
            self.conn = sqlite3.connect(
                self.db_path,
                uri=False,
            )

            self.conn.row_factory = sqlite3.Row

            # Defensive read-only behavior at SQLite level.
            self.conn.execute("PRAGMA query_only = ON")

            self._validate_schema()

        except Exception as exc:
            self.close()

            if isinstance(exc, HistoryQueryError):
                raise

            raise HistoryReadError(
                f"Unable to connect to history database: {exc}"
            ) from exc

    def close(self) -> None:
        if self.conn is not None:
            self.conn.close()
            self.conn = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    # -------------------------------------------------------------------------
    # INTERNAL
    # -------------------------------------------------------------------------

    def _require_connection(self) -> sqlite3.Connection:
        if self.conn is None:
            self.connect()

        if self.conn is None:
            raise HistoryReadError("Database connection unavailable.")

        return self.conn

    def _validate_schema(self) -> None:
        conn = self._require_connection()

        try:
            rows = conn.execute(
                "PRAGMA table_info(market_history)"
            ).fetchall()

            if not rows:
                raise HistorySchemaError(
                    "market_history table does not exist."
                )

            actual_columns = {
                row["name"]
                for row in rows
            }

            missing = REQUIRED_HISTORY_COLUMNS - actual_columns

            if missing:
                raise HistorySchemaError(
                    "market_history schema missing columns: "
                    + ", ".join(sorted(missing))
                )

        except HistorySchemaError:
            raise

        except Exception as exc:
            raise HistorySchemaError(
                f"Schema validation failed: {exc}"
            ) from exc

    @staticmethod
    def _validate_cmc_id(cmc_id: int) -> int:
        try:
            value = int(cmc_id)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Invalid cmc_id: {cmc_id}"
            ) from exc

        if value <= 0:
            raise ValueError(
                f"cmc_id must be positive: {cmc_id}"
            )

        return value

    @staticmethod
    def _validate_limit(limit: int, maximum: int = 10000) -> int:
        try:
            value = int(limit)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Invalid limit: {limit}"
            ) from exc

        if value <= 0:
            raise ValueError(
                "limit must be greater than zero."
            )

        return min(value, maximum)

    @staticmethod
    def _validate_timestamp(timestamp: str) -> str:
        if not timestamp:
            raise ValueError("timestamp cannot be empty.")

        return str(timestamp)

    # -------------------------------------------------------------------------
    # 1. LATEST SNAPSHOT
    # -------------------------------------------------------------------------

    def get_latest_snapshot(self) -> List[Dict[str, Any]]:
        """
        Return all rows belonging to the latest historical snapshot.
        """

        conn = self._require_connection()

        try:
            row = conn.execute("""
                SELECT MAX(timestamp)
                FROM market_history
            """).fetchone()

            latest_timestamp = row[0]

            if latest_timestamp is None:
                return []

            cursor = conn.execute("""
                SELECT
                    id,
                    timestamp,
                    cmc_id,
                    symbol,
                    name,
                    rank,
                    price,
                    market_cap,
                    volume_24h,
                    change_1h,
                    change_24h,
                    change_7d,
                    source,
                    source_timestamp,
                    engine_version,
                    created_at
                FROM market_history
                WHERE timestamp = ?
                ORDER BY cmc_id
            """, (latest_timestamp,))

            return [dict(row) for row in cursor.fetchall()]

        except Exception as exc:
            raise HistoryReadError(
                f"Latest snapshot query failed: {exc}"
            ) from exc

    # -------------------------------------------------------------------------
    # 2. SNAPSHOT BY TIMESTAMP
    # -------------------------------------------------------------------------

    def get_snapshot(
        self,
        timestamp: str,
    ) -> List[Dict[str, Any]]:
        """
        Return one historical snapshot by exact timestamp.
        """

        conn = self._require_connection()

        timestamp = self._validate_timestamp(timestamp)

        try:
            cursor = conn.execute("""
                SELECT
                    id,
                    timestamp,
                    cmc_id,
                    symbol,
                    name,
                    rank,
                    price,
                    market_cap,
                    volume_24h,
                    change_1h,
                    change_24h,
                    change_7d,
                    source,
                    source_timestamp,
                    engine_version,
                    created_at
                FROM market_history
                WHERE timestamp = ?
                ORDER BY cmc_id
            """, (timestamp,))

            return [dict(row) for row in cursor.fetchall()]

        except Exception as exc:
            raise HistoryReadError(
                f"Snapshot query failed: {exc}"
            ) from exc

    # -------------------------------------------------------------------------
    # 3. ASSET HISTORY BY CMC_ID
    # -------------------------------------------------------------------------

    def get_asset_history(
        self,
        cmc_id: int,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Return historical records for one asset.

        IMPORTANT:
            Identity is CMC_ID.
            Symbol is NOT used for identity.
        """

        conn = self._require_connection()

        cmc_id = self._validate_cmc_id(cmc_id)
        limit = self._validate_limit(limit)

        try:
            cursor = conn.execute("""
                SELECT
                    id,
                    timestamp,
                    cmc_id,
                    symbol,
                    name,
                    rank,
                    price,
                    market_cap,
                    volume_24h,
                    change_1h,
                    change_24h,
                    change_7d,
                    source,
                    source_timestamp,
                    engine_version,
                    created_at
                FROM market_history
                WHERE cmc_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (cmc_id, limit))

            return [dict(row) for row in cursor.fetchall()]

        except Exception as exc:
            raise HistoryReadError(
                f"Asset history query failed: {exc}"
            ) from exc

    # -------------------------------------------------------------------------
    # 4. ASSET HISTORY RANGE
    # -------------------------------------------------------------------------

    def get_asset_history_range(
        self,
        cmc_id: int,
        start_timestamp: str,
        end_timestamp: str,
        limit: int = 10000,
    ) -> List[Dict[str, Any]]:
        """
        Return historical records for one CMC_ID within a timestamp range.
        """

        conn = self._require_connection()

        cmc_id = self._validate_cmc_id(cmc_id)
        start_timestamp = self._validate_timestamp(start_timestamp)
        end_timestamp = self._validate_timestamp(end_timestamp)
        limit = self._validate_limit(limit)

        if start_timestamp > end_timestamp:
            raise ValueError(
                "start_timestamp cannot be greater than end_timestamp."
            )

        try:
            cursor = conn.execute("""
                SELECT
                    id,
                    timestamp,
                    cmc_id,
                    symbol,
                    name,
                    rank,
                    price,
                    market_cap,
                    volume_24h,
                    change_1h,
                    change_24h,
                    change_7d,
                    source,
                    source_timestamp,
                    engine_version,
                    created_at
                FROM market_history
                WHERE cmc_id = ?
                  AND timestamp >= ?
                  AND timestamp <= ?
                ORDER BY timestamp ASC
                LIMIT ?
            """, (
                cmc_id,
                start_timestamp,
                end_timestamp,
                limit,
            ))

            return [dict(row) for row in cursor.fetchall()]

        except Exception as exc:
            raise HistoryReadError(
                f"Asset range query failed: {exc}"
            ) from exc

    # -------------------------------------------------------------------------
    # 5. RECENT SNAPSHOT HISTORY
    # -------------------------------------------------------------------------

    def get_snapshot_history(
        self,
        limit: int = 100,
    ) -> List[str]:
        """
        Return the latest distinct snapshot timestamps.
        """

        conn = self._require_connection()

        limit = self._validate_limit(limit)

        try:
            cursor = conn.execute("""
                SELECT DISTINCT timestamp
                FROM market_history
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))

            return [row[0] for row in cursor.fetchall()]

        except Exception as exc:
            raise HistoryReadError(
                f"Snapshot history query failed: {exc}"
            ) from exc

    # -------------------------------------------------------------------------
    # 6. HISTORY DEPTH
    # -------------------------------------------------------------------------

    def get_history_depth(
        self,
        cmc_id: int,
    ) -> Dict[str, Any]:
        """
        Return historical depth information for one CMC_ID.
        """

        conn = self._require_connection()

        cmc_id = self._validate_cmc_id(cmc_id)

        try:
            row = conn.execute("""
                SELECT
                    COUNT(*) AS records,
                    COUNT(DISTINCT timestamp) AS snapshots,
                    MIN(timestamp) AS first_timestamp,
                    MAX(timestamp) AS last_timestamp
                FROM market_history
                WHERE cmc_id = ?
            """, (cmc_id,)).fetchone()

            return {
                "cmc_id": cmc_id,
                "records": row["records"],
                "snapshots": row["snapshots"],
                "first_timestamp": row["first_timestamp"],
                "last_timestamp": row["last_timestamp"],
            }

        except Exception as exc:
            raise HistoryReadError(
                f"History depth query failed: {exc}"
            ) from exc

    # -------------------------------------------------------------------------
    # 7. AVAILABLE ASSETS
    # -------------------------------------------------------------------------

    def get_available_assets(self) -> List[Dict[str, Any]]:
        """
        Return all distinct historical CMC_ID identities.

        Multiple symbols with the same ticker remain separate assets.
        """

        conn = self._require_connection()

        try:
            cursor = conn.execute("""
                SELECT
                    cmc_id,
                    symbol,
                    name,
                    COUNT(*) AS records,
                    COUNT(DISTINCT timestamp) AS snapshots,
                    MIN(timestamp) AS first_timestamp,
                    MAX(timestamp) AS last_timestamp
                FROM market_history
                GROUP BY cmc_id
                ORDER BY cmc_id
            """)

            return [dict(row) for row in cursor.fetchall()]

        except Exception as exc:
            raise HistoryReadError(
                f"Available assets query failed: {exc}"
            ) from exc

    # -------------------------------------------------------------------------
    # 8. ASSET LATEST RECORD
    # -------------------------------------------------------------------------

    def get_asset_latest(
        self,
        cmc_id: int,
    ) -> Optional[Dict[str, Any]]:
        """
        Return the latest historical record for one CMC_ID.
        """

        conn = self._require_connection()

        cmc_id = self._validate_cmc_id(cmc_id)

        try:
            row = conn.execute("""
                SELECT
                    id,
                    timestamp,
                    cmc_id,
                    symbol,
                    name,
                    rank,
                    price,
                    market_cap,
                    volume_24h,
                    change_1h,
                    change_24h,
                    change_7d,
                    source,
                    source_timestamp,
                    engine_version,
                    created_at
                FROM market_history
                WHERE cmc_id = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (cmc_id,)).fetchone()

            if row is None:
                return None

            return dict(row)

        except Exception as exc:
            raise HistoryReadError(
                f"Latest asset query failed: {exc}"
            ) from exc

    # -------------------------------------------------------------------------
    # 9. SYMBOL OBSERVATION
    # -------------------------------------------------------------------------

    def get_symbol_assets(
        self,
        symbol: str,
    ) -> List[Dict[str, Any]]:
        """
        Return all CMC identities currently associated with a symbol.

        This method exists specifically for collision inspection.

        Example:
            AI → Gensyn
            AI → Sleepless AI

        It does NOT treat symbol as identity.
        """

        conn = self._require_connection()

        if not symbol:
            raise ValueError("symbol cannot be empty.")

        normalized_symbol = str(symbol).upper().strip()

        try:
            cursor = conn.execute("""
                SELECT
                    cmc_id,
                    symbol,
                    name,
                    COUNT(*) AS records,
                    COUNT(DISTINCT timestamp) AS snapshots,
                    MIN(timestamp) AS first_timestamp,
                    MAX(timestamp) AS last_timestamp
                FROM market_history
                WHERE UPPER(symbol) = ?
                GROUP BY cmc_id, symbol, name
                ORDER BY cmc_id
            """, (normalized_symbol,))

            return [dict(row) for row in cursor.fetchall()]

        except Exception as exc:
            raise HistoryReadError(
                f"Symbol asset query failed: {exc}"
            ) from exc

    # -------------------------------------------------------------------------
    # 10. GLOBAL HISTORY FINGERPRINT
    # -------------------------------------------------------------------------

    def get_fingerprint(self) -> Dict[str, Any]:
        """
        Return a read-only structural fingerprint of active history.
        """

        conn = self._require_connection()

        try:
            row = conn.execute("""
                SELECT
                    COUNT(*) AS rows,
                    COUNT(DISTINCT timestamp) AS snapshots,
                    COUNT(DISTINCT cmc_id) AS cmc_ids,
                    COUNT(DISTINCT symbol) AS symbols,
                    MIN(timestamp) AS first_timestamp,
                    MAX(timestamp) AS last_timestamp
                FROM market_history
            """).fetchone()

            duplicates = conn.execute("""
                SELECT COUNT(*)
                FROM (
                    SELECT timestamp, cmc_id
                    FROM market_history
                    GROUP BY timestamp, cmc_id
                    HAVING COUNT(*) > 1
                )
            """).fetchone()[0]

            return {
                "rows": row["rows"],
                "snapshots": row["snapshots"],
                "distinct_cmc_ids": row["cmc_ids"],
                "distinct_symbols": row["symbols"],
                "first_timestamp": row["first_timestamp"],
                "last_timestamp": row["last_timestamp"],
                "duplicate_identities": duplicates,
            }

        except Exception as exc:
            raise HistoryReadError(
                f"History fingerprint query failed: {exc}"
            ) from exc


# =============================================================================
# SIMPLE FUNCTION API
# =============================================================================
#
# These wrappers make the layer easy to consume from future engines without
# exposing the database connection itself.
# =============================================================================

def get_latest_snapshot(
    db_path: str = DB_PATH,
) -> List[Dict[str, Any]]:
    with HistoryQueryLayer(db_path) as history:
        return history.get_latest_snapshot()


def get_snapshot(
    timestamp: str,
    db_path: str = DB_PATH,
) -> List[Dict[str, Any]]:
    with HistoryQueryLayer(db_path) as history:
        return history.get_snapshot(timestamp)


def get_asset_history(
    cmc_id: int,
    limit: int = 100,
    db_path: str = DB_PATH,
) -> List[Dict[str, Any]]:
    with HistoryQueryLayer(db_path) as history:
        return history.get_asset_history(cmc_id, limit)


def get_asset_history_range(
    cmc_id: int,
    start_timestamp: str,
    end_timestamp: str,
    limit: int = 10000,
    db_path: str = DB_PATH,
) -> List[Dict[str, Any]]:
    with HistoryQueryLayer(db_path) as history:
        return history.get_asset_history_range(
            cmc_id,
            start_timestamp,
            end_timestamp,
            limit,
        )


def get_snapshot_history(
    limit: int = 100,
    db_path: str = DB_PATH,
) -> List[str]:
    with HistoryQueryLayer(db_path) as history:
        return history.get_snapshot_history(limit)


def get_history_depth(
    cmc_id: int,
    db_path: str = DB_PATH,
) -> Dict[str, Any]:
    with HistoryQueryLayer(db_path) as history:
        return history.get_history_depth(cmc_id)


def get_available_assets(
    db_path: str = DB_PATH,
) -> List[Dict[str, Any]]:
    with HistoryQueryLayer(db_path) as history:
        return history.get_available_assets()


def get_asset_latest(
    cmc_id: int,
    db_path: str = DB_PATH,
) -> Optional[Dict[str, Any]]:
    with HistoryQueryLayer(db_path) as history:
        return history.get_asset_latest(cmc_id)


def get_symbol_assets(
    symbol: str,
    db_path: str = DB_PATH,
) -> List[Dict[str, Any]]:
    with HistoryQueryLayer(db_path) as history:
        return history.get_symbol_assets(symbol)


def get_fingerprint(
    db_path: str = DB_PATH,
) -> Dict[str, Any]:
    with HistoryQueryLayer(db_path) as history:
        return history.get_fingerprint()


# =============================================================================
# SELF TEST
# =============================================================================

def self_test(db_path: str = DB_PATH) -> None:
    """
    Minimal read-only smoke test.
    """

    print("=" * 100)
    print("ARUNDA TRADER — HISTORY QUERY LAYER v0.1")
    print("SELF TEST")
    print("=" * 100)

    with HistoryQueryLayer(db_path) as history:

        print()
        print("DATABASE :", db_path)
        print("MODE     : READ ONLY")
        print("ENGINE   :", ENGINE_VERSION)

        print()
        print("SCHEMA VALIDATION")
        print("-" * 100)
        print("RESULT :", "PASS")

        fingerprint = history.get_fingerprint()

        print()
        print("HISTORY FINGERPRINT")
        print("-" * 100)
        print("Rows              :", fingerprint["rows"])
        print("Snapshots         :", fingerprint["snapshots"])
        print("Distinct CMC IDs  :", fingerprint["distinct_cmc_ids"])
        print("Distinct Symbols  :", fingerprint["distinct_symbols"])
        print("Duplicate IDs     :", fingerprint["duplicate_identities"])
        print("First Timestamp   :", fingerprint["first_timestamp"])
        print("Last Timestamp    :", fingerprint["last_timestamp"])

        latest = history.get_latest_snapshot()

        print()
        print("LATEST SNAPSHOT")
        print("-" * 100)
        print("Rows              :", len(latest))

        if latest:
            print("Timestamp         :", latest[0]["timestamp"])
            print(
                "Distinct CMC IDs  :",
                len({row["cmc_id"] for row in latest})
            )
            print(
                "Distinct Symbols  :",
                len({row["symbol"] for row in latest})
            )

        assets = history.get_available_assets()

        print()
        print("AVAILABLE ASSETS")
        print("-" * 100)
        print("Assets            :", len(assets))

        print()
        print("=" * 100)
        print("SELF TEST VERDICT")
        print("=" * 100)

        if (
            fingerprint["duplicate_identities"] == 0
            and fingerprint["distinct_cmc_ids"] == 1000
            and len(latest) == 1000
            and len(assets) == 1000
        ):
            print("RESULT : PASS")
            print("STATUS : HISTORY QUERY LAYER v0.1 READY")
        else:
            print("RESULT : FAIL")
            print("STATUS : INVESTIGATION REQUIRED")

        print("=" * 100)


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    self_test()