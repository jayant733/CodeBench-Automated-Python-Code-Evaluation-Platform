from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ai_code_evaluator.runtime.harness import evaluate
from ai_code_evaluator.tasks import TaskLoader

FailureCategoryId = Literal[
    "boundary-condition",
    "normalization",
    "ordering-semantics",
    "pagination-control",
    "termination-safety",
    "retry-policy",
    "schema-validation",
]


class FailureCategory(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: FailureCategoryId
    description: str = Field(min_length=20)


class FailureTaxonomy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    categories: list[FailureCategory] = Field(min_length=1)


class CuratedFailureCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z0-9-]+$")
    category: FailureCategoryId
    description: str = Field(min_length=20)
    source: str = Field(pattern=r"^incorrect_solutions/[a-z0-9-]+\.py$")
    expected_failed_tests: list[str] = Field(min_length=1)


class FailureCaseManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    cases: list[CuratedFailureCase] = Field(min_length=2)


def test_curated_incorrect_solutions_exercise_documented_failure_modes(
    task_loader: TaskLoader, repository_root: Path
) -> None:
    benchmark_root = repository_root / "benchmarks" / "python"
    taxonomy = FailureTaxonomy.model_validate_json(
        (benchmark_root / "failure-taxonomy.json").read_text(encoding="utf-8")
    )
    taxonomy_ids = {category.id for category in taxonomy.categories}
    assert len(taxonomy_ids) == len(taxonomy.categories)

    used_categories: set[FailureCategoryId] = set()
    curated_case_count = 0
    for task in task_loader.load_all():
        task_dir = benchmark_root / task.id
        manifest = FailureCaseManifest.model_validate_json(
            (task_dir / "failure_cases.json").read_text(encoding="utf-8")
        )
        assert manifest.task_id == task.id

        job = {
            "function_name": task.function_name,
            "tests": [test.model_dump(mode="json") for test in task.tests],
        }
        for curated_case in manifest.cases:
            source_path = (task_dir / curated_case.source).resolve()
            assert source_path.is_relative_to(task_dir.resolve())
            assert source_path.is_file()

            outcome = evaluate(job, source_path)
            assert outcome["imported"], f"{task.id}/{curated_case.id}"
            assert outcome["function_exists"], f"{task.id}/{curated_case.id}"
            actual_failed_tests = [
                result["id"] for result in outcome["tests"] if result["status"] != "passed"
            ]
            assert actual_failed_tests == curated_case.expected_failed_tests, (
                f"{task.id}/{curated_case.id}: expected "
                f"{curated_case.expected_failed_tests}, observed {actual_failed_tests}"
            )
            used_categories.add(curated_case.category)
            curated_case_count += 1

    assert curated_case_count == 10
    assert used_categories == taxonomy_ids
