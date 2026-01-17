"""
Base tool definitions and utilities.

Provides the ToolDefinition class and helper functions for creating tools
that map to FastAPI endpoints.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Literal, Optional
import httpx
import json


@dataclass
class ToolParameter:
    """Definition of a tool parameter."""
    name: str
    type: str  # "string", "integer", "number", "boolean", "array", "object"
    description: str
    required: bool = True
    enum: Optional[list] = None
    default: Optional[Any] = None
    items: Optional[dict] = None  # For array types


@dataclass
class ToolDefinition:
    """
    Definition of a tool that the agent can use.
    
    Maps to a FastAPI endpoint and provides schema for the LLM.
    """
    name: str
    description: str
    parameters: list[ToolParameter]
    endpoint: str  # API endpoint path (e.g., "/companies/{company_id}/products")
    method: Literal["GET", "POST", "PATCH", "DELETE"] = "GET"
    requires_company_id: bool = True
    
    def to_openapi_schema(self) -> dict:
        """Convert to OpenAPI-compatible tool schema."""
        properties = {}
        required = []
        
        for param in self.parameters:
            prop = {
                "type": param.type,
                "description": param.description,
            }
            if param.enum:
                prop["enum"] = param.enum
            if param.default is not None:
                prop["default"] = param.default
            if param.items:
                prop["items"] = param.items
                
            properties[param.name] = prop
            if param.required:
                required.append(param.name)
        
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": {
                "type": "object",
                "properties": properties,
                "required": required,
            }
        }
    
    def to_mcp_tool(self) -> dict:
        """Convert to MCP tool format for Gateway."""
        return self.to_openapi_schema()


class ToolExecutor:
    """
    Executes tools by calling the FastAPI backend.
    """
    
    def __init__(self, backend_url: str, company_id: str, auth_token: Optional[str] = None):
        self.backend_url = backend_url.rstrip("/")
        self.company_id = company_id
        self.auth_token = auth_token
        self.client = httpx.AsyncClient(timeout=30.0)
    
    def _get_headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers
    
    def _build_url(self, endpoint: str, path_params: dict) -> str:
        """Build full URL with path parameters."""
        url = endpoint
        for key, value in path_params.items():
            url = url.replace(f"{{{key}}}", str(value))
        return f"{self.backend_url}/api/v1{url}"
    
    async def execute(
        self, 
        tool: ToolDefinition, 
        arguments: dict,
        path_params: Optional[dict] = None
    ) -> dict:
        """Execute a tool and return the result."""
        path_params = path_params or {}
        
        # Add company_id if required
        if tool.requires_company_id:
            path_params["company_id"] = self.company_id
        
        url = self._build_url(tool.endpoint, path_params)
        headers = self._get_headers()
        
        try:
            if tool.method == "GET":
                response = await self.client.get(url, params=arguments, headers=headers)
            elif tool.method == "POST":
                response = await self.client.post(url, json=arguments, headers=headers)
            elif tool.method == "PATCH":
                response = await self.client.patch(url, json=arguments, headers=headers)
            elif tool.method == "DELETE":
                response = await self.client.delete(url, headers=headers)
            else:
                return {"error": f"Unsupported method: {tool.method}"}
            
            if response.status_code >= 400:
                return {
                    "error": f"API error: {response.status_code}",
                    "details": response.text
                }
            
            return response.json()
            
        except Exception as e:
            return {"error": str(e)}
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

