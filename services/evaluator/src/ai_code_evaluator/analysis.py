"""Static, non-executing checks used for explainable score signals."""

from __future__ import annotations

import ast

from .models import SourceAnalysis

PROHIBITED_IMPORT_ROOTS = {
    "ftplib",
    "http",
    "requests",
    "socket",
    "subprocess",
    "urllib",
}


def analyze_source(source_code: str, required_function: str) -> SourceAnalysis:
    try:
        tree = ast.parse(source_code, filename="submission.py")
    except SyntaxError as exc:
        location = f"line {exc.lineno}" if exc.lineno else "an unknown line"
        return SourceAnalysis(
            syntax_valid=False,
            function_exists=False,
            prohibited_behavior_absent=True,
            syntax_message=f"Syntax error at {location}: {exc.msg}",
        )

    function_exists = any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == required_function
        for node in tree.body
    )

    prohibited: set[str] = set()
    for node in ast.walk(tree):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
        for name in names:
            root = name.split(".", 1)[0]
            if root in PROHIBITED_IMPORT_ROOTS:
                prohibited.add(root)

    return SourceAnalysis(
        syntax_valid=True,
        function_exists=function_exists,
        prohibited_behavior_absent=not prohibited,
        prohibited_imports=sorted(prohibited),
    )
