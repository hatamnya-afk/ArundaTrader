# ARUNDA_RUNTIME_MAPPING_PROVENANCE_v0.4.py
# ============================================================
# READ-ONLY RUNTIME FORENSIC
#
# PURPOSE:
#   Find the FIRST runtime population/assignment of:
#       bars_by_asset
#       indicators_by_asset
#       structures_by_asset
#
#   Then capture:
#       - process
#       - module
#       - function
#       - file
#       - line
#       - value type
#       - object id
#       - size
#       - keys
#       - caller chain
#       - function arguments
#
# IMPORTANT:
#   - Production source is NOT modified.
#   - Database is NOT opened by this forensic script.
#   - Instrumentation is injected through temporary sitecustomize.py
#     so child processes launched by the pipeline are traced too.
# ============================================================

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path


TARGETS = {
    "bars_by_asset",
    "indicators_by_asset",
    "structures_by_asset",
}


SITE_CUSTOMIZE = r'''
import sys
import os
import json
import time
import traceback
import threading
import linecache

TARGETS = {
    "bars_by_asset",
    "indicators_by_asset",
    "structures_by_asset",
}

LOG_FILE = os.environ.get("ARUNDA_MAPPING_TRACE_LOG")

if not LOG_FILE:
    raise RuntimeError("ARUNDA_MAPPING_TRACE_LOG missing")

_seen = set()
_state = {}
_lock = threading.Lock()


def emit(event, frame, target, value=None, extra=None):

    try:
        filename = os.path.abspath(frame.f_code.co_filename)

        # Never instrument the forensic/temp machinery itself.
        if "sitecustomize.py" in filename:
            return

        function = frame.f_code.co_name
        lineno = frame.f_lineno

        module = frame.f_globals.get("__name__", "<unknown>")

        pid = os.getpid()

        value_type = None
        object_id = None
        size = None
        keys = None
        repr_head = None

        if value is not None:
            try:
                value_type = type(value).__name__
                object_id = id(value)
            except Exception:
                pass

            try:
                size = len(value)
            except Exception:
                pass

            try:
                if isinstance(value, dict):
                    keys = list(value.keys())[:25]
                elif hasattr(value, "keys"):
                    keys = list(value.keys())[:25]
            except Exception:
                pass

            try:
                repr_head = repr(value)[:500]
            except Exception:
                repr_head = "<repr failed>"

        caller_chain = []

        f = frame.f_back
        depth = 0

        while f is not None and depth < 12:

            try:
                caller_chain.append({
                    "file": os.path.abspath(f.f_code.co_filename),
                    "line": f.f_lineno,
                    "function": f.f_code.co_name,
                    "module": f.f_globals.get("__name__", "<unknown>"),
                })
            except Exception:
                pass

            f = f.f_back
            depth += 1

        record = {
            "ts": time.time(),
            "pid": pid,
            "event": event,
            "target": target,
            "file": filename,
            "line": lineno,
            "function": function,
            "module": module,
            "value_type": value_type,
            "object_id": object_id,
            "size": size,
            "keys": keys,
            "repr_head": repr_head,
            "caller_chain": caller_chain,
            "extra": extra or {},
        }

        with _lock:
            with open(LOG_FILE, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    except Exception:
        pass


def snapshot_value(target, value):
    try:
        oid = id(value)
    except Exception:
        oid = None

    try:
        size = len(value)
    except Exception:
        size = None

    try:
        if isinstance(value, dict):
            key_fingerprint = tuple(list(value.keys())[:100])
        elif hasattr(value, "keys"):
            key_fingerprint = tuple(list(value.keys())[:100])
        else:
            key_fingerprint = None
    except Exception:
        key_fingerprint = None

    return oid, size, key_fingerprint


def trace(frame, event, arg):

    try:

        if event == "call":
            return trace

        if event not in ("line", "return"):
            return trace

        filename = os.path.abspath(frame.f_code.co_filename)

        # Ignore Python stdlib/site-packages as much as possible.
        if (
            "\\site-packages\\" in filename
            or "/site-packages/" in filename
            or "\\Lib\\" in filename and "\\site-packages\\" in filename
        ):
            return trace

        locals_now = frame.f_locals

        for target in TARGETS:

            if target not in locals_now:
                continue

            value = locals_now.get(target)

            oid, size, keys = snapshot_value(target, value)

            state_key = (
                os.getpid(),
                id(frame),
                target,
            )

            previous = _state.get(state_key)

            current = (oid, size, keys)

            # FIRST OBSERVATION
            if previous is None:

                _state[state_key] = current

                emit(
                    "FIRST_RUNTIME_OBSERVATION",
                    frame,
                    target,
                    value,
                    {
                        "previous": None,
                        "reason": "target appeared in frame locals",
                    },
                )

                # If this is a function argument, explicitly mark it.
                try:
                    arg_names = frame.f_code.co_varnames[
                        :frame.f_code.co_argcount
                    ]

                    if target in arg_names:

                        emit(
                            "FUNCTION_ARGUMENT_POPULATION",
                            frame,
                            target,
                            value,
                            {
                                "argument_index": arg_names.index(target),
                                "argument_names": list(arg_names),
                            },
                        )
                except Exception:
                    pass

            # OBJECT REPLACED / ASSIGNED
            elif previous[0] != oid:

                old = previous
                _state[state_key] = current

                emit(
                    "OBJECT_REPLACED_OR_REASSIGNED",
                    frame,
                    target,
                    value,
                    {
                        "previous_object_id": old[0],
                        "previous_size": old[1],
                        "new_object_id": oid,
                    },
                )

            # SIZE / KEYSET CHANGED
            elif previous[1] != size or previous[2] != keys:

                old = previous
                _state[state_key] = current

                emit(
                    "MAPPING_MUTATION_OR_POPULATION",
                    frame,
                    target,
                    value,
                    {
                        "previous_size": old[1],
                        "new_size": size,
                        "previous_keys": (
                            list(old[2])[:25]
                            if old[2] is not None
                            else None
                        ),
                        "new_keys": (
                            list(keys)[:25]
                            if keys is not None
                            else None
                        ),
                    },
                )

        return trace

    except Exception:
        return trace


# Install tracing into THIS process.
sys.settrace(trace)

# Ensure newly created threads inherit it.
try:
    threading.settrace(trace)
except Exception:
    pass
'''


def parse_args():
    parser = argparse.ArgumentParser(
        description="ARUNDA runtime mapping provenance forensic"
    )

    parser.add_argument(
        "--entrypoint",
        required=True,
        help="Production entrypoint Python file",
    )

    return parser.parse_args()


def load_records(log_path: Path):
    records = []

    if not log_path.exists():
        return records

    with log_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()

            if not line:
                continue

            try:
                records.append(json.loads(line))
            except Exception:
                continue

    return records


def print_record(r, index=None):

    prefix = f"[{index}] " if index is not None else ""

    print()
    print("-" * 100)

    print(
        f"{prefix}{r.get('event')} "
        f"| TARGET={r.get('target')} "
        f"| PID={r.get('pid')}"
    )

    print(
        f"FILE     : {r.get('file')}"
    )

    print(
        f"LINE     : {r.get('line')}"
    )

    print(
        f"FUNCTION : {r.get('function')}"
    )

    print(
        f"MODULE   : {r.get('module')}"
    )

    print(
        f"TYPE     : {r.get('value_type')}"
    )

    print(
        f"OBJECT ID: {r.get('object_id')}"
    )

    print(
        f"SIZE     : {r.get('size')}"
    )

    print(
        f"KEYS     : {r.get('keys')}"
    )

    extra = r.get("extra") or {}

    if extra:
        print(
            "EXTRA    : "
            + json.dumps(
                extra,
                ensure_ascii=False,
                default=str,
            )
        )

    print("CALLER CHAIN:")

    for n, c in enumerate(r.get("caller_chain") or [], 1):

        print(
            f"  {n}. "
            f"{c.get('file')} :: "
            f"{c.get('function')} "
            f"(line {c.get('line')})"
        )


def main():

    args = parse_args()

    project_root = Path(__file__).resolve().parent
    entrypoint = Path(args.entrypoint).resolve()

    if not entrypoint.exists():
        print(f"ERROR: entrypoint not found: {entrypoint}")
        return 2

    if entrypoint.suffix.lower() != ".py":
        print("ERROR: entrypoint must be a Python file")
        return 2

    print("=" * 100)
    print("ARUNDA TRADER — REAL RUNTIME MAPPING PROVENANCE v0.4")
    print("=" * 100)
    print(f"PROJECT ROOT : {project_root}")
    print("MODE         : READ ONLY / RUNTIME FORENSIC")
    print("SOURCE EDIT  : NONE")
    print("DATABASE     : NOT TOUCHED BY FORENSIC SCRIPT")
    print("SUBPROCESS   : INSTRUMENTED")
    print("=" * 100)

    with tempfile.TemporaryDirectory(
        prefix="arunda_runtime_mapping_"
    ) as temp_dir:

        temp_path = Path(temp_dir)

        site_path = temp_path / "sitecustomize.py"
        log_path = temp_path / "mapping_trace.jsonl"

        site_path.write_text(
            SITE_CUSTOMIZE,
            encoding="utf-8",
        )

        env = os.environ.copy()

        old_pythonpath = env.get("PYTHONPATH", "")

        if old_pythonpath:
            env["PYTHONPATH"] = (
                str(temp_path)
                + os.pathsep
                + old_pythonpath
            )
        else:
            env["PYTHONPATH"] = str(temp_path)

        env["ARUNDA_MAPPING_TRACE_LOG"] = str(log_path)

        env["PYTHONDONTWRITEBYTECODE"] = "1"

        print()
        print("=" * 100)
        print("REAL RUNTIME EXECUTION")
        print("=" * 100)
        print(f"ENTRYPOINT : {entrypoint}")
        print(f"TRACE LOG  : {log_path}")
        print()

        try:

            result = subprocess.run(
                [
                    sys.executable,
                    str(entrypoint),
                ],
                cwd=str(project_root),
                env=env,
                text=True,
            )

            return_code = result.returncode

        except KeyboardInterrupt:

            print()
            print("INTERRUPTED BY USER")
            return_code = 130

        except Exception as exc:

            print()
            print("LAUNCH ERROR")
            print(type(exc).__name__, exc)
            return_code = 1

        records = load_records(log_path)

        print()
        print("=" * 100)
        print("RUNTIME FORENSIC COMPLETE")
        print("=" * 100)

        print(f"ENTRYPOINT EXIT CODE : {return_code}")
        print(f"TRACE EVENTS         : {len(records)}")

        print()
        print("=" * 100)
        print("FIRST RUNTIME POPULATION PER TARGET")
        print("=" * 100)

        for target in sorted(TARGETS):

            target_records = [
                r
                for r in records
                if r.get("target") == target
            ]

            print()
            print(f"TARGET : {target}")

            if not target_records:

                print("STATUS : NOT OBSERVED")

                continue

            first = target_records[0]

            print("STATUS : OBSERVED")

            print(
                f"FIRST EVENT : {first.get('event')}"
            )

            print(
                f"FILE        : {first.get('file')}"
            )

            print(
                f"LINE        : {first.get('line')}"
            )

            print(
                f"FUNCTION    : {first.get('function')}"
            )

            print(
                f"MODULE      : {first.get('module')}"
            )

            print(
                f"PID         : {first.get('pid')}"
            )

            print(
                f"TYPE        : {first.get('value_type')}"
            )

            print(
                f"SIZE        : {first.get('size')}"
            )

            print("CALLER CHAIN:")

            for n, c in enumerate(
                first.get("caller_chain") or [],
                1,
            ):

                print(
                    f"  {n}. "
                    f"{c.get('file')} :: "
                    f"{c.get('function')} "
                    f"(line {c.get('line')})"
                )

        print()
        print("=" * 100)
        print("ALL TARGET EVENTS")
        print("=" * 100)

        for target in sorted(TARGETS):

            print()
            print(f"### {target}")

            target_records = [
                r
                for r in records
                if r.get("target") == target
            ]

            if not target_records:

                print("NO EVENTS")

                continue

            for i, record in enumerate(
                target_records,
                1,
            ):

                print_record(
                    record,
                    i,
                )

        print()
        print("=" * 100)
        print("CROSS-TARGET PROVENANCE")
        print("=" * 100)

        first_by_target = {}

        for target in TARGETS:

            target_records = [
                r
                for r in records
                if r.get("target") == target
            ]

            if target_records:
                first_by_target[target] = target_records[0]

        if len(first_by_target) == 3:

            locations = {
                (
                    r.get("file"),
                    r.get("function"),
                    r.get("line"),
                )
                for r in first_by_target.values()
            }

            if len(locations) == 1:

                print(
                    "THREE TARGETS SHARE THE SAME FIRST RUNTIME LOCATION."
                )

                for target, r in first_by_target.items():

                    print(
                        f"  {target} -> "
                        f"{r.get('file')} :: "
                        f"{r.get('function')} "
                        f"line {r.get('line')}"
                    )

            else:

                print(
                    "THREE TARGETS OBSERVED, BUT FIRST "
                    "RUNTIME LOCATIONS DIFFER."
                )

        elif len(first_by_target) == 0:

            print(
                "NO TARGET WAS OBSERVED IN ANY INSTRUMENTED "
                "RUNTIME PROCESS."
            )

            print()
            print(
                "IMPORTANT:"
            )

            print(
                "This is NOT an AST conclusion."
            )

            print(
                "It means the real executed process tree never "
                "contained these names in runtime locals."
            )

        else:

            print(
                f"ONLY {len(first_by_target)}/3 TARGETS "
                "WERE OBSERVED AT RUNTIME."
            )

            for target in sorted(TARGETS):

                if target not in first_by_target:

                    print(
                        f"  MISSING RUNTIME TARGET: {target}"
                    )

        print()
        print("=" * 100)
        print("FORENSIC STATUS")
        print("=" * 100)

        print(
            "Production source modified : NO"
        )

        print(
            "Forensic DB access         : NO"
        )

        print(
            "Runtime instrumentation    : YES"
        )

        print(
            "Child processes traced     : YES"
        )

        print("=" * 100)

    return return_code


if __name__ == "__main__":
    raise SystemExit(main())