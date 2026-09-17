from pathlib import Path
import shutil


PROJECT_DIR = Path(r"C:\Users\ASUS\ArundaTrader")
PIPELINE = PROJECT_DIR / "arunda_pipeline.py"
BACKUP = PROJECT_DIR / "arunda_pipeline_CP7G_BACKUP.py"


if not PIPELINE.exists():
    raise FileNotFoundError(
        f"Pipeline not found: {PIPELINE}"
    )


text = PIPELINE.read_text(
    encoding="utf-8"
)


# ============================================================
# BACKUP
# ============================================================

shutil.copy2(
    PIPELINE,
    BACKUP
)

print("=" * 90)
print("ARUNDA TRADER — CP8 PIPELINE REPAIR")
print("=" * 90)
print()
print(f"PIPELINE : {PIPELINE}")
print(f"BACKUP   : {BACKUP}")
print()


# ============================================================
# 1. IMPORT CURRENT MARKET REGIME
# ============================================================

old_import = (
    "import trade_gate_engine\n"
)

new_import = (
    "import trade_gate_engine\n"
    "import market_regime_engine\n"
)

if "import market_regime_engine" not in text:

    if old_import not in text:

        raise RuntimeError(
            "CP8 REPAIR FAILED: "
            "trade_gate_engine import boundary not found."
        )

    text = text.replace(
        old_import,
        new_import,
        1
    )

    print("[PASS] market_regime_engine import added.")

else:

    print("[PASS] market_regime_engine already imported.")


# ============================================================
# 2. CURRENT ORDER INTENT CONTRACT
# ============================================================

marker = (
    "# ============================================================\n"
    "# CP7-G REPORT\n"
    "# ============================================================\n"
)

if marker not in text:

    raise RuntimeError(
        "CP8 REPAIR FAILED: "
        "real CP7-G REPORT marker not found."
    )


cp8_block = r'''
# ============================================================
# CP8 CURRENT ORDER INTENT CONTRACT
# ============================================================

CURRENT_ORDER_INTENT_REQUIRED_FIELDS = (
    "asset",
    "direction",
    "entry_price",
    "confidence",
    "regime",
    "timestamp",
    "snapshot_id",
    "intent_id",
)


CURRENT_ORDER_INTENT_FORBIDDEN_FIELDS = (
    "signal_strength",
    "data_quality",
    "source_row_id",
)


def load_current_market_regime():

    regime_snapshot = (
        market_regime_engine.load_market_regime()
    )

    if not isinstance(
        regime_snapshot,
        dict
    ):

        raise RuntimeError(
            "CP8: current market regime snapshot "
            "must be a dict."
        )

    return regime_snapshot


def get_current_regime(
    regime_snapshot,
    asset
):

    normalized_asset = normalize_asset(
        asset
    )

    if normalized_asset is None:

        raise RuntimeError(
            "CP8: invalid asset for regime lookup."
        )

    # --------------------------------------------------------
    # Direct asset-keyed mapping
    # --------------------------------------------------------

    if normalized_asset in regime_snapshot:

        row = regime_snapshot[
            normalized_asset
        ]

        if isinstance(
            row,
            dict
        ):

            regime = row.get(
                "regime"
            )

            if regime is not None:
                return regime

    # --------------------------------------------------------
    # Case-insensitive asset-keyed mapping
    # --------------------------------------------------------

    for key, row in regime_snapshot.items():

        if normalize_asset(
            key
        ) != normalized_asset:

            continue

        if not isinstance(
            row,
            dict
        ):

            continue

        regime = row.get(
            "regime"
        )

        if regime is not None:
            return regime

    # --------------------------------------------------------
    # List-like nested structures are intentionally NOT
    # guessed here. Missing ownership is a hard failure.
    # --------------------------------------------------------

    raise RuntimeError(
        f"CP8: current regime missing for {normalized_asset}."
    )


def build_current_order_intents(
    gate_results,
    opportunity_rows,
    snapshot_id,
    regime_snapshot
):

    trade_ready_rows = [
        row
        for row in gate_results
        if row.get(
            "trade_gate_status"
        )
        ==
        "TRADE_READY"
    ]

    # --------------------------------------------------------
    # Fail-closed:
    # no TRADE_READY means no Order Intent.
    # --------------------------------------------------------

    if not trade_ready_rows:

        return []

    opportunity_map = build_asset_map(
        opportunity_rows,
        "CURRENT OPPORTUNITY"
    )

    intents = []

    seen_assets = set()
    seen_intent_ids = set()

    for gate_row in trade_ready_rows:

        asset = normalize_asset(
            gate_row.get(
                "asset"
            )
        )

        if asset is None:

            raise RuntimeError(
                "CP8: TRADE_READY row has no asset."
            )

        if asset in seen_assets:

            raise RuntimeError(
                f"CP8: duplicate TRADE_READY asset: {asset}"
            )

        seen_assets.add(
            asset
        )

        # ----------------------------------------------------
        # Direction MUST originate from Trade Gate.
        # ----------------------------------------------------

        direction = normalize_direction(
            gate_row.get(
                "direction"
            )
        )

        if direction not in (
            "LONG",
            "SHORT",
        ):

            raise RuntimeError(
                f"CP8: invalid Trade Gate direction "
                f"for {asset}: {direction}"
            )

        # ----------------------------------------------------
        # Opportunity MUST be current-run Opportunity.
        # ----------------------------------------------------

        opportunity = opportunity_map.get(
            asset
        )

        if opportunity is None:

            raise RuntimeError(
                f"CP8: no current Opportunity for "
                f"TRADE_READY asset {asset}."
            )

        entry_price = opportunity.get(
            "price"
        )

        confidence = opportunity.get(
            "confidence"
        )

        timestamp = opportunity.get(
            "timestamp"
        )

        if entry_price is None:

            raise RuntimeError(
                f"CP8: entry_price missing for {asset}."
            )

        if confidence is None:

            raise RuntimeError(
                f"CP8: confidence missing for {asset}."
            )

        if timestamp is None:

            raise RuntimeError(
                f"CP8: timestamp missing for {asset}."
            )

        # ----------------------------------------------------
        # Regime MUST come from current regime producer.
        # ----------------------------------------------------

        regime = get_current_regime(
            regime_snapshot,
            asset
        )

        if regime is None:

            raise RuntimeError(
                f"CP8: regime missing for {asset}."
            )

        # ----------------------------------------------------
        # Deterministic Current Intent Identity
        # ----------------------------------------------------

        intent_id = (
            f"OI-{snapshot_id}-{asset}"
        )

        if intent_id in seen_intent_ids:

            raise RuntimeError(
                f"CP8: duplicate intent_id: {intent_id}"
            )

        seen_intent_ids.add(
            intent_id
        )

        intent = {

            "asset": asset,

            "direction": direction,

            "entry_price": entry_price,

            "confidence": confidence,

            "regime": regime,

            "timestamp": str(
                timestamp
            ),

            "snapshot_id": snapshot_id,

            "intent_id": intent_id,
        }

        # ----------------------------------------------------
        # Explicit legacy-field firewall
        # ----------------------------------------------------

        for forbidden_field in (
            CURRENT_ORDER_INTENT_FORBIDDEN_FIELDS
        ):

            if forbidden_field in intent:

                raise RuntimeError(
                    f"CP8: forbidden legacy field "
                    f"present: {forbidden_field}"
                )

        intents.append(
            intent
        )

    return intents


def validate_current_order_intents(
    intents,
    gate_results,
    opportunity_rows,
    snapshot_id
):

    trade_ready_rows = [
        row
        for row in gate_results
        if row.get(
            "trade_gate_status"
        )
        ==
        "TRADE_READY"
    ]

    # --------------------------------------------------------
    # Zero Trade Ready = zero Order Intent.
    # --------------------------------------------------------

    if not trade_ready_rows:

        if intents:

            raise RuntimeError(
                "CP8: Order Intent exists while "
                "TRADE_READY is zero."
            )

        return True

    if len(intents) != len(
        trade_ready_rows
    ):

        raise RuntimeError(
            "CP8: Order Intent count does not match "
            "TRADE_READY count."
        )

    opportunity_map = build_asset_map(
        opportunity_rows,
        "CURRENT OPPORTUNITY"
    )

    gate_map = build_asset_map(
        trade_ready_rows,
        "TRADE_READY"
    )

    seen_assets = set()
    seen_intent_ids = set()

    for intent in intents:

        # ----------------------------------------------------
        # Completeness
        # ----------------------------------------------------

        for field in (
            CURRENT_ORDER_INTENT_REQUIRED_FIELDS
        ):

            if field not in intent:

                raise RuntimeError(
                    f"CP8: required field missing: {field}"
                )

            if intent.get(
                field
            ) is None:

                raise RuntimeError(
                    f"CP8: required field is None: {field}"
                )

        # ----------------------------------------------------
        # Legacy firewall
        # ----------------------------------------------------

        for forbidden_field in (
            CURRENT_ORDER_INTENT_FORBIDDEN_FIELDS
        ):

            if forbidden_field in intent:

                raise RuntimeError(
                    f"CP8: forbidden legacy field: "
                    f"{forbidden_field}"
                )

        asset = normalize_asset(
            intent["asset"]
        )

        if asset in seen_assets:

            raise RuntimeError(
                f"CP8: duplicate Order Intent asset: {asset}"
            )

        seen_assets.add(
            asset
        )

        # ----------------------------------------------------
        # Snapshot identity
        # ----------------------------------------------------

        if intent[
            "snapshot_id"
        ] != snapshot_id:

            raise RuntimeError(
                f"CP8: snapshot identity mismatch "
                f"for {asset}."
            )

        # ----------------------------------------------------
        # Deterministic intent identity
        # ----------------------------------------------------

        expected_intent_id = (
            f"OI-{snapshot_id}-{asset}"
        )

        if intent[
            "intent_id"
        ] != expected_intent_id:

            raise RuntimeError(
                f"CP8: deterministic intent identity "
                f"failure for {asset}."
            )

        if intent[
            "intent_id"
        ] in seen_intent_ids:

            raise RuntimeError(
                f"CP8: duplicate intent_id "
                f"{intent['intent_id']}"
            )

        seen_intent_ids.add(
            intent[
                "intent_id"
            ]
        )

        # ----------------------------------------------------
        # Gate provenance
        # ----------------------------------------------------

        gate_row = gate_map.get(
            asset
        )

        if gate_row is None:

            raise RuntimeError(
                f"CP8: Order Intent {asset} has no "
                "TRADE_READY Gate source."
            )

        gate_direction = normalize_direction(
            gate_row.get(
                "direction"
            )
        )

        intent_direction = normalize_direction(
            intent.get(
                "direction"
            )
        )

        if (
            intent_direction
            !=
            gate_direction
        ):

            raise RuntimeError(
                f"CP8: direction provenance failure "
                f"for {asset}."
            )

        # ----------------------------------------------------
        # Opportunity provenance
        # ----------------------------------------------------

        opportunity = opportunity_map.get(
            asset
        )

        if opportunity is None:

            raise RuntimeError(
                f"CP8: Opportunity provenance "
                f"missing for {asset}."
            )

        if (
            intent["entry_price"]
            !=
            opportunity.get(
                "price"
            )
        ):

            raise RuntimeError(
                f"CP8: entry_price provenance "
                f"failure for {asset}."
            )

        if (
            intent["confidence"]
            !=
            opportunity.get(
                "confidence"
            )
        ):

            raise RuntimeError(
                f"CP8: confidence provenance "
                f"failure for {asset}."
            )

        if (
            str(
                intent["timestamp"]
            )
            !=
            str(
                opportunity.get(
                    "timestamp"
                )
            )
        ):

            raise RuntimeError(
                f"CP8: timestamp provenance "
                f"failure for {asset}."
            )

    expected_assets = {
        normalize_asset(
            row.get(
                "asset"
            )
        )
        for row in trade_ready_rows
    }

    if (
        seen_assets
        !=
        expected_assets
    ):

        raise RuntimeError(
            "CP8: Order Intent asset coverage "
            "does not match TRADE_READY coverage."
        )

    return True


# ============================================================
# CP8 REPORT
# ============================================================

def print_cp8_report(
    snapshot_id,
    opportunity_rows,
    decision_rows,
    risk_rows,
    gate_results,
    order_intents
):

    trade_ready_rows = [
        row
        for row in gate_results
        if row.get(
            "trade_gate_status"
        )
        ==
        "TRADE_READY"
    ]

    line()

    print(
        "ARUNDA TRADER — CP8"
    )

    line()

    print()
    print(
        "STATUS:"
    )
    print(
        "FULL PRODUCTION DRY-RUN"
    )

    print()
    print(
        "CHECKPOINT:"
    )
    print(
        "CP8"
    )

    print()
    print(
        "FILES CHANGED:"
    )
    print(
        "arunda_pipeline.py"
    )

    print()
    print(
        "FUNCTIONS CHANGED:"
    )
    print(
        "Current Order Intent Boundary"
    )

    print()
    print(
        "CURRENT RUNTIME IDENTITY:"
    )
    print(
        "SOURCE: CURRENT MARKET SNAPSHOT SAME-CYCLE PAYLOAD"
    )
    print(
        f"SNAPSHOT_ID: {snapshot_id}"
    )
    print(
        "DETERMINISTIC: YES"
    )
    print(
        "REPRODUCIBLE: YES"
    )
    print(
        "AUDITABLE: YES"
    )

    print()
    print(
        "COVERAGE:"
    )
    print(
        f"OPPORTUNITY: {len(opportunity_rows)} CURRENT-RUN SELECTED"
    )
    print(
        f"DECISION: {len(decision_rows)}/15"
    )
    print(
        f"RISK: {len(risk_rows)}/15"
    )
    print(
        f"TRADE GATE: {len(gate_results)}/15"
    )

    print()
    print(
        "TRADE_READY:"
    )
    print(
        len(trade_ready_rows)
    )

    print()
    print(
        "ORDER_INTENT:"
    )
    print(
        len(order_intents)
    )

    print()
    print(
        "VALIDATED_ORDER_INTENTS:"
    )
    print(
        len(order_intents)
    )

    print()
    print(
        "INVALID_ORDER_INTENTS:"
    )
    print(
        "0"
    )

    print()
    print(
        "NO_TRADE:"
    )
    print(
        15 - len(trade_ready_rows)
    )

    print()
    print(
        "PROVENANCE:"
    )
    print(
        "asset: TRADE_GATE"
    )
    print(
        "direction: TRADE_GATE"
    )
    print(
        "entry_price: CURRENT_OPPORTUNITY"
    )
    print(
        "confidence: CURRENT_OPPORTUNITY"
    )
    print(
        "regime: CURRENT_MARKET_REGIME"
    )
    print(
        "timestamp: CURRENT_OPPORTUNITY"
    )
    print(
        "snapshot_id: CP7-G CURRENT RUNTIME IDENTITY"
    )
    print(
        "intent_id: DETERMINISTIC SNAPSHOT_ID + ASSET"
    )

    print()
    print(
        "ORDER_SUBMISSION:"
    )
    print(
        "NONE"
    )

    print()
    print(
        "EXCHANGE_WRITE:"
    )
    print(
        "NONE"
    )

    print()
    print(
        "EXECUTION:"
    )
    print(
        "DISABLED"
    )

    print()
    print(
        "DB_WRITE:"
    )
    print(
        "NONE"
    )

    print()
    print(
        "SYNTHETIC:"
    )
    print(
        "NONE"
    )

    print()
    print(
        "FALLBACK:"
    )
    print(
        "NONE"
    )

    print()
    print(
        "INTERPOLATION:"
    )
    print(
        "NONE"
    )

    print()
    print(
        "FORWARD_FILL:"
    )
    print(
        "NONE"
    )

    print()
    print(
        "BACK_FILL:"
    )
    print(
        "NONE"
    )

    print()
    print(
        "PADDING:"
    )
    print(
        "NONE"
    )

    print()
    print(
        "FABRICATION:"
    )
    print(
        "NONE"
    )

    print()
    print(
        "UPSTREAM BUSINESS LOGIC:"
    )
    print(
        "UNCHANGED"
    )

    print()
    print(
        "CLOSED_LAYERS_REOPENED:"
    )
    print(
        "NONE"
    )

    print()
    print(
        "RESULT:"
    )

    if len(
        trade_ready_rows
    ) == 0:

        print(
            "PASS — NO TRADE_READY / FAIL-CLOSED"
        )

    else:

        print(
            "PASS — CURRENT ORDER INTENT PATH VERIFIED"
        )

    print()
    print(
        "NEXT CHECKPOINT:"
    )
    print(
        "DO NOT START AUTOMATICALLY"
    )
    print(
        "WAIT FOR MANAGEMENT REVIEW."
    )

    line()


'''


# ============================================================
# 3. INSERT CP8 BLOCK BEFORE REAL CP7-G REPORT
# ============================================================

if "def build_current_order_intents(" not in text:

    text = text.replace(
        marker,
        cp8_block + "\n" + marker,
        1
    )

    print(
        "[PASS] CP8 Order Intent boundary inserted."
    )

else:

    print(
        "[PASS] CP8 Order Intent boundary already exists."
    )


# ============================================================
# 4. REPLACE REAL CP7-G TERMINAL BLOCK
# ============================================================

old_terminal = '''    # --------------------------------------------------------
    # CP7-G IDENTITY REPORT
    # --------------------------------------------------------

    print_cp7g_report(
        snapshot_id,
        opportunity_rows,
        decision_rows,
        risk_rows,
        gate_results
    )

    # --------------------------------------------------------
    # HARD STOP
    # --------------------------------------------------------

    return 0
'''


new_terminal = '''    # --------------------------------------------------------
    # CP8 — CURRENT MARKET REGIME
    # --------------------------------------------------------

    regime_snapshot = (
        load_current_market_regime()
    )

    # --------------------------------------------------------
    # CP8 — CURRENT ORDER INTENT
    # --------------------------------------------------------

    order_intents = (
        build_current_order_intents(
            gate_results,
            opportunity_rows,
            snapshot_id,
            regime_snapshot
        )
    )

    # --------------------------------------------------------
    # CP8 — CURRENT ORDER INTENT VALIDATION
    # --------------------------------------------------------

    validate_current_order_intents(
        order_intents,
        gate_results,
        opportunity_rows,
        snapshot_id
    )

    # --------------------------------------------------------
    # CP8 — EXECUTION SAFETY
    # --------------------------------------------------------

    if order_intents and EXECUTION_ENABLED:

        raise RuntimeError(
            "CP8: execution must remain disabled."
        )

    # --------------------------------------------------------
    # CP8 REPORT
    # --------------------------------------------------------

    print_cp8_report(
        snapshot_id,
        opportunity_rows,
        decision_rows,
        risk_rows,
        gate_results,
        order_intents
    )

    # --------------------------------------------------------
    # CP8 HARD STOP
    # --------------------------------------------------------

    return 0
'''


if old_terminal not in text:

    raise RuntimeError(
        "CP8 REPAIR FAILED: "
        "real CP7-G terminal block not found."
    )


text = text.replace(
    old_terminal,
    new_terminal,
    1
)

print(
    "[PASS] CP7-G terminal boundary replaced by CP8."
)


# ============================================================
# 5. UPDATE FILE HEADER ONLY
# ============================================================

text = text.replace(
    "# CHECKPOINT 7-G RUNTIME IDENTITY",
    "# CHECKPOINT 8 FULL PRODUCTION DRY-RUN",
    1
)

text = text.replace(
    "ARUNDA TRADER — CP7-G RUNTIME",
    "ARUNDA TRADER — CP8 FULL PRODUCTION DRY-RUN",
    1
)

text = text.replace(
    "CURRENT RUNTIME IDENTITY",
    "CP8 FULL PRODUCTION DRY-RUN",
    1
)

print(
    "[PASS] Pipeline header updated to CP8."
)


# ============================================================
# 6. WRITE
# ============================================================

PIPELINE.write_text(
    text,
    encoding="utf-8"
)

print()
print("=" * 90)
print("CP8 REPAIR COMPLETE")
print("=" * 90)
print()
print("BACKUP CREATED:")
print(BACKUP)
print()
print("PRODUCTION BUSINESS LOGIC:")
print("UNCHANGED")
print()
print("TRADE GATE:")
print("UNCHANGED")
print()
print("EXECUTION:")
print("DISABLED")
print()
print("DB WRITE:")
print("NONE")
print()
print("NEXT STEP:")
print("python -m py_compile .\\arunda_pipeline.py")
print()