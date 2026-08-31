from __future__ import annotations

import subprocess
import time

import pytest

from ai_code_evaluator.runner import DockerRunner
from ai_code_evaluator.tasks import TaskLoader

pytestmark = pytest.mark.docker


def docker_runner_ready() -> bool:
    runner = DockerRunner()
    if not runner.available():
        return False
    image = subprocess.run(
        ["docker", "image", "inspect", runner.image],
        capture_output=True,
        text=True,
        check=False,
    )
    return image.returncode == 0


@pytest.mark.skipif(not docker_runner_ready(), reason="Docker runner image unavailable")
def test_runner_container_has_no_external_network_access() -> None:
    result = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "ai-code-evaluator-runner:local",
            "python",
            "-c",
            ("import socket; socket.create_connection(('1.1.1.1', 443), timeout=0.5)"),
        ],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )

    assert result.returncode != 0
    assert "OSError" in result.stderr


@pytest.mark.skipif(not docker_runner_ready(), reason="Docker runner image unavailable")
def test_infinite_loop_is_terminated_by_wall_clock_limit(
    task_loader: TaskLoader,
) -> None:
    runner = DockerRunner()
    started = time.perf_counter()
    outcome = runner.evaluate(
        task_loader.get("palindrome-normalization"),
        "def is_normalized_palindrome(value):\n    while True:\n        pass\n",
    )

    assert outcome.timed_out
    assert time.perf_counter() - started < 5
