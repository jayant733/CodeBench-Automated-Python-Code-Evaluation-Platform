# Evaluation model

The MVP score is deterministic, additive, and capped at 100 points. It does not
claim to measure maintainability, elegance, or developer ability.

## Weights

| Dimension | Points | Signals |
| --- | ---: | --- |
| Functional correctness | 80 | Proportion of all visible and hidden tests that pass |
| Instruction adherence | 10 | Required top-level function exists (6); prohibited imports are absent (4) |
| Basic execution quality | 10 | Parses (3); imports (3); stays within time (2); no fatal runtime error (2) |

Correctness is `round(80 × passed tests ÷ total tests)`. All other signals are
boolean. There is no hidden model call, nondeterministic style grader, or
subjective review.

## Why imports are prohibited

The benchmark contracts are self-contained. Imports rooted at `socket`,
`requests`, `urllib`, `http`, `ftplib`, or `subprocess` reduce the instruction
score because they are unnecessary and expand behavior outside the contract.
The container still blocks networking and drops capabilities; static detection
is a transparent adherence signal, not the security boundary.

## Result visibility

Visible results include the case name, pass/fail/error status, runtime, and a
comparison message. Hidden results expose only passed, failed, and total counts.
Neither hidden inputs nor expected values appear in the public task or
evaluation response.

## Failure behavior

- Syntax and missing-function errors are reported without starting Docker.
- Import failures, runtime exceptions, and failed assertions produce completed
  evaluation reports rather than transport errors.
- A wall-clock timeout marks all unfinished cases as errors.
- Docker or runner-image unavailability is an HTTP 503 because the evaluation
  did not run.
- Unknown tasks are HTTP 404; malformed bodies are HTTP 422.

## Limitations

- A handful of objective signals cannot represent broad code quality.
- Tests are only as strong as their cases and may miss valid or invalid
  behaviors.
- Python's `round` behavior is part of the deterministic score contract.
- All cases currently run in one imported module, so submission state can carry
  between cases.
- Runtime measurements are diagnostic and are not benchmark-grade performance
  data.

