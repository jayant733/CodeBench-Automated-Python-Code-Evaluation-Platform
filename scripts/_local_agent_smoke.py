"""Run the orchestrator locally with the offline provider and print the iteration trace."""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import uuid
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "services" / "evaluator" / "src"))

os.environ.setdefault("MLFLOW_DISABLED", "1")
os.environ.setdefault("EVALUATOR_DB_URL", "sqlite+aiosqlite:///./local-agent-smoke.db")

from ai_code_evaluator.agents.models import AgentConfig  # noqa: E402
from ai_code_evaluator.orchestrator import AgentOrchestrator, OrchestratorConfig  # noqa: E402
from ai_code_evaluator.providers.offline import OfflineProvider  # noqa: E402
from ai_code_evaluator.service import EvaluationService  # noqa: E402
from ai_code_evaluator.tasks import TaskLoader  # noqa: E402
from ai_code_evaluator.tools.definitions import build_default_registry  # noqa: E402


async def main() -> None:
    task_id = sys.argv[1] if len(sys.argv) > 1 else "palindrome-normalization"
    loader = TaskLoader()
    task = loader.get(task_id)

    orchestrator = AgentOrchestrator(
        provider=OfflineProvider(loader),
        tool_registry=build_default_registry(),
        eval_service=EvaluationService(),
        task_loader=loader,
        config=OrchestratorConfig(max_iterations=4),
        agent_config=AgentConfig(provider="offline", model="offline-fixture-replay"),
    )

    session_id = str(uuid.uuid4())
    with tempfile.TemporaryDirectory() as workspace:
        report = await orchestrator.run(task, session_id, Path(workspace))

    print(f"\ntask={task.id} final_score={report.score} passed={report.passed}")
    print(f"iterations recorded: {len(orchestrator.last_iterations)}")
    for record in orchestrator.last_iterations:
        tools = ", ".join(call["tool_name"] for call in record.tool_calls) or "none"
        review = (record.review_verdict or {}).get("approved")
        security = (record.security_verdict or {}).get("safe")
        print(
            f"  iteration {record.iteration_number}: score={record.score} "
            f"duration={record.duration_ms}ms tools=[{tools}] "
            f"review_approved={review} security_safe={security}"
        )


if __name__ == "__main__":
    asyncio.run(main())
