"""
Agent configuration settings using Pydantic.
"""
from pydantic import BaseModel, Field
class AgentConfig(BaseModel):
    ORCHESTRATOR_MODEL: str = Field(
        default="gpt-4o",
        description="The model used for the agent orchestrator",
    )
    ORCHESTRATOR_MAX_TOKENS: int = Field(
        default=1024,
        description="Maximum tokens for the agent orchestrator model",
    )
    ORCHESTRATOR_TEMPERATURE: float = Field(
        default=0.0,
        description="Temperature setting for the agent orchestrator model",
    )
    SIMPLE_MODEL: str = Field(
        default="gpt-4o",
        description="The model used for simple agent tasks",
    )
    SIMPLE_MAX_TOKENS: int = Field(
        default=1024,
        description="Maximum tokens for the simple agent model",
    )
    SIMPLE_TEMPERATURE: float = Field(
        default=0.0,
        description="Temperature setting for the simple agent model",
    )
    COMPLEXITY_THRESHOLD: float = Field(
        default=0.7,
        description="Threshold for task complexity to decide agent type",
    )
    BACKEND_URL: str = Field(
        default="http://localhost:8000",
        description="URL of the agent backend service",
    )
    ENABLE_FOLLOWUP_QUESTIONS: bool = Field(
        default=True,
        description="Enable follow-up questions in agent interactions",
    )
    MAX_FOLLOWUP_QUESTIONS: int = Field(
        default=3,
        description="Maximum number of follow-up questions allowed",
    )
    MEMORY_BACKEND: str = Field(
        default="in-memory",
        description="Type of memory backend for the agent",
    )
    MEMORY_RETENTION_DAYS: int = Field(
        default=7,
        description="Number of days to retain memory data",
    )
    TABLE_NAME:str = Field(
        default="agent_memory",
        description="Database table name for storing agent memory",
    )
    OPENAI_API_KEY: str = Field(
        default="",
        description="API key for accessing OpenAPI services",
    )