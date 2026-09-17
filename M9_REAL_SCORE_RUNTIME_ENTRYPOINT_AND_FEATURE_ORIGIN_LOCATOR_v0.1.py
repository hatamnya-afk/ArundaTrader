# M9_REAL_FEATURE_OBJECT_LINEAGE_ALIAS_FUNCTION_REFERENCE_FORENSIC_v0.1.py

from __future__ import annotations

import ast
from pathlib import Path
from collections import defaultdict, deque


ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

FEATURES = {
    "bars_by_asset",
    "indicators_by_asset",
    "structures_by_asset",
}

TARGET_MODULE = "signal_scorer"
TARGET_FUNCTION = "run"

EXCLUDE_WORDS = (
    "forensic",
    "audit",
    "locator",
    "trace",
    "repair",
    "backup",
    "broken",
)


# ================================================================
# DATA
# ================================================================

class ModuleInfo:

    def __init__(self, path):

        self.path = path
        self.tree = None

        self.imports = []
        self.functions = []

        self.calls = []
        self.assignments = []
        self.returns = []

        self.feature_defs = []
        self.feature_uses = []

        self.aliases = []
        self.function_refs = []

        self.main_functions = []


# ================================================================
# HELPERS
# ================================================================

def dotted(node):

    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):

        left = dotted(node.value)

        if left:
            return left + "." + node.attr

        return node.attr

    return None


def call_name(node):

    return dotted(node.func)


def names_in_expr(node):

    result = []

    for n in ast.walk(node):

        if isinstance(n, ast.Name):
            result.append(n.id)

    return result


def valid_file(path):

    lower = path.name.lower()

    for word in EXCLUDE_WORDS:

        if word in lower:
            return False

    return True


# ================================================================
# AST ANALYZER
# ================================================================

class Analyzer(ast.NodeVisitor):

    def __init__(self, info):

        self.info = info
        self.current_function = "<module>"

    # ------------------------------------------------------------
    # FUNCTIONS
    # ------------------------------------------------------------

    def visit_FunctionDef(self, node):

        previous = self.current_function

        self.current_function = node.name

        args = [
            a.arg
            for a in node.args.args
        ]

        self.info.functions.append({
            "name": node.name,
            "line": node.lineno,
            "args": args,
        })

        if node.name == "main":
            self.info.main_functions.append(
                node.lineno
            )

        for arg in args:

            if arg in FEATURES:

                self.info.feature_defs.append({
                    "kind": "parameter",
                    "function": node.name,
                    "line": node.lineno,
                    "feature": arg,
                })

        self.generic_visit(node)

        self.current_function = previous

    visit_AsyncFunctionDef = visit_FunctionDef

    # ------------------------------------------------------------
    # IMPORTS
    # ------------------------------------------------------------

    def visit_Import(self, node):

        for alias in node.names:

            self.info.imports.append({
                "type": "import",
                "module": alias.name,
                "alias": alias.asname,
                "line": node.lineno,
            })

            if alias.name == TARGET_MODULE:

                self.info.aliases.append({
                    "kind": "module_alias",
                    "source": TARGET_MODULE,
                    "alias": alias.asname or TARGET_MODULE,
                    "line": node.lineno,
                })

        self.generic_visit(node)

    # ------------------------------------------------------------

    def visit_ImportFrom(self, node):

        module = node.module or ""

        for alias in node.names:

            full = f"{module}.{alias.name}"

            self.info.imports.append({
                "type": "from",
                "module": module,
                "name": alias.name,
                "alias": alias.asname,
                "line": node.lineno,
            })

            if (
                module == TARGET_MODULE
                and alias.name == TARGET_FUNCTION
            ):

                self.info.aliases.append({
                    "kind": "function_import",
                    "source": f"{TARGET_MODULE}.{TARGET_FUNCTION}",
                    "alias": alias.asname or TARGET_FUNCTION,
                    "line": node.lineno,
                })

        self.generic_visit(node)

    # ------------------------------------------------------------
    # ASSIGNMENTS
    # ------------------------------------------------------------

    def visit_Assign(self, node):

        value_name = dotted(node.value)

        targets = []

        for target in node.targets:

            target_name = dotted(target)

            if target_name:
                targets.append(target_name)

        feature_hits = (
            set(names_in_expr(node.value))
            & FEATURES
        )

        record = {
            "function": self.current_function,
            "line": node.lineno,
            "targets": targets,
            "value": value_name,
            "feature_refs": sorted(feature_hits),
        }

        self.info.assignments.append(record)

        # --------------------------------------------------------
        # Feature object creation / propagation
        # --------------------------------------------------------

        for feature in FEATURES:

            if feature in feature_hits:

                self.info.feature_uses.append({
                    "function": self.current_function,
                    "line": node.lineno,
                    "feature": feature,
                    "targets": targets,
                    "value": value_name,
                })

        # --------------------------------------------------------
        # signal_scorer.run function reference
        # --------------------------------------------------------

        if value_name in {
            "signal_scorer.run",
            "run",
        }:

            for target in targets:

                self.info.function_refs.append({
                    "kind": "scorer_function_reference",
                    "function": self.current_function,
                    "line": node.lineno,
                    "target": target,
                    "source": value_name,
                })

        self.generic_visit(node)

    # ------------------------------------------------------------
    # CALLS
    # ------------------------------------------------------------

    def visit_Call(self, node):

        name = call_name(node)

        args = []

        for arg in node.args:

            args.append(dotted(arg) or ast.dump(arg))

        keywords = {}

        for kw in node.keywords:

            keywords[
                kw.arg or "**"
            ] = dotted(kw.value) or ast.dump(kw.value)

        feature_hits = (
            set(names_in_expr(node))
            & FEATURES
        )

        record = {
            "function": self.current_function,
            "line": node.lineno,
            "callee": name,
            "args": args,
            "keywords": keywords,
            "features": sorted(feature_hits),
        }

        self.info.calls.append(record)

        # --------------------------------------------------------
        # Feature producer
        # --------------------------------------------------------

        if name:

            leaf = name.split(".")[-1]

            if leaf in {
                "build_features",
                "load_feature_snapshot",
                "build_feature_snapshot",
                "build_asset_features",
            }:

                self.info.feature_defs.append({
                    "kind": "producer_call",
                    "function": self.current_function,
                    "line": node.lineno,
                    "callee": name,
                    "args": args,
                })

        # --------------------------------------------------------
        # Direct scorer
        # --------------------------------------------------------

        if (
            name == "signal_scorer.run"
            or name == "run"
        ):

            self.info.function_refs.append({
                "kind": "direct_scorer_call",
                "function": self.current_function,
                "line": node.lineno,
                "callee": name,
                "args": args,
                "features": sorted(feature_hits),
            })

        self.generic_visit(node)

    # ------------------------------------------------------------
    # RETURNS
    # ------------------------------------------------------------

    def visit_Return(self, node):

        value_name = dotted(node.value)

        features = (
            set(names_in_expr(node.value))
            & FEATURES
        )

        self.info.returns.append({
            "function": self.current_function,
            "line": node.lineno,
            "value": value_name,
            "features": sorted(features),
        })

        self.generic_visit(node)


# ================================================================
# DISCOVER
# ================================================================

def discover():

    result = []

    for path in ROOT.rglob("*.py"):

        if not path.is_file():
            continue

        if not valid_file(path):
            continue

        result.append(path)

    return sorted(result)


# ================================================================
# PARSE
# ================================================================

def parse(path):

    info = ModuleInfo(path)

    try:

        source = path.read_text(
            encoding="utf-8",
            errors="replace",
        )

        info.tree = ast.parse(
            source,
            filename=str(path),
        )

        Analyzer(info).visit(info.tree)

        return info, None

    except Exception as exc:

        return info, str(exc)


# ================================================================
# MAIN
# ================================================================

def main():

    print("=" * 100)
    print(
        "ARUNDA TRADER — REAL FEATURE OBJECT LINEAGE "
        "ALIAS / FUNCTION REFERENCE FORENSIC v0.1"
    )
    print("=" * 100)

    print(f"PROJECT ROOT : {ROOT}")
    print("MODE         : READ ONLY")
    print("EXECUTION    : STATIC AST ONLY")
    print("DB ACCESS    : NONE")
    print("WRITES       : NONE")
    print("SYNTHETIC    : FORBIDDEN")
    print("=" * 100)

    files = discover()

    print("\nDISCOVERY")
    print("-" * 100)

    print(
        f"Python files discovered : {len(files)}"
    )

    infos = []
    failures = []

    for path in files:

        info, error = parse(path)

        if error:
            failures.append(
                (path, error)
            )
        else:
            infos.append(info)

    print(
        f"Files parsed            : {len(infos)}"
    )

    print(
        f"Syntax failures         : {len(failures)}"
    )

    # ============================================================
    # 1. SIGNAL SCORER IMPORT ALIASES
    # ============================================================

    print("\n" + "=" * 100)
    print("1 — SIGNAL SCORER IMPORT / ALIAS BOUNDARY")
    print("=" * 100)

    alias_hits = []

    for info in infos:

        for item in info.aliases:

            alias_hits.append(
                (info, item)
            )

    if not alias_hits:

        print("NO signal_scorer IMPORT / ALIAS FOUND")

    else:

        for info, item in alias_hits:

            print(
                f"{info.path.name}:{item['line']}"
            )

            print(
                f"  kind   = {item['kind']}"
            )

            print(
                f"  source = {item['source']}"
            )

            print(
                f"  alias  = {item['alias']}"
            )

    # ============================================================
    # 2. FUNCTION REFERENCES
    # ============================================================

    print("\n" + "=" * 100)
    print("2 — SIGNAL SCORER FUNCTION REFERENCES")
    print("=" * 100)

    refs = []

    for info in infos:

        for ref in info.function_refs:

            refs.append(
                (info, ref)
            )

    if not refs:

        print(
            "NO signal_scorer.run FUNCTION REFERENCE FOUND"
        )

    else:

        for info, ref in refs:

            print(
                f"{info.path.name}:{ref['line']}"
            )

            print(
                f"  kind     = {ref['kind']}"
            )

            print(
                f"  function = {ref['function']}"
            )

            print(
                f"  source   = "
                f"{ref.get('source', ref.get('callee'))}"
            )

            if "target" in ref:

                print(
                    f"  target   = {ref['target']}"
                )

            print(
                f"  args     = "
                f"{ref.get('args', [])}"
            )

            print(
                f"  features = "
                f"{ref.get('features', [])}"
            )

    # ============================================================
    # 3. FEATURE PRODUCER CALLS
    # ============================================================

    print("\n" + "=" * 100)
    print("3 — REAL FEATURE PRODUCER CALLS")
    print("=" * 100)

    producer_hits = []

    for info in infos:

        for item in info.feature_defs:

            if item["kind"] == "producer_call":

                producer_hits.append(
                    (info, item)
                )

    if not producer_hits:

        print(
            "NO FEATURE PRODUCER CALL FOUND"
        )

    else:

        for info, item in producer_hits:

            print(
                f"{info.path.name}:{item['line']}"
            )

            print(
                f"  function = {item['function']}"
            )

            print(
                f"  callee   = {item['callee']}"
            )

            print(
                f"  args     = {item['args']}"
            )

    # ============================================================
    # 4. FEATURE OBJECT DATAFLOW
    # ============================================================

    print("\n" + "=" * 100)
    print("4 — FEATURE OBJECT DATAFLOW CANDIDATES")
    print("=" * 100)

    feature_hits = []

    for info in infos:

        for item in info.feature_uses:

            feature_hits.append(
                (info, item)
            )

    if not feature_hits:

        print(
            "NO FEATURE OBJECT DATAFLOW FOUND"
        )

    else:

        for info, item in feature_hits:

            print(
                f"{info.path.name}:{item['line']}"
            )

            print(
                f"  function = {item['function']}"
            )

            print(
                f"  feature  = {item['feature']}"
            )

            print(
                f"  targets  = {item['targets']}"
            )

            print(
                f"  value    = {item['value']}"
            )

    # ============================================================
    # 5. MAIN / RUNTIME ENTRYPOINTS
    # ============================================================

    print("\n" + "=" * 100)
    print("5 — RUNTIME ENTRYPOINTS")
    print("=" * 100)

    for info in infos:

        if info.main_functions:

            print(
                f"{info.path.name}"
            )

            for line in info.main_functions:

                print(
                    f"  main() line = {line}"
                )

    # ============================================================
    # 6. CALLS CONTAINING FEATURE OBJECTS
    # ============================================================

    print("\n" + "=" * 100)
    print("6 — CALLS CARRYING REAL FEATURE OBJECTS")
    print("=" * 100)

    found = False

    for info in infos:

        for call in info.calls:

            if call["features"]:

                found = True

                print(
                    f"{info.path.name}:{call['line']}"
                )

                print(
                    f"  function = {call['function']}"
                )

                print(
                    f"  callee   = {call['callee']}"
                )

                print(
                    f"  args     = {call['args']}"
                )

                print(
                    f"  features = {call['features']}"
                )

    if not found:

        print(
            "NO CALL CARRYING FEATURE OBJECTS FOUND"
        )

    # ============================================================
    # 7. RETURNS CARRYING FEATURES
    # ============================================================

    print("\n" + "=" * 100)
    print("7 — FEATURE-BEARING RETURN PATHS")
    print("=" * 100)

    found = False

    for info in infos:

        for ret in info.returns:

            if ret["features"]:

                found = True

                print(
                    f"{info.path.name}:{ret['line']}"
                )

                print(
                    f"  function = {ret['function']}"
                )

                print(
                    f"  value    = {ret['value']}"
                )

                print(
                    f"  features = {ret['features']}"
                )

    if not found:

        print(
            "NO FEATURE-BEARING RETURN FOUND"
        )

    # ============================================================
    # 8. HIGH VALUE MODULES
    # ============================================================

    print("\n" + "=" * 100)
    print("8 — HIGH-VALUE MODULES")
    print("=" * 100)

    scores = []

    for info in infos:

        score = 0

        if info.aliases:
            score += 10

        if info.function_refs:
            score += 20

        if info.feature_defs:
            score += 15

        if info.feature_uses:
            score += 10

        if info.main_functions:
            score += 5

        name = info.path.name.lower()

        for key in (
            "pipeline",
            "runtime",
            "engine",
            "source",
            "main",
            "scheduler",
            "worker",
            "service",
            "loop",
        ):

            if key in name:

                score += 2

        if score:

            scores.append(
                (score, info)
            )

    scores.sort(
        key=lambda x: x[0],
        reverse=True,
    )

    for score, info in scores[:40]:

        print(
            f"{info.path.name}"
        )

        print(
            f"  SCORE = {score}"
        )

        print(
            f"  imports={len(info.imports)} "
            f"aliases={len(info.aliases)} "
            f"refs={len(info.function_refs)} "
            f"feature_defs={len(info.feature_defs)} "
            f"feature_uses={len(info.feature_uses)}"
        )

    # ============================================================
    # 9. VERDICT
    # ============================================================

    print("\n" + "=" * 100)
    print("FORENSIC VERDICT")
    print("=" * 100)

    direct = [
        (i, r)
        for i, r in refs
        if r["kind"] == "direct_scorer_call"
    ]

    function_refs = [
        (i, r)
        for i, r in refs
        if r["kind"] == "scorer_function_reference"
    ]

    feature_producers = producer_hits

    if direct:

        print(
            "SIGNAL SCORER DIRECT CALL : FOUND"
        )

    elif function_refs:

        print(
            "SIGNAL SCORER FUNCTION REFERENCE : FOUND"
        )

    else:

        print(
            "SIGNAL SCORER DIRECT/REFERENCE CALL : NOT FOUND"
        )

    print(
        f"FEATURE PRODUCER CALLS : "
        f"{len(feature_producers)}"
    )

    print()
    print(
        "OBJECT LINEAGE TARGET:"
    )

    print(
        "REAL MARKET DATA"
    )

    print(
        "      ↓"
    )

    print(
        "FEATURE PRODUCER"
    )

    print(
        "      ↓"
    )

    print(
        "bars_by_asset"
    )

    print(
        "indicators_by_asset"
    )

    print(
        "structures_by_asset"
    )

    print(
        "      ↓"
    )

    print(
        "ALIAS / FUNCTION REFERENCE / WRAPPER"
    )

    print(
        "      ↓"
    )

    print(
        "signal_scorer.run"
    )

    print(
        "      ↓"
    )

    print(
        "load_scores"
    )

    print(
        "      ↓"
    )

    print(
        "DECISION ENGINE"
    )

    print()

    if direct or function_refs:

        print(
            "RESULT : SCORER RUNTIME BOUNDARY "
            "IS NOW TRACEABLE BEYOND SIMPLE CALL SEARCH."
        )

    elif feature_producers:

        print(
            "RESULT : FEATURE PRODUCER EXISTS, "
            "BUT SCORER CONNECTION REMAINS UNRESOLVED."
        )

    else:

        print(
            "RESULT : OBJECT PRODUCER LINEAGE "
            "REMAINS UNRESOLVED."
        )

    print()
    print(
        "NO PRODUCTION MODIFICATION."
    )

    print("=" * 100)
    print("M9 STATUS : COMPLETE")
    print("=" * 100)


if __name__ == "__main__":
    main()