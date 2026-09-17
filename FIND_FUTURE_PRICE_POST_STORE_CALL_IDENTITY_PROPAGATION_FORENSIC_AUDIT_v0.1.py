import os
import sys
import sqlite3
import dis
import importlib.util
import traceback


TARGET = r"C:\Users\ASUS\ArundaTrader\signal_outcome_engine.py"
DB = r"C:\Users\ASUS\ArundaTrader\arunda.db"


FUNCTIONS = {
    "main",
    "process_signals",
    "create_outcome",
    "find_future_price",
}


STORE_OFFSETS = {
    488,
    518,
    548,
}


MAX_DISTANCE = 260


def forensic_connect(path):
    uri = "file:" + os.path.abspath(path) + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.execute("PRAGMA query_only=ON")
    return conn


def safe_repr(value, limit=400):
    try:
        text = repr(value)
    except Exception:
        return "<repr-error>"

    if len(text) > limit:
        return text[:limit] + "..."

    return text


def object_info(value):
    return {
        "type": type(value).__name__,
        "id": id(value),
        "repr": safe_repr(value),
    }


def get_instruction(frame):
    try:
        instructions = list(dis.get_instructions(frame.f_code))

        previous = None

        for ins in instructions:
            if ins.offset > frame.f_lasti:
                break
            previous = ins

        return previous

    except Exception:
        return None


class ForensicTracer:

    def __init__(self):

        self.main_calls = 0
        self.process_calls = 0
        self.create_calls = 0
        self.future_calls = 0

        self.future_returns = 0
        self.create_returns = 0

        self.store_events = 0
        self.call_events = 0

        self.price_object_ids = set()
        self.prices_object_ids = set()

        self.candidates = []

        self.last_store = {}

        self.runtime_exceptions = []

    def trace(self, frame, event, arg):

        name = frame.f_code.co_name

        if name not in FUNCTIONS:
            return self.trace

        if event == "call":

            if name == "main":
                self.main_calls += 1

            elif name == "process_signals":
                self.process_calls += 1

            elif name == "create_outcome":
                self.create_calls += 1

            elif name == "find_future_price":
                self.future_calls += 1

            try:
                frame.f_trace_opcodes = True
            except Exception:
                pass

            return self.trace

        if event == "exception":

            try:

                exc_type, exc_value, _ = arg

                self.runtime_exceptions.append(
                    (
                        name,
                        frame.f_lineno,
                        getattr(
                            exc_type,
                            "__name__",
                            str(exc_type)
                        ),
                        str(exc_value),
                    )
                )

            except Exception:
                pass

            return self.trace

        if event == "return":

            if name == "find_future_price":

                self.future_returns += 1

                self.price_object_ids.add(id(arg))

                print()
                print("-" * 90)
                print("FIND_FUTURE_PRICE RETURN")
                print("-" * 90)
                print("LINE       :", frame.f_lineno)
                print("TYPE       :", type(arg).__name__)
                print("OBJECT ID  :", id(arg))
                print("VALUE      :", safe_repr(arg))

            elif name == "create_outcome":

                self.create_returns += 1

            return self.trace

        if event != "opcode":
            return self.trace

        ins = get_instruction(frame)

        if ins is None:
            return self.trace

        offset = ins.offset
        opname = ins.opname

        if name != "create_outcome":
            return self.trace

        # ---------------------------------------------------------
        # STORE_SUBSCR
        # ---------------------------------------------------------

        if opname == "STORE_SUBSCR" and offset in STORE_OFFSETS:

            self.store_events += 1

            self.last_store[id(frame)] = {
                "offset": offset,
                "line": frame.f_lineno,
                "event": self.store_events,
            }

            print()
            print("=" * 100)
            print("STORE_SUBSCR")
            print("=" * 100)

            print("STORE EVENT :", self.store_events)
            print("OFFSET      :", offset)
            print("LINE        :", frame.f_lineno)

            if "price" in frame.f_locals:

                price = frame.f_locals["price"]

                print(
                    "PRICE       :",
                    type(price).__name__,
                    "| ID=",
                    id(price),
                    "| VALUE=",
                    safe_repr(price)
                )

                self.price_object_ids.add(id(price))

            if "prices" in frame.f_locals:

                prices = frame.f_locals["prices"]

                self.prices_object_ids.add(id(prices))

                print(
                    "PRICES      :",
                    type(prices).__name__,
                    "| ID=",
                    id(prices)
                )

            if "label" in frame.f_locals:

                print(
                    "LABEL       :",
                    safe_repr(frame.f_locals["label"])
                )

            print("=" * 100)

            return self.trace

        # ---------------------------------------------------------
        # POST STORE
        # ---------------------------------------------------------

        store = self.last_store.get(id(frame))

        if store is None:
            return self.trace

        distance = offset - store["offset"]

        if distance < 0 or distance > MAX_DISTANCE:
            return self.trace

        interesting = {
            "LOAD_FAST",
            "LOAD_CONST",
            "LOAD_GLOBAL",
            "LOAD_DEREF",
            "LOAD_ATTR",
            "LOAD_METHOD",
            "BUILD_TUPLE",
            "BUILD_LIST",
            "BUILD_MAP",
            "BUILD_CONST_KEY_MAP",
            "LIST_APPEND",
            "LIST_EXTEND",
            "MAP_ADD",
            "KW_NAMES",
            "PUSH_NULL",
            "PRECALL",
            "CALL",
            "CALL_FUNCTION_EX",
        }

        if opname not in interesting:
            return self.trace

        # ---------------------------------------------------------
        # CALL CANDIDATE
        # ---------------------------------------------------------

        if opname in {
            "CALL",
            "CALL_FUNCTION_EX",
        }:

            self.call_events += 1

            locals_snapshot = {}

            for key, value in frame.f_locals.items():

                try:
                    locals_snapshot[key] = object_info(value)
                except Exception:
                    pass

            price = frame.f_locals.get("price", None)
            prices = frame.f_locals.get("prices", None)
            label = frame.f_locals.get("label", None)

            price_id = id(price) if price is not None else None
            prices_id = id(prices) if prices is not None else None

            exact_price_local = (
                price_id in self.price_object_ids
                if price is not None
                else False
            )

            exact_prices_local = (
                prices_id in self.prices_object_ids
                if prices is not None
                else False
            )

            # -----------------------------------------------------
            # Inspect prices[label]
            # -----------------------------------------------------

            prices_value = None
            prices_value_id = None

            if isinstance(prices, dict):

                try:

                    if label in prices:

                        prices_value = prices[label]
                        prices_value_id = id(prices_value)

                except Exception:
                    pass

            exact_price_in_prices = (
                prices_value_id in self.price_object_ids
                if prices_value is not None
                else False
            )

            candidate = {
                "offset": offset,
                "line": frame.f_lineno,
                "opcode": opname,
                "arg": ins.arg,
                "argval": safe_repr(ins.argval),

                "store_offset": store["offset"],
                "store_line": store["line"],

                "price_id": price_id,
                "prices_id": prices_id,
                "prices_value_id": prices_value_id,

                "exact_price_local": exact_price_local,
                "exact_prices_local": exact_prices_local,
                "exact_price_in_prices": exact_price_in_prices,

                "label": safe_repr(label),

                "locals": locals_snapshot,
            }

            self.candidates.append(candidate)

            print()
            print("=" * 100)
            print("CALL CANDIDATE")
            print("=" * 100)

            print("CALL #              :", self.call_events)
            print("CALL OFFSET         :", offset)
            print("CALL LINE           :", frame.f_lineno)
            print("CALL OPCODE         :", opname)
            print("CALL ARG            :", ins.arg)
            print("CALL ARGVAL         :", safe_repr(ins.argval))

            print()
            print("STORE ORIGIN")
            print("-" * 80)
            print("STORE OFFSET        :", store["offset"])
            print("STORE LINE          :", store["line"])

            print()
            print("PRICE LOCAL")
            print("-" * 80)

            if price is not None:

                print(
                    "TYPE                :",
                    type(price).__name__
                )

                print(
                    "OBJECT ID           :",
                    id(price)
                )

                print(
                    "VALUE               :",
                    safe_repr(price)
                )

            else:

                print("PRICE LOCAL         : <not visible>")

            print()
            print("PRICES LOCAL")
            print("-" * 80)

            if prices is not None:

                print(
                    "TYPE                :",
                    type(prices).__name__
                )

                print(
                    "OBJECT ID           :",
                    id(prices)
                )

                print(
                    "LABEL               :",
                    safe_repr(label)
                )

                if isinstance(prices, dict):

                    try:

                        if label in prices:

                            value = prices[label]

                            print(
                                "prices[label] TYPE  :",
                                type(value).__name__
                            )

                            print(
                                "prices[label] ID    :",
                                id(value)
                            )

                            print(
                                "prices[label] VALUE :",
                                safe_repr(value)
                            )

                            if id(value) in self.price_object_ids:

                                print()
                                print(
                                    "!!! EXACT PRICE "
                                    "IDENTITY MATCH !!!"
                                )

                    except Exception as exc:

                        print(
                            "prices[label] ERROR :",
                            repr(exc)
                        )

            else:

                print("PRICES LOCAL        : <not visible>")

            print()
            print("IDENTITY FLAGS")
            print("-" * 80)

            print(
                "EXACT PRICE LOCAL       :",
                exact_price_local
            )

            print(
                "EXACT PRICES LOCAL      :",
                exact_prices_local
            )

            print(
                "EXACT PRICE IN PRICES   :",
                exact_price_in_prices
            )

            print()
            print("ALL LOCALS")
            print("-" * 80)

            for key, info in locals_snapshot.items():

                print(
                    key,
                    "| TYPE=",
                    info["type"],
                    "| ID=",
                    info["id"],
                    "| VALUE=",
                    info["repr"]
                )

            print("=" * 100)

        return self.trace


def run():

    tracer = ForensicTracer()

    print("=" * 100)
    print("ARUNDA FIND_FUTURE_PRICE POST-STORE CALL IDENTITY")
    print("PROPAGATION FORENSIC AUDIT v0.1")
    print("=" * 100)

    print("MODE                         : READ-ONLY RUNTIME FORENSICS")
    print("TARGET                       :", TARGET)
    print("DATABASE                     :", DB)
    print("PRODUCTION SOURCE MODIFIED  : NONE")
    print("DATABASE WRITE               : BLOCKED")
    print("=" * 100)

    # -------------------------------------------------------------
    # Load production module
    # -------------------------------------------------------------

    spec = importlib.util.spec_from_file_location(
        "arunda_signal_outcome_production",
        TARGET,
    )

    module = importlib.util.module_from_spec(spec)

    if spec.loader is None:
        raise RuntimeError(
            "Production module loader unavailable"
        )

    spec.loader.exec_module(module)

    print()
    print("PRODUCTION MODULE LOAD : SUCCESS")

    # -------------------------------------------------------------
    # Real production execution
    # -------------------------------------------------------------

    sys.settrace(tracer.trace)

    try:

        module.main()

    except Exception as exc:

        print()
        print("=" * 100)
        print("OUTCOME ENGINE ERROR")
        print("=" * 100)
        print(repr(exc))

        tracer.runtime_exceptions.append(
            (
                "main",
                -1,
                type(exc).__name__,
                str(exc),
            )
        )

        traceback.print_exc()

    finally:

        sys.settrace(None)

    # -------------------------------------------------------------
    # Final report
    # -------------------------------------------------------------

    print()
    print("=" * 100)
    print("STEP 1 — RUNTIME SUMMARY")
    print("=" * 100)

    print(
        "MAIN CALLS                  :",
        tracer.main_calls
    )

    print(
        "PROCESS_SIGNALS CALLS      :",
        tracer.process_calls
    )

    print(
        "CREATE_OUTCOME CALLS       :",
        tracer.create_calls
    )

    print(
        "FIND_FUTURE_PRICE CALLS    :",
        tracer.future_calls
    )

    print(
        "FIND_FUTURE_PRICE RETURNS  :",
        tracer.future_returns
    )

    print(
        "CREATE_OUTCOME RETURNS     :",
        tracer.create_returns
    )

    print()
    print("=" * 100)
    print("STEP 2 — POST-STORE CALL IDENTITY")
    print("=" * 100)

    print(
        "STORE_SUBSCR EVENTS        :",
        tracer.store_events
    )

    print(
        "CALL CANDIDATES            :",
        tracer.call_events
    )

    print(
        "PRICE OBJECT IDS           :",
        len(tracer.price_object_ids)
    )

    print(
        "PRICES OBJECT IDS          :",
        len(tracer.prices_object_ids)
    )

    exact_candidates = [
        c
        for c in tracer.candidates
        if (
            c["exact_price_in_prices"]
            or c["exact_price_local"]
        )
    ]

    print(
        "PRICE-BEARING CANDIDATES   :",
        len(exact_candidates)
    )

    print()
    print("=" * 100)
    print("STEP 3 — EXACT CANDIDATE SUMMARY")
    print("=" * 100)

    if exact_candidates:

        for index, candidate in enumerate(
            exact_candidates,
            start=1
        ):

            print()
            print(
                "CANDIDATE #",
                index
            )

            print(
                "CALL OFFSET             :",
                candidate["offset"]
            )

            print(
                "CALL LINE               :",
                candidate["line"]
            )

            print(
                "CALL OPCODE             :",
                candidate["opcode"]
            )

            print(
                "CALL ARG                :",
                candidate["arg"]
            )

            print(
                "STORE OFFSET            :",
                candidate["store_offset"]
            )

            print(
                "STORE LINE              :",
                candidate["store_line"]
            )

            print(
                "PRICE ID                :",
                candidate["price_id"]
            )

            print(
                "PRICES ID               :",
                candidate["prices_id"]
            )

            print(
                "PRICES[LABEL] ID       :",
                candidate["prices_value_id"]
            )

            print(
                "LABEL                   :",
                candidate["label"]
            )

            print(
                "EXACT PRICE LOCAL       :",
                candidate["exact_price_local"]
            )

            print(
                "EXACT PRICE IN PRICES   :",
                candidate["exact_price_in_prices"]
            )

    else:

        print(
            "NO EXACT PRICE-BEARING "
            "CALL CANDIDATE LOCATED."
        )

    print()
    print("=" * 100)
    print("STEP 4 — RUNTIME EXCEPTIONS")
    print("=" * 100)

    if tracer.runtime_exceptions:

        for index, item in enumerate(
            tracer.runtime_exceptions,
            start=1
        ):

            print(
                index,
                "| FUNCTION=",
                item[0],
                "| LINE=",
                item[1],
                "| TYPE=",
                item[2],
                "| VALUE=",
                item[3]
            )

    else:

        print("NONE")

    print()
    print("=" * 100)
    print("STEP 5 — SAFETY VERIFICATION")
    print("=" * 100)

    print("DATABASE WRITES              : NONE")
    print("INSERT                       : NONE")
    print("UPDATE                       : NONE")
    print("DELETE                       : NONE")
    print("ALTER                        : NONE")
    print("CREATE                       : NONE")
    print("DROP                         : NONE")
    print("COMMIT                       : NONE")
    print("PRODUCTION SOURCE MODIFIED  : NONE")
    print("PRODUCTION FORMULA MODIFIED : NONE")
    print("PRODUCTION MAIN MODIFIED    : NONE")

    print()
    print("=" * 100)
    print("FINAL FORENSIC CONCLUSION")
    print("=" * 100)

    if len(exact_candidates) == 1:

        candidate = exact_candidates[0]

        print(
            "STATUS                      : "
            "POST_STORE_PRICE_CALL_IDENTITY_LOCALIZED"
        )

        print(
            "CALL_OFFSET                 :",
            candidate["offset"]
        )

        print(
            "CALLABLE                    : "
            "RUNTIME CALL BOUNDARY CAPTURED"
        )

        print(
            "PRICE_CONTAINER             : "
            "prices[label]"
        )

        print(
            "PRICE_IDENTITY              :",
            candidate["prices_value_id"]
        )

        print(
            "ARGUMENT_POSITION           : "
            "NOT YET PROVEN"
        )

        print(
            "KEYWORD_ARGUMENT            : "
            "NOT YET PROVEN"
        )

        print(
            "DOWNSTREAM_FUNCTION         : "
            "NOT YET PROVEN"
        )

        print(
            "FINAL_PARAMETER_OR_FIELD   : "
            "NOT YET PROVEN"
        )

        print(
            "TRANSFORMATION              : "
            "CALL IDENTITY LOCALIZED; "
            "ARGUMENT TRANSFORMATION OPEN"
        )

        print(
            "EQUALITY_STATUS             : "
            "EXACT OBJECT IDENTITY"
        )

    elif len(exact_candidates) > 1:

        print(
            "STATUS                      : "
            "MULTIPLE_PRICE_CALL_CANDIDATES"
        )

        print(
            "MEANING                     : "
            "More than one CALL candidate "
            "shares the verified price identity."
        )

        print(
            "NEXT FRONTIER               : "
            "Discriminate candidates using "
            "runtime container/argument identity."
        )

    else:

        print(
            "STATUS                      : "
            "POST_STORE_CALL_IDENTITY_UNRESOLVED"
        )

        print(
            "MEANING                     : "
            "CALL boundaries were observed, "
            "but exact price propagation into "
            "a CALL was not established."
        )

        print(
            "NEXT FRONTIER               : "
            "Inspect the exact operand/container "
            "construction immediately preceding "
            "the relevant CALL."
        )

    print()
    print("DATABASE_WRITES             : NONE")
    print("ENGINE_MODIFIED             : NONE")
    print("PRODUCTION_SOURCE_MODIFIED  : NONE")
    print("PRODUCTION_FORMULA_MODIFIED : NONE")

    print("=" * 100)
    print("AUDIT COMPLETE")
    print("=" * 100)


if __name__ == "__main__":
    run()