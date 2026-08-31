"""Export the FastAPI OpenAPI document used for generated browser contracts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .api import create_app


def default_schema_path() -> Path:
    repository_root = Path(__file__).resolve().parents[4]
    return repository_root / "packages" / "shared-types" / "openapi.json"


def build_openapi_document() -> dict[str, Any]:
    return create_app().openapi()


def render_openapi_document() -> str:
    return (
        json.dumps(
            build_openapi_document(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export the evaluator's canonical OpenAPI document."
    )
    parser.add_argument(
        "--check", action="store_true", help="Fail when the committed schema drifts."
    )
    parser.add_argument("--output", type=Path, default=default_schema_path())
    arguments = parser.parse_args()

    rendered = render_openapi_document()
    output = arguments.output.resolve()
    if arguments.check:
        if not output.is_file() or output.read_text(encoding="utf-8") != rendered:
            raise SystemExit(
                f"{output} is stale. Run `npm run contracts:generate` and commit the result."
            )
        return

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
    print(f"Exported OpenAPI schema to {output}")


if __name__ == "__main__":
    main()
