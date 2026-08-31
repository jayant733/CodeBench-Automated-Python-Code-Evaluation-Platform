# Roadmap

The evaluator MVP is the dependency for every later phase. New scope should not
weaken its reproducibility or security posture.

## Phase 1 — Evaluator MVP

- Five Python application-oriented tasks.
- Docker-isolated visible and hidden tests.
- Deterministic structured reports.
- Focused Next.js submission dashboard.
- Automated checks, CI, and explicit security limitations.

## Phase 2 — Debugging benchmark

Add intentionally broken repositories with issue descriptions, seeded defects,
visible tests, hidden regression suites, reproducible environments, and
maintainer-only reference patches. Define patch-evaluation semantics before
adding a large repository collection.

## Phase 3 — Coding agent

Build an iterative agent that can inspect a task, propose a patch, run tests,
interpret failure output, revise, and produce a final explanation and diff.
Keep model access behind a provider interface so task orchestration is not tied
to a vendor. Record tool actions and evaluation evidence; do not fabricate
successful runs.

## Phase 4 — History and comparison

Introduce persistence only when the product supports useful history:

- compare submissions or agent attempts;
- human-versus-agent benchmark summaries;
- failure-category analysis;
- exportable reports;
- reproducible run metadata.

## Near-term quality work

1. Split test cases into fresh processes for stronger state isolation and more
   precise per-case timeouts.
2. Add a narrow worker queue so the API never needs direct Docker-daemon access.
3. Add keyboard-focused browser integration tests and reviewed dashboard
   screenshots.
