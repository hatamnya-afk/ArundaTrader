import ast
import os
import sys
import time
import traceback
from collections import defaultdict, deque


# ============================================================
# ARUNDA
# SIGNAL OUTCOME CALL GRAPH DEEP RESOLUTION
# FORENSIC AUDIT v0.1
# ============================================================
#
# PURPOSE
# -------
# Resolve the REAL production caller chain reaching:
#
#     signal_outcome_engine.py
#             |
#             v
#       create_outcome()
#             |
#             v
#     find_future_price()
#
# This audit is STATIC / READ-ONLY.
#
# It does NOT:
#   - execute production functions
#   - execute production main()
#   - open production DB for writing
#   - modify production files
#   - modify production formulas
#   - fabricate runtime values
#
# It searches:
#   1. direct calls
#   2. module-qualified calls
#   3. imported aliases
#   4. from-import aliases
#   5. function references
#   6. wrappers
#   7. caller chains
#   8. production entrypoint candidates
#
# ============================================================


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

TARGET_FILE_NAME = "signal_outcome_engine.py"
TARGET_FUNCTION = "create_outcome"

SECONDARY_TARGET = "find_future_price"

MAX_CHAIN_DEPTH = 20

EXCLUDED_DIR_NAMES = {
    "__pycache__",
    ".git",
    ".idea",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "backups",
    "backup",
    "archive",
    "archives",
    "old",
    "tmp",
    "temp",
}


EXCLUDED_FILE_KEYWORDS = {
    "forensic",
    "audit",
    "diagnostic",
    "discovery",
    "trace",
    "repair",
    "test",
    "debug",
    "verify",
    "verification",
    "check",
    "probe",
    "experiment",
    "experimental",
    "snapshot",
    "migration",
    "backup",
}


PRODUCTION_ENTRY_NAMES = {
    "main",
    "run",
    "start",
    "execute",
    "pipeline",
    "run_pipeline",
    "process",
    "process_market",
    "process_signal",
    "generate_signal",
    "generate_signals",
    "analyze",
    "analysis",
    "engine",
}


# ============================================================
# STATE
# ============================================================

files_scanned = 0
files_parsed = 0
parse_errors = []

modules = {}
functions = {}
classes = {}

call_sites = []
function_references = []

imports = defaultdict(dict)
from_imports = defaultdict(dict)

reverse_calls = defaultdict(list)
forward_calls = defaultdict(list)

target_calls = []
target_references = []

production_entry_candidates = []

excluded_files = []
included_files = []


# ============================================================
# OUTPUT HELPERS
# ============================================================

def line(char="=", width=100):
    print(char * width)


def section(title):
    print()
    line("=")
    print(title)
    line("=")


def subsection(title):
    print()
    line("-")
    print(title)
    line("-")


def safe_repr(value, limit=1000):
    try:
        text = repr(value)
    except Exception:
        text = "<repr failed>"

    if len(text) > limit:
        return text[:limit] + "...<TRUNCATED>"

    return text


# ============================================================
# FILE CLASSIFICATION
# ============================================================

def is_excluded_path(path):
    normalized = path.lower()

    parts = normalized.replace("\\", "/").split("/")

    for part in parts:
        if part in EXCLUDED_DIR_NAMES:
            return True

    filename = os.path.basename(normalized)

    if not filename.endswith(".py"):
        return True

    if filename == os.path.basename(__file__).lower():
        return True

    for keyword in EXCLUDED_FILE_KEYWORDS:
        if keyword in filename:
            return True

    return False


def discover_python_files():
    global files_scanned

    result = []

    for root, dirs, files in os.walk(PROJECT_DIR):

        dirs[:] = [
            directory
            for directory in dirs
            if directory.lower() not in EXCLUDED_DIR_NAMES
        ]

        for filename in files:

            if not filename.endswith(".py"):
                continue

            full_path = os.path.join(
                root,
                filename
            )

            files_scanned += 1

            if is_excluded_path(full_path):
                excluded_files.append(
                    full_path
                )
                continue

            included_files.append(
                full_path
            )

            result.append(
                full_path
            )

    return sorted(result)


# ============================================================
# QUALIFIED FUNCTION NAME
# ============================================================

def function_key(file_path, function_name):
    return (
        os.path.abspath(file_path)
        + "::"
        + function_name
    )


def display_function(key):
    data = functions.get(key)

    if data is None:
        return key

    relative = os.path.relpath(
        data["file"],
        PROJECT_DIR
    )

    return (
        relative
        + "::"
        + data["name"]
        + "()"
    )


# ============================================================
# AST HELPERS
# ============================================================

def get_attribute_chain(node):
    parts = []

    current = node

    while isinstance(
        current,
        ast.Attribute
    ):
        parts.append(
            current.attr
        )
        current = current.value

    if isinstance(
        current,
        ast.Name
    ):
        parts.append(
            current.id
        )

        parts.reverse()

        return parts

    return []


def get_call_name(node):
    if isinstance(
        node,
        ast.Name
    ):
        return node.id

    if isinstance(
        node,
        ast.Attribute
    ):
        chain = get_attribute_chain(node)

        if chain:
            return ".".join(chain)

    return None


def get_source_segment(source, node):
    try:
        return ast.get_source_segment(
            source,
            node
        )
    except Exception:
        return None


# ============================================================
# PARSE FILES
# ============================================================

def parse_files(files):
    global files_parsed

    for path in files:

        try:

            with open(
                path,
                "r",
                encoding="utf-8"
            ) as handle:

                source = handle.read()

            tree = ast.parse(
                source,
                filename=path
            )

            modules[path] = {
                "source": source,
                "tree": tree,
            }

            files_parsed += 1

        except Exception as exc:

            parse_errors.append(
                {
                    "file": path,
                    "exception": repr(exc),
                    "traceback": traceback.format_exc(),
                }
            )


# ============================================================
# DISCOVER DEFINITIONS
# ============================================================

def discover_definitions():
    for path, module_data in modules.items():

        tree = module_data["tree"]

        for node in ast.walk(tree):

            if isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                )
            ):

                key = function_key(
                    path,
                    node.name
                )

                functions[key] = {
                    "key": key,
                    "name": node.name,
                    "file": path,
                    "line": node.lineno,
                    "node": node,
                }

            elif isinstance(
                node,
                ast.ClassDef
            ):

                key = (
                    os.path.abspath(path)
                    + "::class::"
                    + node.name
                )

                classes[key] = {
                    "key": key,
                    "name": node.name,
                    "file": path,
                    "line": node.lineno,
                    "node": node,
                }


# ============================================================
# DISCOVER IMPORTS
# ============================================================

def discover_imports():
    for path, module_data in modules.items():

        tree = module_data["tree"]

        for node in tree.body:

            if isinstance(
                node,
                ast.Import
            ):

                for alias in node.names:

                    local_name = (
                        alias.asname
                        or alias.name.split(".")[0]
                    )

                    imports[path][
                        local_name
                    ] = alias.name

            elif isinstance(
                node,
                ast.ImportFrom
            ):

                module_name = (
                    node.module
                    or ""
                )

                for alias in node.names:

                    local_name = (
                        alias.asname
                        or alias.name
                    )

                    from_imports[path][
                        local_name
                    ] = {
                        "module": module_name,
                        "name": alias.name,
                    }


# ============================================================
# RESOLVE MODULE FILE
# ============================================================

def module_to_possible_files(
    current_file,
    module_name
):

    if not module_name:
        return []

    candidates = []

    module_parts = module_name.split(".")

    current_dir = os.path.dirname(
        current_file
    )

    project_candidate = os.path.join(
        PROJECT_DIR,
        *module_parts
    )

    candidates.append(
        project_candidate + ".py"
    )

    candidates.append(
        os.path.join(
            project_candidate,
            "__init__.py"
        )
    )

    local_candidate = os.path.join(
        current_dir,
        *module_parts
    )

    candidates.append(
        local_candidate + ".py"
    )

    candidates.append(
        os.path.join(
            local_candidate,
            "__init__.py"
        )
    )

    return [
        os.path.abspath(path)
        for path in candidates
        if os.path.isfile(path)
    ]


# ============================================================
# RESOLVE FUNCTION TARGET
# ============================================================

def resolve_function_candidates(
    current_file,
    call_name
):

    candidates = []

    if not call_name:
        return candidates

    # --------------------------------------------------------
    # Direct local function
    # --------------------------------------------------------

    if "." not in call_name:

        direct_key = function_key(
            current_file,
            call_name
        )

        if direct_key in functions:

            candidates.append(
                direct_key
            )

        # ----------------------------------------------------
        # from module import function
        # ----------------------------------------------------

        imported = from_imports[
            current_file
        ].get(
            call_name
        )

        if imported:

            module_name = imported[
                "module"
            ]

            imported_name = imported[
                "name"
            ]

            for candidate_file in module_to_possible_files(
                current_file,
                module_name
            ):

                candidate_key = function_key(
                    candidate_file,
                    imported_name
                )

                if candidate_key in functions:

                    candidates.append(
                        candidate_key
                    )

        return list(
            dict.fromkeys(candidates)
        )

    # --------------------------------------------------------
    # module.function
    # --------------------------------------------------------

    parts = call_name.split(".")

    module_alias = parts[0]

    function_name = parts[-1]

    imported_module = imports[
        current_file
    ].get(
        module_alias
    )

    if imported_module:

        for candidate_file in module_to_possible_files(
            current_file,
            imported_module
        ):

            candidate_key = function_key(
                candidate_file,
                function_name
            )

            if candidate_key in functions:

                candidates.append(
                    candidate_key
                )

    # --------------------------------------------------------
    # direct module name
    # --------------------------------------------------------

    module_name = ".".join(
        parts[:-1]
    )

    for candidate_file in module_to_possible_files(
        current_file,
        module_name
    ):

        candidate_key = function_key(
            candidate_file,
            function_name
        )

        if candidate_key in functions:

            candidates.append(
                candidate_key
            )

    return list(
        dict.fromkeys(candidates)
    )


# ============================================================
# DISCOVER CALL GRAPH
# ============================================================

def discover_call_graph():
    for path, module_data in modules.items():

        source = module_data["source"]

        for key, function_data in functions.items():

            if function_data["file"] != path:
                continue

            node = function_data["node"]

            for child in ast.walk(node):

                if isinstance(
                    child,
                    ast.Call
                ):

                    call_name = get_call_name(
                        child.func
                    )

                    if not call_name:
                        continue

                    candidates = resolve_function_candidates(
                        path,
                        call_name
                    )

                    event = {
                        "caller": key,
                        "file": path,
                        "line": child.lineno,
                        "column": child.col_offset,
                        "call_name": call_name,
                        "resolved_candidates": candidates,
                        "source": get_source_segment(
                            source,
                            child
                        ),
                    }

                    call_sites.append(
                        event
                    )

                    for target in candidates:

                        forward_calls[
                            key
                        ].append(
                            target
                        )

                        reverse_calls[
                            target
                        ].append(
                            event
                        )

                        if (
                            target
                            == function_key(
                                os.path.join(
                                    PROJECT_DIR,
                                    TARGET_FILE_NAME
                                ),
                                TARGET_FUNCTION
                            )
                        ):

                            target_calls.append(
                                event
                            )


# ============================================================
# FUNCTION REFERENCE DISCOVERY
# ============================================================

def discover_function_references():
    for path, module_data in modules.items():

        tree = module_data["tree"]
        source = module_data["source"]

        local_function_names = {
            data["name"]
            for data in functions.values()
            if data["file"] == path
        }

        for node in ast.walk(tree):

            if not isinstance(
                node,
                ast.Name
            ):
                continue

            if node.id not in local_function_names:
                continue

            parent_context = (
                type(node.ctx).__name__
            )

            event = {
                "file": path,
                "line": node.lineno,
                "name": node.id,
                "context": parent_context,
                "source": get_source_segment(
                    source,
                    node
                ),
            }

            function_references.append(
                event
            )

            if node.id in {
                TARGET_FUNCTION,
                SECONDARY_TARGET,
            }:

                target_references.append(
                    event
                )


# ============================================================
# CALLER CHAIN RESOLUTION
# ============================================================

def resolve_caller_chains(
    target_key
):

    chains = []

    queue = deque()

    queue.append(
        (
            target_key,
            [target_key],
        )
    )

    visited = set()

    while queue:

        current, chain = queue.popleft()

        state = (
            current,
            tuple(chain)
        )

        if state in visited:
            continue

        visited.add(state)

        callers = reverse_calls.get(
            current,
            []
        )

        if not callers:

            chains.append(
                chain
            )

            continue

        if len(chain) >= MAX_CHAIN_DEPTH:

            chains.append(
                chain
            )

            continue

        for event in callers:

            caller = event[
                "caller"
            ]

            if caller in chain:
                continue

            queue.append(
                (
                    caller,
                    chain + [caller]
                )
            )

    return chains


# ============================================================
# ENTRYPOINT DETECTION
# ============================================================

def score_entry_candidate(
    key,
    distance
):

    data = functions.get(
        key
    )

    if data is None:
        return -999

    score = 0

    name = data[
        "name"
    ].lower()

    filename = os.path.basename(
        data["file"]
    ).lower()

    if name == "main":
        score += 100

    if name in PRODUCTION_ENTRY_NAMES:
        score += 50

    if name.startswith("run"):
        score += 20

    if name.startswith("process"):
        score += 20

    if name.startswith("generate"):
        score += 20

    if "engine" in filename:
        score += 10

    if "signal" in filename:
        score += 10

    score -= distance * 2

    return score


def resolve_entry_candidates(
    target_key
):

    chains = resolve_caller_chains(
        target_key
    )

    candidates = []

    for chain in chains:

        for distance, key in enumerate(
            chain[1:],
            start=1
        ):

            score = score_entry_candidate(
                key,
                distance
            )

            if score <= 0:
                continue

            candidates.append(
                {
                    "key": key,
                    "score": score,
                    "distance": distance,
                    "chain": chain,
                }
            )

    candidates.sort(
        key=lambda item: (
            -item["score"],
            item["distance"],
        )
    )

    unique = {}

    for item in candidates:

        key = item["key"]

        if key not in unique:
            unique[key] = item

    return list(
        unique.values()
    )


# ============================================================
# STATIC WRITE DETECTION
# ============================================================

WRITE_PREFIXES = (
    "INSERT",
    "UPDATE",
    "DELETE",
    "ALTER",
    "CREATE",
    "DROP",
    "REPLACE",
    "VACUUM",
    "REINDEX",
)


def static_write_reference_count():
    count = 0

    for path, module_data in modules.items():

        source_upper = (
            module_data["source"]
            .upper()
        )

        for prefix in WRITE_PREFIXES:

            count += source_upper.count(
                prefix
            )

    return count


# ============================================================
# TARGET REPORT
# ============================================================

def report_target():
    target_key = function_key(
        os.path.join(
            PROJECT_DIR,
            TARGET_FILE_NAME
        ),
        TARGET_FUNCTION
    )

    secondary_key = function_key(
        os.path.join(
            PROJECT_DIR,
            TARGET_FILE_NAME
        ),
        SECONDARY_TARGET
    )

    section(
        "STEP 5 — TARGET FUNCTION RESOLUTION"
    )

    print(
        "TARGET FILE              : "
        + TARGET_FILE_NAME
    )

    print(
        "TARGET FUNCTION          : "
        + TARGET_FUNCTION
        + "()"
    )

    print(
        "SECONDARY TARGET         : "
        + SECONDARY_TARGET
        + "()"
    )

    print(
        "TARGET EXISTS            : "
        + str(target_key in functions)
    )

    print(
        "SECONDARY EXISTS         : "
        + str(secondary_key in functions)
    )

    print()

    print(
        "DIRECT CALL SITES"
    )

    line("-", 100)

    if not target_calls:

        print(
            "NONE"
        )

    else:

        for event in target_calls:

            print(
                "CALLER="
                + display_function(
                    event["caller"]
                )
                + " | LINE="
                + str(event["line"])
                + " | CALL="
                + event["call_name"]
            )


# ============================================================
# CALLER REPORT
# ============================================================

def report_callers():
    target_key = function_key(
        os.path.join(
            PROJECT_DIR,
            TARGET_FILE_NAME
        ),
        TARGET_FUNCTION
    )

    section(
        "STEP 6 — DEEP CALLER CHAIN RESOLUTION"
    )

    chains = resolve_caller_chains(
        target_key
    )

    print(
        "CALLER CHAINS FOUND : "
        + str(len(chains))
    )

    if not chains:

        print(
            "NO CALLER CHAIN RESOLVED"
        )

        return []

    for index, chain in enumerate(
        chains[:50],
        start=1
    ):

        print()

        print(
            "CHAIN "
            + str(index)
        )

        for depth, key in enumerate(
            chain
        ):

            print(
                "  "
                + ("  " * depth)
                + "-> "
                + display_function(key)
            )

    return chains


# ============================================================
# ENTRYPOINT REPORT
# ============================================================

def report_entrypoints():
    target_key = function_key(
        os.path.join(
            PROJECT_DIR,
            TARGET_FILE_NAME
        ),
        TARGET_FUNCTION
    )

    section(
        "STEP 7 — PRODUCTION ENTRYPOINT CANDIDATE RESOLUTION"
    )

    candidates = resolve_entry_candidates(
        target_key
    )

    production_entry_candidates.clear()

    production_entry_candidates.extend(
        candidates
    )

    print(
        "ENTRYPOINT CANDIDATES : "
        + str(len(candidates))
    )

    if not candidates:

        print(
            "NO RELIABLE PRODUCTION ENTRYPOINT RESOLVED"
        )

        return candidates

    for index, item in enumerate(
        candidates[:30],
        start=1
    ):

        print()

        print(
            "CANDIDATE "
            + str(index)
        )

        print(
            "FUNCTION : "
            + display_function(
                item["key"]
            )
        )

        print(
            "SCORE    : "
            + str(item["score"])
        )

        print(
            "DISTANCE : "
            + str(item["distance"])
        )

        print(
            "CHAIN    :"
        )

        for key in item["chain"]:

            print(
                "  "
                + display_function(
                    key
                )
            )

    return candidates


# ============================================================
# FUNCTION REFERENCE REPORT
# ============================================================

def report_references():
    section(
        "STEP 8 — FUNCTION REFERENCE OBSERVATION"
    )

    target_events = [
        event
        for event in target_references
        if event["name"]
        in {
            TARGET_FUNCTION,
            SECONDARY_TARGET,
        }
    ]

    print(
        "TARGET FUNCTION REFERENCES : "
        + str(len(target_events))
    )

    if not target_events:

        print(
            "NONE"
        )

        return

    for event in target_events[:100]:

        relative = os.path.relpath(
            event["file"],
            PROJECT_DIR
        )

        print(
            relative
            + " | "
            + event["name"]
            + " | LINE="
            + str(event["line"])
            + " | CONTEXT="
            + event["context"]
        )


# ============================================================
# WRITE SAFETY REPORT
# ============================================================

def report_write_safety():
    section(
        "STEP 9 — WRITE SAFETY"
    )

    count = static_write_reference_count()

    print(
        "STATIC WRITE-LIKE REFERENCES : "
        + str(count)
    )

    print(
        "PRODUCTION EXECUTION          : NONE"
    )

    print(
        "PRODUCTION main()             : NOT CALLED"
    )

    print(
        "DATABASE CONNECTION           : NOT OPENED"
    )

    print(
        "DATABASE WRITE                : BLOCKED"
    )

    print()
    print(
        "IMPORTANT:"
    )

    print(
        "This audit is static only."
    )

    print(
        "No production function was executed."
    )

    print(
        "Static write-like references were not executed."
    )


# ============================================================
# FINAL DETERMINATION
# ============================================================

def determine_status():
    target_key = function_key(
        os.path.join(
            PROJECT_DIR,
            TARGET_FILE_NAME
        ),
        TARGET_FUNCTION
    )

    if target_key not in functions:

        return (
            "TARGET_FUNCTION_NOT_FOUND",
            "The requested production target function was not found."
        )

    if not target_calls:

        return (
            "PRODUCTION_CALLER_NOT_RESOLVED",
            "No direct production caller of create_outcome() was resolved."
        )

    if not production_entry_candidates:

        return (
            "PRODUCTION_CALL_CHAIN_FOUND_ENTRYPOINT_UNRESOLVED",
            "Caller references were found, but no sufficiently reliable production entrypoint was resolved."
        )

    return (
        "PRODUCTION_CALL_GRAPH_DEEP_RESOLVED",
        "A production caller chain reaching create_outcome() was resolved through static call-graph analysis."
    )


# ============================================================
# FINAL SUMMARY
# ============================================================

def final_summary():
    status, meaning = determine_status()

    selected = None

    if production_entry_candidates:

        selected = production_entry_candidates[0]

    section(
        "STEP 10 — FINAL FORENSIC SUMMARY"
    )

    print(
        "PYTHON FILES SCANNED        : "
        + str(files_scanned)
    )

    print(
        "FILES PARSED                : "
        + str(files_parsed)
    )

    print(
        "PARSE ERRORS                : "
        + str(len(parse_errors))
    )

    print(
        "FUNCTIONS DISCOVERED        : "
        + str(len(functions))
    )

    print(
        "CALL GRAPH EDGES            : "
        + str(len(call_sites))
    )

    print(
        "TARGET DIRECT CALL SITES    : "
        + str(len(target_calls))
    )

    print(
        "FUNCTION REFERENCES         : "
        + str(len(function_references))
    )

    print(
        "EXCLUDED FILES              : "
        + str(len(excluded_files))
    )

    print(
        "STATIC WRITE REFERENCES     : "
        + str(static_write_reference_count())
    )

    print()

    print(
        "FORENSIC CONCLUSION"
    )

    line("-")

    print(
        "STATUS                      : "
        + status
    )

    print(
        "MEANING                     : "
        + meaning
    )

    if selected is not None:

        print(
            "SELECTED ENTRYPOINT         : "
            + display_function(
                selected["key"]
            )
        )

        print(
            "ENTRYPOINT SCORE            : "
            + str(selected["score"])
        )

        print(
            "ENTRYPOINT DISTANCE         : "
            + str(selected["distance"])
        )

        print(
            "NEXT FRONTIER               : "
            "Build a dedicated READ-ONLY runtime trace "
            "for the resolved production caller chain."
        )

    elif status == (
        "PRODUCTION_CALLER_NOT_RESOLVED"
    ):

        print(
            "NEXT FRONTIER               : "
            "Continue static call-graph resolution "
            "from create_outcome()."
        )

    else:

        print(
            "NEXT FRONTIER               : "
            "Inspect unresolved target references "
            "and production module boundaries."
        )

    print()

    print(
        "IMPORTANT                   : "
        "No production function was executed."
    )

    print(
        "IMPORTANT                   : "
        "No production main() was executed."
    )

    print(
        "IMPORTANT                   : "
        "No runtime value was fabricated."
    )

    print(
        "IMPORTANT                   : "
        "No production formula was modified."
    )

    print(
        "IMPORTANT                   : "
        "No production database write was permitted."
    )

    print()

    print(
        "DATABASE WRITE OPERATIONS   : NONE"
    )

    print(
        "ENGINE MODIFICATIONS        : NONE ON DISK"
    )

    print(
        "INSERT                      : NONE"
    )

    print(
        "UPDATE                      : NONE"
    )

    print(
        "DELETE                      : NONE"
    )

    print(
        "ALTER                       : NONE"
    )

    print(
        "CREATE                      : NONE"
    )

    print(
        "DROP                        : NONE"
    )

    print(
        "PRODUCTION DB WRITE         : BLOCKED"
    )


# ============================================================
# ERROR REPORT
# ============================================================

def report_parse_errors():
    if not parse_errors:
        return

    section(
        "PARSE ERRORS"
    )

    for item in parse_errors[:50]:

        print(
            "FILE      : "
            + item["file"]
        )

        print(
            "EXCEPTION : "
            + item["exception"]
        )

        print()


# ============================================================
# MAIN
# ============================================================

def main():

    started = time.perf_counter()

    section(
        "ARUNDA SIGNAL OUTCOME CALL GRAPH DEEP "
        "RESOLUTION FORENSIC AUDIT v0.1"
    )

    print(
        "MODE                         : "
        "STATIC READ-ONLY FORENSICS"
    )

    print(
        "TARGET                       : "
        + TARGET_FILE_NAME
        + " -> "
        + TARGET_FUNCTION
        + "()"
    )

    print(
        "SECONDARY TARGET             : "
        + SECONDARY_TARGET
        + "()"
    )

    print(
        "PRODUCTION EXECUTION         : NONE"
    )

    print(
        "DATABASE WRITE               : BLOCKED"
    )

    try:

        section(
            "STEP 1 — PROJECT FILE DISCOVERY"
        )

        files = discover_python_files()

        print(
            "PYTHON FILES SELECTED        : "
            + str(len(files))
        )

        print(
            "EXCLUDED FILES               : "
            + str(len(excluded_files))
        )

        section(
            "STEP 2 — STATIC PARSING"
        )

        parse_files(
            files
        )

        print(
            "FILES PARSED                 : "
            + str(files_parsed)
        )

        print(
            "PARSE ERRORS                 : "
            + str(len(parse_errors))
        )

        section(
            "STEP 3 — SYMBOL DISCOVERY"
        )

        discover_definitions()

        print(
            "FUNCTIONS DISCOVERED         : "
            + str(len(functions))
        )

        print(
            "CLASSES DISCOVERED           : "
            + str(len(classes))
        )

        section(
            "STEP 4 — IMPORT GRAPH DISCOVERY"
        )

        discover_imports()

        print(
            "MODULE IMPORT TABLES         : "
            + str(len(imports))
        )

        print(
            "FROM-IMPORT TABLES           : "
            + str(len(from_imports))
        )

        section(
            "STEP 5 — CALL GRAPH BUILD"
        )

        discover_call_graph()

        print(
            "CALL GRAPH EDGES             : "
            + str(len(call_sites))
        )

        report_target()

        report_callers()

        report_entrypoints()

        discover_function_references()

        report_references()

        report_write_safety()

        final_summary()

        report_parse_errors()

        elapsed = (
            time.perf_counter()
            - started
        )

        print()

        line("=")

        print(
            "ELAPSED SECONDS              : "
            + f"{elapsed:.3f}"
        )

        print(
            "AUDIT COMPLETE"
        )

        line("=")

        return 0

    except Exception as exc:

        print()

        line("=")

        print(
            "FORENSIC AUDIT ERROR"
        )

        line("=")

        print(
            repr(exc)
        )

        print(
            traceback.format_exc()
        )

        print()

        print(
            "DATABASE WRITE OPERATIONS    : NONE"
        )

        print(
            "PRODUCTION DB WRITE          : BLOCKED"
        )

        return 1


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    raise SystemExit(
        main()
    )