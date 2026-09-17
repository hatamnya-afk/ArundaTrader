# -*- coding: utf-8 -*-

import sqlite3
import inspect
import sys
import signal_engine

DB = r"C:\Users\ASUS\ArundaTrader\arunda.db"


def trace_function(func, *args):
    events = []
    target_file = inspect.getsourcefile(func)
    start_line = inspect.getsourcelines(func)[1]
    end_line = start_line + len(inspect.getsource(func).splitlines())

    def tracer(frame, event, arg):
        if frame.f_code.co_filename != target_file:
            return tracer

        line = frame.f_lineno

        if event == "line" and start_line <= line <= end_line:
            src = inspect.getsource(func).splitlines()
            text = src[line - start_line].strip()

            if text.startswith(("if ", "elif ", "else", "return")):
                events.append((line, text))

        return tracer

    old = sys.gettrace()
    sys.settrace(tracer)

    try:
        result = func(*args)
    except Exception as e:
        result = None
        events.append(("EXCEPTION", f"{type(e).__name__}: {e}"))
    finally:
        sys.settrace(old)

    return result, events


def get_latest_assets():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    rows = conn.execute("""
        SELECT asset, direction
        FROM fusion_signals
        WHERE engine_version = 'FUSION_v0.5'
        ORDER BY timestamp DESC, id DESC
        LIMIT 4
    """).fetchall()

    conn.close()
    return rows


def build_inputs(asset):
    regime_data = None
    structural_data = None

    if hasattr(signal_engine, "load_regime_contract"):
        fn = signal_engine.load_regime_contract
        try:
            sig = inspect.signature(fn)
            if len(sig.parameters) == 0:
                regime_data = fn()
            else:
                regime_data = fn(asset)
        except Exception:
            pass

    if hasattr(signal_engine, "load_structural_state"):
        fn = signal_engine.load_structural_state
        try:
            sig = inspect.signature(fn)
            if len(sig.parameters) == 0:
                structural_data = fn()
            else:
                structural_data = fn(asset)
        except Exception:
            pass

    return regime_data, structural_data


def main():
    print("=" * 82)
    print("ARUNDA TRADER — BUILD_SIGNAL BRANCH TRACE")
    print("=" * 82)
    print("MODE      : READ ONLY")
    print("SYNTHETIC : NO")
    print("DB WRITE  : NO")
    print("ORDER     : NO")
    print()

    rows = get_latest_assets()

    for row in rows:
        asset = row["asset"]
        direction = row["direction"]

        if direction not in ("LONG", "SHORT"):
            print(f"{asset}: STOP — direction={direction}")
            continue

        regime_data, structural_data = build_inputs(asset)

        if regime_data is None or structural_data is None:
            print(f"{asset}: INPUT_ERROR — build_signal inputs unavailable")
            continue

        result, events = trace_function(
            signal_engine.build_signal,
            asset,
            regime_data,
            structural_data
        )

        failure = None

        for event in events:
            if event[0] == "EXCEPTION":
                failure = event[1]
                break

        if failure:
            print(f"{asset}: FAIL — {failure}")
            continue

        if result is None:
            print(f"{asset}: FAIL — build_signal returned None")
            continue

        print(f"{asset}: PASS — build_signal returned {type(result).__name__}")

    print()
    print("TRACE COMPLETE")
    print("REPAIR: NONE")
    print("DB WRITE: NONE")
    print("FRONTIER: LIVE_SIGNAL_ORDER_INTENT_VALIDATION_CONTRACT_REPAIR")


if __name__ == "__main__":
    main()