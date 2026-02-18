"""
Action Sub-Agent -- handles create / update / delete operations.

Uses ``gpt-4.1-mini`` (configurable) with explicit HTTP-based tools that
map to the REST API endpoints. The agent can ask follow-up questions when
required information is missing.

The agent is implemented as a LangGraph ``create_react_agent`` so it can
autonomously decide when to call tools, when to ask follow-ups, and
when to respond.
"""

from __future__ import annotations

import traceback

from langchain_core.messages import BaseMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from api.agent.prompts import ACTION_AGENT_SYSTEM_PROMPT
from api.agent.state import AgentState
from api.agent.tools.api_tools import ALL_API_TOOLS, set_company_id
from api.agent.tools.query_tools import QUERY_TOOLS
from api.settings.agent import AgentConfig

import structlog

logger = structlog.get_logger(__name__)

_FOLLOWUP_INDICATORS = [
    "could you please",
    "can you provide",
    "please provide",
    "please specify",
    "what is the",
    "what are the",
    "which one",
    "could you clarify",
    "i need more information",
    "please confirm",
    "would you like",
    "do you want",
    "let me know",
    "can you confirm",
]


def _looks_like_followup(text: str) -> bool:
    """Heuristic check whether the agent response is asking a follow-up."""
    lower = text.lower()
    return any(indicator in lower for indicator in _FOLLOWUP_INDICATORS) and "?" in text


async def build_action_agent(config: AgentConfig):
    """Build a compiled LangGraph ReAct agent for CRUD operations.

    The agent gets all API tools (read + write) AND the SQL query tools
    so it can look up entities before performing mutations.
    """
    logger.info(
        "[ACTION_AGENT] Building action agent",
        model=config.COMPLEX_MODEL,
        temperature=config.COMPLEX_TEMPERATURE,
        max_tokens=config.COMPLEX_MAX_TOKENS,
    )

    llm = ChatOpenAI(
        model=config.COMPLEX_MODEL,
        temperature=config.COMPLEX_TEMPERATURE,
        max_tokens=config.COMPLEX_MAX_TOKENS,
        api_key=config.OPENAI_API_KEY,
    )

    # All API tools (read + write) plus SQL tools for lookups
    all_tools = list(ALL_API_TOOLS) + list(QUERY_TOOLS)

    logger.info(
        "[ACTION_AGENT] Tools available",
        total_count=len(all_tools),
        api_tool_count=len(ALL_API_TOOLS),
        sql_tool_count=len(QUERY_TOOLS),
        all_tool_names=[t.name for t in all_tools],
    )

    agent = create_react_agent(
        model=llm,
        tools=all_tools,
        prompt=ACTION_AGENT_SYSTEM_PROMPT,
    )
    logger.debug("[ACTION_AGENT] ReAct agent compiled")
    return agent


async def run_action_agent(state: AgentState, config: AgentConfig) -> dict:
    """Execute the action sub-agent and return state updates."""
    logger.info(
        "[ACTION_AGENT] Starting action agent execution",
        session_id=state.get("session_id"),
        company_id=state.get("company_id"),
        message_count=len(state.get("messages", [])),
    )

    try:
        agent = await build_action_agent(config)
    except Exception as exc:
        logger.error(
            "[ACTION_AGENT] Failed to build action agent",
            error=str(exc),
            traceback=traceback.format_exc(),
        )
        return {
            "final_response": f"I'm sorry, I encountered an error setting up the action agent: {exc}",
            "sub_agent_used": "action_agent",
            "tool_calls": [],
            "needs_followup": False,
            "followup_question": None,
        }

    # Inject company_id into context so every tool picks it up automatically
    set_company_id(state["company_id"])

    for i, msg in enumerate(state["messages"]):
        logger.debug(
            "[ACTION_AGENT] Input message",
            index=i,
            type=type(msg).__name__,
            content_preview=str(msg.content)[:150] if hasattr(msg, "content") else "N/A",
        )

    try:
        logger.debug("[ACTION_AGENT] Invoking ReAct agent...")
        result = await agent.ainvoke({"messages": state["messages"]})
        logger.debug("[ACTION_AGENT] ReAct agent invocation complete")
    except Exception as exc:
        logger.error(
            "[ACTION_AGENT] Agent execution failed",
            error=str(exc),
            traceback=traceback.format_exc(),
        )
        return {
            "final_response": f"I'm sorry, an error occurred while processing your action: {exc}",
            "sub_agent_used": "action_agent",
            "tool_calls": [],
            "needs_followup": False,
            "followup_question": None,
        }

    result_messages: list[BaseMessage] = result["messages"]
    final_message = ""
    tool_calls_log: list[dict] = []

    logger.debug(
        "[ACTION_AGENT] Processing result messages",
        result_message_count=len(result_messages),
    )

    for msg in result_messages:
        if isinstance(msg, AIMessage):
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_calls_log.append({
                        "tool": tc["name"],
                        "args": tc["args"],
                    })
                    logger.debug(
                        "[ACTION_AGENT] Tool call recorded",
                        tool=tc["name"],
                        args_preview=str(tc["args"])[:200],
                    )
            if msg.content and not msg.tool_calls:
                final_message = msg.content

    if not final_message:
        for msg in reversed(result_messages):
            if isinstance(msg, AIMessage) and msg.content:
                final_message = msg.content
                break

    needs_followup = False
    followup_question = None

    if config.ENABLE_FOLLOWUP_QUESTIONS and _looks_like_followup(final_message):
        needs_followup = True
        followup_question = final_message
        logger.info(
            "[ACTION_AGENT] Follow-up question detected",
            followup_preview=final_message[:200],
        )

    logger.info(
        "[ACTION_AGENT] Action agent completed",
        tool_calls_count=len(tool_calls_log),
        tool_names_used=[tc["tool"] for tc in tool_calls_log],
        response_length=len(final_message),
        response_preview=final_message[:200] if final_message else "(empty)",
        needs_followup=needs_followup,
    )

    return {
        "messages": result_messages,
        "final_response": final_message,
        "sub_agent_used": "action_agent",
        "tool_calls": tool_calls_log,
        "needs_followup": needs_followup,
        "followup_question": followup_question,
    }
