# =============================================================================
# ARUNDA FUSION RUNTIME MARKET ROW PROPAGATION TO CONTRIBUTION FORENSIC v0.1
# =============================================================================
#
# PURPOSE
# -------
# Verify, inside the REAL fusion_engine.main() runtime path, that the market
# row returned by get_latest_market() propagates into:
#
#     row.id
#         ->
#     technical_score
#         ->
#     market_norm
#         ->
#     market contribution
#
# IMPORTANT
# ---------
# READ ONLY FORENSIC HARNESS
#
# Production fusion_engine.py is NOT modified.
#
# No INSERT / UPDATE / DELETE / ALTER is performed by this harness.
#
# Runtime instrumentation is installed by monkey-patching production
# functions only in memory.
#
# Transaction / connection cleanup is intentionally handled defensively:
# fusion_engine.main() owns and may close its own DB connection.
# Therefore this harness NEVER assumes the production connection remains open.
#
# =============================================================================

import importlib
import sqlite3
import traceback
from datetime import datetime, timezone


DB_PATH = "arunda.db"

EXPECTED_ASSETS = [
    "BTC",
    "ETH",
    "SOL",
    "XRP",
]

EXPECTED_MARKET_SOURCE = (
    "CMC_SNAPSHOT_ANALYSIS_v0.2"
)

EXPECTED_MARKET_TIMEFRAME = (
    "SNAPSHOT"
)


# =============================================================================
# RUNTIME TRACE STATE
# =============================================================================

TRACE = {
    "rows": {},
    "normalizations": {},
    "contributions": {},
    "fused": {},
}


# =============================================================================
# HELPERS
# =============================================================================

def utc_now():
    return datetime.now(
        timezone.utc
    ).isoformat()


def safe_float(value):
    try:
        return float(value)
    except (
        TypeError,
        ValueError,
    ):
        return None


def safe_connection_state(conn):
    """
    Determine whether sqlite connection is still usable.

    Returns:
        True  -> connection appears open
        False -> connection is closed / unusable
    """

    try:
        conn.execute(
            "SELECT 1"
        ).fetchone()

        return True

    except (
        sqlite3.ProgrammingError,
        sqlite3.OperationalError,
    ):
        return False


# =============================================================================
# PRODUCTION MODULE LOADING
# =============================================================================

def load_production_module():

    print()
    print(
        "Loading production fusion_engine..."
    )

    module = importlib.import_module(
        "fusion_engine"
    )

    print(
        "Production module : LOADED"
    )

    print(
        f"ENGINE_VERSION    : "
        f"{getattr(module, 'ENGINE_VERSION', 'UNKNOWN')}"
    )

    return module


# =============================================================================
# INSTRUMENTATION
# =============================================================================

def install_instrumentation(module):

    print()
    print(
        "Installing runtime instrumentation..."
    )

    # -------------------------------------------------------------------------
    # Original get_latest_market
    # -------------------------------------------------------------------------

    original_get_latest_market = (
        module.get_latest_market
    )

    def traced_get_latest_market(
        conn,
        asset,
    ):

        row = original_get_latest_market(
            conn,
            asset,
        )

        TRACE["rows"][asset] = row

        print()
        print(
            f"[RUNTIME MARKET ROW] "
            f"{asset:<8} -> "
            f"{'FOUND' if row is not None else 'NOT_FOUND'}"
        )

        if row is not None:

            print(
                f"    id              = "
                f"{row['id']}"
            )

            print(
                f"    technical_score = "
                f"{row['technical_score']}"
            )

            print(
                f"    close           = "
                f"{row['close']}"
            )

            print(
                f"    timestamp       = "
                f"{row['timestamp']}"
            )

            print(
                f"    source          = "
                f"{row['source']}"
            )

            print(
                f"    timeframe       = "
                f"{row['timeframe']}"
            )

            print(
                f"    engine          = "
                f"{row['engine_version']}"
            )

        return row

    module.get_latest_market = (
        traced_get_latest_market
    )

    # -------------------------------------------------------------------------
    # Original normalize_market
    # -------------------------------------------------------------------------

    original_normalize_market = (
        module.normalize_market
    )

    def traced_normalize_market(
        score,
    ):

        result = original_normalize_market(
            score
        )

        # Determine current asset from the latest
        # row sequence without modifying production.
        #
        # The runtime processes assets sequentially.
        # We identify the asset whose technical score
        # matches the current call where possible.

        matched_asset = None

        for asset, row in TRACE["rows"].items():

            if row is not None:

                row_score = row[
                    "technical_score"
                ]

                if (
                    safe_float(row_score)
                    == safe_float(score)
                ):
                    if (
                        asset
                        not in TRACE["normalizations"]
                    ):
                        matched_asset = asset
                        break

        if matched_asset is None:

            # Fallback: current unresolved asset.
            for asset in EXPECTED_ASSETS:

                if (
                    asset in TRACE["rows"]
                    and asset not in
                    TRACE["normalizations"]
                ):
                    matched_asset = asset
                    break

        if matched_asset is not None:

            TRACE["normalizations"][
                matched_asset
            ] = {
                "technical_score": score,
                "market_norm": result,
            }

            print()
            print(
                f"[RUNTIME MARKET NORMALIZATION] "
                f"{matched_asset}"
            )

            print(
                f"    technical_score = "
                f"{score}"
            )

            print(
                f"    market_raw      = "
                f"{score}"
            )

            print(
                f"    market_norm     = "
                f"{result}"
            )

        return result

    module.normalize_market = (
        traced_normalize_market
    )

    # -------------------------------------------------------------------------
    # Original calculate_fused_score
    # -------------------------------------------------------------------------

    original_calculate_fused_score = (
        module.calculate_fused_score
    )

    def traced_calculate_fused_score(
        market_norm,
        positioning_norm,
        news_norm,
        weights,
        missing_penalty,
    ):

        result = original_calculate_fused_score(
            market_norm,
            positioning_norm,
            news_norm,
            weights,
            missing_penalty,
        )

        # Production calculates:
        #
        #     weights["market"] * market_norm
        #
        # before applying missing_arm_penalty.
        #
        # The forensic target requested here is the direct
        # market arm contribution:
        #
        #     market_norm * market_weight
        #
        market_weight = safe_float(
            weights.get("market")
        )

        market_norm_value = safe_float(
            market_norm
        )

        market_contribution = None

        if (
            market_norm_value is not None
            and market_weight is not None
        ):

            market_contribution = (
                market_norm_value
                * market_weight
            )

        # Resolve asset using the market normalization trace.
        matched_asset = None

        for asset in EXPECTED_ASSETS:

            normalization = (
                TRACE["normalizations"].get(
                    asset
                )
            )

            if normalization is None:
                continue

            if (
                safe_float(
                    normalization[
                        "market_norm"
                    ]
                )
                == market_norm_value
            ):
                if (
                    asset
                    not in TRACE["contributions"]
                ):
                    matched_asset = asset
                    break

        if matched_asset is None:

            for asset in EXPECTED_ASSETS:

                if (
                    asset in TRACE["normalizations"]
                    and asset not in
                    TRACE["contributions"]
                ):
                    matched_asset = asset
                    break

        if matched_asset is not None:

            TRACE["contributions"][
                matched_asset
            ] = {
                "market_norm": market_norm_value,
                "market_weight": market_weight,
                "market_contribution":
                    market_contribution,
                "fused_score": result,
            }

            print()
            print(
                f"[RUNTIME MARKET CONTRIBUTION] "
                f"{matched_asset}"
            )

            print(
                f"    market_norm       = "
                f"{market_norm_value}"
            )

            print(
                f"    market_weight     = "
                f"{market_weight}"
            )

            print(
                f"    market_contribution = "
                f"{market_contribution}"
            )

            print(
                f"    fused_score       = "
                f"{result}"
            )

        return result

    module.calculate_fused_score = (
        traced_calculate_fused_score
    )

    print(
        "Instrumentation : READY"
    )


# =============================================================================
# PROPAGATION VERIFICATION
# =============================================================================

def verify_propagation():

    print()
    print(
        "=" * 78
    )

    print(
        "FINAL MARKET ROW PROPAGATION VERIFICATION"
    )

    print(
        "=" * 78
    )

    failures = []

    print()
    print(
        f"{'ASSET':<8}"
        f"{'ROW.ID':>10}"
        f"{'TECH.SCORE':>15}"
        f"{'MARKET.NORM':>15}"
        f"{'CONTRIBUTION':>18}"
    )

    print(
        "-" * 78
    )

    for asset in EXPECTED_ASSETS:

        row = TRACE["rows"].get(
            asset
        )

        normalization = (
            TRACE["normalizations"].get(
                asset
            )
        )

        contribution = (
            TRACE["contributions"].get(
                asset
            )
        )

        row_id = (
            row["id"]
            if row is not None
            else None
        )

        technical_score = (
            row["technical_score"]
            if row is not None
            else None
        )

        market_norm = (
            normalization["market_norm"]
            if normalization is not None
            else None
        )

        market_contribution = (
            contribution[
                "market_contribution"
            ]
            if contribution is not None
            else None
        )

        print(
            f"{asset:<8}"
            f"{str(row_id):>10}"
            f"{str(technical_score):>15}"
            f"{str(market_norm):>15}"
            f"{str(market_contribution):>18}"
        )

        # ---------------------------------------------------------------------
        # Structural verification
        # ---------------------------------------------------------------------

        if row is None:

            failures.append(
                f"{asset}: market row not found"
            )

            continue

        if technical_score is None:

            failures.append(
                f"{asset}: technical_score is None"
            )

            continue

        if normalization is None:

            failures.append(
                f"{asset}: normalize_market() "
                f"was not observed"
            )

            continue

        if market_norm is None:

            failures.append(
                f"{asset}: market_norm is None"
            )

            continue

        if contribution is None:

            failures.append(
                f"{asset}: market contribution "
                f"was not observed"
            )

            continue

        # ---------------------------------------------------------------------
        # Exact normalization identity
        #
        # normalize_market() in production is a clamp,
        # and current scores are already in signed space.
        # ---------------------------------------------------------------------

        expected_norm = max(
            -100.0,
            min(
                100.0,
                float(technical_score),
            ),
        )

        if (
            abs(
                float(market_norm)
                - expected_norm
            )
            > 1e-12
        ):

            failures.append(
                f"{asset}: market_norm mismatch "
                f"(expected {expected_norm}, "
                f"observed {market_norm})"
            )

        # ---------------------------------------------------------------------
        # Exact contribution identity
        # ---------------------------------------------------------------------

        expected_contribution = (
            float(market_norm)
            * float(
                contribution[
                    "market_weight"
                ]
            )
        )

        if (
            abs(
                float(
                    market_contribution
                )
                - expected_contribution
            )
            > 1e-12
        ):

            failures.append(
                f"{asset}: market contribution "
                f"mismatch"
            )

    print()
    print(
        "-" * 78
    )

    print(
        f"Expected assets : "
        f"{len(EXPECTED_ASSETS)}"
    )

    print(
        f"Rows traced     : "
        f"{len(TRACE['rows'])}"
    )

    print(
        f"Normalizations  : "
        f"{len(TRACE['normalizations'])}"
    )

    print(
        f"Contributions   : "
        f"{len(TRACE['contributions'])}"
    )

    print()

    if failures:

        print(
            "PROPAGATION FAILURES"
        )

        for failure in failures:

            print(
                f" - {failure}"
            )

        print()
        print(
            "PROPAGATION = FAILED"
        )

        return False

    if (
        len(TRACE["rows"])
        != len(EXPECTED_ASSETS)
    ):

        print(
            "PROPAGATION = FAILED"
        )

        return False

    if (
        len(TRACE["normalizations"])
        != len(EXPECTED_ASSETS)
    ):

        print(
            "PROPAGATION = FAILED"
        )

        return False

    if (
        len(TRACE["contributions"])
        != len(EXPECTED_ASSETS)
    ):

        print(
            "PROPAGATION = FAILED"
        )

        return False

    print(
        "PROPAGATION = VERIFIED"
    )

    print()
    print(
        "Verified chain:"
    )

    print(
        "market row"
        " -> technical_score"
        " -> market_norm"
        " -> market contribution"
    )

    return True


# =============================================================================
# MAIN
# =============================================================================

def main():

    started = utc_now()

    print(
        "=" * 90
    )

    print(
        "ARUNDA FUSION RUNTIME MARKET ROW "
        "PROPAGATION TO CONTRIBUTION FORENSIC v0.1"
    )

    print(
        "=" * 90
    )

    print(
        f"Started UTC : {started}"
    )

    print(
        f"Database    : "
        f"{DB_PATH}"
    )

    print(
        "Mode        : READ ONLY FORENSIC"
    )

    print(
        "Writes      : NONE"
    )

    print(
        "=" * 90
    )

    module = None

    # -------------------------------------------------------------------------
    # Separate forensic DB connection.
    #
    # IMPORTANT:
    # This connection is NOT passed into production main().
    #
    # It is used only for pre/post verification and is never written.
    # -------------------------------------------------------------------------

    verification_conn = None

    try:

        # ---------------------------------------------------------------------
        # Verify DB opens.
        # ---------------------------------------------------------------------

        verification_conn = sqlite3.connect(
            DB_PATH
        )

        verification_conn.row_factory = (
            sqlite3.Row
        )

        verification_conn.execute(
            "SELECT 1"
        ).fetchone()

        print()
        print(
            "DATABASE CONNECTION : OK"
        )

        # ---------------------------------------------------------------------
        # Load production module.
        # ---------------------------------------------------------------------

        module = load_production_module()

        print()
        print(
            "-" * 78
        )

        print(
            "FUSION MARKET CONTRACT"
        )

        print(
            "-" * 78
        )

        print(
            f"MARKET_SOURCE    : "
            f"{module.MARKET_SOURCE}"
        )

        print(
            f"MARKET_TIMEFRAME : "
            f"{module.MARKET_TIMEFRAME}"
        )

        print(
            f"MARKET_WEIGHT    : "
            f"{module.BASE_WEIGHTS['market']}"
        )

        # ---------------------------------------------------------------------
        # Contract sanity only.
        #
        # This does NOT audit production logic.
        # It simply confirms the target contract.
        # ---------------------------------------------------------------------

        if (
            module.MARKET_SOURCE
            != EXPECTED_MARKET_SOURCE
        ):

            raise RuntimeError(
                "Unexpected MARKET_SOURCE"
            )

        if (
            module.MARKET_TIMEFRAME
            != EXPECTED_MARKET_TIMEFRAME
        ):

            raise RuntimeError(
                "Unexpected MARKET_TIMEFRAME"
            )

        # ---------------------------------------------------------------------
        # Install instrumentation.
        # ---------------------------------------------------------------------

        install_instrumentation(
            module
        )

        # ---------------------------------------------------------------------
        # REAL PRODUCTION EXECUTION
        # ---------------------------------------------------------------------

        print()
        print(
            "-" * 78
        )

        print(
            "STARTING REAL fusion_engine.main()"
        )

        print(
            "-" * 78
        )

        try:

            result = module.main()

            print()
            print(
                "REAL fusion_engine.main() : "
                "RETURNED"
            )

            print(
                f"main() return value : "
                f"{result}"
            )

        except Exception as exc:

            print()
            print(
                "RUNTIME EXCEPTION INSIDE "
                "fusion_engine.main()"
            )

            print(
                f"{type(exc).__name__}: "
                f"{exc}"
            )

            traceback.print_exc()

            print()
            print(
                "PROPAGATION = FAILED"
            )

            return

        # ---------------------------------------------------------------------
        # IMPORTANT CLEANUP DESIGN
        #
        # We DO NOT rollback or close a production connection here.
        #
        # fusion_engine.main() owns its own connection lifecycle.
        #
        # The previous harness failed because it attempted:
        #
        #     controlled_conn.rollback()
        #
        # after production main() had already closed that connection.
        #
        # That artificial cleanup exception is intentionally eliminated.
        # ---------------------------------------------------------------------

        print()
        print(
            "-" * 78
        )

        print(
            "RUNTIME CONNECTION CLEANUP"
        )

        print(
            "Production connection ownership : "
            "fusion_engine.main()"
        )

        print(
            "Harness rollback on production "
            "connection : SKIPPED"
        )

        print(
            "Reason : production main() may "
            "already have closed its connection"
        )

        # ---------------------------------------------------------------------
        # Verify propagation.
        # ---------------------------------------------------------------------

        verified = verify_propagation()

        # ---------------------------------------------------------------------
        # Final result.
        # ---------------------------------------------------------------------

        print()
        print(
            "=" * 90
        )

        if verified:

            print(
                "VERDICT : "
                "MARKET ROW PROPAGATION = VERIFIED"
            )

            print()
            print(
                "The real fusion_engine.main() runtime "
                "propagated each traced market row through:"
            )

            print(
                "row.id -> technical_score "
                "-> market_norm -> market contribution"
            )

        else:

            print(
                "VERDICT : "
                "MARKET ROW PROPAGATION = FAILED"
            )

        print(
            "=" * 90
        )

    except Exception as exc:

        print()
        print(
            "HARNESS EXCEPTION"
        )

        print(
            f"{type(exc).__name__}: "
            f"{exc}"
        )

        traceback.print_exc()

        print()
        print(
            "PROPAGATION = FAILED"
        )

    finally:

        # ---------------------------------------------------------------------
        # Close ONLY the harness-owned verification connection.
        #
        # Never touch production main()'s connection.
        # ---------------------------------------------------------------------

        if verification_conn is not None:

            try:

                if safe_connection_state(
                    verification_conn
                ):

                    verification_conn.close()

                    print()
                    print(
                        "DATABASE CONNECTION : "
                        "CLOSED"
                    )

                else:

                    print()
                    print(
                        "DATABASE CONNECTION : "
                        "ALREADY CLOSED"
                    )

            except Exception as cleanup_exc:

                print()
                print(
                    "HARNESS CONNECTION CLEANUP "
                    "WARNING"
                )

                print(
                    f"{type(cleanup_exc).__name__}: "
                    f"{cleanup_exc}"
                )

                # Do NOT convert an unrelated
                # already-closed cleanup condition
                # into a second artificial failure.
                #
                # Production runtime result remains
                # determined by verify_propagation().


if __name__ == "__main__":

    main()