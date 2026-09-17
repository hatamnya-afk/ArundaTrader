import ast
from pathlib import Path

PROJECT = Path(r"C:\Users\ASUS\ArundaTrader")
TARGET = "upgrade_db.py"

EXCLUDED = {
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "env",
}

def syntax_ok(path):
    try:
        ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        return True
    except Exception:
        return False

def name_of(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = name_of(node.value)
        if parent:
            return parent + "." + node.attr
        return node.attr
    return ""

def main():
    target = PROJECT / TARGET

    print("=" * 90)
    print("ARUNDA PROJECT UPGRADE DB REAL CALLCHAIN FORENSIC v0.1")
    print("=" * 90)
    print("MODE              : READ ONLY")
    print("DATABASE          : NOT USED")
    print("NETWORK           : NOT USED")
    print("EXECUTION         : STATIC ANALYSIS ONLY")
    print("PRODUCTION RUN    : NOT PERFORMED")
    print("FILE MODIFICATION : NOT PERFORMED")
    print("-" * 90)

    if not target.exists():
        print("TARGET            : NOT FOUND")
        return

    print("TARGET            : upgrade_db.py")
    print("TARGET EXISTS     : True")
    print("TARGET SYNTAX     : " + str(syntax_ok(target)))

    real = []
    text = []

    for path in PROJECT.rglob("*.py"):
        if not path.is_file():
            continue

        try:
            rel = path.relative_to(PROJECT)
        except Exception:
            continue

        if any(part in EXCLUDED for part in rel.parts):
            continue

        if path.name == TARGET:
            continue

        try:
            source = path.read_text(
                encoding="utf-8",
                errors="replace"
            )
        except Exception:
            continue

        lower = source.lower()

        if "upgrade_db.py" in lower or "upgrade_db" in lower:
            lines = source.splitlines()

            for number, line in enumerate(lines, 1):
                if "upgrade_db.py" in line.lower():
                    text.append(
                        (str(rel), number, line.strip())
                    )

            if not syntax_ok(path):
                continue

            try:
                tree = ast.parse(source)
            except Exception:
                continue

            for node in ast.walk(tree):

                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if (
                            alias.name == "upgrade_db"
                            or alias.name.endswith(".upgrade_db")
                        ):
                            real.append(
                                (
                                    str(rel),
                                    node.lineno,
                                    "IMPORT",
                                    alias.name
                                )
                            )

                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""

                    if (
                        module == "upgrade_db"
                        or module.endswith(".upgrade_db")
                    ):
                        real.append(
                            (
                                str(rel),
                                node.lineno,
                                "IMPORT_FROM",
                                module
                            )
                        )

                elif isinstance(node, ast.Call):
                    function = name_of(node.func)

                    if function in {
                        "subprocess.run",
                        "subprocess.Popen",
                        "subprocess.call",
                        "subprocess.check_call",
                        "subprocess.check_output",
                        "os.system",
                        "runpy.run_module",
                        "runpy.run_path",
                    }:
                        segment = ast.get_source_segment(
                            source,
                            node
                        ) or ""

                        if "upgrade_db" in segment.lower():
                            real.append(
                                (
                                    str(rel),
                                    node.lineno,
                                    "PROCESS_CALL",
                                    function
                                )
                            )

    print()
    print("=" * 90)
    print("REAL CALLCHAIN REFERENCES")
    print("=" * 90)

    if not real:
        print("NONE")

    for item in real:
        print(
            "FILE   : " + item[0]
        )
        print(
            "LINE   : " + str(item[1])
        )
        print(
            "TYPE   : " + item[2]
        )
        print(
            "SOURCE : " + item[3]
        )
        print("-" * 90)

    print()
    print("=" * 90)
    print("TEXT REFERENCES")
    print("=" * 90)

    if not text:
        print("NONE")

    for item in text:
        print(
            "FILE   : " + item[0]
        )
        print(
            "LINE   : " + str(item[1])
        )
        print(
            "SOURCE : " + item[2]
        )
        print("-" * 90)

    print()
    print("=" * 90)
    print("FORENSIC VERDICT")
    print("=" * 90)

    if real:
        print("REAL CALLCHAIN : FOUND")
        print("STATUS         : REAL_CALLCHAIN_REFERENCE_FOUND")
    else:
        print("REAL CALLCHAIN : NOT FOUND")
        print("STATUS         : NO_REAL_UPGRADE_DB_CALLCHAIN")

    print()
    print("IMPORTANT:")
    print("upgrade_db.py was NOT executed.")
    print("arunda.db was NOT opened.")
    print("No SQL was executed.")
    print("No production state was modified.")
    print("=" * 90)

if __name__ == "__main__":
    main()