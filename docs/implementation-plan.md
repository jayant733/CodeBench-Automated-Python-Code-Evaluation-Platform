# MVP implementation plan

## Goal

Deliver a reproducible monorepo that demonstrates the complete local evaluation
flow: browse a task, submit Python, execute it in a disposable Docker container,
and render a structured report without exposing hidden test cases through the
API.

## Assumptions

- Docker Desktop or another Linux Docker daemon is a required local dependency.
- The evaluator targets Python 3.12 even if a contributor's host Python differs;
  submitted code always runs in the pinned runner image.
- Task definitions and results remain file-backed and request-scoped for the
  MVP. There is no database or authentication.
- The first security boundary is suitable for a trusted local demonstration,
  not hostile public multi-tenant execution.
- Hidden test definitions are withheld from API responses. They are present on
  the evaluator host and are staged into the disposable runner at evaluation
  time, so filesystem confidentiality inside a compromised container is not
  claimed.
- The dashboard talks directly to the evaluator through a configurable public
  API base URL.

## Delivery phases

1. **Foundation**
   - Establish the monorepo directories, shared configuration, ignore rules,
     license, and developer commands.
2. **Evaluator domain**
   - Add typed task definitions, public task projections, deterministic scoring,
     validation, and five benchmark tasks with separate reference solutions.
3. **Isolated execution**
   - Add the Python runner image and host-side Docker orchestration with no
     network, a non-root user, read-only mounts, resource limits, timeouts, and
     cleanup.
4. **API**
   - Expose task discovery and evaluation endpoints with typed, sanitized error
     responses.
5. **Dashboard**
   - Build a responsive Next.js task workspace with a prefilled submission,
     clear evaluation states, test details, captured output, and actionable
     service errors.
6. **Verification**
   - Add focused evaluator and dashboard tests, lint/type checks, CI, Compose,
     and an end-to-end smoke path.
7. **Documentation**
   - Finalize architecture, scoring, security, contribution, setup, and roadmap
     documents so they match the implemented behavior.

## Verification gates

- Evaluator: Ruff, mypy, pytest, and API contract tests.
- Runner: timeout, malformed source, missing function, runtime exception,
  Docker-unavailable, and network-denial coverage.
- Dashboard: strict TypeScript, lint, production build, and meaningful component
  tests.
- Integration: build the runner image, start Compose, list tasks, evaluate the
  prefilled solution, and confirm hidden case details are absent.

## Deferred work

- Repository-level debugging benchmarks.
- AI coding-agent orchestration and model-provider adapters.
- Persistence, accounts, evaluation history, and comparisons.
- Claims or controls required for a hostile public multi-tenant sandbox.
