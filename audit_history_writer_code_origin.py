"""
ARUNDA TRADER
HISTORY WRITER CODE ORIGIN AUDIT v0.1

Purpose
-------
Read-only source-code audit for discovering the code origin of
market_history writers.

This audit:
    - DOES NOT modify the database
    - DOES NOT modify source files
    - DOES NOT INSERT / UPDATE / DELETE
    - DOES NOT ALTER / CREATE database objects
    - DOES NOT execute project modules
    - ONLY reads source files and analyzes text/code structure

Database fingerprint supplied by previous audits:
    Total contaminated rows : 699,000
    Contaminated assets      : 987
    Batch size               : 1,000 rows
    Batch frequency          : ~60 seconds
    Number of batches        : 699
    First contaminated ID    : 4,936
    Lineage                  : NULL / NULL
"""

from __future__ import annotations

import argparse
import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


# =============================================================================
# VERSION
# =============================================================================

AUDIT_NAME = "ARUNDA TRADER — HISTORY WRITER CODE ORIGIN AUDIT v0.1"
AUDIT_VERSION = "v0.1"


# =============================================================================
# DATABASE FINGERPRINT
# =============================================================================

DB_FINGERPRINT = {
    "contaminated_rows": 699_000,
    "assets": 987,
    "batch_size": 1_000,
    "batch_frequency_seconds": 60.0,
    "batches": 699,
    "first_id": 4_936,
    "lineage_source": None,
    "lineage_engine": None,
}


# =============================================================================
# FILE CONFIGURATION
# =============================================================================

DEFAULT_EXTENSIONS = {
    ".py",
    ".pyw",
}

DEFAULT_EXCLUDED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".idea",
    ".vscode",
    "node_modules",
    "dist",
    "build",
    "site-packages",
}


# =============================================================================
# REGEX PATTERNS
# =============================================================================

PATTERNS = {
    "market_history": re.compile(
        r"\bmarket_history\b",
        re.IGNORECASE,
    ),
    "insert_market_history": re.compile(
        r"""
        INSERT\s+INTO\s+
        ["'`]?market_history["'`]?
        """,
        re.IGNORECASE | re.VERBOSE,
    ),
    "insert": re.compile(
        r"\bINSERT\b",
        re.IGNORECASE,
    ),
    "executemany": re.compile(
        r"\bexecutemany\s*\(",
        re.IGNORECASE,
    ),
    "execute": re.compile(
        r"\bexecute\s*\(",
        re.IGNORECASE,
    ),
    "created_at": re.compile(
        r"\bcreated_at\b",
        re.IGNORECASE,
    ),
    "timestamp": re.compile(
        r"\btimestamp\b",
        re.IGNORECASE,
    ),
    "source": re.compile(
        r"\bsource\b",
        re.IGNORECASE,
    ),
    "engine": re.compile(
        r"\bengine\b",
        re.IGNORECASE,
    ),
    "sleep": re.compile(
        r"\bsleep\s*\(",
        re.IGNORECASE,
    ),
    "while_true": re.compile(
        r"\bwhile\s+True\s*:",
        re.IGNORECASE,
    ),
    "batch": re.compile(
        r"\bbatch\b",
        re.IGNORECASE,
    ),
}


# Numeric literals / obvious configuration values
NUMBER_1000 = re.compile(r"(?<!\d)1000(?!\d)")
NUMBER_987 = re.compile(r"(?<!\d)987(?!\d)")
NUMBER_60 = re.compile(r"(?<![\d.])60(?:\.0+)?(?![\d.])")


# =============================================================================
# DATA STRUCTURES
# =============================================================================


@dataclass
class SourceHit:
    path: Path
    line_number: int
    category: str
    text: str


@dataclass
class FunctionInfo:
    name: str
    qualname: str
    line: int
    end_line: int | None
    is_async: bool = False
    decorators: list[str] = field(default_factory=list)


@dataclass
class CodeCandidate:
    path: Path

    market_history_refs: list[SourceHit] = field(default_factory=list)
    insert_market_history_hits: list[SourceHit] = field(default_factory=list)

    execute_hits: list[SourceHit] = field(default_factory=list)
    executemany_hits: list[SourceHit] = field(default_factory=list)

    created_at_hits: list[SourceHit] = field(default_factory=list)
    timestamp_hits: list[SourceHit] = field(default_factory=list)

    source_hits: list[SourceHit] = field(default_factory=list)
    engine_hits: list[SourceHit] = field(default_factory=list)

    sleep_hits: list[SourceHit] = field(default_factory=list)
    while_true_hits: list[SourceHit] = field(default_factory=list)

    batch_hits: list[SourceHit] = field(default_factory=list)

    number_1000_hits: list[SourceHit] = field(default_factory=list)
    number_987_hits: list[SourceHit] = field(default_factory=list)
    number_60_hits: list[SourceHit] = field(default_factory=list)

    functions: list[FunctionInfo] = field(default_factory=list)

    syntax_error: str | None = None

    score: int = 0
    confidence: str = "LOW"

    fingerprint_matches: dict[str, str] = field(default_factory=dict)


# =============================================================================
# TERMINAL HELPERS
# =============================================================================


def line(char: str = "-", width: int = 100) -> str:
    return char * width


def header(title: str) -> None:
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def section(title: str) -> None:
    print()
    print("-" * 100)
    print(title)
    print("-" * 100)


def safe_relative(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


# =============================================================================
# FILE DISCOVERY
# =============================================================================


def should_skip(path: Path, excluded_dirs: set[str]) -> bool:
    return any(part in excluded_dirs for part in path.parts)


def iter_source_files(
    root: Path,
    extensions: set[str],
    excluded_dirs: set[str],
) -> Iterable[Path]:

    for path in root.rglob("*"):
        if not path.is_file():
            continue

        if should_skip(path, excluded_dirs):
            continue

        if path.suffix.lower() not in extensions:
            continue

        yield path


# =============================================================================
# SOURCE READING
# =============================================================================


def read_text(path: Path) -> str:
    encodings = (
        "utf-8",
        "utf-8-sig",
        "cp1252",
        "latin-1",
    )

    for encoding in encodings:
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue

    raise UnicodeDecodeError(
        "unknown",
        b"",
        0,
        1,
        f"Unable to decode {path}",
    )


# =============================================================================
# AST ANALYSIS
# =============================================================================


class FunctionCollector(ast.NodeVisitor):
    def __init__(self) -> None:
        self.stack: list[str] = []
        self.functions: list[FunctionInfo] = []

    def _visit_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> None:

        name = node.name

        if self.stack:
            qualname = ".".join(self.stack + [name])
        else:
            qualname = name

        decorators: list[str] = []

        for decorator in node.decorator_list:
            try:
                decorators.append(ast.unparse(decorator))
            except Exception:
                decorators.append("<unparseable>")

        self.functions.append(
            FunctionInfo(
                name=name,
                qualname=qualname,
                line=node.lineno,
                end_line=getattr(node, "end_lineno", None),
                is_async=isinstance(node, ast.AsyncFunctionDef),
                decorators=decorators,
            )
        )

        self.stack.append(name)

        for child in node.body:
            self.visit(child)

        self.stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(
        self,
        node: ast.AsyncFunctionDef,
    ) -> None:
        self._visit_function(node)


def parse_functions(source: str) -> tuple[list[FunctionInfo], str | None]:
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [], f"{exc.msg} at line {exc.lineno}"

    collector = FunctionCollector()
    collector.visit(tree)

    return collector.functions, None


# =============================================================================
# HIT EXTRACTION
# =============================================================================


def make_hits(
    path: Path,
    lines: list[str],
    pattern: re.Pattern[str],
    category: str,
) -> list[SourceHit]:

    hits: list[SourceHit] = []

    for index, text in enumerate(lines, start=1):
        if pattern.search(text):
            hits.append(
                SourceHit(
                    path=path,
                    line_number=index,
                    category=category,
                    text=text.strip(),
                )
            )

    return hits


def make_numeric_hits(
    path: Path,
    lines: list[str],
    pattern: re.Pattern[str],
    category: str,
) -> list[SourceHit]:

    return make_hits(
        path,
        lines,
        pattern,
        category,
    )


# =============================================================================
# CANDIDATE ANALYSIS
# =============================================================================


def analyze_file(path: Path) -> CodeCandidate | None:

    try:
        source = read_text(path)
    except Exception as exc:
        print(
            f"[READ ERROR] {path}: {exc}"
        )
        return None

    lines = source.splitlines()

    candidate = CodeCandidate(path=path)

    candidate.market_history_refs = make_hits(
        path,
        lines,
        PATTERNS["market_history"],
        "MARKET_HISTORY",
    )

    candidate.insert_market_history_hits = make_hits(
        path,
        lines,
        PATTERNS["insert_market_history"],
        "INSERT_MARKET_HISTORY",
    )

    candidate.execute_hits = make_hits(
        path,
        lines,
        PATTERNS["execute"],
        "EXECUTE",
    )

    candidate.executemany_hits = make_hits(
        path,
        lines,
        PATTERNS["executemany"],
        "EXECUTEMANY",
    )

    candidate.created_at_hits = make_hits(
        path,
        lines,
        PATTERNS["created_at"],
        "CREATED_AT",
    )

    candidate.timestamp_hits = make_hits(
        path,
        lines,
        PATTERNS["timestamp"],
        "TIMESTAMP",
    )

    candidate.source_hits = make_hits(
        path,
        lines,
        PATTERNS["source"],
        "SOURCE",
    )

    candidate.engine_hits = make_hits(
        path,
        lines,
        PATTERNS["engine"],
        "ENGINE",
    )

    candidate.sleep_hits = make_hits(
        path,
        lines,
        PATTERNS["sleep"],
        "SLEEP",
    )

    candidate.while_true_hits = make_hits(
        path,
        lines,
        PATTERNS["while_true"],
        "WHILE_TRUE",
    )

    candidate.batch_hits = make_hits(
        path,
        lines,
        PATTERNS["batch"],
        "BATCH",
    )

    candidate.number_1000_hits = make_numeric_hits(
        path,
        lines,
        NUMBER_1000,
        "NUMBER_1000",
    )

    candidate.number_987_hits = make_numeric_hits(
        path,
        lines,
        NUMBER_987,
        "NUMBER_987",
    )

    candidate.number_60_hits = make_numeric_hits(
        path,
        lines,
        NUMBER_60,
        "NUMBER_60",
    )

    candidate.functions, candidate.syntax_error = parse_functions(
        source
    )

    calculate_score(candidate)

    return candidate


# =============================================================================
# SCORE
# =============================================================================


def calculate_score(candidate: CodeCandidate) -> None:

    score = 0

    if candidate.insert_market_history_hits:
        score += 50

    if candidate.market_history_refs:
        score += 20

    if candidate.executemany_hits:
        score += 15

    if candidate.execute_hits:
        score += 5

    if candidate.created_at_hits:
        score += 5

    if candidate.timestamp_hits:
        score += 5

    if candidate.source_hits:
        score += 3

    if candidate.engine_hits:
        score += 3

    if candidate.sleep_hits:
        score += 5

    if candidate.while_true_hits:
        score += 5

    if candidate.number_1000_hits:
        score += 10

    if candidate.number_987_hits:
        score += 10

    if candidate.number_60_hits:
        score += 10

    candidate.score = score

    if candidate.insert_market_history_hits:
        if (
            candidate.executemany_hits
            and candidate.number_1000_hits
            and candidate.sleep_hits
        ):
            candidate.confidence = "HIGH"

        elif candidate.executemany_hits:
            candidate.confidence = "HIGH"

        else:
            candidate.confidence = "MEDIUM"

    elif candidate.market_history_refs:
        if candidate.executemany_hits or candidate.execute_hits:
            candidate.confidence = "MEDIUM"
        else:
            candidate.confidence = "LOW"

    else:
        candidate.confidence = "LOW"


# =============================================================================
# CONTEXT ANALYSIS
# =============================================================================


def get_context(
    path: Path,
    line_number: int,
    radius: int = 3,
) -> list[tuple[int, str]]:

    try:
        lines = read_text(path).splitlines()
    except Exception:
        return []

    start = max(1, line_number - radius)
    end = min(len(lines), line_number + radius)

    result: list[tuple[int, str]] = []

    for number in range(start, end + 1):
        result.append(
            (
                number,
                lines[number - 1].strip(),
            )
        )

    return result


def nearest_function(
    candidate: CodeCandidate,
    line_number: int,
) -> FunctionInfo | None:

    matches = []

    for function in candidate.functions:

        if function.line > line_number:
            continue

        if function.end_line is not None:
            if line_number <= function.end_line:
                matches.append(function)
        else:
            matches.append(function)

    if not matches:
        return None

    return max(
        matches,
        key=lambda item: item.line,
    )


# =============================================================================
# FINGERPRINT MATCHING
# =============================================================================


def match_fingerprint(candidate: CodeCandidate) -> None:

    candidate.fingerprint_matches = {}

    # -------------------------------------------------------------------------
    # Batch size
    # -------------------------------------------------------------------------

    if candidate.number_1000_hits:
        candidate.fingerprint_matches["BATCH SIZE"] = "MATCH"
    else:
        candidate.fingerprint_matches["BATCH SIZE"] = "NO DIRECT MATCH"

    # -------------------------------------------------------------------------
    # Asset count
    # -------------------------------------------------------------------------

    if candidate.number_987_hits:
        candidate.fingerprint_matches["ASSET UNIVERSE"] = "MATCH"
    else:
        candidate.fingerprint_matches["ASSET UNIVERSE"] = "NO DIRECT MATCH"

    # -------------------------------------------------------------------------
    # Interval
    # -------------------------------------------------------------------------

    if candidate.number_60_hits or candidate.sleep_hits:
        candidate.fingerprint_matches["~60 SEC LOOP"] = "POSSIBLE MATCH"
    else:
        candidate.fingerprint_matches["~60 SEC LOOP"] = "NO DIRECT MATCH"

    # -------------------------------------------------------------------------
    # Bulk insertion
    # -------------------------------------------------------------------------

    if candidate.executemany_hits:
        candidate.fingerprint_matches["BULK INSERT"] = "MATCH"
    elif candidate.execute_hits:
        candidate.fingerprint_matches["BULK INSERT"] = "POSSIBLE"
    else:
        candidate.fingerprint_matches["BULK INSERT"] = "NO MATCH"

    # -------------------------------------------------------------------------
    # Lineage
    # -------------------------------------------------------------------------

    has_source = bool(candidate.source_hits)
    has_engine = bool(candidate.engine_hits)

    if has_source and has_engine:
        candidate.fingerprint_matches["LINEAGE FIELDS"] = "PRESENT"
    elif has_source or has_engine:
        candidate.fingerprint_matches["LINEAGE FIELDS"] = "PARTIAL"
    else:
        candidate.fingerprint_matches["LINEAGE FIELDS"] = "NOT FOUND"


# =============================================================================
# RANKING
# =============================================================================


def rank_candidates(
    candidates: list[CodeCandidate],
) -> list[CodeCandidate]:

    for candidate in candidates:
        match_fingerprint(candidate)

    return sorted(
        candidates,
        key=lambda item: (
            item.score,
            len(item.insert_market_history_hits),
            len(item.executemany_hits),
            len(item.market_history_refs),
        ),
        reverse=True,
    )


# =============================================================================
# REPORTING
# =============================================================================


def print_candidate_summary(
    candidate: CodeCandidate,
    root: Path,
) -> None:

    print()
    print(f"FILE       : {safe_relative(candidate.path, root)}")
    print(f"SCORE      : {candidate.score}")
    print(f"CONFIDENCE : {candidate.confidence}")

    print()
    print("MATCH COUNTS")
    print(
        f"  market_history refs : "
        f"{len(candidate.market_history_refs)}"
    )
    print(
        f"  INSERT market_history : "
        f"{len(candidate.insert_market_history_hits)}"
    )
    print(
        f"  executemany : "
        f"{len(candidate.executemany_hits)}"
    )
    print(
        f"  execute : "
        f"{len(candidate.execute_hits)}"
    )
    print(
        f"  created_at : "
        f"{len(candidate.created_at_hits)}"
    )
    print(
        f"  timestamp : "
        f"{len(candidate.timestamp_hits)}"
    )
    print(
        f"  source : "
        f"{len(candidate.source_hits)}"
    )
    print(
        f"  engine : "
        f"{len(candidate.engine_hits)}"
    )
    print(
        f"  sleep : "
        f"{len(candidate.sleep_hits)}"
    )
    print(
        f"  while True : "
        f"{len(candidate.while_true_hits)}"
    )
    print(
        f"  literal 1000 : "
        f"{len(candidate.number_1000_hits)}"
    )
    print(
        f"  literal 987 : "
        f"{len(candidate.number_987_hits)}"
    )
    print(
        f"  literal 60 : "
        f"{len(candidate.number_60_hits)}"
    )

    print()
    print("DATABASE FINGERPRINT COMPARISON")

    for key, value in candidate.fingerprint_matches.items():
        print(
            f"  {key:<20} : {value}"
        )

    if candidate.syntax_error:
        print()
        print(
            f"AST STATUS : SYNTAX ERROR — "
            f"{candidate.syntax_error}"
        )


def print_hits(
    title: str,
    hits: list[SourceHit],
    root: Path,
    limit: int = 12,
) -> None:

    if not hits:
        return

    print()
    print(title)

    for hit in hits[:limit]:

        print(
            f"  {safe_relative(hit.path, root)}:"
            f"{hit.line_number}"
            f" | {hit.text}"
        )

    if len(hits) > limit:
        print(
            f"  ... {len(hits) - limit} additional hits"
        )


def print_function_context(
    candidate: CodeCandidate,
    root: Path,
) -> None:

    interesting_hits = (
        candidate.insert_market_history_hits
        or candidate.executemany_hits
        or candidate.market_history_refs
    )

    if not interesting_hits:
        return

    print()
    print("WRITER FUNCTION CONTEXT")

    seen: set[tuple[str, int]] = set()

    for hit in interesting_hits[:20]:

        function = nearest_function(
            candidate,
            hit.line_number,
        )

        if function is None:
            key = ("<module>", 0)

            if key in seen:
                continue

            seen.add(key)

            print(
                f"  {safe_relative(candidate.path, root)}:"
                f"{hit.line_number}"
                f" | FUNCTION : <MODULE>"
            )

        else:
            key = (
                function.qualname,
                function.line,
            )

            if key in seen:
                continue

            seen.add(key)

            print(
                f"  {safe_relative(candidate.path, root)}:"
                f"{hit.line_number}"
                f" | FUNCTION : {function.qualname}"
                f" | DEFINITION LINE : {function.line}"
            )


# =============================================================================
# CROSS-CANDIDATE ANALYSIS
# =============================================================================


def identify_confirmed_candidates(
    candidates: list[CodeCandidate],
) -> list[CodeCandidate]:

    result = []

    for candidate in candidates:

        if not candidate.insert_market_history_hits:
            continue

        if candidate.executemany_hits:
            result.append(candidate)
            continue

        if (
            candidate.execute_hits
            and candidate.market_history_refs
        ):
            result.append(candidate)

    return result


def identify_possible_candidates(
    candidates: list[CodeCandidate],
) -> list[CodeCandidate]:

    result = []

    for candidate in candidates:

        if candidate in identify_confirmed_candidates(candidates):
            continue

        if candidate.market_history_refs:
            result.append(candidate)

    return result


# =============================================================================
# ARGUMENTS
# =============================================================================


def parse_args() -> argparse.Namespace:

    parser = argparse.ArgumentParser(
        description=(
            "ArundaTrader History Writer Code Origin Audit v0.1"
        )
    )

    parser.add_argument(
        "root",
        nargs="?",
        default=".",
        help="ArundaTrader project root",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Number of top candidates to display",
    )

    parser.add_argument(
        "--show-context",
        action="store_true",
        help="Show source context around important hits",
    )

    parser.add_argument(
        "--all-hits",
        action="store_true",
        help="Display more matching source lines",
    )

    return parser.parse_args()


# =============================================================================
# MAIN AUDIT
# =============================================================================


def main() -> int:

    args = parse_args()

    root = Path(args.root).expanduser().resolve()

    header(AUDIT_NAME)

    print(
        f"MODE                 : READ ONLY"
    )
    print(
        f"SOURCE ROOT          : {root}"
    )
    print(
        f"DATABASE              : NOT ACCESSED"
    )
    print(
        f"WRITE OPERATIONS     : NONE"
    )
    print(
        f"SCHEMA CHANGES       : NONE"
    )
    print(
        f"DELETE OPERATIONS    : NONE"
    )
    print(
        f"INSERT OPERATIONS    : NONE"
    )
    print(
        f"UPDATE OPERATIONS    : NONE"
    )
    print(
        f"ALTER / CREATE       : NONE"
    )
    print(
        f"PROJECT MODULES      : NOT EXECUTED"
    )

    if not root.exists():
        print()
        print(
            f"[ERROR] Source root does not exist:"
            f" {root}"
        )
        return 1

    if not root.is_dir():
        print()
        print(
            f"[ERROR] Source root is not a directory:"
            f" {root}"
        )
        return 1

    # -------------------------------------------------------------------------
    # Discover files
    # -------------------------------------------------------------------------

    section("SOURCE FILE DISCOVERY")

    files = list(
        iter_source_files(
            root=root,
            extensions=DEFAULT_EXTENSIONS,
            excluded_dirs=DEFAULT_EXCLUDED_DIRS,
        )
    )

    files.sort()

    print(
        f"Python source files scanned : {len(files):,}"
    )

    print(
        f"Excluded directories        : "
        f"{len(DEFAULT_EXCLUDED_DIRS)}"
    )

    # -------------------------------------------------------------------------
    # Analyze files
    # -------------------------------------------------------------------------

    section("SOURCE CODE ANALYSIS")

    candidates: list[CodeCandidate] = []

    for index, path in enumerate(files, start=1):

        candidate = analyze_file(path)

        if candidate is None:
            continue

        if candidate.market_history_refs:
            candidates.append(candidate)

        elif candidate.insert_market_history_hits:
            candidates.append(candidate)

        # Progress is intentionally minimal.
        if index % 250 == 0:
            print(
                f"Scanned : {index:,}/{len(files):,}"
            )

    candidates = rank_candidates(candidates)

    print(
        f"Files referencing market_history : "
        f"{len(candidates):,}"
    )

    # -------------------------------------------------------------------------
    # Candidate ranking
    # -------------------------------------------------------------------------

    section("WRITER CANDIDATE RANKING")

    if not candidates:

        print(
            "NO SOURCE-CODE REFERENCE TO market_history FOUND."
        )

        print()
        print(
            "This does NOT prove that no writer exists."
        )

        print(
            "Possible reasons:"
        )

        print(
            "  - dynamic SQL"
        )
        print(
            "  - table name assembled at runtime"
        )
        print(
            "  - writer lives outside scanned Python files"
        )
        print(
            "  - generated code"
        )

        print()
        print(
            f"{AUDIT_NAME} COMPLETE"
        )

        return 0

    display_limit = max(1, args.limit)

    for index, candidate in enumerate(
        candidates[:display_limit],
        start=1,
    ):

        print()
        print(
            f"[CANDIDATE #{index}]"
        )

        print_candidate_summary(
            candidate,
            root,
        )

        print_function_context(
            candidate,
            root,
        )

        print_hits(
            "INSERT market_history HITS",
            candidate.insert_market_history_hits,
            root,
            limit=100 if args.all_hits else 12,
        )

        print_hits(
            "EXECUTEMANY HITS",
            candidate.executemany_hits,
            root,
            limit=100 if args.all_hits else 8,
        )

        if args.show_context:

            important = (
                candidate.insert_market_history_hits
                or candidate.executemany_hits
                or candidate.market_history_refs
            )

            for hit in important[:5]:

                print()
                print(
                    f"CONTEXT "
                    f"{safe_relative(candidate.path, root)}:"
                    f"{hit.line_number}"
                )

                for number, text in get_context(
                    candidate.path,
                    hit.line_number,
                    radius=3,
                ):

                    marker = ">>" if number == hit.line_number else "  "

                    print(
                        f"  {marker} "
                        f"{number:>5} | {text}"
                    )

    # -------------------------------------------------------------------------
    # Confirmed / possible
    # -------------------------------------------------------------------------

    confirmed = identify_confirmed_candidates(
        candidates
    )

    possible = identify_possible_candidates(
        candidates
    )

    section("CONFIRMED WRITER CANDIDATES")

    if confirmed:

        for index, candidate in enumerate(
            confirmed,
            start=1,
        ):

            print(
                f"{index}. "
                f"{safe_relative(candidate.path, root)}"
                f" | score={candidate.score}"
                f" | confidence={candidate.confidence}"
            )

    else:

        print(
            "No high-confidence market_history writer "
            "was confirmed from source text."
        )

    section("POSSIBLE WRITER CANDIDATES")

    if possible:

        for index, candidate in enumerate(
            possible,
            start=1,
        ):

            print(
                f"{index}. "
                f"{safe_relative(candidate.path, root)}"
                f" | score={candidate.score}"
                f" | confidence={candidate.confidence}"
            )

    else:

        print(
            "No additional possible writers found."
        )

    # -------------------------------------------------------------------------
    # Database fingerprint reference
    # -------------------------------------------------------------------------

    section("DATABASE CONTAMINATION FINGERPRINT — REFERENCE ONLY")

    print(
        f"Contaminated rows       : "
        f"{DB_FINGERPRINT['contaminated_rows']:,}"
    )

    print(
        f"Assets                  : "
        f"{DB_FINGERPRINT['assets']:,}"
    )

    print(
        f"Batch size              : "
        f"{DB_FINGERPRINT['batch_size']:,}"
    )

    print(
        f"Approx interval         : "
        f"{DB_FINGERPRINT['batch_frequency_seconds']:.1f} sec"
    )

    print(
        f"Observed batches        : "
        f"{DB_FINGERPRINT['batches']:,}"
    )

    print(
        f"First contaminated ID   : "
        f"{DB_FINGERPRINT['first_id']:,}"
    )

    print(
        f"Lineage source          : "
        f"{DB_FINGERPRINT['lineage_source']}"
    )

    print(
        f"Lineage engine          : "
        f"{DB_FINGERPRINT['lineage_engine']}"
    )

    # -------------------------------------------------------------------------
    # Final assessment
    # -------------------------------------------------------------------------

    section("ROOT CAUSE CODE ORIGIN ASSESSMENT")

    if confirmed:

        strongest = confirmed[0]

        print(
            "HIGH-CONFIDENCE WRITER CANDIDATE FOUND"
        )

        print()
        print(
            f"FILE       : "
            f"{safe_relative(strongest.path), root}"
        )

        print(
            f"SCORE      : "
            f"{strongest.score}"
        )

        print(
            f"CONFIDENCE : "
            f"{strongest.confidence}"
        )

        print()
        print(
            "IMPORTANT:"
        )

        print(
            "This audit identifies a code candidate."
        )

        print(
            "It does NOT modify or execute that writer."
        )

        print(
            "It does NOT yet declare the database records valid/invalid."
        )

    elif possible:

        print(
            "POSSIBLE WRITER CODE FOUND"
        )

        print(
            "Further static analysis is required."
        )

    else:

        print(
            "WRITER CODE ORIGIN UNRESOLVED"
        )

        print(
            "No direct Python market_history writer was identified."
        )

    # -------------------------------------------------------------------------
    # Safety confirmation
    # -------------------------------------------------------------------------

    section("SAFETY CONFIRMATION")

    print(
        "Database accessed           : NO"
    )

    print(
        "Database modified           : NO"
    )

    print(
        "INSERT executed             : NO"
    )

    print(
        "UPDATE executed             : NO"
    )

    print(
        "DELETE executed             : NO"
    )

    print(
        "ALTER executed              : NO"
    )

    print(
        "CREATE executed             : NO"
    )

    print(
        "Project modules executed    : NO"
    )

    print(
        "Source files modified       : NO"
    )

    print()
    print("=" * 100)
    print(
        f"{AUDIT_NAME} COMPLETE"
    )
    print("=" * 100)

    return 0


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    raise SystemExit(main())