import ast
import py_compile
from pathlib import Path


PRODUCER = Path(__file__).with_name("account_balance_observation_v0_1.py")
SOURCE = PRODUCER.read_text(encoding="utf-8")
TREE = ast.parse(SOURCE, filename=str(PRODUCER))


def _non_docstring_source(tree):
    lines = SOURCE.splitlines()
    spans = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Expr,)) and isinstance(getattr(node, "value", None), ast.Constant):
            if isinstance(node.value.value, str):
                spans.append((node.lineno, getattr(node, "end_lineno", node.lineno)))
    for start, end in spans:
        for index in range(start - 1, end):
            lines[index] = ""
    return "\n".join(lines)


def test_provider_neutral_source():
    upper = SOURCE.upper()
    for provider in ("TOOBIT", "KUCOIN", "BITGET"):
        assert provider not in upper


def test_forbidden_architecture_identifiers_absent_from_code():
    code = _non_docstring_source(TREE).upper()
    for token in (
        "EXPECTED_ASSETS",
        "RISK_PER_TRADE",
        "MAX_PORTFOLIO_RISK",
        "ORDER_INTENT",
        "POSITION_SIZING",
        "RISK_BUDGET",
        "TOTAL_EXPOSURE",
        "CONCENTRATION",
        "CORRELATION_EXPOSURE",
        "SQLITE3",
        "CAPITAL",
        "AVAILABLE_CAPITAL",
    ):
        assert token not in code


def test_no_fixed_15_constant():
    for node in ast.walk(TREE):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            assert node.value != 15


def test_no_side_effect_imports_or_calls():
    forbidden_imports = {"sqlite3", "requests", "urllib", "subprocess", "httpx"}
    forbidden_calls = {
        "connect",
        "execute",
        "executemany",
        "execute_order",
        "submit_order",
    }
    for node in ast.walk(TREE):
        if isinstance(node, ast.Import):
            assert all(alias.name.split(".")[0] not in forbidden_imports for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".")[0] not in forbidden_imports
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id not in forbidden_calls
            elif isinstance(node.func, ast.Attribute):
                assert node.func.attr not in forbidden_calls


def test_no_production_capital_literals():
    for node in ast.walk(TREE):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    assert target.id not in {"CAPITAL", "AVAILABLE_CAPITAL"}
                    if target.id in {"CAPITAL", "AVAILABLE_CAPITAL"}:
                        assert not (isinstance(node.value, ast.Constant) and node.value.value == 1000000)


def test_python_compile():
    py_compile.compile(str(PRODUCER), doraise=True)
