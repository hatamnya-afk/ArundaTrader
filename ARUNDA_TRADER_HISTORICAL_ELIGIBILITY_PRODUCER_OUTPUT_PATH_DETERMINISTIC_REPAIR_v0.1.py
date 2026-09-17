import ast
import json
import os
from pathlib import Path
from datetime import datetime, timezone


PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

PRODUCER = (
    PROJECT_ROOT
    / "ARUNDA_TRADER_LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_GATE_v0.1.py"
)

TARGET_NAME = "LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_REPORT.json"

FORENSIC_REPORT_NAME = (
    "HISTORICAL_ELIGIBILITY_PRODUCER_OUTPUT_PATH_DETERMINISTIC_REPAIR_REPORT.json"
)

FORENSIC_REPORT_PATH = PROJECT_ROOT / FORENSIC_REPORT_NAME


class DeterministicOutputPathRepair:
    def __init__(self):
        self.source = None
        self.tree = None

        self.target_assignments = []
        self.writer_calls = []
        self.path_operations = []

        self.report_path_assignments = []
        self.main_functions = []

        self.syntax_valid = False
        self.producer_exists = False

    def utc_now(self):
        return datetime.now(timezone.utc).isoformat()

    def load_source(self):
        self.producer_exists = PRODUCER.exists()

        if not self.producer_exists:
            return False

        self.source = PRODUCER.read_text(
            encoding="utf-8",
            errors="replace",
        )

        try:
            self.tree = ast.parse(
                self.source,
                filename=str(PRODUCER),
            )
            self.syntax_valid = True
            return True

        except SyntaxError:
            self.syntax_valid = False
            return False

    def get_call_name(self, node):
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

    def get_string(self, node):
        if isinstance(node, ast.Constant):
            if isinstance(node.value, str):
                return node.value

        return None

    def scan_target_assignment(self):
        for node in ast.walk(self.tree):

            if not isinstance(node, ast.Assign):
                continue

            value = self.get_string(node.value)

            if value != TARGET_NAME:
                continue

            for target in node.targets:

                if isinstance(target, ast.Name):

                    self.target_assignments.append(
                        {
                            "line": node.lineno,
                            "variable": target.id,
                            "value": value,
                        }
                    )

    def scan_report_path(self):
        for node in ast.walk(self.tree):

            if not isinstance(node, ast.Assign):
                continue

            for target in node.targets:

                if not isinstance(target, ast.Name):
                    continue

                if target.id != "report_path":
                    continue

                self.report_path_assignments.append(
                    {
                        "line": node.lineno,
                        "source": ast.unparse(node.value),
                    }
                )

    def scan_writers(self):
        for node in ast.walk(self.tree):

            if not isinstance(node, ast.Call):
                continue

            name = self.get_call_name(node.func)

            if name == "open":

                args = []

                for arg in node.args:
                    args.append(ast.unparse(arg))

                self.writer_calls.append(
                    {
                        "line": node.lineno,
                        "type": "open",
                        "arguments": args,
                    }
                )

            elif name == "json.dump":

                args = []

                for arg in node.args:
                    args.append(ast.unparse(arg))

                self.writer_calls.append(
                    {
                        "line": node.lineno,
                        "type": "json.dump",
                        "arguments": args,
                    }
                )

    def scan_path_operations(self):
        path_names = {
            "Path",
            "resolve",
            "absolute",
            "joinpath",
            "mkdir",
        }

        for node in ast.walk(self.tree):

            if not isinstance(node, ast.Call):
                continue

            name = self.get_call_name(node.func)

            if name in path_names:

                self.path_operations.append(
                    {
                        "line": node.lineno,
                        "call": name,
                        "expression": ast.unparse(node),
                    }
                )

    def scan_main(self):
        for node in ast.walk(self.tree):

            if not isinstance(node, ast.FunctionDef):
                continue

            if node.name != "main":
                continue

            self.main_functions.append(
                {
                    "line": node.lineno,
                    "end_line": getattr(
                        node,
                        "end_lineno",
                        node.lineno,
                    ),
                }
            )

    def determine_current_path(self):
        if not self.report_path_assignments:
            return {
                "found": False,
                "deterministic": False,
                "reason": "report_path assignment not found",
            }

        expressions = [
            item["source"]
            for item in self.report_path_assignments
        ]

        deterministic = any(
            TARGET_NAME in expression
            for expression in expressions
        )

        return {
            "found": True,
            "deterministic": deterministic,
            "assignments": self.report_path_assignments,
        }

    def build_repair_contract(self):
        current = self.determine_current_path()

        canonical_expression = (
            "PROJECT_ROOT / "
            '"LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_REPORT.json"'
        )

        repair_required = not current["deterministic"]

        return {
            "repair_required": repair_required,
            "canonical_target_name": TARGET_NAME,
            "canonical_expression": canonical_expression,
            "repair_type": (
                "DETERMINISTIC_ABSOLUTE_PROJECT_ROOT_PATH"
                if repair_required
                else "NO_REPAIR_REQUIRED"
            ),
            "constraints": [
                "READ_ONLY_ANALYSIS",
                "DO_NOT_EXECUTE_PRODUCER",
                "DO_NOT_IMPORT_PRODUCER",
                "DO_NOT_WRITE_PRODUCTION_DB",
                "DO_NOT_REGENERATE_TARGET_REPORT",
                "DO_NOT_CREATE_SYNTHETIC_TARGET_ARTIFACT",
                "DO_NOT_MODIFY_PRODUCTION_SOURCE",
            ],
        }

    def build_patch(self):
        contract = self.build_repair_contract()

        if not contract["repair_required"]:
            return {
                "patch_required": False,
                "patch": None,
            }

        patch = (
            'PROJECT_ROOT = Path(r"C:\\Users\\ASUS\\ArundaTrader")\n'
            '\n'
            'report_path = PROJECT_ROOT / '
            '"LIVE_SIGNAL_ELIGIBILITY_NO_TRADE_REPORT.json"\n'
        )

        return {
            "patch_required": True,
            "patch": patch,
        }

    def build_report(self):
        current = self.determine_current_path()
        contract = self.build_repair_contract()
        patch = self.build_patch()

        status = (
            "DETERMINISTIC_OUTPUT_PATH_REPAIR_REQUIRED"
            if contract["repair_required"]
            else "DETERMINISTIC_OUTPUT_PATH_ALREADY_VALID"
        )

        return {
            "artifact": {
                "name": (
                    "ARUNDA TRADER HISTORICAL ELIGIBILITY "
                    "PRODUCER OUTPUT PATH DETERMINISTIC REPAIR v0.1"
                ),
                "mode": "READ-ONLY REPAIR SPECIFICATION",
                "timestamp_utc": self.utc_now(),
            },
            "project": {
                "root": str(PROJECT_ROOT),
                "producer": str(PRODUCER),
                "target": TARGET_NAME,
            },
            "producer": {
                "exists": self.producer_exists,
                "syntax_valid": self.syntax_valid,
            },
            "current_path_analysis": current,
            "target_assignments": self.target_assignments,
            "writer_calls": self.writer_calls,
            "path_operations": self.path_operations,
            "main_functions": self.main_functions,
            "repair_contract": contract,
            "patch": patch,
            "decision": {
                "status": status,
                "repair_required": contract["repair_required"],
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
                "repair_applied": False,
            },
            "final_verdict": {
                "historical_eligibility_output_path": status,
                "report": str(FORENSIC_REPORT_PATH),
            },
        }

    def write_report(self, report):
        with open(
            FORENSIC_REPORT_PATH,
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
        current = report["current_path_analysis"]
        contract = report["repair_contract"]
        patch = report["patch"]

        print("=" * 100)
        print("ARUNDA TRADER")
        print(
            "HISTORICAL ELIGIBILITY PRODUCER "
            "OUTPUT PATH DETERMINISTIC REPAIR v0.1"
        )
        print("=" * 100)

        print("MODE                         : READ-ONLY REPAIR SPECIFICATION")
        print(f"PROJECT ROOT                 : {PROJECT_ROOT}")
        print(f"PRODUCER                     : {PRODUCER.name}")
        print(f"TARGET REPORT                : {TARGET_NAME}")

        print("=" * 100)
        print("PRODUCER")
        print("=" * 100)

        print(
            f"Producer exists               : "
            f"{report['producer']['exists']}"
        )

        print(
            f"Producer syntax valid         : "
            f"{report['producer']['syntax_valid']}"
        )

        print("=" * 100)
        print("CURRENT OUTPUT PATH")
        print("=" * 100)

        print(
            f"report_path found             : "
            f"{current['found']}"
        )

        print(
            f"Deterministic                : "
            f"{current['deterministic']}"
        )

        for item in current.get("assignments", []):
            print(
                f"  line={item['line']} | "
                f"report_path = {item['source']}"
            )

        print("=" * 100)
        print("REPAIR CONTRACT")
        print("=" * 100)

        print(
            f"Repair required               : "
            f"{contract['repair_required']}"
        )

        print(
            f"Repair type                   : "
            f"{contract['repair_type']}"
        )

        print(
            f"Canonical target              : "
            f"{contract['canonical_target_name']}"
        )

        print(
            f"Canonical expression          : "
            f"{contract['canonical_expression']}"
        )

        print("=" * 100)
        print("PROPOSED PATCH")
        print("=" * 100)

        if patch["patch_required"]:
            print(patch["patch"])
        else:
            print("NO PATCH REQUIRED")

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
        print("Repair applied               : NO")

        print("=" * 100)
        print("FINAL VERDICT")
        print("=" * 100)

        print(
            "HISTORICAL ELIGIBILITY OUTPUT PATH : "
            f"{report['decision']['status']}"
        )

        print(
            f"FORENSIC REPORT              : "
            f"{FORENSIC_REPORT_PATH}"
        )

        print("=" * 100)

    def run(self):
        if not self.load_source():
            print(
                "ERROR: Producer source could not be loaded."
            )
            return

        self.scan_target_assignment()
        self.scan_report_path()
        self.scan_writers()
        self.scan_path_operations()
        self.scan_main()

        report = self.build_report()

        self.write_report(report)
        self.print_report(report)


if __name__ == "__main__":
    forensic = DeterministicOutputPathRepair()
    forensic.run()