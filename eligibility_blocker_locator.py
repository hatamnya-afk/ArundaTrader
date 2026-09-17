# =============================================================================
# ARUNDA TRADER
# ELIGIBILITY BLOCKER LOCATOR v0.1
#
# PURPOSE:
#   Consume the CURRENT production artifact only.
#   Identify the exact eligibility blocker for existing rows.
#
# IMPORTANT:
#   READ ONLY
#   NO DB WRITE
#   NO ARTIFACT WRITE
#   NO STRATEGY CHANGE
#   NO THRESHOLD CHANGE
#   NO SIGNAL FABRICATION
#   NO BYPASS
#   NO REBUILD
#   NO FORENSIC RE-AUDIT
#
# NEXT TARGET:
#   If a real BUG/WIRING defect is exposed:
#
#       MINIMAL PRODUCTION REPAIR
#               ↓
#       REAL RUNTIME
#               ↓
#       REAL ELIGIBLE SIGNAL
#               ↓
#       ORDER INTENT
#               ↓
#       VALIDATION
#               ↓
#       EXECUTION GATE
#               ↓
#       FINAL LAUNCH GATE
# =============================================================================


import sqlite3
import math
import json
import os
import importlib


DB_PATH = "arunda.db"


# =============================================================================
# POSSIBLE ARTIFACT SOURCES
# =============================================================================
#
# The script first tries the known production artifact tables.
# It does NOT create anything.
#
# If your project stores the artifact in a Python module instead,
# the script reports that and stops cleanly.
# =============================================================================

ARTIFACT_TABLE_CANDIDATES = [
    "release_artifact",
    "release_artifacts",
    "signal_artifact",
    "signal_artifacts",
    "eligible_signals",
    "signal_candidates",
    "fusion_signals",
]


# =============================================================================
# HELPERS
# =============================================================================


def normalize(value):

    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    return text


def safe_float(value):

    if value is None:
        return None

    try:
        value = float(value)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(value):
        return None

    return value


def print_section(title):

    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


# =============================================================================
# DATABASE
# =============================================================================


def table_exists(conn, table_name):

    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        """,
        (table_name,),
    ).fetchone()

    return row is not None


def get_columns(conn, table_name):

    rows = conn.execute(
        'PRAGMA table_info("{}")'.format(
            table_name
        )
    ).fetchall()

    return [
        row[1]
        for row in rows
    ]


def discover_artifact_table(conn):

    found = []

    for table_name in ARTIFACT_TABLE_CANDIDATES:

        if table_exists(
            conn,
            table_name,
        ):

            columns = get_columns(
                conn,
                table_name,
            )

            found.append(
                (
                    table_name,
                    columns,
                )
            )

    return found


# =============================================================================
# ARTIFACT ROW LOADING
# =============================================================================


def load_current_rows():

    if not os.path.exists(DB_PATH):

        raise RuntimeError(
            "Database not found: "
            + DB_PATH
        )

    conn = sqlite3.connect(
        DB_PATH
    )

    conn.row_factory = sqlite3.Row

    try:

        artifacts = discover_artifact_table(
            conn
        )

        if not artifacts:

            raise RuntimeError(
                "No known artifact table found."
            )

        print_section(
            "ARTIFACT TABLE DISCOVERY"
        )

        for table_name, columns in artifacts:

            print(
                "TABLE :",
                table_name
            )

            print(
                "COLUMNS:",
                ", ".join(columns)
            )

        # ---------------------------------------------------------------------
        # Prefer the first table containing explicit eligibility information.
        # ---------------------------------------------------------------------

        preferred = None

        eligibility_names = {
            "eligible",
            "is_eligible",
            "eligibility",
            "trade_eligible",
            "eligible_signal",
        }

        for table_name, columns in artifacts:

            lowered = {
                str(column).lower()
                for column in columns
            }

            if lowered.intersection(
                eligibility_names
            ):

                preferred = (
                    table_name,
                    columns,
                )

                break

        if preferred is None:

            preferred = artifacts[0]

        table_name, columns = preferred

        print()
        print(
            "SELECTED ARTIFACT TABLE:",
            table_name
        )

        query = """
            SELECT *
            FROM "{table}"
        """.format(
            table=table_name
        )

        rows = conn.execute(
            query
        ).fetchall()

        # ---------------------------------------------------------------------
        # We expect the CURRENT artifact, not a newly constructed dataset.
        # ---------------------------------------------------------------------

        print(
            "ROWS FOUND:",
            len(rows)
        )

        return table_name, columns, rows

    finally:

        conn.close()


# =============================================================================
# ELIGIBILITY FIELD DISCOVERY
# =============================================================================


def find_field(
    columns,
    candidates,
):

    normalized = {
        str(column).lower(): column
        for column in columns
    }

    for candidate in candidates:

        key = str(candidate).lower()

        if key in normalized:

            return normalized[key]

    return None


def discover_eligibility_fields(columns):

    return {

        "eligible":
            find_field(
                columns,
                [
                    "eligible",
                    "is_eligible",
                    "trade_eligible",
                    "eligible_signal",
                ],
            ),

        "decision":
            find_field(
                columns,
                [
                    "decision",
                    "trade_decision",
                    "final_decision",
                ],
            ),

        "status":
            find_field(
                columns,
                [
                    "status",
                    "signal_status",
                ],
            ),

        "reason":
            find_field(
                columns,
                [
                    "reason",
                    "eligibility_reason",
                    "no_trade_reason",
                    "rejection_reason",
                ],
            ),

        "symbol":
            find_field(
                columns,
                [
                    "symbol",
                    "asset",
                    "ticker",
                ],
            ),

        "timestamp":
            find_field(
                columns,
                [
                    "timestamp",
                    "signal_timestamp",
                    "created_at",
                ],
            ),

        "score":
            find_field(
                columns,
                [
                    "score",
                    "fused_score",
                    "final_score",
                ],
            ),

        "direction":
            find_field(
                columns,
                [
                    "direction",
                    "signal_direction",
                    "side",
                ],
            ),

        "entry_price":
            find_field(
                columns,
                [
                    "entry_price",
                    "entry",
                ],
            ),

    }


# =============================================================================
# ROW DUMP
# =============================================================================


def print_row(
    row,
    index,
):

    print()
    print(
        "ROW",
        index
    )

    print(
        "-" * 100
    )

    for key in row.keys():

        value = row[key]

        print(
            "{:<35} : {}".format(
                key,
                repr(value),
            )
        )


# =============================================================================
# ELIGIBILITY ANALYSIS
# =============================================================================


def classify_row(
    row,
    fields,
):

    result = {
        "index": None,
        "eligible_value": None,
        "decision": None,
        "status": None,
        "reason": None,
        "blockers": [],
    }

    eligible_field = fields["eligible"]

    if eligible_field is not None:

        value = row[eligible_field]

        result["eligible_value"] = value

        if isinstance(
            value,
            str,
        ):

            normalized = value.strip().upper()

            if normalized in {
                "FALSE",
                "NO",
                "0",
                "N",
                "NONE",
            }:

                result["blockers"].append(
                    "EXPLICIT_ELIGIBLE_FALSE"
                )

    decision_field = fields["decision"]

    if decision_field is not None:

        value = row[decision_field]

        result["decision"] = value

        if normalize(value):

            decision = str(
                value
            ).strip().upper()

            if decision in {
                "NO_TRADE",
                "NO-TRADE",
                "NO TRADE",
                "NO_T",
            }:

                result["blockers"].append(
                    "DECISION_NO_TRADE"
                )

    status_field = fields["status"]

    if status_field is not None:

        result["status"] = row[
            status_field
        ]

    reason_field = fields["reason"]

    if reason_field is not None:

        result["reason"] = row[
            reason_field
        ]

        if normalize(
            result["reason"]
        ):

            result["blockers"].append(
                "EXPLICIT_REASON_PRESENT"
            )

    # -------------------------------------------------------------------------
    # Missing core fields are reported as evidence.
    # They are NOT repaired here.
    # -------------------------------------------------------------------------

    if eligible_field is None:

        result["blockers"].append(
            "NO_ELIGIBILITY_FIELD_IN_ARTIFACT"
        )

    if decision_field is None:

        result["blockers"].append(
            "NO_DECISION_FIELD_IN_ARTIFACT"
        )

    return result


# =============================================================================
# PRODUCTION MODULE DISCOVERY
# =============================================================================
#
# This does NOT modify or execute the production pipeline.
# It only checks whether the currently imported artifact exposes metadata
# useful for identifying the producer.
# =============================================================================


def inspect_known_modules():

    module_names = [
        "signal_engine",
        "signal_generator",
        "signal_pipeline",
        "release_preflight",
        "execution_preflight",
    ]

    print_section(
        "KNOWN PRODUCTION MODULE PRESENCE"
    )

    for module_name in module_names:

        try:

            module = importlib.import_module(
                module_name
            )

            print(
                "{:<30} : PRESENT".format(
                    module_name
                )
            )

            # Only inspect names.
            # Do NOT call functions.

            names = [
                name
                for name in dir(module)
                if (
                    "eligib" in name.lower()
                    or "signal" in name.lower()
                    or "decision" in name.lower()
                )
            ]

            if names:

                print(
                    "  Relevant names:",
                    ", ".join(
                        names
                    )
                )

        except Exception:

            print(
                "{:<30} : NOT IMPORTED".format(
                    module_name
                )
            )


# =============================================================================
# MAIN ANALYSIS
# =============================================================================


def main():

    print("=" * 100)

    print(
        "ARUNDA TRADER — ELIGIBILITY BLOCKER LOCATOR v0.1"
    )

    print("=" * 100)

    print(
        "MODE              : READ ONLY"
    )

    print(
        "DB WRITE           : NONE"
    )

    print(
        "ARTIFACT WRITE     : NONE"
    )

    print(
        "SIGNAL FABRICATION : NONE"
    )

    print(
        "THRESHOLD CHANGE   : NONE"
    )

    print(
        "STRATEGY CHANGE    : NONE"
    )

    print(
        "BYPASS             : NONE"
    )

    print()

    table_name, columns, rows = (
        load_current_rows()
    )

    print_section(
        "CURRENT ARTIFACT"
    )

    print(
        "Artifact table:",
        table_name
    )

    print(
        "Current rows:",
        len(rows)
    )

    fields = discover_eligibility_fields(
        columns
    )

    print()

    print(
        "Eligibility field:",
        fields["eligible"]
    )

    print(
        "Decision field:",
        fields["decision"]
    )

    print(
        "Status field:",
        fields["status"]
    )

    print(
        "Reason field:",
        fields["reason"]
    )

    print(
        "Symbol field:",
        fields["symbol"]
    )

    print(
        "Timestamp field:",
        fields["timestamp"]
    )

    print(
        "Score field:",
        fields["score"]
    )

    print(
        "Direction field:",
        fields["direction"]
    )

    print(
        "Entry field:",
        fields["entry_price"]
    )

    # -------------------------------------------------------------------------
    # Print every CURRENT row.
    # -------------------------------------------------------------------------

    print_section(
        "CURRENT ARTIFACT ROWS"
    )

    analyses = []

    for index, row in enumerate(
        rows,
        start=1,
    ):

        print_row(
            row,
            index,
        )

        analysis = classify_row(
            row,
            fields,
        )

        analysis["index"] = index

        analyses.append(
            analysis
        )

    # -------------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------------

    print_section(
        "ELIGIBILITY BLOCKER SUMMARY"
    )

    explicit_false = 0
    no_trade = 0
    reason_present = 0

    for analysis in analyses:

        if (
            "EXPLICIT_ELIGIBLE_FALSE"
            in analysis["blockers"]
        ):

            explicit_false += 1

        if (
            "DECISION_NO_TRADE"
            in analysis["blockers"]
        ):

            no_trade += 1

        if (
            "EXPLICIT_REASON_PRESENT"
            in analysis["blockers"]
        ):

            reason_present += 1

        print(
            "ROW {:>3} | eligible={} | decision={} | status={} | reason={} | blockers={}".format(
                analysis["index"],
                repr(
                    analysis[
                        "eligible_value"
                    ]
                ),
                repr(
                    analysis[
                        "decision"
                    ]
                ),
                repr(
                    analysis[
                        "status"
                    ]
                ),
                repr(
                    analysis[
                        "reason"
                    ]
                ),
                ", ".join(
                    analysis[
                        "blockers"
                    ]
                )
                if analysis[
                    "blockers"
                ]
                else "NONE",
            )
        )

    print()

    print(
        "Rows analyzed        :",
        len(rows)
    )

    print(
        "Explicit eligible=F  :",
        explicit_false
    )

    print(
        "NO_TRADE decisions   :",
        no_trade
    )

    print(
        "Rows with reason     :",
        reason_present
    )

    # -------------------------------------------------------------------------
    # Important conclusion.
    # -------------------------------------------------------------------------

    print_section(
        "ENGINEERING CONCLUSION"
    )

    if len(rows) == 0:

        print(
            "BLOCKER : CURRENT ARTIFACT CONTAINS ZERO ROWS"
        )

        print(
            "NEXT    : DO NOT REPAIR. RETURN TO THE EXISTING PRODUCTION RUNTIME BOUNDARY."
        )

    elif (
        fields["eligible"] is not None
        and explicit_false == len(rows)
    ):

        print(
            "BLOCKER : ALL CURRENT ROWS ARE EXPLICITLY INELIGIBLE."
        )

        print(
            "CAUSE   : MUST BE DETERMINED FROM THE EXISTING ELIGIBILITY PRODUCER."
        )

        print(
            "ACTION  : NO THRESHOLD/STRATEGY/BYPASS CHANGE."
        )

        print(
            "NEXT    : TRACE ONLY THE EXISTING ELIGIBILITY DECISION FOR THESE ROWS."
        )

    elif no_trade == len(rows):

        print(
            "BLOCKER : ALL CURRENT ROWS ARE NO_TRADE."
        )

        print(
            "CAUSE   : EXISTING NO_TRADE REASON/PRODUCER MUST BE CONSUMED."
        )

        print(
            "ACTION  : NO STRATEGY CHANGE."
        )

        print(
            "NEXT    : IDENTIFY THE EXISTING PRODUCTION CONDITION RESPONSIBLE."
        )

    else:

        print(
            "BLOCKER : NOT DETERMINED BY ARTIFACT FIELDS ALONE."
        )

        print(
            "ACTION  : DO NOT MODIFY ANY CONTRACT OR THRESHOLD."
        )

        print(
            "NEXT    : USE ONLY THE SPECIFIC EXISTING FIELD/PRODUCER EVIDENCE."
        )

    print()

    print(
        "IMPORTANT:"
    )

    print(
        "This script does NOT create an eligible signal."
    )

    print(
        "This script does NOT change eligibility."
    )

    print(
        "This script does NOT change strategy."
    )

    print(
        "This script does NOT modify the database."
    )

    print(
        "This script does NOT modify the artifact."
    )

    print()

    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )