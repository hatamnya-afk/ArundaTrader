import ast
from pathlib import Path

tree = ast.parse(
    Path("arunda_pipeline.py").read_text(encoding="utf-8-sig")
)

refs = []

def walk(node, scope="<module>"):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        scope = node.name

    if isinstance(node, ast.Name) and node.id == "market_data_result":
        refs.append(
            (
                node.lineno,
                node.col_offset,
                type(node.ctx).__name__,
                scope,
            )
        )

    for child in ast.iter_child_nodes(node):
        walk(child, scope)

walk(tree)

print("MARKET_DATA_RESULT_SCOPE_TRACE")
for item in refs:
    print(
        f"line={item[0]} col={item[1]} "
        f"ctx={item[2]} scope={item[3]}"
    )

