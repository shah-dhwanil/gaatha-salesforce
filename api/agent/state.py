"""
LangGraph agent state definition.

Defines the shared state that flows through all nodes of the orchestrator
graph -- from intent classification through sub-agent execution to memory
persistence.
"""

from __future__ import annotations

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    """Shared state for the LangGraph orchestrator graph.

    Attributes:
        messages: Conversation message history (managed by ``add_messages`` reducer).
        user_id: UUID of the requesting user.
        session_id: Chat session identifier.
        company_id: Company UUID (determines the tenant schema).
        query_type: Classification result -- ``"query"`` or ``"action"``.
        needs_followup: Whether the agent needs to ask the user a follow-up question.
        followup_question: The follow-up question text (if any).
        sub_agent_used: Which sub-agent handled the request (``"query_agent"`` | ``"action_agent"``).
        tool_calls: List of tool invocations made during processing.
        final_response: The final user-facing response text.
    """

    messages: Annotated[list[BaseMessage], add_messages]
    user_id: str
    session_id: str
    company_id: str
    query_type: str | None
    needs_followup: bool
    followup_question: str | None
    sub_agent_used: str | None
    tool_calls: list[dict]
    final_response: str | None
