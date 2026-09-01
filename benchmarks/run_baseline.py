import asyncio
import json
import logging
import sys
from pathlib import Path

# Add services to path so we can import evaluator modules
sys.path.append(str(Path(__file__).parent.parent / "services" / "evaluator" / "src"))

from ai_code_evaluator.service import EvaluationService
from ai_code_evaluator.tasks import TaskLoader

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_baseline() -> None:
    loader = TaskLoader()
    tasks = loader.list_public()
    
    # We will use mock evaluation service since docker isn't running in our CI
    # In a real environment, we would use EvaluationService() directly.
    # For now, let's use the standard EvaluationService but handle exceptions.
    from ai_code_evaluator.service import EvaluationService
    eval_service = EvaluationService()

    results = []
    
    for summary in tasks:
        task = loader.get(summary.id)
        logger.info(f"Running baseline evaluation for task {task.id}")
        
        try:
            # For baseline, we evaluate the starter_code which should fail, or
            # we evaluate a known solution. Here we just evaluate starter_code.
            report = await asyncio.to_thread(eval_service.evaluate, task, task.starter_code)
            
            results.append({
                "task_id": task.id,
                "score": report.score,
                "passed": report.passed,
                "runtime_ms": report.runtime_ms,
                "feedback": report.feedback,
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

    output_file = Path("benchmarks/baseline_results.json")
    output_file.write_text(json.dumps(results, indent=2))
    logger.info(f"Saved {len(results)} results to {output_file}")

if __name__ == "__main__":
    asyncio.run(run_baseline())
