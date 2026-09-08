"""Run the orchestrated agent across every benchmark task and record real results."""

import argparse
import asyncio
import json
import logging
import sys
import tempfile
import uuid
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "services" / "evaluator" / "src"))

from ai_code_evaluator.agents.models import AgentConfig
from ai_code_evaluator.orchestrator import AgentOrchestrator, OrchestratorConfig
from ai_code_evaluator.providers import resolve_provider
from ai_code_evaluator.service import EvaluationService
from ai_code_evaluator.tasks import TaskLoader
from ai_code_evaluator.tools.definitions import build_default_registry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_agent(max_iterations: int, require_security: bool, output: Path) -> None:
    loader = TaskLoader()
    eval_service = EvaluationService()
    provider, provider_name = resolve_provider(loader)
    logger.info(f"Using '{provider_name}' provider with up to {max_iterations} iteration(s)")

    results = []

    for summary in loader.list_public():
        task = loader.get(summary.id)
        session_id = str(uuid.uuid4())
        logger.info(f"Running agent session {session_id} for task {task.id}")

        # A fresh orchestrator per task keeps agent memory from leaking across tasks.
        orchestrator = AgentOrchestrator(
            provider=provider,
            tool_registry=build_default_registry(),
            eval_service=eval_service,
            task_loader=loader,
            config=OrchestratorConfig(
                max_iterations=max_iterations,
                require_security=require_security,
            ),
            agent_config=AgentConfig(provider=provider_name),
        )

        with tempfile.TemporaryDirectory(prefix=f"agent-{task.id}-") as workspace:
            try:
                report = await orchestrator.run(task, session_id, Path(workspace))
                results.append(
                    {
                        "task_id": task.id,
                        "session_id": session_id,
                        "score": report.score,
                        "passed": report.passed,
                        "runtime_ms": report.runtime_ms,
                        "iterations": len(orchestrator.last_iterations),
                        "iteration_scores": [
                            record.score for record in orchestrator.last_iterations
                        ],
                    }
                )
                logger.info(f"Task {task.id}: score {report.score}, passed {report.passed}")
            except Exception as exc:
                logger.error(f"Failed to evaluate task {task.id}: {exc}")
                results.append(
                    {
                        "task_id": task.id,
                        "session_id": session_id,
                        "score": 0,
                        "passed": False,
                        "runtime_ms": 0,
                        "iterations": 0,
                        "error": str(exc),
                    }
                )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, indent=2), encoding="utf-8")
    logger.info(f"Saved {len(results)} results to {output}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=3,
        help="Attempt budget per task before the run is reported as-is.",
    )
    parser.add_argument(
        "--no-security",
        action="store_true",
        help="Skip the security agent pass.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent / "agent_results.json",
        help="Where to write the benchmark summary.",
    )
    args = parser.parse_args()

    asyncio.run(run_agent(args.max_iterations, not args.no_security, args.output))


if __name__ == "__main__":
    main()
