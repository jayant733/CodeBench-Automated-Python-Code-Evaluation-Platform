from __future__ import annotations

import asyncio
from typing import Any

from pydantic import BaseModel, ConfigDict

from ai_code_evaluator.agents.models import AgentConfig
from ai_code_evaluator.agents.planner import PlannerAgent
from ai_code_evaluator.agents.coder import CodingAgent
from ai_code_evaluator.agents.reviewer import ReviewAgent
from ai_code_evaluator.agents.test_agent import TestAgent
from ai_code_evaluator.agents.security_agent import SecurityAgent
from ai_code_evaluator.providers import ModelProvider
from ai_code_evaluator.tools.registry import ToolRegistry, ToolContext, ToolPermission
from ai_code_evaluator.models import TaskDefinition, EvaluationReport
from ai_code_evaluator.service import EvaluationService


class OrchestratorConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    max_iterations: int = 3
    require_planner: bool = True
    require_reviewer: bool = True
    require_security: bool = True


class AgentOrchestrator:
    """Manages the lifecycle and interactions of all agents."""

    def __init__(
        self,
        provider: ModelProvider,
        tool_registry: ToolRegistry,
        eval_service: EvaluationService,
        config: OrchestratorConfig | None = None,
        agent_config: AgentConfig | None = None,
    ) -> None:
        self.provider = provider
        self.tool_registry = tool_registry
        self.eval_service = eval_service
        self.config = config or OrchestratorConfig()
        
        ac = agent_config or AgentConfig()
        
        # Instantiate agents
        self.planner = PlannerAgent(ac, provider)
        self.coder = CodingAgent(ac, provider)
        self.reviewer = ReviewAgent(ac, provider)
        self.tester = TestAgent(ac, provider)
        self.security = SecurityAgent(ac, provider)

    async def run(
        self,
        task: TaskDefinition,
        session_id: str,
        workspace_path: Any,  # Path
    ) -> EvaluationReport:
        """Run the end-to-end agentic workflow."""
        
        # 1. Setup Context
        tool_context = ToolContext(
            session_id=session_id,
            task_id=task.id,
            workspace_path=workspace_path,
            allowed_permissions={ToolPermission.READ, ToolPermission.WRITE, ToolPermission.EXECUTE},
            services={"evaluation": self.eval_service},
        )
        tools = self.tool_registry.get_schemas_for_llm()
        
        context: dict[str, Any] = {
            "task": task,
            "tools": tools,
            "plan": None,
            "review": None,
            "test_summary": None,
        }

        # 2. Planning Phase
        if self.config.require_planner:
            plan_response = await self.planner.invoke(context)
            context["plan"] = plan_response.structured_output

        # 3. Coding Loop
        report = None
        for iteration in range(self.config.max_iterations):
            # A. Generate Code
            coder_response = await self.coder.invoke(context)
            
            # Handle tool calls returned by the coder
            if getattr(coder_response, 'tool_calls', None):
                # We just blindly execute tools until the model stops calling them (or max tool steps)
                # For simplicity in this demo, we run them once per iteration.
                for tc in coder_response.tool_calls:
                    import json
                    try:
                        args = json.loads(tc.function["arguments"]) if isinstance(tc.function["arguments"], str) else tc.function["arguments"]
                        tool_result = await self.tool_registry.execute(
                            tc.function["name"],
                            args,
                            tool_context
                        )
                        # Normally we would feed tool_result back to the LLM, but for this portfolio MVP
                        # we assume the write_file tool is the main one and it wrote to the sandbox.
                    except Exception as e:
                        print(f"Tool execution failed: {e}")
            
            # B. Deterministic Evaluation
            # We extract code from the sandbox (solution.py)
            source_code = ""
            solution_path = workspace_path / "solution.py"
            if solution_path.exists():
                source_code = solution_path.read_text(encoding="utf-8")
            else:
                source_code = task.starter_code
                
            report = await asyncio.to_thread(
                self.eval_service.evaluate,
                task,
                source_code,
            )
            
            if report.score == 100:
                break
                
            # C. Test Analysis
            context["report"] = report
            test_response = await self.tester.invoke(context)
            context["test_summary"] = test_response.structured_output.model_dump_json(indent=2)
            
            # D. Code Review
            if self.config.require_reviewer:
                context["source_code"] = source_code
                review_response = await self.reviewer.invoke(context)
                context["review"] = review_response.structured_output
        
        if not report:
            raise RuntimeError("Coding loop failed to produce an evaluation report.")

        # 4. Security Check (Post-evaluation or during)
        if self.config.require_security:
            # Re-read solution.py in case it changed
            source_code = ""
            solution_path = workspace_path / "solution.py"
            if solution_path.exists():
                source_code = solution_path.read_text(encoding="utf-8")
                
            sec_context = {"source_code": source_code, "analysis": None}
            sec_response = await self.security.invoke(sec_context)
            sec_verdict = sec_response.structured_output
            
            if not sec_verdict.safe:
                # If unsafe, we fail the evaluation report
                report.score = 0
                report.passed = False
                report.summary = f"Security Check Failed: {sec_verdict.risk_level} risk."

        return report
