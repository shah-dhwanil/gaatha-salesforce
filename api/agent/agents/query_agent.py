"""
Query Sub-Agent -- handles read-only data retrieval questions.

Has access to **two categories of tools**:

1. REST API tools (explicit HTTP tools) -- for straightforward list/get
   operations that map directly to existing GET endpoints.
2. SQL tools -- ``get_table_schema`` + ``execute_read_query`` for complex
   analytics that require aggregation, joins, date arithmetic, etc.

The agent is instructed to prefer API tools over SQL whenever the API can
answer the question, falling back to SQL for complex analytical queries.

The agent is implemented as a LangGraph ``create_react_agent`` so it can
autonomously decide when to call tools and when to respond.
"""

from __future__ import annotations

import traceback

from langchain_core.messages import BaseMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from api.agent.prompts import QUERY_AGENT_SYSTEM_PROMPT
from api.agent.state import AgentState
from api.agent.tools.api_tools import READ_TOOLS, set_company_id
from api.agent.tools.query_tools import QUERY_TOOLS
from api.settings.agent import AgentConfig

import structlog

logger = structlog.get_logger(__name__)


async def build_query_agent(config: AgentConfig):
    """Build a compiled LangGraph ReAct agent for read-only queries.

    The agent receives both the REST API read tools and the SQL tools
    so it can pick the most appropriate approach for each question.
    """
    logger.info(
        "[QUERY_AGENT] Building query agent",
        model=config.SIMPLE_MODEL,
        temperature=config.SIMPLE_TEMPERATURE,
        max_tokens=config.SIMPLE_MAX_TOKENS,
    )

    llm = ChatOpenAI(
        model=config.SIMPLE_MODEL,
        temperature=config.SIMPLE_TEMPERATURE,
        max_tokens=config.SIMPLE_MAX_TOKENS,
        api_key=config.OPENAI_API_KEY,
    )

    # Combine: API read tools first (preferred), then SQL tools (fallback)
    all_tools = list(READ_TOOLS) + list(QUERY_TOOLS)

    logger.info(
        "[QUERY_AGENT] Tools available",
        total_count=len(all_tools),
        api_tool_count=len(READ_TOOLS),
        sql_tool_count=len(QUERY_TOOLS),
        all_tool_names=[t.name for t in all_tools],
    )

    agent = create_react_agent(
        model=llm,
        tools=all_tools,
        prompt=QUERY_AGENT_SYSTEM_PROMPT,
    )
    logger.debug("[QUERY_AGENT] ReAct agent compiled")
    return agent


async def run_query_agent(state: AgentState, config: AgentConfig) -> dict:
    """Execute the query sub-agent and return state updates."""
    logger.info(
        "[QUERY_AGENT] Starting query agent execution",
        session_id=state.get("session_id"),
        company_id=state.get("company_id"),
        message_count=len(state.get("messages", [])),
    )

    try:
        agent = await build_query_agent(config)
    except Exception as exc:
        logger.error(
            "[QUERY_AGENT] Failed to build query agent",
            error=str(exc),
            traceback=traceback.format_exc(),
        )
        return {
            "final_response": f"I'm sorry, I encountered an error setting up the query agent: {exc}",
            "sub_agent_used": "query_agent",
            "tool_calls": [],
            "needs_followup": False,
            "followup_question": None,
        }

    # Inject company_id into context so every tool picks it up automatically
    set_company_id(state["company_id"])

    for i, msg in enumerate(state["messages"]):
        logger.debug(
            "[QUERY_AGENT] Input message",
            index=i,
            type=type(msg).__name__,
            content_preview=str(msg.content)[:150] if hasattr(msg, "content") else "N/A",
        )

    try:
        logger.debug("[QUERY_AGENT] Invoking ReAct agent...")
        result = await agent.ainvoke({"messages": state["messages"]})
        logger.debug("[QUERY_AGENT] ReAct agent invocation complete")
    except Exception as exc:
        logger.error(
            "[QUERY_AGENT] Agent execution failed",
            error=str(exc),
            traceback=traceback.format_exc(),
        )
        return {
            "final_response": f"I'm sorry, an error occurred while processing your query: {exc}",
            "sub_agent_used": "query_agent",
            "tool_calls": [],
            "needs_followup": False,
            "followup_question": None,
        }

    result_messages: list[BaseMessage] = result["messages"]
    final_message = ""
    tool_calls_log: list[dict] = []

    logger.debug(
        "[QUERY_AGENT] Processing result messages",
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
                        "[QUERY_AGENT] Tool call recorded",
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

    logger.info(
        "[QUERY_AGENT] Query agent completed",
        tool_calls_count=len(tool_calls_log),
        tool_names_used=[tc["tool"] for tc in tool_calls_log],
        response_length=len(final_message),
        response_preview=final_message[:200] if final_message else "(empty)",
    )

    return {
        "messages": result_messages,
        "final_response": final_message,
        "sub_agent_used": "query_agent",
        "tool_calls": tool_calls_log,
        "needs_followup": False,
        "followup_question": None,
    }
