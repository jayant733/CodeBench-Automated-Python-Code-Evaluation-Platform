"""Host-side orchestration for disposable Docker evaluations."""

from __future__ import annotations

import contextlib
import json
import logging
import os
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Any

from .errors import (
    DockerUnavailableError,
    RunnerImageUnavailableError,
    RunnerProtocolError,
)
from .models import ExecutionOutcome, TaskDefinition

logger = logging.getLogger(__name__)


def _subprocess_flags() -> int:
    return int(getattr(subprocess, "CREATE_NO_WINDOW", 0))


class DockerRunner:
    def __init__(
        self,
        *,
        image: str | None = None,
        docker_binary: str | None = None,
        job_root: Path | None = None,
        docker_job_root: Path | None = None,
    ) -> None:
        self.image: str = (
            image or os.getenv("EVALUATOR_RUNNER_IMAGE") or "ai-code-evaluator-runner:local"
        )
        self.docker_binary: str = docker_binary or os.getenv("DOCKER_BINARY") or "docker"
        configured_job_root = job_root or Path(
            os.getenv("EVALUATOR_JOB_ROOT", tempfile.gettempdir())
        )
        self.job_root = configured_job_root.resolve()
        configured_docker_root = docker_job_root or Path(
            os.getenv("EVALUATOR_DOCKER_JOB_ROOT", str(self.job_root))
        )
        self.docker_job_root = configured_docker_root.resolve()
        self.job_volume = os.getenv("EVALUATOR_JOB_VOLUME")
        self.harness_path = Path(__file__).parent / "runtime" / "harness.py"

    def available(self) -> bool:
        try:
            result = subprocess.run(
                [self.docker_binary, "info", "--format", "{{.ServerVersion}}"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
                creationflags=_subprocess_flags(),
            )
        except (OSError, subprocess.TimeoutExpired):
            return False
        return result.returncode == 0

    def _ensure_ready(self) -> None:
        if not self.available():
            raise DockerUnavailableError
        result = subprocess.run(
            [self.docker_binary, "image", "inspect", self.image],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
            creationflags=_subprocess_flags(),
        )
        if result.returncode != 0:
            raise RunnerImageUnavailableError

    def evaluate(self, task: TaskDefinition, source_code: str) -> ExecutionOutcome:
        self._ensure_ready()
        self.job_root.mkdir(parents=True, exist_ok=True)
        container_name = f"aices-{uuid.uuid4().hex[:12]}"
        timeout_seconds = task.time_limit_seconds + 1.0

        with tempfile.TemporaryDirectory(prefix="aices-", dir=self.job_root) as directory:
            local_workspace = Path(directory)
            local_workspace.chmod(0o755)
            docker_workspace = self.docker_job_root / local_workspace.name
            if self.job_volume:
                mount_spec = (
                    f"type=volume,source={self.job_volume},target=/workspace,"
                    f"readonly,volume-subpath={local_workspace.name}"
                )
            else:
                mount_spec = f"type=bind,source={docker_workspace},target=/workspace,readonly"
            (local_workspace / "submission.py").write_text(source_code, encoding="utf-8")
            (local_workspace / "harness.py").write_text(
                self.harness_path.read_text(encoding="utf-8"), encoding="utf-8"
            )
            job: dict[str, Any] = {
                "task_id": task.id,
                "function_name": task.function_name,
                "tests": [test.model_dump(mode="json") for test in task.tests],
            }
            (local_workspace / "job.json").write_text(
                json.dumps(job, separators=(",", ":")), encoding="utf-8"
            )
            for staged_file in local_workspace.iterdir():
                staged_file.chmod(0o444)

            command = [
                self.docker_binary,
                "run",
                "--name",
                container_name,
                "--rm",
                "--network",
                "none",
                "--read-only",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges:true",
                "--cpus",
                os.getenv("EVALUATOR_CPU_LIMIT", "0.5"),
                "--memory",
                f"{task.memory_limit_mb}m",
                "--memory-swap",
                f"{task.memory_limit_mb}m",
                "--pids-limit",
                "64",
                "--user",
                "65532:65532",
                "--tmpfs",
                "/tmp:rw,noexec,nosuid,size=16m",
                "--env",
                "PYTHONDONTWRITEBYTECODE=1",
                "--mount",
                mount_spec,
                "--workdir",
                "/workspace",
                self.image,
                "python",
                "/workspace/harness.py",
                "/workspace/job.json",
                "/workspace/submission.py",
            ]

            try:
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds,
                    check=False,
                    creationflags=_subprocess_flags(),
                )
            except subprocess.TimeoutExpired:
                self._cleanup(container_name)
                return ExecutionOutcome(
                    imported=True,
                    function_exists=True,
                    timed_out=True,
                    runtime_ms=round(task.time_limit_seconds * 1000),
                    fatal_code="timeout",
                    fatal_message=(
                        f"Execution exceeded the {task.time_limit_seconds:g} second time limit."
                    ),
                )
            finally:
                self._cleanup(container_name)

        if result.returncode != 0 and not result.stdout.strip():
            logger.error(
                "Runner container exited with code %s: %s",
                result.returncode,
                self._sanitized_diagnostic(result.stderr),
            )
            raise RunnerProtocolError
        try:
            payload = json.loads(result.stdout)
            if "protocol_error" in payload:
                raise RunnerProtocolError
            return ExecutionOutcome.model_validate(payload)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.error(
                "Runner returned invalid JSON: %s",
                self._sanitized_diagnostic(result.stderr),
            )
            raise RunnerProtocolError from exc

    def _sanitized_diagnostic(self, value: str) -> str:
        sanitized = value[-1000:]
        for path in (self.job_root, self.docker_job_root):
            sanitized = sanitized.replace(str(path), "<job-root>")
        return sanitized.strip() or "no diagnostic output"

    def _cleanup(self, container_name: str) -> None:
        with contextlib.suppress(OSError, subprocess.TimeoutExpired):
            subprocess.run(
                [self.docker_binary, "rm", "--force", container_name],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
                creationflags=_subprocess_flags(),
            )
