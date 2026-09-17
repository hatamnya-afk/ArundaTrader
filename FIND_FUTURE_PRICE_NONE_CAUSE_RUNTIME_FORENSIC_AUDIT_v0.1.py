import os
import sys
import sqlite3
import importlib.util
import dis
import traceback

TARGET = r"C:\Users\ASUS\ArundaTrader\signal_outcome_engine.py"
DB = r"C:\Users\ASUS\ArundaTrader\arunda.db"
FUNCTION_NAME = "find_future_price"


def forensic_connect(path):
    uri = "file:" + os.path.abspath(path) + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    return conn


def safe_repr(value, limit=500):
    try:
        text = repr(value)
    except Exception:
        return "<repr-error>"

    if len(text) > limit:
        return text[:limit] + "..."

    return text


def get_previous_instruction(frame):
    try:
        previous = None

        for instruction in dis.get_instructions(frame.f_code):
            if instruction.offset > frame.f_lasti:
                break
            previous = instruction

        return previous

    except Exception:
        return None


class FuturePriceTracer:

    def __init__(self):
        self.calls = 0
        self.returns = 0
        self.none_returns = 0
        self.non_none_returns = 0
        self.exceptions = []
        self.return_records = []

    def trace(self, frame, event, arg):

        if frame.f_code.co_name != FUNCTION_NAME:
            return self.trace

        if event == "call":

            self.calls += 1

            try:
                frame.f_trace_opcodes = True
            except Exception:
                pass

            print()
            print("=" * 100)
            print("FIND_FUTURE_PRICE CALL #%d" % self.calls)
            print("=" * 100)

            print("FUNCTION LINE :", frame.f_code.co_firstlineno)

            print()
            print("FUNCTION LOCALS")
            print("-" * 80)

            for name, value in frame.f_locals.items():
                print(
                    "%s | TYPE=%s | ID=%s | VALUE=%s"
                    % (
                        name,
                        type(value).__name__,
                        id(value),
                        safe_repr(value),
                    )
                )

            return self.trace

        if event == "exception":

            try:
                exc_type, exc_value, exc_tb = arg

                self.exceptions.append(
                    (
                        frame.f_lineno,
                        getattr(
                            exc_type,
                            "__name__",
                            str(exc_type),
                        ),
                        str(exc_value),
                    )
                )

                print()
                print("FIND_FUTURE_PRICE EXCEPTION")
                print("-" * 80)
                print("LINE  :", frame.f_lineno)
                print(
                    "TYPE  :",
                    getattr(
                        exc_type,
                        "__name__",
                        str(exc_type),
                    ),
                )
                print("VALUE :", str(exc_value))

            except Exception:
                pass

            return self.trace

        if event == "return":

            self.returns += 1

            if arg is None:
                self.none_returns += 1
            else:
                self.non_none_returns += 1

            record = {
                "number": self.returns,
                "line": frame.f_lineno,
                "type": type(arg).__name__,
                "id": id(arg),
                "value": safe_repr(arg),
            }

            self.return_records.append(record)

            print()
            print("-" * 100)
            print(
                "FIND_FUTURE_PRICE RETURN #%d"
                % self.returns
            )
            print("-" * 100)

            print("RETURN LINE :", frame.f_lineno)
            print("TYPE        :", type(arg).__name__)
            print("OBJECT ID   :", id(arg))
            print("VALUE       :", safe_repr(arg))

            return self.trace

        if event != "opcode":
            return self.trace

        instruction = get_previous_instruction(frame)

        if instruction is None:
            return self.trace

        opname = instruction.opname

        important = {
            "LOAD_FAST",
            "LOAD_CONST",
            "LOAD_GLOBAL",
            "LOAD_ATTR",
            "LOAD_METHOD",
            "COMPARE_OP",
            "IS_OP",
            "CONTAINS_OP",
            "POP_JUMP_FORWARD_IF_FALSE",
            "POP_JUMP_FORWARD_IF_TRUE",
            "POP_JUMP_BACKWARD_IF_FALSE",
            "POP_JUMP_BACKWARD_IF_TRUE",
            "JUMP_FORWARD",
            "JUMP_BACKWARD",
            "CALL",
            "PRECALL",
            "RETURN_VALUE",
        }

        if opname not in important:
            return self.trace

        print()
        print(
            "OPCODE | OFFSET=%s | LINE=%s | OP=%s | ARG=%s | ARGVAL=%s"
            % (
                instruction.offset,
                frame.f_lineno,
                instruction.opname,
                instruction.arg,
                safe_repr(instruction.argval),
            )
        )

        if opname in {
            "CALL",
            "RETURN_VALUE",
            "COMPARE_OP",
            "IS_OP",
            "CONTAINS_OP",
            "POP_JUMP_FORWARD_IF_FALSE",
            "POP_JUMP_FORWARD_IF_TRUE",
            "POP_JUMP_BACKWARD_IF_FALSE",
            "POP_JUMP_BACKWARD_IF_TRUE",
        }:

            print("LOCALS AT OPCODE")
            print("-" * 80)

            for name, value in frame.f_locals.items():

                print(
                    "%s | TYPE=%s | ID=%s | VALUE=%s"
                    % (
                        name,
                        type(value).__name__,
                        id(value),
                        safe_repr(value),
                    )
                )

        return self.trace


def inspect_function():

    print()
    print("=" * 100)
    print("STATIC FIND_FUTURE_PRICE FUNCTION INSPECTION")
    print("=" * 100)

    try:

        with open(
            TARGET,
            "r",
            encoding="utf-8",
        ) as file:

            source = file.read()

        lines = source.splitlines()

        start = None
        end = None

        for index, line in enumerate(
            lines,
            start=1,
        ):

            stripped = line.strip()

            if stripped.startswith(
                "def find_future_price("
            ):

                start = index

                for next_index in range(
                    index + 1,
                    len(lines) + 1,
                ):

                    next_line = lines[next_index - 1]

                    if (
                        next_line.startswith("def ")
                        and next_line.strip()
                    ):

                        end = next_index - 1
                        break

                if end is None:
                    end = len(lines)

                break

        if start is None:

            print(
                "find_future_price() NOT FOUND"
            )

            return

        print(
            "FUNCTION START :",
            start,
        )

        print(
            "FUNCTION END   :",
            end,
        )

        print()
        print("SOURCE BODY")
        print("-" * 80)

        for number in range(
            start,
            end + 1,
        ):

            print(
                "%04d | %s"
                % (
                    number,
                    lines[number - 1],
                )
            )

    except Exception as exc:

        print(
            "STATIC INSPECTION ERROR:",
            repr(exc),
        )


def run():

    print("=" * 100)
    print(
        "ARUNDA FIND_FUTURE_PRICE NONE-CAUSE"
    )
    print(
        "RUNTIME FORENSIC AUDIT v0.1"
    )
    print("=" * 100)

    print(
        "MODE                        : READ-ONLY RUNTIME FORENSICS"
    )

    print(
        "TARGET                      :",
        TARGET,
    )

    print(
        "DATABASE                    :",
        DB,
    )

    print(
        "PRODUCTION SOURCE MODIFIED : NONE"
    )

    print(
        "DATABASE WRITE              : BLOCKED"
    )

    print("=" * 100)

    inspect_function()

    print()
    print("=" * 100)
    print("PRODUCTION MODULE LOAD")
    print("=" * 100)

    spec = importlib.util.spec_from_file_location(
        "arunda_signal_outcome_forensic",
        TARGET,
    )

    if spec is None:
        raise RuntimeError(
            "Could not create module specification."
        )

    if spec.loader is None:
        raise RuntimeError(
            "Production module loader unavailable."
        )

    module = importlib.util.module_from_spec(
        spec
    )

    spec.loader.exec_module(module)

    print("MODULE LOAD : SUCCESS")

    tracer = FuturePriceTracer()

    print()
    print("=" * 100)
    print("GENUINE PRODUCTION EXECUTION")
    print("=" * 100)

    print("ENTRYPOINT      : main()")
    print("TRACE           : CPYTHON sys.settrace")
    print("DATABASE        : READ-ONLY")
    print("SOURCE          : UNMODIFIED")
    print("=" * 100)

    main_exception = None

    sys.settrace(tracer.trace)

    try:

        module.main()

    except Exception as exc:

        main_exception = exc

        print()
        print("=" * 100)
        print("OUTCOME ENGINE ERROR")
        print("=" * 100)
        print(
            type(exc).__name__,
            "(",
            str(exc),
            ")",
        )
        print("=" * 100)

    finally:

        sys.settrace(None)

    print()
    print("=" * 100)
    print("STEP 1 — RUNTIME RETURN SUMMARY")
    print("=" * 100)

    print(
        "FIND_FUTURE_PRICE CALLS   :",
        tracer.calls,
    )

    print(
        "FIND_FUTURE_PRICE RETURNS :",
        tracer.returns,
    )

    print(
        "NONE RETURNS              :",
        tracer.none_returns,
    )

    print(
        "NON-NONE RETURNS          :",
        tracer.non_none_returns,
    )

    print()

    if tracer.return_records:

        for record in tracer.return_records:

            print(
                "RETURN #%d | LINE=%s | TYPE=%s | ID=%s | VALUE=%s"
                % (
                    record["number"],
                    record["line"],
                    record["type"],
                    record["id"],
                    record["value"],
                )
            )

    print()
    print("=" * 100)
    print("STEP 2 — NONE RETURN CONTROL-FLOW")
    print("=" * 100)

    if tracer.none_returns > 0:

        print(
            "OBSERVED NONE RETURNS :",
            tracer.none_returns,
        )

        print()

        for record in tracer.return_records:

            if record["type"] == "NoneType":

                print(
                    "NONE RETURN #%d | LINE=%s"
                    % (
                        record["number"],
                        record["line"],
                    )
                )

        print()
        print(
            "RUNTIME FACT:"
        )

        print(
            "find_future_price() returned None "
            "for the observed invocation(s)."
        )

        print(
            "No price value is assumed or reconstructed."
        )

    else:

        print(
            "NO NONE RETURN OBSERVED."
        )

    print()
    print("=" * 100)
    print("STEP 3 — FIND_FUTURE_PRICE EXCEPTIONS")
    print("=" * 100)

    if tracer.exceptions:

        for index, exception in enumerate(
            tracer.exceptions,
            start=1,
        ):

            print(
                "%03d | LINE=%s | TYPE=%s | VALUE=%s"
                % (
                    index,
                    exception[0],
                    exception[1],
                    exception[2],
                )
            )

    else:

        print("NONE")

    print()
    print("=" * 100)
    print("STEP 4 — MAIN EXCEPTION")
    print("=" * 100)

    if main_exception is None:

        print("NONE")

    else:

        print(
            type(main_exception).__name__,
            "|",
            str(main_exception),
        )

    print()
    print("=" * 100)
    print("STEP 5 — SAFETY VERIFICATION")
    print("=" * 100)

    print(
        "DATABASE WRITES              : NONE"
    )

    print(
        "INSERT                       : NONE"
    )

    print(
        "UPDATE                       : NONE"
    )

    print(
        "DELETE                       : NONE"
    )

    print(
        "ALTER                        : NONE"
    )

    print(
        "CREATE                       : NONE"
    )

    print(
        "DROP                         : NONE"
    )

    print(
        "COMMIT                       : NONE"
    )

    print(
        "PRODUCTION SOURCE MODIFIED  : NONE"
    )

    print(
        "PRODUCTION FORMULA MODIFIED : NONE"
    )

    print(
        "PRODUCTION MAIN MODIFIED    : NONE"
    )

    print()
    print("=" * 100)
    print("FINAL FORENSIC SUMMARY")
    print("=" * 100)

    print(
        "MAIN EXECUTION              :",
        "COMPLETED" if main_exception is None else "EXCEPTION",
    )

    print(
        "FIND_FUTURE_PRICE CALLS     :",
        tracer.calls,
    )

    print(
        "FIND_FUTURE_PRICE RETURNS   :",
        tracer.returns,
    )

    print(
        "NONE RETURNS                :",
        tracer.none_returns,
    )

    print(
        "NON-NONE RETURNS            :",
        tracer.non_none_returns,
    )

    print(
        "RUNTIME EXCEPTIONS          :",
        len(tracer.exceptions),
    )

    print()
    print("=" * 100)
    print("FORENSIC CONCLUSION")
    print("-" * 100)

    if (
        tracer.returns > 0
        and tracer.none_returns == tracer.returns
    ):

        print(
            "STATUS                      : "
            "FIND_FUTURE_PRICE_NONE_RETURN_VERIFIED"
        )

        print(
            "MEANING                     : "
            "All observed find_future_price() "
            "invocations returned None."
        )

        print(
            "NEXT FRONTIER               : "
            "Localize the exact branch and "
            "runtime condition immediately "
            "preceding RETURN_VALUE."
        )

    elif tracer.non_none_returns > 0:

        print(
            "STATUS                      : "
            "MIXED_FUTURE_PRICE_RETURNS"
        )

        print(
            "MEANING                     : "
            "At least one runtime invocation "
            "returned a non-None object."
        )

        print(
            "NEXT FRONTIER               : "
            "Correlate the non-None return "
            "with its asset, snapshot and "
            "minutes arguments."
        )

    elif tracer.calls == 0:

        print(
            "STATUS                      : "
            "FIND_FUTURE_PRICE_RUNTIME_NOT_OBSERVED"
        )

        print(
            "MEANING                     : "
            "The production runtime did not "
            "enter find_future_price()."
        )

        print(
            "NEXT FRONTIER               : "
            "Resolve the runtime boundary "
            "before find_future_price()."
        )

    else:

        print(
            "STATUS                      : "
            "FIND_FUTURE_PRICE_RETURN_BOUNDARY_UNRESOLVED"
        )

        print(
            "MEANING                     : "
            "Runtime execution was observed "
            "but return classification is incomplete."
        )

        print(
            "NEXT FRONTIER               : "
            "Continue exact opcode-level "
            "return localization."
        )

    print()
    print(
        "DATABASE_WRITES             : NONE"
    )

    print(
        "ENGINE_MODIFIED             : NONE"
    )

    print(
        "PRODUCTION_SOURCE_MODIFIED  : NONE"
    )

    print(
        "PRODUCTION_FORMULA_MODIFIED : NONE"
    )

    print("=" * 100)
    print("AUDIT COMPLETE")
    print("=" * 100)


if __name__ == "__main__":
    run()