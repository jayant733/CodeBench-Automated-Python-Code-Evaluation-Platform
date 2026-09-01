from __future__ import annotations

from typing import Any

from ai_code_evaluator.providers import ModelProvider
from ai_code_evaluator.analysis import SourceAnalysis
from .base import BaseAgent
from .models import AgentConfig, AgentMessage, AgentResponse, SecurityFinding, SecurityVerdict


class SecurityAgent(BaseAgent):
    """Checks the source code for security issues and malicious patterns."""

    def __init__(self, config: AgentConfig, provider: ModelProvider) -> None:
        super().__init__(
            agent_id="security",
            role="Security Engineer",
            system_prompt=(
                "You are an expert Security Engineer. Review the provided source code and its AST analysis "
                "for potential security risks, sandbox escape attempts, resource abuse (fork bombs, "
                "memory bombs), or data exfiltration attempts. Output a structured SecurityVerdict. "
                "If the code is purely algorithmic and safe, set `safe` to true."
            ),
            config=config,
            provider=provider,
        )

    async def invoke(self, context: dict[str, Any]) -> AgentResponse:
        source_code: str = context["source_code"]
        analysis: SourceAnalysis | None = context.get("analysis")
        
        prompt = f"Submission:\n```python\n{source_code}\n```\n\n"
        
        if analysis:
            prompt += (
                f"AST Analysis:\n"
                f"- Syntax valid: {analysis.syntax_valid}\n"
                f"- Prohibited imports found: {analysis.prohibited_imports}\n\n"
            )
            
        prompt += "Please review and output a structured SecurityVerdict."

        self.memory.append(AgentMessage(role="user", content=prompt))
        
        response = await self._call_llm(
            messages=self.memory.messages,
            response_format=SecurityVerdict,
        )
        
        # Override LLM if AST analysis found prohibited imports
        if analysis and analysis.prohibited_imports:
            verdict: SecurityVerdict = response.structured_output
            verdict.safe = False
            verdict.risk_level = "high"
            
            # Ensure the finding is present
            already_found = any(f.category == "prohibited_import" for f in verdict.findings)
            if not already_found:
                verdict.findings.append(
                    SecurityFinding(
                        category="prohibited_import",
                        severity="critical",
                        evidence=f"AST analysis found: {analysis.prohibited_imports}",
                        recommendation="Remove all networking and system-level imports."
                    )
                )
                
        return response
