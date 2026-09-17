import os
import json
import hashlib
import zipfile
import ast
from datetime import datetime, timezone


# ==================================================================================================
# ARUNDA TRADER
# HISTORICAL ELIGIBILITY RUNTIME EVIDENCE CHAIN FORENSIC v0.1
# ==================================================================================================

MODE = "READ-ONLY FORENSIC"

PROJECT_ROOT = r"C:\Users\ASUS\ArundaTrader"

PRODUCER = "ARUNDA_TRADER_LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_GATE_v0.1.py"
TARGET_REPORT = "LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_REPORT.json"
CONSUMER = "ARUNDA_TRADER_LIVE_TRADE_CANDIDATE_RANKING_MULTI_ASSET_GATE_v0.1.py"

OUTPUT_REPORT = os.path.join(
    PROJECT_ROOT,
    "HISTORICAL_ELIGIBILITY_RUNTIME_EVIDENCE_CHAIN_FORENSIC_REPORT.json"
)

BACKUP_DIR = os.path.join(PROJECT_ROOT, "_backups")

MAX_FILE_SIZE = 15 * 1024 * 1024

TEXT_EXTENSIONS = {
    ".py", ".txt", ".log", ".json", ".jsonl",
    ".md", ".csv", ".yaml", ".yml", ".ini",
    ".cfg", ".xml"
}

SKIP_DIRS = {
    "__pycache__",
    ".git",
    ".idea",
    ".vscode",
    "node_modules"
}

RUNTIME_TERMS = [
    "stdout",
    "stderr",
    "returncode",
    "runtime",
    "execution",
    "executed",
    "invocation",
    "invoke",
    "launch",
    "entrypoint",
    "working directory",
    "cwd",
    "output",
    "output_path",
    "report",
    "capture",
    "subprocess",
    "Popen",
    "run(",
    "check_output",
    "check_call",
    "communicate",
]

PRODUCER_TERMS = [
    PRODUCER,
    "LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_GATE_v0.1",
    "ELIGIBILITY_NO_TRADE",
    "SIGNAL_ELIGIBILITY",
]

REPORT_TERMS = [
    TARGET_REPORT,
    "LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_REPORT",
    "eligibility_report",
    "eligible_pool",
    "candidate_created",
    "eligibility_executed",
]

OUTPUT_PATH_TERMS = [
    "output_path",
    "report_path",
    "report_file",
    "output_file",
    "json_path",
    "artifact_path",
    "write",
    "dump",
    "json.dump",
    "open(",
]

INVOCATION_TERMS = [
    "subprocess",
    "Popen",
    "subprocess.run",
    "subprocess.Popen",
    "os.system",
    "entrypoint",
    "main(",
    "__main__",
]


# ==================================================================================================
# UTILITY
# ==================================================================================================

def utc_now():
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path):
    h = hashlib.sha256()

    try:
        with open(path, "rb") as f:
            while True:
                chunk = f.read(1024 * 1024)
                if not chunk:
                    break
                h.update(chunk)

        return h.hexdigest()

    except Exception:
        return None


def safe_read_text(path):
    try:
        if os.path.getsize(path) > MAX_FILE_SIZE:
            return None

        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    except Exception:
        return None


def normalize(text):
    return text.replace("\\", "/").lower()


def term_hits(text, terms):
    lower = text.lower()
    hits = []

    for term in terms:
        if term.lower() in lower:
            hits.append(term)

    return hits


def score_candidate(text):
    score = 0

    producer_hits = term_hits(text, PRODUCER_TERMS)
    report_hits = term_hits(text, REPORT_TERMS)
    runtime_hits = term_hits(text, RUNTIME_TERMS)
    output_hits = term_hits(text, OUTPUT_PATH_TERMS)
    invocation_hits = term_hits(text, INVOCATION_TERMS)

    score += len(producer_hits) * 12
    score += len(report_hits) * 10
    score += len(runtime_hits) * 4
    score += len(output_hits) * 5
    score += len(invocation_hits) * 5

    return {
        "score": score,
        "producer_hits": producer_hits,
        "report_hits": report_hits,
        "runtime_hits": runtime_hits,
        "output_path_hits": output_hits,
        "invocation_hits": invocation_hits,
    }


def extract_context(text, terms, radius=220, max_contexts=12):
    contexts = []
    lower = text.lower()

    for term in terms:
        search = term.lower()
        start = 0

        while len(contexts) < max_contexts:
            pos = lower.find(search, start)

            if pos == -1:
                break

            left = max(0, pos - radius)
            right = min(len(text), pos + len(term) + radius)

            snippet = text[left:right].replace("\x00", " ")

            contexts.append({
                "term": term,
                "snippet": snippet
            })

            start = pos + max(1, len(search))

    return contexts


def file_metadata(path):
    try:
        stat = os.stat(path)

        return {
            "path": path,
            "size": stat.st_size,
            "mtime_utc": datetime.fromtimestamp(
                stat.st_mtime,
                timezone.utc
            ).isoformat(),
        }

    except Exception:
        return {
            "path": path,
            "size": None,
            "mtime_utc": None,
        }


# ==================================================================================================
# STATIC AST FORENSIC
# ==================================================================================================

def ast_forensic(path):
    result = {
        "parse": False,
        "imports_producer": False,
        "subprocess_calls": [],
        "function_calls": [],
        "write_like_calls": [],
    }

    if not path.lower().endswith(".py"):
        return result

    text = safe_read_text(path)

    if text is None:
        return result

    try:
        tree = ast.parse(text, filename=path)
        result["parse"] = True

    except Exception:
        return result

    for node in ast.walk(tree):

        if isinstance(node, ast.Import):
            for alias in node.names:
                if PRODUCER.lower() in alias.name.lower():
                    result["imports_producer"] = True

        elif isinstance(node, ast.ImportFrom):
            if node.module and PRODUCER.lower() in node.module.lower():
                result["imports_producer"] = True

        elif isinstance(node, ast.Call):

            name = None

            if isinstance(node.func, ast.Name):
                name = node.func.id

            elif isinstance(node.func, ast.Attribute):
                name = node.func.attr

            if name:
                lname = name.lower()

                if lname in {
                    "run",
                    "popen",
                    "check_output",
                    "check_call",
                    "system",
                    "communicate"
                }:
                    result["subprocess_calls"].append(name)

                if lname in {
                    "dump",
                    "dumps",
                    "write",
                    "writelines"
                }:
                    result["write_like_calls"].append(name)

                result["function_calls"].append(name)

    return result


# ==================================================================================================
# FILESYSTEM INVENTORY
# ==================================================================================================

def inventory_files():
    files = []

    for root, dirs, filenames in os.walk(PROJECT_ROOT):

        dirs[:] = [
            d for d in dirs
            if d not in SKIP_DIRS
        ]

        for filename in filenames:
            path = os.path.join(root, filename)

            if os.path.abspath(path) == os.path.abspath(OUTPUT_REPORT):
                continue

            files.append(path)

    return files


# ==================================================================================================
# EXACT ARTIFACT SEARCH
# ==================================================================================================

def find_exact_artifacts(files):
    matches = []

    target_lower = TARGET_REPORT.lower()

    for path in files:
        if os.path.basename(path).lower() == target_lower:
            matches.append(file_metadata(path))

    return matches


# ==================================================================================================
# CONTENT PROVENANCE SEARCH
# ==================================================================================================

def content_search(files):
    candidates = []

    all_terms = (
        PRODUCER_TERMS
        + REPORT_TERMS
        + RUNTIME_TERMS
        + OUTPUT_PATH_TERMS
        + INVOCATION_TERMS
    )

    for path in files:

        ext = os.path.splitext(path)[1].lower()

        if ext not in TEXT_EXTENSIONS:
            continue

        text = safe_read_text(path)

        if text is None:
            continue

        hits = score_candidate(text)

        if hits["score"] <= 0:
            continue

        metadata = file_metadata(path)

        candidate = {
            **metadata,
            **hits,
            "sha256": sha256_file(path),
            "contexts": extract_context(
                text,
                all_terms,
                radius=180,
                max_contexts=15
            ),
        }

        if ext == ".py":
            candidate["ast"] = ast_forensic(path)

        candidates.append(candidate)

    candidates.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    return candidates


# ==================================================================================================
# RUNTIME EVIDENCE CHAIN
# ==================================================================================================

def runtime_chain_candidates(candidates):

    result = []

    for item in candidates:

        producer_ref = bool(item["producer_hits"])
        report_ref = bool(item["report_hits"])

        runtime_strength = (
            len(item["runtime_hits"])
            + len(item["output_path_hits"])
            + len(item["invocation_hits"])
        )

        if not (producer_ref or report_ref):
            continue

        result.append({
            "path": item["path"],
            "score": item["score"],
            "producer_reference": producer_ref,
            "report_reference": report_ref,
            "runtime_strength": runtime_strength,
            "runtime_terms": item["runtime_hits"],
            "output_path_terms": item["output_path_hits"],
            "invocation_terms": item["invocation_hits"],
            "contexts": item["contexts"],
        })

    result.sort(
        key=lambda x: (
            x["producer_reference"],
            x["report_reference"],
            x["score"],
            x["runtime_strength"]
        ),
        reverse=True
    )

    return result


# ==================================================================================================
# JSON EVIDENCE FORENSIC
# ==================================================================================================

def json_forensic(files):

    results = []

    for path in files:

        if not path.lower().endswith(".json"):
            continue

        text = safe_read_text(path)

        if text is None:
            continue

        try:
            data = json.loads(text)
        except Exception:
            continue

        flat_text = json.dumps(
            data,
            ensure_ascii=False
        )

        producer_ref = any(
            term.lower() in flat_text.lower()
            for term in PRODUCER_TERMS
        )

        report_ref = any(
            term.lower() in flat_text.lower()
            for term in REPORT_TERMS
        )

        runtime_ref = any(
            term.lower() in flat_text.lower()
            for term in RUNTIME_TERMS
        )

        if producer_ref or report_ref or runtime_ref:

            results.append({
                **file_metadata(path),
                "sha256": sha256_file(path),
                "valid_json": True,
                "producer_reference": producer_ref,
                "report_reference": report_ref,
                "runtime_reference": runtime_ref,
                "top_level_type": type(data).__name__,
                "top_level_keys": (
                    list(data.keys())
                    if isinstance(data, dict)
                    else []
                ),
            })

    return results


# ==================================================================================================
# ARCHIVE FORENSIC
# ==================================================================================================

def archive_forensic():

    archives = []

    if not os.path.isdir(BACKUP_DIR):
        return archives

    for root, _, files in os.walk(BACKUP_DIR):

        for filename in files:

            if not filename.lower().endswith(
                (".zip", ".7z", ".tar", ".gz")
            ):
                continue

            path = os.path.join(root, filename)

            record = {
                **file_metadata(path),
                "archive_type": os.path.splitext(path)[1].lower(),
                "target_member_found": False,
                "producer_member_found": False,
                "runtime_evidence_members": [],
                "members_inspected": 0,
            }

            if filename.lower().endswith(".zip"):

                try:
                    with zipfile.ZipFile(path, "r") as z:

                        members = z.namelist()

                        record["members_inspected"] = len(members)

                        for member in members:

                            member_lower = member.lower()

                            if member_lower.endswith(
                                TARGET_REPORT.lower()
                            ):
                                record["target_member_found"] = True

                            if PRODUCER.lower() in member_lower:
                                record["producer_member_found"] = True

                            runtime_score = 0

                            for term in (
                                RUNTIME_TERMS
                                + REPORT_TERMS
                                + PRODUCER_TERMS
                            ):
                                if term.lower() in member_lower:
                                    runtime_score += 1

                            if runtime_score > 0:

                                record[
                                    "runtime_evidence_members"
                                ].append({
                                    "member": member,
                                    "score": runtime_score,
                                })

                except Exception as exc:

                    record["error"] = str(exc)

            archives.append(record)

    return archives


# ==================================================================================================
# TIMELINE
# ==================================================================================================

def timeline_signals(candidates):

    timeline = []

    for item in candidates:

        mtime = item.get("mtime_utc")

        if not mtime:
            continue

        if not (
            item["producer_hits"]
            or item["report_hits"]
        ):
            continue

        timeline.append({
            "timestamp_utc": mtime,
            "path": item["path"],
            "score": item["score"],
            "producer_reference": bool(
                item["producer_hits"]
            ),
            "report_reference": bool(
                item["report_hits"]
            ),
        })

    timeline.sort(
        key=lambda x: x["timestamp_utc"],
        reverse=True
    )

    return timeline


# ==================================================================================================
# PROVENANCE DECISION
# ==================================================================================================

def determine_status(
    exact_artifacts,
    runtime_candidates,
    json_candidates,
    archives
):

    if exact_artifacts:
        return "EXACT_ARTIFACT_PRESENT"

    archive_exact = any(
        x.get("target_member_found")
        for x in archives
    )

    if archive_exact:
        return "EXACT_ARCHIVE_ARTIFACT_PRESENT"

    runtime_found = any(
        x["producer_reference"]
        and x["report_reference"]
        and x["runtime_strength"] > 0
        for x in runtime_candidates
    )

    json_runtime_found = any(
        x["producer_reference"]
        and x["report_reference"]
        and x["runtime_reference"]
        for x in json_candidates
    )

    if runtime_found or json_runtime_found:
        return (
            "RUNTIME_EVIDENCE_CHAIN_FOUND_ARTIFACT_UNRECOVERED"
        )

    return "RUNTIME_EVIDENCE_CHAIN_NOT_FOUND"


# ==================================================================================================
# MAIN
# ==================================================================================================

def main():

    started = utc_now()

    print("=" * 100)
    print("ARUNDA TRADER")
    print("HISTORICAL ELIGIBILITY RUNTIME EVIDENCE CHAIN FORENSIC v0.1")
    print("=" * 100)
    print(f"MODE                         : {MODE}")
    print(f"PROJECT ROOT                 : {PROJECT_ROOT}")
    print(f"TARGET REPORT                : {TARGET_REPORT}")
    print(f"PRODUCER                     : {PRODUCER}")
    print(f"CONSUMER                     : {CONSUMER}")
    print("=" * 100)

    # ----------------------------------------------------------------------------------------------
    # INVENTORY
    # ----------------------------------------------------------------------------------------------

    files = inventory_files()

    print("FILESYSTEM INVENTORY")
    print("=" * 100)
    print(f"Files discovered              : {len(files)}")

    # ----------------------------------------------------------------------------------------------
    # EXACT ARTIFACT
    # ----------------------------------------------------------------------------------------------

    exact_artifacts = find_exact_artifacts(files)

    print("=" * 100)
    print("EXACT ARTIFACT DISCOVERY")
    print("=" * 100)
    print(f"Exact target files found      : {len(exact_artifacts)}")

    for item in exact_artifacts:
        print(f"  - {item['path']}")

    # ----------------------------------------------------------------------------------------------
    # CONTENT SEARCH
    # ----------------------------------------------------------------------------------------------

    print("=" * 100)
    print("CONTENT PROVENANCE SEARCH")
    print("=" * 100)

    candidates = content_search(files)

    print(f"Content candidates             : {len(candidates)}")

    for i, item in enumerate(candidates[:30], 1):

        print(
            f"{i:3d} | score={item['score']:3d} | "
            f"{item['path']}"
        )

    # ----------------------------------------------------------------------------------------------
    # RUNTIME CHAIN
    # ----------------------------------------------------------------------------------------------

    runtime_candidates = runtime_chain_candidates(
        candidates
    )

    print("=" * 100)
    print("RUNTIME EVIDENCE CHAIN")
    print("=" * 100)

    print(
        f"Runtime evidence candidates   : "
        f"{len(runtime_candidates)}"
    )

    for i, item in enumerate(runtime_candidates[:30], 1):

        print(
            f"{i:3d} | score={item['score']:3d} | "
            f"runtime_strength={item['runtime_strength']:2d} | "
            f"{item['path']}"
        )

    # ----------------------------------------------------------------------------------------------
    # JSON FORENSIC
    # ----------------------------------------------------------------------------------------------

    json_candidates = json_forensic(files)

    print("=" * 100)
    print("JSON EVIDENCE FORENSIC")
    print("=" * 100)

    print(
        f"JSON evidence candidates      : "
        f"{len(json_candidates)}"
    )

    for i, item in enumerate(json_candidates, 1):

        print(
            f"{i:3d} | "
            f"producer={item['producer_reference']} | "
            f"report={item['report_reference']} | "
            f"runtime={item['runtime_reference']} | "
            f"{item['path']}"
        )

    # ----------------------------------------------------------------------------------------------
    # ARCHIVE FORENSIC
    # ----------------------------------------------------------------------------------------------

    archives = archive_forensic()

    print("=" * 100)
    print("ARCHIVE FORENSIC")
    print("=" * 100)

    print(
        f"Archives inspected             : "
        f"{len(archives)}"
    )

    for item in archives:

        print(
            f"  - {item['path']} | "
            f"target_member={item['target_member_found']} | "
            f"producer_member={item['producer_member_found']} | "
            f"runtime_members="
            f"{len(item['runtime_evidence_members'])}"
        )

    # ----------------------------------------------------------------------------------------------
    # TIMELINE
    # ----------------------------------------------------------------------------------------------

    timeline = timeline_signals(candidates)

    print("=" * 100)
    print("TIMELINE SIGNALS")
    print("=" * 100)

    print(
        f"Timeline candidates            : "
        f"{len(timeline)}"
    )

    for i, item in enumerate(timeline[:20], 1):

        print(
            f"{i:3d} | "
            f"{item['timestamp_utc']} | "
            f"{item['path']}"
        )

    # ----------------------------------------------------------------------------------------------
    # STATUS
    # ----------------------------------------------------------------------------------------------

    status = determine_status(
        exact_artifacts,
        runtime_candidates,
        json_candidates,
        archives
    )

    runtime_found = any(
        x["producer_reference"]
        and x["report_reference"]
        and x["runtime_strength"] > 0
        for x in runtime_candidates
    )

    archive_exact = any(
        x.get("target_member_found")
        for x in archives
    )

    # ----------------------------------------------------------------------------------------------
    # SAFETY INVARIANTS
    # ----------------------------------------------------------------------------------------------

    safety = {
        "producer_executed": False,
        "producer_imported": False,
        "eligibility_executed": False,
        "eligibility_rebuilt": False,
        "report_regenerated": False,
        "synthetic_artifact_created": False,
        "production_db_writes": "NONE",
        "production_source_modified": "NONE",
        "network_access": "NONE",
        "recovery_staging_performed": False,
    }

    # ----------------------------------------------------------------------------------------------
    # FINAL REPORT
    # ----------------------------------------------------------------------------------------------

    report = {
        "artifact": {
            "target_report": TARGET_REPORT,
            "producer": PRODUCER,
            "consumer": CONSUMER,
        },

        "forensic": {
            "version": "v0.1",
            "mode": MODE,
            "started_utc": started,
            "completed_utc": utc_now(),
            "project_root": PROJECT_ROOT,
        },

        "inventory": {
            "files_discovered": len(files),
        },

        "exact_artifact": {
            "found": bool(exact_artifacts),
            "matches": exact_artifacts,
        },

        "runtime_evidence_chain": {
            "found": runtime_found,
            "candidate_count": len(runtime_candidates),
            "candidates": runtime_candidates,
        },

        "json_evidence": {
            "candidate_count": len(json_candidates),
            "candidates": json_candidates,
        },

        "archive_forensic": {
            "archives_inspected": len(archives),
            "exact_archive_artifact_found": archive_exact,
            "archives": archives,
        },

        "historical_timeline": {
            "candidate_count": len(timeline),
            "signals": timeline,
        },

        "recovery_decision": {
            "status": status,
            "exact_artifact_recovered": bool(
                exact_artifacts
            ),
            "exact_archive_artifact_found": archive_exact,
            "runtime_evidence_chain_found": runtime_found,
            "artifact_content_recovered": False,
            "recovery_staging_performed": False,
        },

        "safety": safety,

        "final_verdict": {
            "historical_eligibility_runtime_evidence":
                status,

            "artifact_recovered":
                bool(exact_artifacts) or archive_exact,

            "runtime_evidence_found":
                runtime_found,

            "producer_executed":
                False,

            "producer_imported":
                False,

            "eligibility_executed":
                False,

            "eligibility_rebuilt":
                False,

            "report_regenerated":
                False,

            "synthetic_artifact":
                False,

            "production_db_writes":
                "NONE",

            "production_source_modification":
                "NONE",

            "network_access":
                "NONE",
        },

        "report_path": OUTPUT_REPORT,
    }

    # ----------------------------------------------------------------------------------------------
    # WRITE ONLY FORENSIC OUTPUT
    # ----------------------------------------------------------------------------------------------

    with open(
        OUTPUT_REPORT,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            report,
            f,
            ensure_ascii=False,
            indent=2
        )

    # ----------------------------------------------------------------------------------------------
    # CONSOLE VERDICT
    # ----------------------------------------------------------------------------------------------

    print("=" * 100)
    print("PROVENANCE DECISION")
    print("=" * 100)
    print(f"STATUS                       : {status}")
    print(
        f"EXACT ARTIFACT RECOVERED    : "
        f"{bool(exact_artifacts)}"
    )
    print(
        f"EXACT ARCHIVE ARTIFACT      : "
        f"{archive_exact}"
    )
    print(
        f"RUNTIME EVIDENCE CHAIN      : "
        f"{runtime_found}"
    )

    print("=" * 100)
    print("SAFETY")
    print("=" * 100)
    print("Producer executed            : NO")
    print("Producer imported            : NO")
    print("Eligibility executed         : NO")
    print("Eligibility rebuilt          : NO")
    print("Report regenerated           : NO")
    print("Synthetic artifact           : NO")
    print("Production DB writes         : NONE")
    print("Production source modified   : NONE")
    print("Network access               : NONE")
    print("Recovery staging             : NONE")

    print("=" * 100)
    print("FINAL VERDICT")
    print("=" * 100)
    print(
        f"HISTORICAL ELIGIBILITY RUNTIME EVIDENCE : "
        f"{status}"
    )
    print(
        f"FORENSIC REPORT              : "
        f"{OUTPUT_REPORT}"
    )
    print("=" * 100)


if __name__ == "__main__":
    main()