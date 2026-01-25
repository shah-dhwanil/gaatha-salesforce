"""
Main Agent Orchestrator.

Coordinates:
1. Query analysis and routing (via ModelRouter)
2. Tool selection and execution
3. Follow-up question generation when needed
4. Response formatting
5. Persistent chat memory storage
"""

from uuid import UUID
from langchain_openai import ChatOpenAI
import json
from dataclasses import dataclass, field
from typing import Any, Optional
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.tools import tool as langchain_tool

from api.settings.agent import AgentConfig
from api.agent.router import ModelRouter, QueryAnalysis
from api.agent.prompts.system import SYSTEM_PROMPT, FOLLOWUP_PROMPT
from api.agent.tools import ALL_TOOLS
from api.agent.tools.base import ToolDefinition, ToolExecutor
from api.agent.memory import ChatMemory, ChatMessage


@dataclass
class AgentResponse:
    """Response from the agent."""
    message: str
    needs_followup: bool = False
    followup_question: Optional[str] = None
    tools_used: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class SalesAgentOrchestrator:
    """
    Main orchestrator for the Sales Management AI Agent.
    
    Handles:
    - Query routing between Haiku and Sonnet
    - Tool execution via FastAPI backend
    - Conversation management with persistent storage
    - Follow-up question generation
    """
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.company_id: Optional[UUID] = None
        self.router = ModelRouter(self.config)
        print(self.config)
        # Initialize LangChain models
        self.orchestrator_llm = ChatOpenAI(
            model=self.config.ORCHESTRATOR_MODEL,
            temperature=self.config.ORCHESTRATOR_TEMPERATURE,
            max_tokens=self.config.ORCHESTRATOR_MAX_TOKENS,
            api_key=self.config.OPENAI_API_KEY,
        )
        
        self.simple_llm = ChatOpenAI(
            model=self.config.SIMPLE_MODEL,
            temperature=self.config.SIMPLE_TEMPERATURE,
            max_tokens=self.config.SIMPLE_MAX_TOKENS,
            api_key=self.config.OPENAI_API_KEY,
        )
        
        # Tool executor (initialized with company context)
        self.tool_executor: Optional[ToolExecutor] = None
        
        # Available tools
        self.tools = {tool.name: tool for tool in ALL_TOOLS}
        
        # Persistent memory (DynamoDB in Lambda, in-memory locally)
        self.memory = ChatMemory(
            backend=self.config.MEMORY_BACKEND,
            table_name=self.config.TABLE_NAME,
            ttl_days=self.config.MEMORY_RETENTION_DAYS,
        )
        
        # Follow-up tracking (in-memory, resets on cold start)
        self.followup_counts: dict[str, int] = {}
    
    def _get_tool_executor(self, auth_token: Optional[str] = None) -> ToolExecutor:
        """Get or create tool executor."""
        if self.tool_executor is None:
            self.tool_executor = ToolExecutor(
                backend_url=self.config.BACKEND_URL,
                company_id=self.company_id or None,
                auth_token=auth_token,
            )
        return self.tool_executor
    
    def _format_tools_for_langchain(self) -> list:
        """Format tools for LangChain."""
        from langchain_core.tools import StructuredTool
        from pydantic import BaseModel, Field, create_model
        
        langchain_tools = []
        for tool_def in self.tools.values():
            # Create a Pydantic model for the tool's input schema
            fields = {}
            for param in tool_def.parameters:
                field_type = str
                if param.type == "integer":
                    field_type = int
                elif param.type == "number":
                    field_type = float
                elif param.type == "boolean":
                    field_type = bool
                elif param.type == "array":
                    # Handle array types - get item type from items dict
                    item_type = str
                    if param.items:
                        item_type_str = param.items.get("type", "string")
                        if item_type_str == "integer":
                            item_type = int
                        elif item_type_str == "number":
                            item_type = float
                        elif item_type_str == "boolean":
                            item_type = bool
                    field_type = list[item_type]
                elif param.type == "object":
                    field_type = dict
                
                if param.required:
                    fields[param.name] = (field_type, Field(description=param.description))
                else:
                    fields[param.name] = (Optional[field_type], Field(default=None, description=param.description))
            
            InputModel = create_model(f"{tool_def.name}_input", **fields)
            
            # Create a placeholder async function for the tool
            async def placeholder_coroutine(**kwargs):
                return kwargs
            
            # Create the LangChain tool
            lc_tool = StructuredTool(
                name=tool_def.name,
                description=tool_def.description,
                args_schema=InputModel,
                coroutine=placeholder_coroutine,
            )
            langchain_tools.append(lc_tool)
        
        return langchain_tools
    
    async def process_message(
        self,
        user_message: str,
        session_id: str = "default",
        auth_token: Optional[str] = None,
        company_id: Optional[str] = None,
    ) -> AgentResponse:
        """
        Process a user message and return agent response.
        
        Args:
            user_message: The user's input
            session_id: Session ID for conversation tracking
            auth_token: JWT token for backend authentication
            company_id: Override company ID for this request
            
        Returns:
            AgentResponse with message and metadata
        """
        # Override company ID if provided
        if company_id:
            self.company_id = company_id
        
        # Initialize follow-up count if needed
        if session_id not in self.followup_counts:
            self.followup_counts[session_id] = 0
        
        # Load conversation history from persistent storage
        history = await self.memory.get_history(session_id, limit=10)
        print("History:", history)
        # Analyze query for routing (pass history for context)
        analysis = await self.router.analyze_query(user_message, history)
        
        # Check if follow-up is needed
        if analysis.needs_followup and self.followup_counts[session_id] < self.config.MAX_FOLLOWUP_QUESTIONS:
            followup = await self._generate_followup(user_message, analysis.missing_info)
            self.followup_counts[session_id] += 1
            
            # Store in persistent memory
            await self.memory.save(session_id, "user", user_message)
            await self.memory.save(session_id, "assistant", followup)
            
            return AgentResponse(
                message=followup,
                needs_followup=True,
                followup_question=followup,
                metadata={"analysis": analysis.__dict__}
            )
        
        # Reset follow-up count on new complete query
        self.followup_counts[session_id] = 0
        
        # Get appropriate model
        model_id = self.router.get_model_for_query(analysis)
        
        # Build messages for Bedrock (from history)
        messages = self._build_messages_from_history(user_message, history)
        
        # Call Bedrock with tools
        response = await self._call_bedrock_with_tools(
            messages=messages,
            model_id=model_id,
            auth_token=auth_token,
        )
        
        # Store in persistent memory
        await self.memory.save(session_id, "user", user_message)
        await self.memory.save(
            session_id, 
            "assistant", 
            response.message,
            tool_calls=response.tools_used,
            metadata={"model_used": model_id}
        )
        
        return response
    
    def _build_messages_from_history(
        self, 
        user_message: str, 
        history: list[ChatMessage]
    ) -> list:
        """Build message list for LangChain from chat history."""
        messages = []
        
        # Add conversation history
        for msg in history:
            if msg.role == "user":
                messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                messages.append(AIMessage(content=msg.content))
        
        # Add current message
        messages.append(HumanMessage(content=user_message))
        
        return messages
    
    async def _call_bedrock_with_tools(
        self,
        messages: list,
        model_id: str,
        auth_token: Optional[str] = None,
    ) -> AgentResponse:
        """Call LangChain with tool use."""
        tools_used = []
        
        try:
            # Get LangChain tools
            langchain_tools = self._format_tools_for_langchain()
            
            # Select appropriate LLM based on model_id
            if model_id == self.config.ORCHESTRATOR_MODEL:
                llm = self.orchestrator_llm
            else:
                llm = self.simple_llm
            
            # Bind tools to LLM
            llm_with_tools = llm.bind_tools(langchain_tools)
            
            # Add system message to the beginning
            full_messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
            
            # Initial call
            response = await llm_with_tools.ainvoke(full_messages)
            
            # Handle tool use loop
            while response.tool_calls:
                # Process each tool call
                tool_results = []
                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    tool_input = tool_call["args"]
                    tool_call_id = tool_call["id"]
                    
                    tools_used.append(tool_name)
                    
                    # Execute the tool
                    result = await self._execute_tool(
                        tool_name,
                        tool_input,
                        auth_token
                    )
                    
                    # Create tool message
                    tool_message = ToolMessage(
                        content=json.dumps(result),
                        tool_call_id=tool_call_id,
                    )
                    tool_results.append(tool_message)
                
                # Add assistant message with tool calls and tool results to messages
                messages.append(response)
                messages.extend(tool_results)
                
                # Continue conversation
                full_messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
                response = await llm_with_tools.ainvoke(full_messages)
            
            # Extract final response text
            final_message = response.content
            
            return AgentResponse(
                message=final_message,
                tools_used=tools_used,
                metadata={
                    "model_used": model_id,
                }
            )
            
        except Exception as e:
            return AgentResponse(
                message=f"I encountered an error processing your request: {str(e)}",
                metadata={"error": str(e)}
            )
    
    async def _execute_tool(
        self,
        tool_name: str,
        tool_input: dict,
        auth_token: Optional[str] = None,
    ) -> dict:
        """Execute a tool and return results."""
        if tool_name not in self.tools:
            return {"error": f"Unknown tool: {tool_name}"}
        
        tool = self.tools[tool_name]
        executor = self._get_tool_executor(auth_token)
        
        # Extract path parameters from input
        path_params = {}
        query_params = {}
        
        for param in tool.parameters:
            if param.name in tool_input:
                # Check if this is a path parameter
                if f"{{{param.name}}}" in tool.endpoint:
                    path_params[param.name] = tool_input[param.name]
                else:
                    query_params[param.name] = tool_input[param.name]
        
        return await executor.execute(tool, query_params, path_params)
    
    async def _generate_followup(self, user_message: str, missing_info: list[str]) -> str:
        """Generate a follow-up question for missing information."""
        prompt = FOLLOWUP_PROMPT.format(
            user_message=user_message,
            missing_info="\n".join(f"- {info}" for info in missing_info)
        )
        
        try:
            response = await self.simple_llm.ainvoke(prompt)
            return response.content
            
        except Exception:
            # Fallback generic question
            return f"I need a bit more information. Could you please clarify: {missing_info[0]}?"
    
    async def clear_session(self, session_id: str):
        """Clear conversation history for a session."""
        await self.memory.clear(session_id)
        if session_id in self.followup_counts:
            del self.followup_counts[session_id]
    
    async def close(self):
        """Cleanup resources."""
        if self.tool_executor:
            await self.tool_executor.close()
