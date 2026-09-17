from pathlib import Path
import py_compile
import importlib.util
import sys

ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

FILES = [
    "dynamic_feature_contract_boundary_v0_1.py",
    "feature_engine.py",
    "feature_contract.py",
    "indicator_engine.py",
    "market_structure_engine.py",
]

print("=" * 90)
print("ARUNDA DYNAMIC FEATURE CONTRACT BOUNDARY v0.1")
print("STATIC CHECK ONLY")
print("=" * 90)

failed = False

for name in FILES:
    path = ROOT / name

    if not path.exists():
        print(f"FILE={name}")
        print("EXISTS=FAIL")
        failed = True
        continue

    try:
        py_compile.compile(
            str(path),
            doraise=True,
        )
        print(f"FILE={name}")
        print("EXISTS=PASS")
        print("COMPILE=PASS")
    except Exception as exc:
        print(f"FILE={name}")
        print("COMPILE=FAIL")
        print(f"ERROR={type(exc).__name__}:{exc}")
        failed = True

boundary_path = ROOT / "dynamic_feature_contract_boundary_v0_1.py"

if boundary_path.exists():
    spec = importlib.util.spec_from_file_location(
        "arunda_dynamic_feature_contract_boundary_v01",
        boundary_path,
    )

    if spec is None or spec.loader is None:
        print("BOUNDARY_IMPORT=FAIL")
        failed = True
    else:
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module

        try:
            spec.loader.exec_module(module)
            print("BOUNDARY_IMPORT=PASS")

            required = (
                "normalize_dynamic_symbol",
                "validate_real_bar_sequence",
                "validate_cardinality",
                "validate_feature_records",
                "build_dynamic_feature_context",
            )

            for name in required:
                if hasattr(module, name):
                    print(f"BOUNDARY_INTERFACE_{name}=PASS")
                else:
                    print(f"BOUNDARY_INTERFACE_{name}=FAIL")
                    failed = True

            print(f"DB_WRITES={getattr(module, 'DB_WRITES', 'MISSING')}")
            print(f"EXECUTION={getattr(module, 'EXECUTION', 'MISSING')}")
            print(f"CMC_FORBIDDEN={getattr(module, 'CMC_FORBIDDEN', 'MISSING')}")
            print(f"SYNTHETIC_DATA={getattr(module, 'SYNTHETIC_DATA', 'MISSING')}")
            print(f"INTERPOLATION={getattr(module, 'INTERPOLATION', 'MISSING')}")
            print(f"FILL={getattr(module, 'FILL', 'MISSING')}")
            print(f"BACKFILL={getattr(module, 'BACKFILL', 'MISSING')}")
            print(f"PADDING={getattr(module, 'PADDING', 'MISSING')}")
            print(f"BLENDING={getattr(module, 'BLENDING', 'MISSING')}")

            safety_ok = (
                getattr(module, "DB_WRITES", None) == 0
                and getattr(module, "EXECUTION", None) is False
                and getattr(module, "CMC_FORBIDDEN", None) is True
                and getattr(module, "SYNTHETIC_DATA", None) is False
                and getattr(module, "INTERPOLATION", None) is False
                and getattr(module, "FILL", None) is False
                and getattr(module, "BACKFILL", None) is False
                and getattr(module, "PADDING", None) is False
                and getattr(module, "BLENDING", None) is False
            )

            print(
                "SAFETY_CONTRACT="
                + ("PASS" if safety_ok else "FAIL")
            )

            if not safety_ok:
                failed = True

        except Exception as exc:
            print("BOUNDARY_IMPORT=FAIL")
            print(f"ERROR={type(exc).__name__}:{exc}")
            failed = True

print("-" * 90)

print(
    "STATIC_COMPILE="
    + ("FAIL" if failed else "PASS")
)

print(
    "STATIC_IMPORT="
    + ("FAIL" if failed else "PASS")
)

print(
    "RUNTIME_EXECUTED=FALSE"
)

print(
    "PRODUCTION_DB_TOUCHED=FALSE"
)

print(
    "DB_WRITES=0"
)

print(
    "FINAL_GATE="
    + ("BLOCKED" if failed else "STATIC_PASS")
)

raise SystemExit(1 if failed else 0)
