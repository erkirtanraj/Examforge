import ast
from pathlib import Path


def test_server_email_router_imports_only_symbols_that_exist():
    backend = Path(__file__).resolve().parents[2]
    server_tree = ast.parse((backend / "server.py").read_text(encoding="utf-8"))
    email_tree = ast.parse((backend / "email_routes.py").read_text(encoding="utf-8"))

    exported = {
        node.name for node in email_tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    }
    imported = {
        alias.name for node in server_tree.body
        if isinstance(node, ast.ImportFrom) and node.module == "email_routes"
        for alias in node.names
    }
    assert imported <= exported
