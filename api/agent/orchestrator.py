"""
Sales Agent Orchestrator -- the main LangGraph StateGraph.

Flow
----
1. ``load_history``    -- fetch recent chat from DynamoDB, inject as context
2. ``classify_intent`` -- use gpt-5-mini to decide query / action / followup
3. Conditional routing:
   - "query"           -> ``run_query``   -> ``save_memory`` -> END
   - "action"          -> ``run_action``  -> ``save_memory`` -> END
   - "followup_needed" -> ``save_memory`` -> END  (returns follow-up question)
4. ``save_memory``     -- persist the Q+A pair to DynamoDB
"""

from __future__ import annotations

import json
import traceback
from dataclasses import dataclass
from typing import Any

import structlog
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from api.agent.agents.action_agent import run_action_agent
from api.agent.agents.query_agent import run_query_agent
from api.agent.memory import ChatMemory
from api.agent.prompts import ORCHESTRATOR_SYSTEM_PROMPT
from api.agent.state import AgentState
from api.settings.agent import AgentConfig

logger = structlog.get_logger(__name__)


@dataclass
class OrchestratorResponse:
    """Value object returned by ``SalesAgentOrchestrator.process_message``."""

    message: str
    needs_followup: bool = False
    followup_question: str | None = None
    sub_agent_used: str | None = None
    tool_calls: list[dict] | None = None


class SalesAgentOrchestrator:
    """High-level entry-point that builds and runs the LangGraph workflow."""

    def __init__(self, config: AgentConfig) -> None:
        self._config = config
        logger.info(
            "[ORCHESTRATOR] Initializing orchestrator",
            orchestrator_model=config.ORCHESTRATOR_MODEL,
            simple_model=config.SIMPLE_MODEL,
            complex_model=config.COMPLEX_MODEL,
            memory_backend=config.MEMORY_BACKEND,
            backend_url=config.BACKEND_URL,
        )
        self._memory = ChatMemory(
            backend=config.MEMORY_BACKEND,
            table_name=config.TABLE_NAME,
        )
        self._graph = self._build_graph()
        logger.debug("[ORCHESTRATOR] Initialization complete")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def process_message(
        self,
        user_message: str,
        user_id: Any,
        session_id: str,
        user_context: Any | None,
        company_id: str,
    ) -> OrchestratorResponse:
        """Process a single user message through the orchestrator graph."""
        logger.info(
            "[ORCHESTRATOR] Processing message",
            user_id=str(user_id),
            session_id=session_id,
            company_id=str(company_id),
            message_preview=user_message[:200],
        )

        initial_state: AgentState = {
            "messages": [HumanMessage(content=user_message)],
            "user_id": str(user_id),
            "session_id": session_id,
            "company_id": str(company_id),
            "query_type": None,
            "needs_followup": False,
            "followup_question": None,
            "sub_agent_used": None,
            "tool_calls": [],
            "final_response": None,
        }

        try:
            # Run the graph
            logger.debug("[ORCHESTRATOR] Invoking LangGraph state graph...")
            final_state = await self._graph.ainvoke(initial_state)
            logger.debug("[ORCHESTRATOR] LangGraph invocation complete")
        except Exception as exc:
            logger.error(
                "[ORCHESTRATOR] Graph execution failed",
                error=str(exc),
                traceback=traceback.format_exc(),
            )
            return OrchestratorResponse(
                message=f"I'm sorry, an internal error occurred: {exc}",
            )

        response = OrchestratorResponse(
            message=final_state.get("final_response") or "I'm sorry, I couldn't process your request.",
            needs_followup=final_state.get("needs_followup", False),
            followup_question=final_state.get("followup_question"),
            sub_agent_used=final_state.get("sub_agent_used"),
            tool_calls=final_state.get("tool_calls"),
        )

        logger.info(
            "[ORCHESTRATOR] Message processing complete",
            sub_agent_used=response.sub_agent_used,
            needs_followup=response.needs_followup,
            tool_calls_count=len(response.tool_calls) if response.tool_calls else 0,
            response_preview=response.message[:200],
        )

        return response

    # ------------------------------------------------------------------
    # Graph construction
    # ------------------------------------------------------------------

    def _build_graph(self) -> Any:
        """Construct and compile the LangGraph StateGraph."""
        logger.debug("[ORCHESTRATOR] Building LangGraph StateGraph")
        graph = StateGraph(AgentState)

        # Add nodes
        graph.add_node("load_history", self._load_history)
        graph.add_node("classify_intent", self._classify_intent)
        graph.add_node("run_query", self._run_query_agent)
        graph.add_node("run_action", self._run_action_agent)
        graph.add_node("save_memory", self._save_memory)

        # Edges
        graph.set_entry_point("load_history")
        graph.add_edge("load_history", "classify_intent")

        # Conditional routing after classification
        graph.add_conditional_edges(
            "classify_intent",
            self._route_after_classification,
            {
                "query": "run_query",
                "action": "run_action",
                "followup_needed": "save_memory",
            },
        )

        graph.add_edge("run_query", "save_memory")
        graph.add_edge("run_action", "save_memory")
        graph.add_edge("save_memory", END)

        compiled = graph.compile()
        logger.debug("[ORCHESTRATOR] StateGraph compiled successfully")
        return compiled

    # ------------------------------------------------------------------
    # Node implementations
    # ------------------------------------------------------------------

    async def _load_history(self, state: AgentState) -> dict:
        """Load recent chat history and prepend as context messages."""
        logger.debug(
            "[ORCHESTRATOR] Loading chat history",
            session_id=state["session_id"],
        )

        try:
            history_messages = await self._memory.get_history(
                state["session_id"], limit=10
            )
            logger.debug(
                "[ORCHESTRATOR] History loaded",
                history_count=len(history_messages),
            )
        except Exception as exc:
            logger.error(
                "[ORCHESTRATOR] Failed to load history, continuing without it",
                error=str(exc),
            )
            history_messages = []

        context_msgs: list[Any] = []
        for msg in history_messages:
            if msg.role == "user":
                context_msgs.append(HumanMessage(content=msg.content))
            else:
                context_msgs.append(AIMessage(content=msg.content))

        # Prepend history before the current user message
        current_messages = list(state["messages"])
        all_messages = context_msgs + current_messages

        logger.debug(
            "[ORCHESTRATOR] Messages prepared for classification",
            history_msgs=len(context_msgs),
            current_msgs=len(current_messages),
            total_msgs=len(all_messages),
        )

        return {"messages": all_messages}

    async def _classify_intent(self, state: AgentState) -> dict:
        """Use the orchestrator LLM to classify user intent."""
        logger.debug(
            "[ORCHESTRATOR] Classifying intent",
            model=self._config.ORCHESTRATOR_MODEL,
            message_count=len(state["messages"]),
        )

        llm = ChatOpenAI(
            model=self._config.ORCHESTRATOR_MODEL,
            temperature=self._config.ORCHESTRATOR_TEMPERATURE,
            max_tokens=self._config.ORCHESTRATOR_MAX_TOKENS,
            api_key=self._config.OPENAI_API_KEY,
        )

        classification_messages = [
            SystemMessage(content=ORCHESTRATOR_SYSTEM_PROMPT),
            *state["messages"],
        ]

        try:
            response = await llm.ainvoke(classification_messages)
            content = response.content.strip()
            logger.debug(
                "[ORCHESTRATOR] Raw classifier response",
                raw_content=content[:500],
            )
        except Exception as exc:
            logger.error(
                "[ORCHESTRATOR] LLM classification call failed",
                error=str(exc),
                traceback=traceback.format_exc(),
            )
            return {"query_type": "query"}

        # Parse the JSON response
        try:
            # Handle possible markdown code-block wrapping
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            parsed = json.loads(content)
            query_type = parsed.get("query_type", "query")
            followup_q = parsed.get("followup_question")
        except (json.JSONDecodeError, IndexError) as parse_exc:
            logger.warning(
                "[ORCHESTRATOR] Failed to parse classifier output, defaulting to query",
                raw_output=content,
                parse_error=str(parse_exc),
            )
            query_type = "query"
            followup_q = None

        # Safety net: override "followup_needed" when the user message is
        # clearly a query or action.  This prevents the LLM from being
        # overly cautious and asking "do you want me to…?" for obvious
        # requests like "list all areas".
        if query_type == "followup_needed":
            user_text = self._get_last_user_text(state)
            override = self._heuristic_classify(user_text)
            if override is not None:
                logger.warning(
                    "[ORCHESTRATOR] Overriding followup_needed with heuristic",
                    original="followup_needed",
                    override=override,
                    user_text=user_text[:200],
                )
                query_type = override
                followup_q = None

        logger.info(
            "[ORCHESTRATOR] Intent classified",
            query_type=query_type,
            has_followup=followup_q is not None,
        )

        updates: dict[str, Any] = {"query_type": query_type}

        if query_type == "followup_needed" and followup_q:
            updates["needs_followup"] = True
            updates["followup_question"] = followup_q
            updates["final_response"] = followup_q
            updates["sub_agent_used"] = "orchestrator"
            logger.info(
                "[ORCHESTRATOR] Routing to follow-up",
                followup_question=followup_q[:200],
            )

        return updates

    # ------------------------------------------------------------------
    # Heuristic helpers
    # ------------------------------------------------------------------

    # Keywords that strongly signal a "query" intent
    _QUERY_KEYWORDS = [
        "list", "show", "get", "give", "fetch", "display", "what",
        "which", "how many", "how much", "tell me", "find", "search",
        "view", "see", "check", "look up", "lookup", "retrieve",
        "count", "total", "top", "bottom", "lowest", "highest",
        "best", "worst", "average", "compare", "report", "summary",
        "details", "detail", "info", "status", "stock",
    ]

    # Keywords that strongly signal an "action" intent
    _ACTION_KEYWORDS = [
        "create", "add", "insert", "make", "new", "update", "edit",
        "change", "modify", "set", "increase", "decrease", "delete",
        "remove", "assign", "unassign", "enable", "disable", "activate",
        "deactivate", "apply", "upload", "import",
    ]

    @staticmethod
    def _get_last_user_text(state: AgentState) -> str:
        """Extract the last user message text from the state."""
        for msg in reversed(state.get("messages", [])):
            if isinstance(msg, HumanMessage) and msg.content:
                return msg.content
        return ""

    @classmethod
    def _heuristic_classify(cls, user_text: str) -> str | None:
        """Return 'query' or 'action' if the text clearly matches, else None."""
        if not user_text:
            return None
        lower = user_text.lower().strip()

        # Check action keywords first (they're more specific)
        for kw in cls._ACTION_KEYWORDS:
            if lower.startswith(kw) or f" {kw} " in f" {lower} ":
                return "action"

        # Then check query keywords
        for kw in cls._QUERY_KEYWORDS:
            if lower.startswith(kw) or f" {kw} " in f" {lower} ":
                return "query"

        # If the message ends with "?" it's very likely a query
        if lower.endswith("?"):
            return "query"

        return None

    @staticmethod
    def _route_after_classification(state: AgentState) -> str:
        """Return the routing key based on the classified intent."""
        route = state.get("query_type") or "query"
        logger.info("[ORCHESTRATOR] Routing decision", route=route)
        return route

    async def _run_query_agent(self, state: AgentState) -> dict:
        """Delegate to the query sub-agent."""
        logger.info("[ORCHESTRATOR] Delegating to query sub-agent")
        return await run_query_agent(state, self._config)

    async def _run_action_agent(self, state: AgentState) -> dict:
        """Delegate to the action sub-agent."""
        logger.info("[ORCHESTRATOR] Delegating to action sub-agent")
        return await run_action_agent(state, self._config)

    async def _save_memory(self, state: AgentState) -> dict:
        """Persist the interaction to DynamoDB."""
        user_message = ""
        for msg in state["messages"]:
            if isinstance(msg, HumanMessage):
                user_message = msg.content  # last user message

        assistant_response = state.get("final_response") or ""

        logger.debug(
            "[ORCHESTRATOR] Saving memory",
            session_id=state["session_id"],
            user_message_preview=user_message[:100],
            assistant_response_preview=assistant_response[:100],
            sub_agent=state.get("sub_agent_used"),
            tool_calls_count=len(state.get("tool_calls", [])),
        )

        try:
            await self._memory.save_interaction(
                session_id=state["session_id"],
                user_id=state["user_id"],
                user_message=user_message,
                assistant_response=assistant_response,
                tool_calls=state.get("tool_calls"),
                sub_agent_used=state.get("sub_agent_used") or "",
                needs_followup=state.get("needs_followup", False),
                followup_question=state.get("followup_question"),
            )
            logger.debug("[ORCHESTRATOR] Memory saved successfully")
        except Exception as exc:
            logger.error(
                "[ORCHESTRATOR] Failed to save memory",
                error=str(exc),
                traceback=traceback.format_exc(),
            )

        return {}
