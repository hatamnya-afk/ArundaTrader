# trace_structure_direction_unknown.py

import market_regime_engine


ASSETS = ["XRP", "SOL", "ETH"]


print("=" * 82)
print("ARUNDA TRADER — STRUCTURE_DIRECTION UNKNOWN FORENSIC TRACE")
print("=" * 82)
print("MODE      : READ ONLY")
print("SYNTHETIC : NO")
print("DB WRITE  : NO")
print("SIGNAL    : NO")
print("SCORING   : NO")
print("DECISION  : NO")
print()

print("TARGET")
print("----------------------------------------------------------------------------------")
print("Why does calculate_structure() emit structure_direction = UNKNOWN?")
print("")

for asset in ASSETS:

    print("-" * 82)
    print(asset)
    print("-" * 82)

    try:

        history = market_regime_engine.load_market_data_by_symbol()

        bars = history.get(asset, [])

        print("BARS              :", len(bars))
        print("WINDOW_SIZE       :", market_regime_engine.WINDOW_SIZE)

        if len(bars) < market_regime_engine.WINDOW_SIZE:
            print("RESULT            : INSUFFICIENT DATA")
            continue

        window = bars[-market_regime_engine.WINDOW_SIZE:]

        analysis = market_regime_engine.market_structure_engine.analyze_market_structure(
            window,
            left_bars=market_regime_engine.LEFT_BARS,
            right_bars=market_regime_engine.RIGHT_BARS,
        )

        if not isinstance(analysis, dict):
            print("RESULT            : INVALID ANALYSIS OBJECT")
            continue

        structure_points = analysis.get("structure_points", [])

        swings = analysis.get("swings", [])
        events = analysis.get("events", [])

        print("SWINGS            :", len(swings))
        print("STRUCTURE POINTS  :", len(structure_points))
        print("EVENTS            :", len(events))

        if not structure_points:

            print("DIRECTION CALL    : NOT EXECUTED")
            print("FIRST CONDITION   : structure_points is empty")
            print("EMITTED DIRECTION : UNKNOWN")
            print("ROOT               : NO STRUCTURE POINTS")

            continue

        direction = (
            market_regime_engine
            .market_structure_engine
            .classify_structure_direction(
                structure_points
            )
        )

        print("DIRECTION CALL    : EXECUTED")
        print("RAW DIRECTION     :", repr(direction))
        print("NORMALIZED        :", repr(
            market_regime_engine._normalize_text(direction)
        ))

        if direction is None:
            print("ROOT               : classify_structure_direction returned None")

        elif market_regime_engine._normalize_text(direction) == "UNKNOWN":
            print("ROOT               : structure engine classified direction as UNKNOWN")

        else:
            print("ROOT               : direction produced by structure engine")

    except Exception as error:

        print("RESULT            : FAILURE")
        print("ERROR TYPE        :", type(error).__name__)
        print("ERROR             :", str(error))


print()
print("=" * 82)
print("FINAL FORENSIC RESULT")
print("=" * 82)
print("TRACE SCOPE       : structure_direction only")
print("REPAIR            : NONE")
print("DB WRITE          : NONE")
print("SYNTHETIC         : NO")
print("ORDER             : NONE")
print("NEXT ROOT         : classify_structure_direction() OR empty structure_points")
print("=" * 82)