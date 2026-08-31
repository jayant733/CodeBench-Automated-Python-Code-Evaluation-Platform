from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

from ai_code_evaluator.runner import DockerRunner
from ai_code_evaluator.tasks import TaskLoader


def completed(
    args: list[str],
    *,
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=args,
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


def test_runner_applies_isolation_controls_and_parses_result(
    tmp_path: Path, task_loader: TaskLoader
) -> None:
    payload = {
        "imported": True,
        "function_exists": True,
        "runtime_ms": 4,
        "stdout": "",
        "stderr": "",
        "tests": [],
    }
    calls: list[list[str]] = []

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        if command[1] == "info":
            return completed(command, stdout="29.0")
        if command[1:3] == ["image", "inspect"]:
            return completed(command)
        if command[1] == "run":
            return completed(command, stdout=json.dumps(payload))
        return completed(command)

    runner = DockerRunner(job_root=tmp_path, docker_job_root=tmp_path)
    with patch("ai_code_evaluator.runner.subprocess.run", side_effect=fake_run):
        outcome = runner.evaluate(
            task_loader.get("palindrome-normalization"),
            "def is_normalized_palindrome(value):\n    return True\n",
        )

    assert outcome.imported
    run_command = next(command for command in calls if command[1] == "run")
    assert run_command[run_command.index("--network") : run_command.index("--network") + 2] == [
        "--network",
        "none",
    ]
    assert "--read-only" in run_command
    assert run_command[run_command.index("--cap-drop") : run_command.index("--cap-drop") + 2] == [
        "--cap-drop",
        "ALL",
    ]
    assert "no-new-privileges:true" in run_command
    assert "--cpus" in run_command
    assert "--memory" in run_command
    assert "--pids-limit" in run_command
    assert run_command[run_command.index("--user") : run_command.index("--user") + 2] == [
        "--user",
        "65532:65532",
    ]
    mount = run_command[run_command.index("--mount") + 1]
    assert mount.endswith(",target=/workspace,readonly")


def test_runner_timeout_returns_structured_outcome_and_forces_cleanup(
    tmp_path: Path, task_loader: TaskLoader
) -> None:
    cleanup_seen = False

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        nonlocal cleanup_seen
        if command[1] == "info":
            return completed(command, stdout="29.0")
        if command[1:3] == ["image", "inspect"]:
            return completed(command)
        if command[1] == "run":
            raise subprocess.TimeoutExpired(command, timeout=2)
        if command[1:3] == ["rm", "--force"]:
            cleanup_seen = True
        return completed(command)

    runner = DockerRunner(job_root=tmp_path, docker_job_root=tmp_path)
    with patch("ai_code_evaluator.runner.subprocess.run", side_effect=fake_run):
        outcome = runner.evaluate(
            task_loader.get("palindrome-normalization"),
            "def is_normalized_palindrome(value):\n    while True:\n        pass\n",
        )

    assert outcome.timed_out
    assert outcome.fatal_code == "timeout"
    assert cleanup_seen


def test_available_handles_missing_docker_binary() -> None:
    runner = DockerRunner()
    with patch(
        "ai_code_evaluator.runner.subprocess.run",
        Mock(side_effect=FileNotFoundError),
    ):
        assert not runner.available()
