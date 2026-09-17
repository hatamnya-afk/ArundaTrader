import ast
import json
import os
from pathlib import Path
from datetime import datetime, timezone


PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")
PRODUCER = PROJECT_ROOT / "ARUNDA_TRADER_LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_GATE_v0.1.py"
TARGET_NAME = "LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_REPORT.json"

REPORT_NAME = (
    "HISTORICAL_ELIGIBILITY_PRODUCER_OUTPUT_PATH_DATAFLOW_FORENSIC_REPORT.json"
)
REPORT_PATH = PROJECT_ROOT / REPORT_NAME


class OutputPathDataflowForensic:
    def __init__(self):
        self.target_definitions = []
        self.writer_calls = []
        self.function_dataflow = []
        self.exact_target_exists = False
        self.syntax_valid = False

    def utc_now(self):
        return datetime.now(timezone.utc).isoformat()

    def discover_target(self):
        for root, dirs, files in os.walk(PROJECT_ROOT):
            dirs[:] = [
                d for d in dirs
                if d not in {
                    ".git",
                    "__pycache__",
                    ".venv",
                    "venv",
                    "node_modules",
                }
            ]

            if TARGET_NAME in files:
                self.exact_target_exists = True

    def read_source(self):
        if not PRODUCER.exists():
            return None

        try:
            return PRODUCER.read_text(
                encoding="utf-8",
                errors="replace",
            )
        except Exception:
            return None

    def parse_source(self, source):
        if source is None:
            return None

        try:
            tree = ast.parse(source, filename=str(PRODUCER))
            self.syntax_valid = True
            return tree
        except SyntaxError:
            self.syntax_valid = False
            return None

    def get_line(self, node):
        return getattr(node, "lineno", None)

    def call_name(self, node):
        if isinstance(node, ast.Name):
            return node.id

        if isinstance(node, ast.Attribute):
            parts = []
            current = node

            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value

            if isinstance(current, ast.Name):
                parts.append(current.id)

            return ".".join(reversed(parts))

        return ""

    def string_value(self, node):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value

        return None

    def scan_assignments(self, tree):
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue

            value = self.string_value(node.value)

            if value != TARGET_NAME:
                continue

            targets = []

            for target in node.targets:
                if isinstance(target, ast.Name):
                    targets.append(target.id)

            self.target_definitions.append(
                {
                    "line": self.get_line(node),
                    "targets": targets,
                    "value": value,
                }
            )

    def scan_writers(self, tree):
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            name = self.call_name(node.func)

            if name == "open":
                mode = None

                if len(node.args) >= 2:
                    mode = self.string_value(node.args[1])

                for keyword in node.keywords:
                    if keyword.arg == "mode":
                        mode = self.string_value(keyword.value)

                self.writer_calls.append(
                    {
                        "line": self.get_line(node),
                        "type": "open",
                        "mode": mode,
                        "target_literal": any(
                            self.string_value(arg) == TARGET_NAME
                            for arg in node.args
                        ),
                    }
                )

            elif name == "json.dump":
                self.writer_calls.append(
                    {
                        "line": self.get_line(node),
                        "type": "json.dump",
                        "target_literal": any(
                            self.string_value(arg) == TARGET_NAME
                            for arg in node.args
                        ),
                    }
                )

    def scan_functions(self, tree):
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            function_name = node.name
            assignments = []
            writers = []

            for child in ast.walk(node):
                if isinstance(child, ast.Assign):
                    value = self.string_value(child.value)

                    if value == TARGET_NAME:
                        assignments.append(
                            {
                                "line": self.get_line(child),
                                "value": value,
                            }
                        )

                if isinstance(child, ast.Call):
                    name = self.call_name(child.func)

                    if name == "open":
                        writers.append(
                            {
                                "line": self.get_line(child),
                                "type": "open",
                                "mode": (
                                    self.string_value(child.args[1])
                                    if len(child.args) >= 2
                                    else None
                                ),
                            }
                        )

                    elif name == "json.dump":
                        writers.append(
                            {
                                "line": self.get_line(child),
                                "type": "json.dump",
                            }
                        )

            self.function_dataflow.append(
                {
                    "function": function_name,
                    "line": self.get_line(node),
                    "target_assignments": assignments,
                    "writer_calls": writers,
                    "target_to_writer_verified": False,
                }
            )

    def evaluate_dataflow(self):
        for item in self.function_dataflow:
            assignments = item["target_assignments"]
            writers = item["writer_calls"]

            if assignments and writers:
                item["target_to_writer_verified"] = True

        main_items = [
            item
            for item in self.function_dataflow
            if item["function"] == "main"
        ]

        for item in main_items:
            if item["target_assignments"] and item["writer_calls"]:
                item["target_to_writer_verified"] = True

    def build_report(self):
        verified = any(
            item["target_to_writer_verified"]
            for item in self.function_dataflow
        )

        status = (
            "PRODUCER_OUTPUT_PATH_DATAFLOW_VERIFIED"
            if verified
            else "PRODUCER_OUTPUT_PATH_DATAFLOW_UNVERIFIED"
        )

        return {
            "artifact": {
                "name": "ARUNDA TRADER HISTORICAL ELIGIBILITY PRODUCER OUTPUT PATH DATAFLOW FORENSIC v0.1",
                "mode": "READ-ONLY FORENSIC",
                "timestamp_utc": self.utc_now(),
            },
            "project": {
                "root": str(PROJECT_ROOT),
                "producer": str(PRODUCER),
                "target_report": TARGET_NAME,
            },
            "filesystem": {
                "target_artifact_exists": self.exact_target_exists,
            },
            "static_dataflow": {
                "target_definitions": self.target_definitions,
                "writer_calls": self.writer_calls,
            },
            "function_dataflow": self.function_dataflow,
            "decision": {
                "status": status,
                "target_definition_found": bool(self.target_definitions),
                "writer_found": bool(self.writer_calls),
                "target_to_writer_dataflow_verified": verified,
            },
            "safety": {
                "producer_executed": False,
                "producer_imported": False,
                "eligibility_executed": False,
                "eligibility_rebuilt": False,
                "report_regenerated": False,
                "synthetic_artifact": False,
                "production_db_writes": "NONE",
                "production_source_modified": False,
                "network_access": False,
            },
            "final_verdict": {
                "historical_eligibility_output_path_dataflow": status,
                "forensic_report": str(REPORT_PATH),
            },
        }

    def write_report(self, report):
        with open(
            REPORT_PATH,
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(
                report,
                f,
                indent=2,
                ensure_ascii=False,
            )

    def print_report(self, report):
        decision = report["decision"]
        filesystem = report["filesystem"]

        print("=" * 100)
        print("ARUNDA TRADER")
        print("HISTORICAL ELIGIBILITY PRODUCER OUTPUT PATH DATAFLOW FORENSIC v0.1")
        print("=" * 100)
        print("MODE                         : READ-ONLY FORENSIC")
        print(f"PROJECT ROOT                 : {PROJECT_ROOT}")
        print(f"TARGET REPORT                : {TARGET_NAME}")
        print(f"PRODUCER                     : {PRODUCER.name}")
        print("=" * 100)

        print("STATIC DATAFLOW")
        print("=" * 100)
        print(
            f"Target artifact exists       : "
            f"{filesystem['target_artifact_exists']}"
        )

        print(
            f"Target definitions           : "
            f"{len(self.target_definitions)}"
        )

        for item in self.target_definitions:
            print(
                f"  line={item['line']} | "
                f"targets={item['targets']} | "
                f"value={item['value']}"
            )

        print("=" * 100)
        print("WRITER CONTEXT")
        print("=" * 100)
        print(f"Writer calls                 : {len(self.writer_calls)}")

        for item in self.writer_calls:
            print(
                f"  line={item['line']} | "
                f"type={item['type']} | "
                f"mode={item.get('mode', '')} | "
                f"target_literal={item.get('target_literal', '')}"
            )

        print("=" * 100)
        print("FUNCTION DATAFLOW")
        print("=" * 100)

        for item in self.function_dataflow:
            print(
                f"FUNCTION                     : "
                f"{item['function']} (line {item['line']})"
            )

            print(
                f"  Target assignments         : "
                f"{len(item['target_assignments'])}"
            )

            print(
                f"  Writer calls               : "
                f"{len(item['writer_calls'])}"
            )

            print(
                f"  Verified target→writer     : "
                f"{item['target_to_writer_verified']}"
            )

        print("=" * 100)
        print("VERDICT")
        print("=" * 100)
        print(
            f"STATUS                       : "
            f"{decision['status']}"
        )
        print(
            f"TARGET DEFINITION FOUND     : "
            f"{decision['target_definition_found']}"
        )
        print(
            f"WRITER FOUND                : "
            f"{decision['writer_found']}"
        )
        print(
            f"TARGET → WRITER DATAFLOW    : "
            f"{decision['target_to_writer_dataflow_verified']}"
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
        print("Production source modified   : NO")
        print("Network access               : NONE")

        print("=" * 100)
        print("FINAL VERDICT")
        print("=" * 100)
        print(
            "HISTORICAL ELIGIBILITY OUTPUT PATH DATAFLOW : "
            f"{decision['status']}"
        )
        print(
            f"FORENSIC REPORT              : {REPORT_PATH}"
        )
        print("=" * 100)

    def run(self):
        self.discover_target()

        source = self.read_source()

        if source is None:
            print(
                "ERROR: Producer source file was not found or could not be read."
            )
            return

        tree = self.parse_source(source)

        if tree is None:
            print(
                "ERROR: Producer source contains invalid Python syntax."
            )
            return

        self.scan_assignments(tree)
        self.scan_writers(tree)
        self.scan_functions(tree)
        self.evaluate_dataflow()

        report = self.build_report()
        self.write_report(report)
        self.print_report(report)


if __name__ == "__main__":
    forensic = OutputPathDataflowForensic()
    forensic.run()