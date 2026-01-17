from fastapi import Depends
from api.models.agent import AgentResponse
from api.models.agent import AgentRequest
from fastapi import APIRouter
from api.agent.orchestrator import SalesAgentOrchestrator
from api.settings.settings import Settings,get_settings
import structlog
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


@router.post("/chat",response_model=AgentResponse)
async def chat_with_agent(request:AgentRequest,config: Settings = Depends(get_settings)) -> AgentResponse:
    """Endpoint to handle chat interactions with the sales agent."""

    orchestrator = SalesAgentOrchestrator(config=config.AGENT)
    response = await orchestrator.process_message(request.user_message, request.session_id,None,request.company_id)
    return AgentResponse(session_id=request.session_id,message=response.message,needs_followup=response.needs_followup,followup_question=response.followup_question)