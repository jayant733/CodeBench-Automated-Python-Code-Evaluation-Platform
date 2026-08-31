# Contributing

Thank you for improving AI Code Evaluation Suite. The project favors small,
reviewable changes with evidence over broad feature additions.

## Before you start

1. Read [the architecture](docs/architecture.md), [evaluation model](docs/evaluation-model.md),
   and [security notes](docs/security.md).
2. Open an issue for changes that alter task contracts, score semantics, the
   sandbox boundary, or public API fields.
3. Create a focused branch and keep unrelated formatting changes out of the
   patch.

## Local checks

Install Python 3.12, Node.js 22, and Docker. Then run:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e "services/evaluator[dev]"
npm ci
docker build -t ai-code-evaluator-runner:local -f docker/runner/Dockerfile .
ruff check services/evaluator
ruff format --check services/evaluator
mypy services/evaluator/src
pytest services/evaluator/tests
npm run dashboard:lint
npm run dashboard:typecheck
npm run dashboard:test
npm run dashboard:build
```

## Adding a benchmark task

- Create `benchmarks/python/<task-id>/task.json`.
- Add both visible and hidden cases with unique identifiers.
- Add `reference_solution.py` separately from the task definition.
- Keep the task deterministic and free of network or wall-clock dependencies.
- State edge cases, validation behavior, and the exact function signature.
- Run `test_reference_solutions.py`; a task is not accepted until the reference
  passes every case.

Hidden tests are confidential only at the API boundary in this MVP. Do not add
secrets or proprietary data to any task file.

## Pull requests

Describe the behavior change, tests run, security implications, and any known
limitations. Screenshots are useful for visible dashboard changes. Do not claim
coverage, benchmark performance, or security properties that the patch does not
demonstrate.
