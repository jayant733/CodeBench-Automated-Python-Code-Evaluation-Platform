from ai_code_evaluator.analysis import analyze_source


def test_source_analysis_detects_function_and_prohibited_import() -> None:
    analysis = analyze_source(
        "import socket\n\ndef solve():\n    return 1\n",
        "solve",
    )

    assert analysis.syntax_valid
    assert analysis.function_exists
    assert not analysis.prohibited_behavior_absent
    assert analysis.prohibited_imports == ["socket"]


def test_source_analysis_reports_syntax_without_host_path() -> None:
    analysis = analyze_source("def solve(:\n    pass", "solve")

    assert not analysis.syntax_valid
    assert analysis.syntax_message is not None
    assert "line 1" in analysis.syntax_message
    assert "C:\\" not in analysis.syntax_message
