# Benchmark quality

The benchmark suite treats task design as an evaluation artifact, not just a
collection of prompts. Every task includes:

- a precise behavioral contract;
- four visible and four hidden cases;
- a separate reference solution that must pass every case;
- at least two plausible incorrect submissions;
- an explicit failure classification and exact expected failing cases.

## Failure taxonomy

| Classification | What it detects |
| --- | --- |
| `boundary-condition` | Empty, falsey, minimum, maximum, and off-by-one mistakes |
| `normalization` | Missing or incorrect canonicalization |
| `ordering-semantics` | Incorrect first-seen, stable-order, or replacement behavior |
| `pagination-control` | Incomplete traversal or incorrect cursor progression |
| `termination-safety` | Missing page, attempt, or other execution bounds |
| `retry-policy` | Incorrect attempt budgets, delay progression, or caps |
| `schema-validation` | Malformed nested data or incorrect field types accepted |

The canonical descriptions live in
[`benchmarks/python/failure-taxonomy.json`](../benchmarks/python/failure-taxonomy.json).
Each task's `failure_cases.json` maps curated incorrect submissions to one
classification and the exact cases expected to reject it.

## Mutation-style validation

`test_benchmark_quality.py` executes ten curated incorrect submissions across
the same visible and hidden cases used by the evaluator. CI fails when an
incorrect submission unexpectedly passes, fails for a different reason, or no
longer exercises its declared failure mode. This provides a small,
human-readable mutation suite without claiming broad statistical coverage.

The suite still contains five tasks and should not be presented as a
general-purpose benchmark. Its purpose is to demonstrate careful contracts,
edge-case selection, deterministic grading, and auditable failure analysis.
