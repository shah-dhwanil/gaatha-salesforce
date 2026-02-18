"""
Agent controller/router for FastAPI endpoints.

Exposes the chat endpoint (backed by the LangGraph orchestrator), chat
history retrieval, table schema inspection, and raw SQL execution.
"""

import traceback
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
import structlog

from api.agent.memory import ChatMemory
from api.agent.orchestrator import SalesAgentOrchestrator
from api.agent.schema import TABLE_SCHEMA_DICT
from api.dependencies import DatabasePoolDep
from api.models.agent import (
    AgentRequest,
    AgentResponse,
    ChatHistory,
    ChatSessionList,
    ExecuteQueryRequest,
)
from api.repository.utils import get_schema_name, set_search_path
from api.settings.settings import Settings, get_settings

logger = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/agents",
    tags=["Agents"],
    responses={
        400: {"description": "Bad Request - Invalid input or hierarchy"},
        404: {"description": "Resource Not Found"},
        500: {"description": "Internal Server Error"},
    },
)


# ------------------------------------------------------------------
# Chat history endpoints
# ------------------------------------------------------------------


@router.get("/{user_id}/chat")
async def get_chat(
    user_id: UUID,
    config: Settings = Depends(get_settings),
):
    """Retrieve the list of chat session IDs for a user."""
    logger.debug("[CONTROLLER] get_chat called", user_id=str(user_id))
    memory = ChatMemory(
        backend=config.AGENT.MEMORY_BACKEND,
        table_name=config.AGENT.TABLE_NAME,
        region=config.AWS.region_name,
    )
    sessions = await memory.get_user_sessions(user_id)
    logger.debug("[CONTROLLER] get_chat result", session_count=len(sessions))
    return ChatSessionList(sessions=sessions)


@router.get("/{user_id}/chat/{session_id}")
async def get_chat_session(
    user_id: UUID,
    session_id: str,
    config: Settings = Depends(get_settings),
):
    """Retrieve the full chat history for a specific session."""
    logger.debug(
        "[CONTROLLER] get_chat_session called",
        user_id=str(user_id),
        session_id=session_id,
    )
    memory = ChatMemory(
        backend=config.AGENT.MEMORY_BACKEND,
        table_name=config.AGENT.TABLE_NAME,
        region=config.AWS.region_name,
    )
    history = await memory.get_history(session_id)
    logger.debug(
        "[CONTROLLER] get_chat_session result",
        message_count=len(history),
    )
    return ChatHistory(
        items=[
            ChatHistory.ChatHistoryItem(role=msg.role, message=msg.content)
            for msg in history
        ]
    )


# ------------------------------------------------------------------
# Main chat endpoint
# ------------------------------------------------------------------


@router.post("/chat", response_model=AgentResponse)
async def chat_with_agent(
    request: AgentRequest,
    config: Settings = Depends(get_settings),
) -> AgentResponse:
    """Handle a chat interaction with the sales agent orchestrator."""
    logger.info(
        "[CONTROLLER] chat_with_agent called",
        user_id=str(request.user_id),
        session_id=request.session_id,
        company_id=str(request.company_id),
        message_preview=request.user_message[:200],
    )

    try:
        orchestrator = SalesAgentOrchestrator(config=config.AGENT)
        logger.debug("[CONTROLLER] Orchestrator created, processing message...")

        response = await orchestrator.process_message(
            user_message=request.user_message,
            user_id=request.user_id,
            session_id=request.session_id,
            user_context=None,
            company_id=request.company_id,
        )

        logger.info(
            "[CONTROLLER] Agent response received",
            session_id=request.session_id,
            sub_agent=response.sub_agent_used,
            needs_followup=response.needs_followup,
            tool_calls_count=len(response.tool_calls) if response.tool_calls else 0,
            response_preview=response.message[:200] if response.message else "(empty)",
        )

        return AgentResponse(
            session_id=request.session_id,
            message=response.message,
            needs_followup=response.needs_followup,
            followup_question=response.followup_question,
        )

    except Exception as exc:
        logger.error(
            "[CONTROLLER] chat_with_agent failed",
            user_id=str(request.user_id),
            session_id=request.session_id,
            error=str(exc),
            traceback=traceback.format_exc(),
        )
        raise


# ------------------------------------------------------------------
# Debug / introspection endpoints
# ------------------------------------------------------------------


@router.get("/debug/tools", response_model=dict)
async def debug_list_tools():
    """Debug endpoint: list all tools available to agents.

    Returns the tool names and their short descriptions for API tools
    (read + write) and SQL query tools.
    """
    from api.agent.tools.api_tools import READ_TOOLS, WRITE_TOOLS
    from api.agent.tools.query_tools import QUERY_TOOLS

    logger.info("[CONTROLLER] debug_list_tools called")

    def _info(tools: list) -> list[dict]:
        return [{"name": t.name, "description": (t.description or "")[:200]} for t in tools]

    read_info = _info(READ_TOOLS)
    write_info = _info(WRITE_TOOLS)
    sql_info = _info(QUERY_TOOLS)

    result = {
        "read_tools_count": len(read_info),
        "read_tools": read_info,
        "write_tools_count": len(write_info),
        "write_tools": write_info,
        "sql_tools_count": len(sql_info),
        "sql_tools": sql_info,
        "total_tools": len(read_info) + len(write_info) + len(sql_info),
    }

    logger.info(
        "[CONTROLLER] debug_list_tools result",
        read_count=len(read_info),
        write_count=len(write_info),
        sql_count=len(sql_info),
        total=result["total_tools"],
    )

    return result


# ------------------------------------------------------------------
# Utility endpoints (kept for backward compatibility / debugging)
# ------------------------------------------------------------------


@router.get("/table_schema", response_model=dict)
async def get_table_schema(
    table_name: Annotated[list[str], Query(...)],
):
    """Return the schema definition for the requested database tables."""
    logger.debug("[CONTROLLER] get_table_schema called", table_names=table_name)
    result: dict = {}
    for name in table_name:
        schema = TABLE_SCHEMA_DICT.get(name)
        result[name] = schema if schema else "Schema not found"
    return result


@router.post("/{company_id}/execute_query", response_model=list[dict])
async def execute_query(
    company_id: str,
    query: ExecuteQueryRequest,
    db_pool: DatabasePoolDep,
) -> list[dict]:
    """Execute a SQL query against a company's tenant schema."""
    logger.debug(
        "[CONTROLLER] execute_query called",
        company_id=company_id,
        sql_preview=query.sql_query[:200],
    )
    async with db_pool.acquire() as connection:
        await set_search_path(connection, get_schema_name(company_id))
        results = await connection.fetch(query.sql_query)
        logger.debug("[CONTROLLER] execute_query result", row_count=len(results))
        return [dict(record) for record in results]
