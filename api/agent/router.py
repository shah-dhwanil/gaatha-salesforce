"""
Model Router for intelligent query complexity assessment.

Uses Haiku (fast, cheap) to analyze queries and determine:
1. Complexity level (simple vs complex)
2. Request type (query vs action)
3. Missing information that requires follow-up

This allows routing simple queries to Haiku and complex ones to Sonnet.
"""

from langchain_openai import ChatOpenAI
import json
import re
from dataclasses import dataclass
from typing import Literal, Optional

from api.settings.agent import AgentConfig
from api.agent.prompts.system import ROUTER_PROMPT


@dataclass
class QueryAnalysis:
    """Result of analyzing a user query."""
    complexity: float  # 0.0 to 1.0
    request_type: Literal["QUERY", "ACTION", "MIXED"]
    missing_info: list[str]
    summary: str
    suggested_tools: list[str]
    use_orchestrator: bool  # True = use Sonnet, False = use Haiku
    needs_followup: bool  # True if missing critical info


class ModelRouter:
    """
    Routes queries to appropriate model based on complexity.
    
    Simple queries (lookups, basic filtering) -> Haiku (fast, cheap)
    Complex queries (analytics, multi-step, actions) -> Sonnet (powerful)
    """
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.llm = ChatOpenAI(
            model= config.ORCHESTRATOR_MODEL,
            max_completion_tokens=config.ORCHESTRATOR_MAX_TOKENS,
            temperature=config.ORCHESTRATOR_TEMPERATURE,
            api_key=config.OPENAI_API_KEY,
        )
    
    async def analyze_query(self, user_message: str, conversation_history: Optional[list] = None) -> QueryAnalysis:
        """
        Analyze a user query to determine routing and requirements.
        
        Args:
            user_message: The user's input message
            conversation_history: Previous messages for context
            
        Returns:
            QueryAnalysis with complexity, type, and routing decision
        """
        # Use Haiku for fast analysis
        prompt = ROUTER_PROMPT.format(user_message=user_message)
        
        try:
            response = await self.llm.ainvoke(prompt)
            response_text = response.content
            analysis = self._parse_analysis(response_text)
            
            # Determine if we should use orchestrator model
            analysis.use_orchestrator = (
                analysis.complexity >= self.config.COMPLEXITY_THRESHOLD or
                analysis.request_type in ["ACTION", "MIXED"]
            )
            
            # Determine if follow-up is needed
            analysis.needs_followup = (
                len(analysis.missing_info) > 0 and
                self.config.ENABLE_FOLLOWUP_QUESTIONS and
                analysis.request_type == "ACTION"  # Only for actions
            )
            
            return analysis
            
        except Exception as e:
            # Fallback to orchestrator on analysis failure
            return QueryAnalysis(
                complexity=0.7,
                request_type="QUERY",
                missing_info=[],
                summary=user_message[:100],
                suggested_tools=[],
                use_orchestrator=True,
                needs_followup=False,
            )
    
    def _parse_analysis(self, response_text: str) -> QueryAnalysis:
        """Parse the JSON response from the router model."""
        try:
            # Extract JSON from response (may have markdown code blocks)
            json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = json.loads(response_text)
            
            return QueryAnalysis(
                complexity=float(data.get("complexity", 0.5)),
                request_type=data.get("type", "QUERY"),
                missing_info=data.get("missing_info", []),
                summary=data.get("summary", ""),
                suggested_tools=data.get("suggested_tools", []),
                use_orchestrator=False,  # Set later
                needs_followup=False,  # Set later
            )
        except (json.JSONDecodeError, ValueError):
            # Default analysis on parse failure
            return QueryAnalysis(
                complexity=0.5,
                request_type="QUERY",
                missing_info=[],
                summary="",
                suggested_tools=[],
                use_orchestrator=False,
                needs_followup=False,
            )
    
    def get_model_for_query(self, analysis: QueryAnalysis) -> str:
        """Get the appropriate model ID based on analysis."""
        if analysis.use_orchestrator:
            return self.config.ORCHESTRATOR_MODEL
        return self.config.SIMPLE_MODEL

