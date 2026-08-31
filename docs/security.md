# Security model

## Intended use

This sandbox is designed for a trusted local portfolio demonstration and CI. It
is not approved for hostile, anonymous, public multi-tenant code execution.

## Implemented protections

Each accepted submission starts a fresh container with:

- `--network none`;
- a numeric non-root user (`65532:65532`);
- a read-only root filesystem and read-only job mount;
- all Linux capabilities dropped;
- `no-new-privileges`;
- CPU, memory, swap, PID, and wall-clock limits;
- a small `noexec,nosuid` temporary filesystem;
- captured, size-limited standard output and standard error;
- forced cleanup on completion or timeout.

The trusted API process parses source but never imports or calls it. API errors
do not return host paths or raw Docker diagnostics. Hidden case identifiers,
inputs, and expectations are excluded from public responses.

CI includes a Docker integration test that attempts an external socket
connection from the same runner image under `--network none`.

## Remaining risks

- Containers share the host kernel. A container-runtime or kernel vulnerability
  could cross the boundary.
- The Compose evaluator receives the Docker daemon socket. Compromise of the
  trusted evaluator service is effectively host-level compromise.
- Hidden task definitions are staged into the same runner filesystem as the
  submission. They are API-hidden, not cryptographically confidential from a
  malicious program inside the container.
- There is no seccomp profile beyond Docker's default, no mandatory-access
  policy tuned for Python, and no syscall-level audit.
- Output capture limits memory returned to the API, but the process can produce
  data until the container is terminated.
- There is no rate limit, authentication, per-user quota, abuse detection, or
  durable audit trail.
- Docker behavior varies across Linux, macOS, and Windows virtualization layers.

## Requirements before public multi-tenant use

Use a dedicated worker fleet separated from the API and users. Replace the
Docker socket with a narrow job-control API; consider microVMs or hardened
runtime isolation; encrypt and isolate hidden tests; enforce ingress rate and
size limits; add identity, quotas, audit logs, image provenance, patch
management, egress policy, secret scanning, and incident response. Commission a
security review and adversarial testing before making security claims.

## Reporting a vulnerability

Do not open an issue containing an exploit or sensitive detail. Contact the
repository owner privately once a security contact is published. Until then,
keep the repository private if a vulnerability requires coordination.

