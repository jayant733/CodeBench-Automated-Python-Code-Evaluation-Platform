from __future__ import annotations

from ai_code_evaluator.export_openapi import default_schema_path, render_openapi_document
from ai_code_evaluator.export_typescript import (
    default_typescript_path,
    render_typescript_contract,
)


def test_committed_openapi_document_matches_fastapi_contract() -> None:
    schema_path = default_schema_path()

    assert schema_path.is_file()
    assert schema_path.read_text(encoding="utf-8") == render_openapi_document()


def test_generated_typescript_contract_matches_openapi_document() -> None:
    typescript_path = default_typescript_path()
    generated = render_typescript_contract()

    assert typescript_path.is_file()
    assert typescript_path.read_text(encoding="utf-8") == generated
    assert "execution_signals: number;" in generated
    assert "code_quality" not in generated
