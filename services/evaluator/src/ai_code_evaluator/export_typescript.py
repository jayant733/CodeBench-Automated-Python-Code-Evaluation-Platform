"""Generate browser-side TypeScript contracts from the committed OpenAPI document."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from .export_openapi import default_schema_path

IDENTIFIER = re.compile(r"^[A-Za-z_$][A-Za-z0-9_$]*$")


def default_typescript_path() -> Path:
    return default_schema_path().parent / "src" / "generated" / "api.ts"


def _reference_name(reference: str) -> str:
    prefix = "#/components/schemas/"
    if not reference.startswith(prefix):
        raise ValueError(f"Unsupported OpenAPI reference: {reference}")
    return reference.removeprefix(prefix)


def _literal(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    return json.dumps(value, ensure_ascii=False)


def _property_name(name: str) -> str:
    return name if IDENTIFIER.fullmatch(name) else json.dumps(name)


def _typescript_type(schema: dict[str, Any]) -> str:
    if reference := schema.get("$ref"):
        return _reference_name(reference)
    if "const" in schema:
        return _literal(schema["const"])
    if enum := schema.get("enum"):
        return " | ".join(_literal(value) for value in enum)
    if variants := schema.get("anyOf"):
        return " | ".join(_typescript_type(variant) for variant in variants)
    if variants := schema.get("oneOf"):
        return " | ".join(_typescript_type(variant) for variant in variants)
    if parts := schema.get("allOf"):
        return " & ".join(_typescript_type(part) for part in parts)

    schema_type = schema.get("type")
    if schema_type == "string":
        return "string"
    if schema_type in {"integer", "number"}:
        return "number"
    if schema_type == "boolean":
        return "boolean"
    if schema_type == "null":
        return "null"
    if schema_type == "array":
        item_type = _typescript_type(schema.get("items", {}))
        if " | " in item_type or " & " in item_type:
            item_type = f"({item_type})"
        return f"{item_type}[]"
    if schema_type == "object":
        properties = schema.get("properties")
        if properties:
            required = set(schema.get("required", []))
            fields = [
                (
                    f"{_property_name(name)}{'' if name in required else '?'}: "
                    f"{_typescript_type(property_schema)};"
                )
                for name, property_schema in sorted(properties.items())
            ]
            return "{ " + " ".join(fields) + " }"
        return "Record<string, unknown>"
    if not schema_type:
        return "unknown"
    raise ValueError(f"Unsupported OpenAPI schema fragment: {schema}")


def render_typescript_contract(schema_path: Path | None = None) -> str:
    source = (schema_path or default_schema_path()).resolve()
    document = json.loads(source.read_text(encoding="utf-8"))
    schemas: dict[str, dict[str, Any]] = document["components"]["schemas"]

    lines = [
        "/**",
        " * Generated from packages/shared-types/openapi.json.",
        " * Do not edit directly; run `npm run contracts:generate`.",
        " */",
        "",
    ]
    for name, schema in sorted(schemas.items()):
        if schema.get("type") != "object" or not schema.get("properties"):
            lines.append(f"export type {name} = {_typescript_type(schema)};")
            lines.append("")
            continue

        required = set(schema.get("required", []))
        lines.append(f"export interface {name} {{")
        for property_name, property_schema in sorted(schema["properties"].items()):
            optional = "" if property_name in required else "?"
            lines.append(
                f"  {_property_name(property_name)}{optional}: {_typescript_type(property_schema)};"
            )
        lines.append("}")
        lines.append("")

    if "TaskSummary" in schemas:
        lines.append('export type Difficulty = TaskSummary["difficulty"];')
    if "TestResult" in schemas:
        lines.append('export type TestStatus = TestResult["status"];')
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate TypeScript types from the evaluator OpenAPI document."
    )
    parser.add_argument("--check", action="store_true", help="Fail when generated types drift.")
    parser.add_argument("--schema", type=Path, default=default_schema_path())
    parser.add_argument("--output", type=Path, default=default_typescript_path())
    arguments = parser.parse_args()

    rendered = render_typescript_contract(arguments.schema)
    output = arguments.output.resolve()
    if arguments.check:
        if not output.is_file() or output.read_text(encoding="utf-8") != rendered:
            raise SystemExit(
                f"{output} is stale. Run `npm run contracts:generate` and commit the result."
            )
        return

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
    print(f"Generated TypeScript contracts at {output}")


if __name__ == "__main__":
    main()
