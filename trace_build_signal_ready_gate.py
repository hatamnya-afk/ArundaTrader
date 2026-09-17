# trace_build_signal_ready_gate.py
# ARUNDA TRADER — READY GATE FORENSIC TRACE
# READ ONLY — NO DB WRITE — NO SYNTHETIC DATA — NO ORDER

import ast
import inspect
import sqlite3
import signal_engine

DB = r"C:\Users\ASUS\ArundaTrader\arunda.db"


def get_build_signal_source():
    file = inspect.getsourcefile(signal_engine.build_signal)
    source = inspect.getsource(signal_engine.build_signal)
    return file, source


def find_ready_references(source):
    tree = ast.parse(source)
    hits = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.If, ast.AnnAssign, ast.Assign, ast.Return)):
            text = ast.get_source_segment(source, node)

            if text and "READY" in text.upper():
                hits.append(
                    (
                        getattr(node, "lineno", None),
                        text.strip().splitlines()[0]
                    )
                )

    return hits


def find_ready_runtime_objects():
    objects = []

    for name in dir(signal_engine):
        if "ready" in name.lower():
            try:
                obj = getattr(signal_engine, name)
                objects.append(
                    (
                        name,
                        type(obj).__name__,
                        getattr(obj, "__module__", None),
                        getattr(obj, "__file__", None),
                    )
                )
            except Exception:
                pass

    return objects


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


def main():
    print("=" * 82)
    print("ARUNDA TRADER — READY GATE FORENSIC TRACE")
    print("=" * 82)
    print("MODE      : READ ONLY")
    print("SYNTHETIC : NO")
    print("DB WRITE  : NO")
    print("ORDER     : NO")
    print()

    file, source = get_build_signal_source()

    print(f"BUILD_SIGNAL : {file}")
    print(f"LINE         : {inspect.getsourcelines(signal_engine.build_signal)[1]}")
    print()

    ready_hits = find_ready_references(source)

    print("READY REFERENCES")

    if ready_hits:
        for line, text in ready_hits:
            print(f"LINE {line}: {text}")
    else:
        print("NONE INSIDE build_signal()")

    print()
    print("READY-RELATED RUNTIME OBJECTS")

    objects = find_ready_runtime_objects()

    if objects:
        for name, typ, module, obj_file in objects:
            print(f"{name}: {typ} | {module} | {obj_file}")
    else:
        print("NONE")

    print()
    print("CURRENT ASSETS")

    for row in get_latest_assets():
        asset = row["asset"]
        direction = row["direction"]

        if direction not in ("LONG", "SHORT"):
            print(f"{asset}: STOP — direction={direction}")
            continue

        try:
            # Reproduce the same input acquisition used previously.
            regime_data = None
            structural_data = None

            if hasattr(signal_engine, "load_regime_contract"):
                fn = signal_engine.load_regime_contract
                try:
                    params = inspect.signature(fn).parameters
                    regime_data = fn(asset) if params else fn()
                except Exception:
                    pass

            if hasattr(signal_engine, "load_structural_state"):
                fn = signal_engine.load_structural_state
                try:
                    params = inspect.signature(fn).parameters
                    structural_data = fn(asset) if params else fn()
                except Exception:
                    pass

            if regime_data is None or structural_data is None:
                print(f"{asset}: INPUT_UNAVAILABLE")
                continue

            signal_engine.build_signal(
                asset,
                regime_data,
                structural_data
            )

            print(f"{asset}: READY_GATE_NOT_TRIGGERED")

        except RuntimeError as e:
            msg = str(e)

            if "not READY" in msg.upper():
                print(f"{asset}: NOT_READY")
                print(f"  FIRST OBSERVED: {msg}")
            else:
                print(f"{asset}: RUNTIME_ERROR — {msg}")

        except Exception as e:
            print(f"{asset}: ERROR — {type(e).__name__}: {e}")

    print()
    print("=" * 82)
    print("TRACE COMPLETE")
    print("REPAIR: NONE")
    print("DB WRITE: NONE")
    print("SYNTHETIC DATA: NO")
    print("ORDER: NONE")
    print("FRONTIER: LIVE_SIGNAL_ORDER_INTENT_VALIDATION_CONTRACT_REPAIR")
    print("=" * 82)


if __name__ == "__main__":
    main()