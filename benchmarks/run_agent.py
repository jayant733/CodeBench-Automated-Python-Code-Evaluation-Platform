import asyncio
import json
import logging
import sys
import uuid
from pathlib import Path
from typing import Any, Sequence
from pydantic import BaseModel

sys.path.append(str(Path(__file__).parent.parent / "services" / "evaluator" / "src"))

from ai_code_evaluator.agents.models import AgentConfig
from ai_code_evaluator.orchestrator import AgentOrchestrator, OrchestratorConfig
from ai_code_evaluator.providers import ModelProvider, GenerateResult, StructuredResult, TokenUsage
from ai_code_evaluator.service import EvaluationService
from ai_code_evaluator.tasks import TaskLoader
from ai_code_evaluator.tools.registry import ToolRegistry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockBenchmarkProvider(ModelProvider):
    async def generate(
        self,
        messages: Sequence[dict[str, Any]],
        model: str,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> GenerateResult:
        return GenerateResult(
            content="Mocked benchmark response",
            tool_calls=None,
            usage=TokenUsage(),
            model=model,
            finish_reason="stop",
        )

    async def structured_generate(
        self,
        messages: Sequence[dict[str, Any]],
        response_format: type[BaseModel],
        model: str,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> StructuredResult:
        # Generate instance of response_format using default values if possible
        try:
            parsed = response_format()
        except Exception:
            # Fallback for models like CodingPlan or ReviewVerdict
            if hasattr(response_format, "model_construct"):
                parsed = response_format.model_construct(
                    summary="Mocked plan",
                    steps=[],
                    approved=True,
                    safe=True,
                    risk_level="none",
                )
            else:
                parsed = None
        return StructuredResult(
            parsed=parsed,
            usage=TokenUsage(),
            model=model,
        )

async def run_agent() -> None:
    loader = TaskLoader()
    tasks = loader.list_public()
    
    provider = MockBenchmarkProvider()
    eval_service = EvaluationService()
    registry = ToolRegistry()
    
    orchestrator = AgentOrchestrator(
        provider=provider,
        tool_registry=registry,
        eval_service=eval_service,
        config=OrchestratorConfig(max_iterations=1, require_security=False),
        agent_config=AgentConfig()
    )

    results = []
    workspace = Path("/tmp/mock_workspace")
    workspace.mkdir(parents=True, exist_ok=True)
    
    for summary in tasks:
        task = loader.get(summary.id)
        session_id = str(uuid.uuid4())
        logger.info(f"Running agent evaluation for task {task.id}")
        
        try:
            report = await orchestrator.run(task, session_id, workspace)
            
            results.append({
                "task_id": task.id,
                "score": report.score,
                "passed": report.passed,
                "runtime_ms": report.runtime_ms,
                "iterations": 1,
            })
            logger.info(f"Task {task.id}: Score {report.score}, Passed: {report.passed}")
        except Exception as e:
            logger.error(f"Failed to evaluate task {task.id}: {e}")
            results.append({
                "task_id": task.id,
                "score": 0,
                "passed": False,
                "runtime_ms": 0,
                "error": str(e)
            })

    output_file = Path("benchmarks/agent_results.json")
    output_file.write_text(json.dumps(results, indent=2))
    logger.info(f"Saved {len(results)} results to {output_file}")

if __name__ == "__main__":
    asyncio.run(run_agent())
