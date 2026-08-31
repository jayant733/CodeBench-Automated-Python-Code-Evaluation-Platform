from __future__ import annotations

from pathlib import Path

import pytest

from ai_code_evaluator.tasks import TaskLoader


@pytest.fixture
def repository_root() -> Path:
    return Path(__file__).resolve().parents[3]


@pytest.fixture
def task_loader(repository_root: Path) -> TaskLoader:
    return TaskLoader(repository_root / "benchmarks" / "python")
