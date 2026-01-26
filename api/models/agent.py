from uuid import UUID
from typing import Optional
from pydantic import BaseModel, Field

class ChatSessionList(BaseModel):
    sessions: list[str] = Field(..., description="List of session IDs for the user")
class ChatHistory(BaseModel):
    class ChatHistoryItem(BaseModel):
        role: str = Field(..., description="Role of the message sender (user/agent)")
        message: str = Field(..., description="The content of the message")
    items: list[ChatHistoryItem] = Field(..., description="List of chat history items")


class AgentRequest(BaseModel):
    user_id:UUID = Field(..., description="Unique identifier for the user")
    session_id: str = Field(..., description="Unique identifier for the session")
    company_id: str = Field(..., description="Identifier for the company")
    user_message: str = Field(..., description="The message or query from the user")

class AgentResponse(BaseModel):
    role: str = Field(default="assistant", description="Role of the agent responding")
    session_id: str = Field(..., description="Unique identifier for the session")
    message: str = Field(..., description="The response message from the agent")
    needs_followup: bool = Field(False, description="Indicates if a follow-up question is needed")
    followup_question: Optional[str] = Field(None, description="The follow-up question if applicable")

class ExecuteQueryRequest(BaseModel):
    sql_query: str = Field(..., description="The SQL query to be executed")