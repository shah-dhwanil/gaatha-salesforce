"""
Chat Memory Storage for the Sales Management Agent.

Provides persistent storage for conversation history.
Supports multiple backends:
1. DynamoDB (recommended for Lambda)
2. In-memory (for local testing)
3. AgentCore Memory (for full AgentCore deployment)
"""

from uuid import UUID
from api.settings import get_settings
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import Optional
import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

memory_datastore=None

@dataclass
class ChatMessage:
    """A single chat message."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: float
    tool_calls: Optional[list] = None
    metadata: Optional[dict] = None
    
    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "tool_calls": self.tool_calls or [],
            "metadata": self.metadata or {},
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ChatMessage":
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=data.get("timestamp", time.time()),
            tool_calls=data.get("tool_calls"),
            metadata=data.get("metadata"),
        )


class MemoryBackend(ABC):
    """Abstract base class for memory backends."""
    
    @abstractmethod
    async def save_message(self, session_id: str, user_id: UUID, message: ChatMessage) -> None:
        """Save a message to storage."""
        pass
    
    @abstractmethod
    async def get_history(self, session_id: str, limit: int = 20) -> list[ChatMessage]:
        """Get conversation history for a session."""
        pass
    
    @abstractmethod
    async def clear_session(self, session_id: str) -> None:
        """Clear all messages for a session."""
        pass


class InMemoryBackend(MemoryBackend):
    """In-memory storage for local testing."""
    
    def __init__(self):
        self.sessions: dict[str, list[ChatMessage]] = {}
    
    async def save_message(self, session_id: str, user_id: UUID, message: ChatMessage) -> None:
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        self.sessions[session_id].append(message)
    
    async def get_history(self, session_id: str, limit: int = 20) -> list[ChatMessage]:
        messages = self.sessions.get(session_id, [])
        return messages[-limit:]
    
    async def clear_session(self, session_id: str) -> None:
        if session_id in self.sessions:
            del self.sessions[session_id]


class DynamoDBBackend(MemoryBackend):
    """
    DynamoDB storage for persistent chat history.
    
    Table Schema:
    - session_id (PK): String
    - timestamp (SK): Number
    - role: String
    - content: String
    - tool_calls: List
    - metadata: Map
    - ttl: Number (optional, for auto-expiry)
    """
    
    def __init__(
        self,
        table_name: str = "sales-agent-chats-new",
        region: str = "us-west-2",
        ttl_days: int = 30,
    ):
        self.config = get_settings()
        self.table_name = table_name
        self.region = region
        self.ttl_days = ttl_days
        self.dynamodb = boto3.resource(
            "dynamodb",
            region_name=self.config.AWS.region_name,
            aws_access_key_id=self.config.AWS.access_key_id,
            aws_secret_access_key=self.config.AWS.secret_access_key,
        )
        self.table = self.dynamodb.Table(table_name)
        self._table_verified = False
    
    async def _ensure_table(self) -> None:
        """Create table if it doesn't exist."""
        if self._table_verified:
            return
        
        client = boto3.client(
            "dynamodb",
            region_name=self.config.AWS.region_name,
            aws_access_key_id=self.config.AWS.access_key_id,
            aws_secret_access_key=self.config.AWS.secret_access_key,
        )
        
        try:
            client.describe_table(TableName=self.table_name)
            self._table_verified = True
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                # Create the table
                client.create_table(
                    TableName=self.table_name,
                    KeySchema=[
                        {"AttributeName": "session_id", "KeyType": "HASH"},
                        {"AttributeName": "timestamp", "KeyType": "RANGE"},
                    ],
                    AttributeDefinitions=[
                        {"AttributeName": "session_id", "AttributeType": "S"},
                        {"AttributeName": "timestamp", "AttributeType": "N"},
                    ],
                    BillingMode="PAY_PER_REQUEST",
                )
                
                # Wait for table to be active
                waiter = client.get_waiter("table_exists")
                waiter.wait(TableName=self.table_name)
                
                # Enable TTL
                client.update_time_to_live(
                    TableName=self.table_name,
                    TimeToLiveSpecification={
                        "Enabled": True,
                        "AttributeName": "ttl",
                    },
                )
                
                self.table = self.dynamodb.Table(self.table_name)
                self._table_verified = True
            else:
                raise
    
    async def save_message(self, session_id: str, user_id: UUID, message: ChatMessage) -> None:
        await self._ensure_table()
        
        item = {
            "user_id": str(user_id),
            "session_id": session_id,
            "timestamp": int(message.timestamp * 1000),  # milliseconds
            "role": message.role,
            "content": message.content,
            "tool_calls": json.dumps(message.tool_calls or []),
            "metadata": json.dumps(message.metadata or {}),
            "ttl": int(time.time()) + (self.ttl_days * 86400),
        }
        
        self.table.put_item(Item=item)
    
    async def get_history(self, session_id: str, limit: int = 20) -> list[ChatMessage]:
        await self._ensure_table()
        
        response = self.table.query(
            KeyConditionExpression="session_id = :sid",
            ExpressionAttributeValues={":sid": session_id},
            ScanIndexForward=True,  # Oldest first
            Limit=limit * 2,  # Get more to handle limit after sorting
        )
        
        messages = []
        for item in response.get("Items", []):
            messages.append(ChatMessage(
                role=item["role"],
                content=item["content"],
                timestamp=item["timestamp"] / 1000,
                tool_calls=json.loads(item.get("tool_calls", "[]")),
                metadata=json.loads(item.get("metadata", "{}")),
            ))
        
        return messages[-limit:]
    
    async def clear_session(self, session_id: str) -> None:
        await self._ensure_table()
        
        # Query all items for the session
        response = self.table.query(
            KeyConditionExpression="session_id = :sid",
            ExpressionAttributeValues={":sid": session_id},
            ProjectionExpression="session_id, #ts",
            ExpressionAttributeNames={"#ts": "timestamp"},
        )
        
        # Delete each item
        with self.table.batch_writer() as batch:
            for item in response.get("Items", []):
                batch.delete_item(Key={
                    "session_id": item["session_id"],
                    "timestamp": item["timestamp"],
                })
    
    async def get_user_sessions(self,user_id: UUID) -> list[str]:
        """Get all session IDs for given user_id"""
        await self._ensure_table()
        
        response = self.table.query(
            IndexName="user_idx",  # GSI name
            KeyConditionExpression=Key("user_id").eq(str(user_id)),
            ProjectionExpression="session_id"
        )
        
        session_ids = set()
        for item in response.get("Items", []):
            session_ids.add(item["session_id"])
        
        return list(session_ids)


class ChatMemory:
    """
    Main interface for chat memory.
    
    Usage:
        memory = ChatMemory(backend="dynamodb")
        await memory.save("session-123", ChatMessage(role="user", content="Hello"))
        history = await memory.get_history("session-123")
    """
    
    def __init__(
        self,
        backend: str = "memory",
        table_name: str = "sales-agent-chats",
        region: str = "us-west-2",
        ttl_days: int = 30,
    ):
        if backend == "dynamodb":
            self._backend = DynamoDBBackend(
                table_name=table_name,
                region=region,
                ttl_days=ttl_days,
            )
        else:
            global memory_datastore
            if memory_datastore is None:
                memory_datastore = InMemoryBackend()
            self._backend = memory_datastore
        
        self.backend_type = backend
    
    async def save(self, session_id: str, user_id: UUID, role: str, content: str, **kwargs) -> None:
        """Save a message."""
        message = ChatMessage(
            role=role,
            content=content,
            timestamp=time.time(),
            tool_calls=kwargs.get("tool_calls"),
            metadata=kwargs.get("metadata"),
        )
        await self._backend.save_message(session_id, user_id, message)
    
    async def get_history(self, session_id: str, limit: int = 20) -> list[ChatMessage]:
        """Get conversation history."""
        return await self._backend.get_history(session_id, limit)
    
    async def clear(self, session_id: str) -> None:
        """Clear a session."""
        await self._backend.clear_session(session_id)
    
    def format_for_bedrock(self, messages: list[ChatMessage]) -> list[dict]:
        """Format messages for Bedrock Converse API (legacy support)."""
        return [
            {
                "role": msg.role,
                "content": [{"text": msg.content}]
            }
            for msg in messages
        ]
    
    def format_for_langchain(self, messages: list[ChatMessage]) -> list:
        """Format messages for LangChain."""
        from langchain_core.messages import HumanMessage, AIMessage
        
        lc_messages = []
        for msg in messages:
            if msg.role == "user":
                lc_messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                lc_messages.append(AIMessage(content=msg.content))
        
        return lc_messages
    
    async def get_user_sessions(self,user_id: UUID) -> list[str]:
        """Get all session IDs for given user_id (DynamoDB only)"""
        # if self.backend_type != "dynamodb":
        #     raise NotImplementedError("get_user_sessions is only supported for DynamoDB backend.")
        
        return await self._backend.get_user_sessions(user_id)

