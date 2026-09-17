from pathlib import Path
import ast
import re

BASE_DIR = Path(__file__).resolve().parent
ENGINE_PATH = BASE_DIR / "market_data_engine.py"

TARGET = "rsi14"

print("=" * 100)
print("ARUNDA RSI14 STORAGE ASSIGNMENT FORENSIC AUDIT v0.1")
print("=" * 100)
print("MODE                  : READ ONLY")
print("DATABASE WRITE        : NONE")
print("FORMULA WRITE        : NONE")
print("PRODUCTION RECALCULATION : NONE")
print("PURPOSE               : RESOLVE RSI14 RETURN → STORAGE ASSIGNMENT")
print("=" * 100)

if not ENGINE_PATH.exists():
    print("ENGINE FOUND          : False")
    print("STATUS                : BLOCKED")
    print("REASON                : market_data_engine.py NOT FOUND")
    raise SystemExit(1)

source = ENGINE_PATH.read_text(encoding="utf-8")
lines = source.splitlines()

print("ENGINE PATH            :", ENGINE_PATH)
print("ENGINE FOUND           : True")
print("SOURCE SIZE            :", len(source), "characters")
print("SOURCE LINES           :", len(lines))

try:
    tree = ast.parse(source)
    print("AST STATUS             : SUCCESS")
except SyntaxError as exc:
    print("AST STATUS             : FAILED")
    print("SYNTAX ERROR           :", exc)
    raise SystemExit(1)


def line_text(line_no):
    if 1 <= line_no <= len(lines):
        return lines[line_no - 1].strip()
    return ""


def get_call_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


print()
print("=" * 100)
print("RSI14 TARGET FIELD SEARCH")
print("=" * 100)

target_hits = []

for node in ast.walk(tree):
    if isinstance(node, ast.Name) and node.id == TARGET:
        target_hits.append(
            (
                getattr(node, "lineno", 0),
                "NAME",
                line_text(getattr(node, "lineno", 0)),
            )
        )

    elif isinstance(node, ast.Constant) and node.value == TARGET:
        target_hits.append(
            (
                getattr(node, "lineno", 0),
                "STRING",
                line_text(getattr(node, "lineno", 0)),
            )
        )

for line_no, kind, text in sorted(target_hits):
    print(f"[{kind:<6}] LINE {line_no:<5} : {text}")

print()
print("TARGET REFERENCES        :", len(target_hits))


print()
print("=" * 100)
print("DIRECT RSI14 ASSIGNMENT ANALYSIS")
print("=" * 100)

direct_assignments = []
producer_assignments = []

for node in ast.walk(tree):

    if isinstance(node, ast.Assign):
        value = node.value

        if isinstance(value, ast.Call):
            call_name = get_call_name(value.func)

            if call_name == "rsi":
                for target_node in node.targets:
                    if isinstance(target_node, ast.Name):
                        if target_node.id.lower() == "rsi14":
                            direct_assignments.append(
                                (
                                    node.lineno,
                                    target_node.id,
                                    line_text(node.lineno),
                                )
                            )

                        else:
                            producer_assignments.append(
                                (
                                    node.lineno,
                                    target_node.id,
                                    line_text(node.lineno),
                                )
                            )

    elif isinstance(node, ast.AnnAssign):
        value = node.value

        if isinstance(value, ast.Call):
            call_name = get_call_name(value.func)

            if call_name == "rsi":
                if isinstance(node.target, ast.Name):
                    producer_assignments.append(
                        (
                            node.lineno,
                            node.target.id,
                            line_text(node.lineno),
                        )
                    )


if direct_assignments:
    print("DIRECT RSI14 ASSIGNMENTS FOUND")
    for line_no, name, text in direct_assignments:
        print(f"  [FOUND] LINE {line_no} : {text}")
else:
    print("DIRECT RSI14 ASSIGNMENTS FOUND : NONE")


print()
print("=" * 100)
print("RSI PRODUCER → VARIABLE CHAIN")
print("=" * 100)

rsi_producer_variables = []

for line_no, name, text in producer_assignments:
    rsi_producer_variables.append(name)
    print(f"  [FOUND] LINE {line_no} : {name} = rsi(...)")

if not rsi_producer_variables:
    print("  [NONE] No variable assignment from rsi() identified")


print()
print("=" * 100)
print("RSI VARIABLE → TARGET FIELD SEARCH")
print("=" * 100)

variable_to_target = []

for variable in rsi_producer_variables:

    for node in ast.walk(tree):

        if isinstance(node, ast.Assign):

            value = node.value

            if isinstance(value, ast.Name) and value.id == variable:

                for target_node in node.targets:

                    if isinstance(target_node, ast.Subscript):
                        target_text = ast.unparse(target_node)

                        if "rsi14" in target_text.lower():
                            variable_to_target.append(
                                (
                                    node.lineno,
                                    variable,
                                    target_text,
                                    line_text(node.lineno),
                                )
                            )

                    elif isinstance(target_node, ast.Name):

                        target_name = target_node.id

                        if target_name.lower() == "analysis":

                            variable_to_target.append(
                                (
                                    node.lineno,
                                    variable,
                                    target_name,
                                    line_text(node.lineno),
                                )
                            )

        elif isinstance(node, ast.AnnAssign):

            value = node.value

            if isinstance(value, ast.Name) and value.id == variable:

                target_node = node.target

                if isinstance(target_node, ast.Subscript):

                    target_text = ast.unparse(target_node)

                    if "rsi14" in target_text.lower():
                        variable_to_target.append(
                            (
                                node.lineno,
                                variable,
                                target_text,
                                line_text(node.lineno),
                            )
                        )


if variable_to_target:
    for line_no, variable, target, text in variable_to_target:
        print(
            f"  [FOUND] LINE {line_no} : "
            f"{variable} → {target}"
        )
        print(f"           SOURCE : {text}")
else:
    print("  [NONE] Producer variable → rsi14 target assignment not directly resolved")


print()
print("=" * 100)
print("DICTIONARY / ANALYSIS OBJECT ASSIGNMENT SEARCH")
print("=" * 100)

dictionary_assignments = []

for node in ast.walk(tree):

    if isinstance(node, ast.Dict):

        for key, value in zip(node.keys, node.values):

            if (
                isinstance(key, ast.Constant)
                and key.value == TARGET
            ):

                dictionary_assignments.append(
                    (
                        node.lineno,
                        line_text(node.lineno),
                        ast.unparse(value)
                        if value is not None
                        else "None",
                    )
                )

if dictionary_assignments:

    for line_no, text, value in dictionary_assignments:
        print(f"  [FOUND] LINE {line_no}")
        print(f"           SOURCE : {text}")
        print(f"           VALUE  : {value}")
else:
    print("  [NONE] Dictionary assignment containing rsi14 not found")


print()
print("=" * 100)
print("TEXTUAL RSI14 STORAGE REFERENCES")
print("=" * 100)

storage_patterns = [
    r'["\']rsi14["\']\s*:',
    r'["\']rsi14["\']\s*\]',
    r'\[\s*["\']rsi14["\']\s*\]',
]

storage_hits = []

for idx, text in enumerate(lines, start=1):

    for pattern in storage_patterns:

        if re.search(pattern, text, re.IGNORECASE):
            storage_hits.append((idx, text.strip()))
            break

if storage_hits:
    for line_no, text in storage_hits:
        print(f"  [FOUND] LINE {line_no:<5} : {text}")
else:
    print("  [NONE] RSI14 storage references not found")


print()
print("=" * 100)
print("FINAL RSI14 STORAGE ASSIGNMENT VERDICT")
print("=" * 100)

if direct_assignments:
    print("TARGET FIELD STATUS       : RESOLVED")
    print("STORAGE ASSIGNMENT STATUS : DIRECT_RSI14_ASSIGNMENT_FOUND")
    print("CAUSE STATUS              : STORAGE_CHAIN_RESOLVED")

elif variable_to_target:
    print("TARGET FIELD STATUS       : RESOLVED")
    print("STORAGE ASSIGNMENT STATUS : PRODUCER_VARIABLE_TO_TARGET_FOUND")
    print("CAUSE STATUS              : STORAGE_CHAIN_RESOLVED")

elif dictionary_assignments:
    print("TARGET FIELD STATUS       : RESOLVED")
    print("STORAGE ASSIGNMENT STATUS : DICTIONARY_TARGET_FOUND")
    print("CAUSE STATUS              : STORAGE_CHAIN_RESOLVED")

elif storage_hits:
    print("TARGET FIELD STATUS       : TEXTUAL_EVIDENCE_ONLY")
    print("STORAGE ASSIGNMENT STATUS : NOT_PROVEN")
    print("CAUSE STATUS              : CAUSE_NOT_PROVEN")

else:
    print("TARGET FIELD STATUS       : UNRESOLVED")
    print("STORAGE ASSIGNMENT STATUS : NOT_FOUND")
    print("CAUSE STATUS              : CAUSE_NOT_PROVEN")


print()
print("=" * 100)
print("FORENSIC RULE")
print("=" * 100)
print("Source pattern presence alone does NOT prove runtime storage.")
print("A valid chain requires:")
print("TARGET FIELD → PRODUCER → RSI CALL → RETURN → STORAGE ASSIGNMENT")

print()
print("DATABASE WRITE OPERATIONS : NONE")
print("ENGINE MODIFICATIONS      : NONE")
print("FORMULA WRITE             : NONE")
print("PRODUCTION RECALCULATION  : NONE")
print("AUDIT COMPLETE")