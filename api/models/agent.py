from typing import Optional
from pydantic import BaseModel, Field


class AgentRequest(BaseModel):
    session_id: str = Field(..., description="Unique identifier for the session")
    company_id: str = Field(..., description="Identifier for the company")
    user_message: str = Field(..., description="The message or query from the user")

class AgentResponse(BaseModel):
    session_id: str = Field(..., description="Unique identifier for the session")
    message: str = Field(..., description="The response message from the agent")
    needs_followup: bool = Field(False, description="Indicates if a follow-up question is needed")
    followup_question: Optional[str] = Field(None, description="The follow-up question if applicable")

class ExecuteQueryRequest(BaseModel):
    sql_query: str = Field(..., description="The SQL query to be executed")