"""
DynamoDB-backed chat memory for the agentic sales assistant.

Each user question + assistant response is stored as a single DynamoDB row,
along with metadata about tool calls and which sub-agent was used. An
in-memory fallback is provided for local development.
"""

from __future__ import annotations

import asyncio
import json
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID
from api.settings import get_settings
import boto3
import structlog
from boto3.dynamodb.conditions import Key

logger = structlog.get_logger(__name__)


@dataclass
class ChatMessage:
    """A single message in the conversation history."""

    role: str  # "user" or "assistant"
    content: str
    timestamp: str = ""
    tool_calls: list[dict] | None = None
    sub_agent_used: str | None = None


@dataclass
class InteractionRecord:
    """Complete interaction row stored in DynamoDB."""

    session_id: str
    created_at: str
    user_id: str
    user_message: str
    assistant_response: str
    tool_calls: list[dict] = field(default_factory=list)
    sub_agent_used: str = ""
    needs_followup: bool = False
    followup_question: str | None = None


class ChatMemory:
    """Manages conversation memory using DynamoDB (or an in-memory fallback).

    DynamoDB table schema
    ---------------------
    - Partition key: ``session_id`` (S)
    - Sort key: ``created_at`` (S)  -- ISO-8601 timestamp
    - GSI ``user_id-index``: PK = ``user_id``, SK = ``session_id``

    Call :meth:`ensure_table_exists` once at application startup to create
    the table (and GSI) if it does not already exist.
    """

    def __init__(
        self,
        backend: str = "dynamodb",
        table_name: str = "agent_memory",
        region: str = "ap-south-1",
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
    ) -> None:
        self._backend = backend
        self._table_name = table_name
        self._region = region

        logger.debug(
            "[MEMORY] Initializing ChatMemory",
            backend=backend,
            table_name=table_name,
            region=region,
        )

        if backend == "dynamodb":
            settings = get_settings()
            kwargs: dict[str, Any] = {"region_name": settings.AWS.region_name}
            kwargs["aws_access_key_id"] = aws_access_key_id or settings.AWS.access_key_id
            kwargs["aws_secret_access_key"] = (
                aws_secret_access_key or settings.AWS.secret_access_key
            )
            self._boto_kwargs = kwargs
            self._dynamodb = boto3.resource("dynamodb", **kwargs)
            self._table = self._dynamodb.Table(settings.AGENT.TABLE_NAME)
            logger.debug(
                "[MEMORY] DynamoDB resource initialized",
                table=settings.AGENT.TABLE_NAME,
                region=settings.AWS.region_name,
            )
        else:
            self._boto_kwargs = {}
            # In-memory store for local dev / tests
            self._store: dict[str, list[InteractionRecord]] = {}
            logger.debug("[MEMORY] Using in-memory backend")

    # ------------------------------------------------------------------
    # Table provisioning
    # ------------------------------------------------------------------

    async def ensure_table_exists(self) -> None:
        """Create the DynamoDB table and GSI if they do not already exist."""
        if self._backend != "dynamodb":
            logger.debug("[MEMORY] Skipping DynamoDB table creation (backend=%s)", self._backend)
            return

        logger.info("[MEMORY] Ensuring DynamoDB table exists", table=self._table_name)
        await asyncio.to_thread(self._create_table_sync)

    def _create_table_sync(self) -> None:
        """Synchronous helper that creates the table (called via ``to_thread``)."""
        client = boto3.client("dynamodb", **self._boto_kwargs)

        # Check whether the table already exists
        try:
            resp = client.describe_table(TableName=self._table_name)
            status = resp.get("Table", {}).get("TableStatus", "UNKNOWN")
            logger.info(
                "[MEMORY] DynamoDB table already exists",
                table=self._table_name,
                status=status,
            )
            return
        except client.exceptions.ResourceNotFoundException:
            logger.info("[MEMORY] Table not found, creating...", table=self._table_name)

        try:
            client.create_table(
                TableName=self._table_name,
                KeySchema=[
                    {"AttributeName": "session_id", "KeyType": "HASH"},
                    {"AttributeName": "created_at", "KeyType": "RANGE"},
                ],
                AttributeDefinitions=[
                    {"AttributeName": "session_id", "AttributeType": "S"},
                    {"AttributeName": "created_at", "AttributeType": "S"},
                    {"AttributeName": "user_id", "AttributeType": "S"},
                ],
                GlobalSecondaryIndexes=[
                    {
                        "IndexName": "user_id-index",
                        "KeySchema": [
                            {"AttributeName": "user_id", "KeyType": "HASH"},
                            {"AttributeName": "session_id", "KeyType": "RANGE"},
                        ],
                        "Projection": {
                            "ProjectionType": "INCLUDE",
                            "NonKeyAttributes": ["created_at"],
                        },
                    },
                ],
                BillingMode="PAY_PER_REQUEST",
                Tags=[
                    {"Key": "Application", "Value": "salesforce-agent"},
                    {"Key": "ManagedBy", "Value": "api"},
                ],
            )

            # Wait until the table is active
            waiter = client.get_waiter("table_exists")
            waiter.wait(
                TableName=self._table_name,
                WaiterConfig={"Delay": 2, "MaxAttempts": 30},
            )

            # Refresh the resource handle so subsequent calls use the live table
            self._table = self._dynamodb.Table(self._table_name)
            logger.info("[MEMORY] DynamoDB table created successfully", table=self._table_name)
        except Exception as exc:
            logger.error(
                "[MEMORY] Failed to create DynamoDB table",
                table=self._table_name,
                error=str(exc),
                traceback=traceback.format_exc(),
            )
            raise

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def save_interaction(
        self,
        session_id: str,
        user_id: str | UUID,
        user_message: str,
        assistant_response: str,
        tool_calls: list[dict] | None = None,
        sub_agent_used: str = "",
        needs_followup: bool = False,
        followup_question: str | None = None,
    ) -> None:
        """Persist a single Q+A exchange."""
        logger.debug(
            "[MEMORY] Saving interaction",
            session_id=session_id,
            user_id=str(user_id),
            sub_agent=sub_agent_used,
            tool_calls_count=len(tool_calls) if tool_calls else 0,
            needs_followup=needs_followup,
        )

        record = InteractionRecord(
            session_id=session_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            user_id=str(user_id),
            user_message=user_message,
            assistant_response=assistant_response,
            tool_calls=tool_calls or [],
            sub_agent_used=sub_agent_used,
            needs_followup=needs_followup,
            followup_question=followup_question,
        )

        if self._backend == "dynamodb":
            await self._dynamo_put(record)
        else:
            self._store.setdefault(session_id, []).append(record)

        logger.info(
            "[MEMORY] Interaction saved",
            session_id=session_id,
            sub_agent=sub_agent_used,
        )

    async def get_history(
        self,
        session_id: str,
        limit: int = 20,
    ) -> list[ChatMessage]:
        """Return ordered conversation history for a session."""
        logger.debug(
            "[MEMORY] Fetching history",
            session_id=session_id,
            limit=limit,
        )

        if self._backend == "dynamodb":
            messages = await self._dynamo_get_history(session_id, limit)
        else:
            messages = []
            for rec in self._store.get(session_id, [])[-limit:]:
                messages.append(
                    ChatMessage(role="user", content=rec.user_message, timestamp=rec.created_at)
                )
                messages.append(
                    ChatMessage(
                        role="assistant",
                        content=rec.assistant_response,
                        timestamp=rec.created_at,
                        tool_calls=rec.tool_calls,
                        sub_agent_used=rec.sub_agent_used,
                    )
                )

        logger.debug(
            "[MEMORY] History fetched",
            session_id=session_id,
            message_count=len(messages),
        )
        return messages

    async def get_user_sessions(self, user_id: str | UUID) -> list[str]:
        """Return distinct session IDs for a user (via GSI)."""
        logger.debug("[MEMORY] Fetching user sessions", user_id=str(user_id))

        if self._backend == "dynamodb":
            sessions = await self._dynamo_get_sessions(str(user_id))
        else:
            found: set[str] = set()
            for sid, records in self._store.items():
                if any(r.user_id == str(user_id) for r in records):
                    found.add(sid)
            sessions = sorted(found)

        logger.debug(
            "[MEMORY] User sessions fetched",
            user_id=str(user_id),
            session_count=len(sessions),
        )
        return sessions

    # ------------------------------------------------------------------
    # DynamoDB helpers (run in thread to avoid blocking the event loop)
    # ------------------------------------------------------------------

    async def _dynamo_put(self, record: InteractionRecord) -> None:
        """Write a record to DynamoDB."""

        def _put() -> None:
            item: dict[str, Any] = {
                "session_id": record.session_id,
                "created_at": record.created_at,
                "user_id": record.user_id,
                "user_message": record.user_message,
                "assistant_response": record.assistant_response,
                "tool_calls": json.loads(json.dumps(record.tool_calls, default=str)),
                "sub_agent_used": record.sub_agent_used,
                "needs_followup": record.needs_followup,
            }
            if record.followup_question:
                item["followup_question"] = record.followup_question
            logger.debug("[MEMORY] DynamoDB put_item", session_id=record.session_id)
            self._table.put_item(Item=item)

        try:
            await asyncio.to_thread(_put)
        except Exception as exc:
            logger.error(
                "[MEMORY] DynamoDB put_item failed",
                session_id=record.session_id,
                error=str(exc),
                traceback=traceback.format_exc(),
            )
            raise

    async def _dynamo_get_history(
        self,
        session_id: str,
        limit: int,
    ) -> list[ChatMessage]:
        """Query history from DynamoDB, newest first then reversed."""

        def _query() -> list[dict]:
            logger.debug("[MEMORY] DynamoDB query", session_id=session_id, limit=limit)
            resp = self._table.query(
                KeyConditionExpression=Key("session_id").eq(session_id),
                ScanIndexForward=False, #newest first so Limit grabs recent items 
                Limit=limit,
            )
            items = resp.get("Items", [])
            items.reverse()
            logger.debug("[MEMORY] DynamoDB query result", item_count=len(items))
            return items

        try:
            items = await asyncio.to_thread(_query)
        except Exception as exc:
            logger.error(
                "[MEMORY] DynamoDB query failed",
                session_id=session_id,
                error=str(exc),
                traceback=traceback.format_exc(),
            )
            return []

        messages: list[ChatMessage] = []
        for item in items:
            messages.append(
                ChatMessage(
                    role="user",
                    content=item["user_message"],
                    timestamp=item["created_at"],
                )
            )
            messages.append(
                ChatMessage(
                    role="assistant",
                    content=item["assistant_response"],
                    timestamp=item["created_at"],
                    tool_calls=item.get("tool_calls"),
                    sub_agent_used=item.get("sub_agent_used"),
                )
            )
        return messages

    async def _dynamo_get_sessions(self, user_id: str) -> list[str]:
        """List sessions from the user_id GSI."""

        def _query() -> list[str]:
            logger.debug("[MEMORY] DynamoDB GSI query", user_id=user_id)
            resp = self._table.query(
                IndexName="user_id-index",
                KeyConditionExpression=Key("user_id").eq(user_id),
                ProjectionExpression="session_id",
            )
            items = resp.get("Items", [])
            logger.debug("[MEMORY] DynamoDB GSI query result", item_count=len(items))
            return sorted({item["session_id"] for item in items})

        try:
            return await asyncio.to_thread(_query)
        except Exception as exc:
            logger.error(
                "[MEMORY] DynamoDB GSI query failed",
                user_id=user_id,
                error=str(exc),
                traceback=traceback.format_exc(),
            )
            return []
