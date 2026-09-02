from __future__ import annotations

import os
from typing import Any

from ai_code_evaluator.analysis import analyze_source
from ai_code_evaluator.tasks import TaskLoader
from ai_code_evaluator.service import EvaluationService
from ai_code_evaluator.models import EvaluationReport

from .registry import ToolContext, ToolPermission, ToolRegistry, ToolSchema

# 1. list_files
list_files_schema = ToolSchema(
    name="list_files",
    description="List all files in the current agent workspace.",
    parameters={
        "type": "object",
        "properties": {
            "directory": {
                "type": "string",
                "description": "Optional subdirectory to list (relative to workspace root). Defaults to '.'",
                "default": ".",
            }
        },
    },
    returns={
        "type": "object",
        "properties": {
            "files": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of relative file paths.",
            }
        },
    },
    permissions=[ToolPermission.READ],
)

def list_files_handler(context: ToolContext, directory: str = ".") -> dict[str, Any]:
    target_dir = (context.workspace_path / directory).resolve()
    if not target_dir.is_relative_to(context.workspace_path.resolve()):
        raise ValueError("Path escape attempt blocked.")
    
    if not target_dir.exists() or not target_dir.is_dir():
        return {"files": []}
    
    files = []
    for root, _, filenames in os.walk(target_dir):
        for filename in filenames:
            full_path = os.path.join(root, filename)
            rel_path = os.path.relpath(full_path, context.workspace_path)
            files.append(rel_path)
    
    return {"files": files}

# 2. read_file
read_file_schema = ToolSchema(
    name="read_file",
    description="Read the contents of a file in the agent workspace.",
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Relative path to the file to read.",
            }
        },
        "required": ["path"],
    },
    returns={
        "type": "object",
        "properties": {
            "content": {"type": "string"}
        },
    },
    permissions=[ToolPermission.READ],
)

def read_file_handler(context: ToolContext, path: str) -> dict[str, str]:
    target_path = (context.workspace_path / path).resolve()
    if not target_path.is_relative_to(context.workspace_path.resolve()):
        raise ValueError("Path escape attempt blocked.")
    if not target_path.exists() or not target_path.is_file():
        raise FileNotFoundError(f"File not found: {path}")
    
    return {"content": target_path.read_text(encoding="utf-8")}

# 3. write_file
write_file_schema = ToolSchema(
    name="write_file",
    description="Write content to a file in the agent workspace.",
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Relative path to the file to write.",
            },
            "content": {
                "type": "string",
                "description": "Content to write.",
            },
        },
        "required": ["path", "content"],
    },
    returns={
        "type": "object",
        "properties": {
            "success": {"type": "boolean"},
            "bytes_written": {"type": "integer"}
        },
    },
    permissions=[ToolPermission.WRITE],
)

def write_file_handler(context: ToolContext, path: str, content: str) -> dict[str, Any]:
    target_path = (context.workspace_path / path).resolve()
    if not target_path.is_relative_to(context.workspace_path.resolve()):
        raise ValueError("Path escape attempt blocked.")
    
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(content, encoding="utf-8")
    
    return {"success": True, "bytes_written": len(content)}

# 4. inspect_ast
inspect_ast_schema = ToolSchema(
    name="inspect_ast",
    description="Analyze source code for syntax errors and prohibited imports.",
    parameters={
        "type": "object",
        "properties": {
            "source_code": {
                "type": "string",
                "description": "Python source code to analyze.",
            },
            "expected_function": {
                "type": "string",
                "description": "Name of the function expected to be in the code.",
            }
        },
        "required": ["source_code", "expected_function"],
    },
    returns={
        "type": "object",
        "properties": {
            "syntax_valid": {"type": "boolean"},
            "module_imported": {"type": "boolean"},
            "function_exists": {"type": "boolean"},
            "prohibited_imports_found": {
                "type": "array",
                "items": {"type": "string"}
            }
        },
    },
    permissions=[ToolPermission.READ],
)

def inspect_ast_handler(context: ToolContext, source_code: str, expected_function: str) -> dict[str, Any]:
    analysis = analyze_source(source_code, expected_function)
    return {
        "syntax_valid": analysis.syntax_valid,
        "module_imported": analysis.module_imported,
        "function_exists": analysis.function_exists,
        "prohibited_imports_found": analysis.prohibited_imports_found,
    }

# 5. retrieve_task
retrieve_task_schema = ToolSchema(
    name="retrieve_task",
    description="Retrieve the public contract and visible tests for a task.",
    parameters={
        "type": "object",
        "properties": {
            "task_id": {
                "type": "string",
                "description": "The ID of the task to retrieve.",
            }
        },
        "required": ["task_id"],
    },
    returns={
        "type": "object",
        "description": "The public task definition.",
    },
    permissions=[ToolPermission.READ],
)

def retrieve_task_handler(context: ToolContext, task_id: str) -> dict[str, Any]:
    task_loader: TaskLoader = context.services["task_loader"]
    task = task_loader.get_public(task_id)
    return task.model_dump(mode="json")


# 6. run_tests
run_tests_schema = ToolSchema(
    name="run_tests",
    description="Evaluate the agent's submission against the visible tests using the deterministic sandbox.",
    parameters={
        "type": "object",
        "properties": {
            "task_id": {
                "type": "string",
                "description": "The ID of the task.",
            },
            "source_code": {
                "type": "string",
                "description": "The complete Python source code to evaluate.",
            }
        },
        "required": ["task_id", "source_code"],
    },
    returns={
        "type": "object",
        "description": "An EvaluationReport containing score, pass/fail status, and details of visible tests.",
    },
    permissions=[ToolPermission.EXECUTE],
    timeout_seconds=60.0,
)

def run_tests_handler(context: ToolContext, task_id: str, source_code: str) -> dict[str, Any]:
    task_loader: TaskLoader = context.services["task_loader"]
    eval_service: EvaluationService = context.services["evaluation_service"]
    
    task_def = task_loader.get(task_id)
    report: EvaluationReport = eval_service.evaluate(task_def, source_code)
    
    return report.model_dump(mode="json")


DEFAULT_TOOLS: list[tuple[ToolSchema, Any]] = [
    (list_files_schema, list_files_handler),
    (read_file_schema, read_file_handler),
    (write_file_schema, write_file_handler),
    (inspect_ast_schema, inspect_ast_handler),
    (retrieve_task_schema, retrieve_task_handler),
    (run_tests_schema, run_tests_handler),
]


def build_default_registry() -> ToolRegistry:
    """Registry containing every tool the coding agent is allowed to call."""
    registry = ToolRegistry()
    for schema, handler in DEFAULT_TOOLS:
        registry.register(schema, handler)
    return registry
