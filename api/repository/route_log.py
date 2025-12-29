"""
Repository for RouteLog entity operations.

This repository handles all database operations for route logs in a multi-tenant architecture.
Route logs are stored per tenant schema and track daily route execution details.
"""

from datetime import date
from typing import Optional
from uuid import UUID

import asyncpg
import structlog

from api.database import DatabasePool
from api.exceptions.route_log import (
    RouteLogNotFoundException,
    RouteLogOperationException,
)
from api.models.route_log import (
    RouteLogCreate,
    RouteLogInDB,
    RouteLogListItem,
    RouteLogUpdate,
)
from api.repository.utils import get_schema_name, set_search_path

logger = structlog.get_logger(__name__)


class RouteLogRepository:
    """
    Repository for managing RouteLog entities in a multi-tenant database.

    This repository provides methods for CRUD operations on route logs,
    handling schema-per-tenant isolation using asyncpg.
    All methods raise exceptions when records are not found.
    """

    def __init__(self, db_pool: DatabasePool, company_id: UUID) -> None:
        """
        Initialize the RouteLogRepository.

        Args:
            db_pool: Database pool instance for connection management
            company_id: UUID of the company (tenant) for schema isolation
        """
        self.db_pool = db_pool
        self.company_id = company_id
        self.schema_name = get_schema_name(company_id)

    async def _create_route_log(
        self, route_log_data: RouteLogCreate, connection: asyncpg.Connection
    ) -> RouteLogInDB:
        """
        Private method to create a route log with a provided connection.

        Args:
            route_log_data: Route log data to create
            connection: Database connection

        Returns:
            Created route log

        Raises:
            RouteLogOperationException: If creation fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Insert the route log
            row = await connection.fetchrow(
                """
                INSERT INTO route_logs (route_assignment_id, co_worker_id, date, start_time, end_time)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id, route_assignment_id, co_worker_id, date, start_time, end_time,
                          created_at, updated_at
                """,
                route_log_data.route_assignment_id,
                route_log_data.co_worker_id,
                route_log_data.date,
                route_log_data.start_time,
                route_log_data.end_time,
            )

            logger.info(
                "Route log created successfully",
                route_log_id=row["id"],
                route_assignment_id=route_log_data.route_assignment_id,
                date=str(route_log_data.date),
                company_id=str(self.company_id),
            )
            return RouteLogInDB(**dict(row))
        except asyncpg.ForeignKeyViolationError as e:
            if "fk_route_logs_route_assignment_id" in str(e):
                raise RouteLogOperationException(
                    message=f"Route assignment with id {route_log_data.route_assignment_id} not found",
                    operation="create",
                ) from e
            elif "fk_route_logs_co_worker_id" in str(e):
                raise RouteLogOperationException(
                    message=f"Co-worker with id {route_log_data.co_worker_id} not found",
                    operation="create",
                ) from e
            else:
                raise RouteLogOperationException(
                    message=f"Failed to create route log: {str(e)}",
                    operation="create",
                ) from e
        except asyncpg.CheckViolationError as e:
            if "check_valid_time_range" in str(e):
                raise RouteLogOperationException(
                    message="End time must be after start time",
                    operation="create",
                ) from e
            else:
                raise RouteLogOperationException(
                    message=f"Failed to create route log: {str(e)}",
                    operation="create",
                ) from e
        except Exception as e:
            logger.error(
                "Failed to create route log",
                route_assignment_id=route_log_data.route_assignment_id,
                date=str(route_log_data.date),
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RouteLogOperationException(
                message=f"Failed to create route log: {str(e)}",
                operation="create",
            ) from e

    async def create_route_log(
        self, route_log_data: RouteLogCreate, connection: Optional[asyncpg.Connection] = None
    ) -> RouteLogInDB:
        """
        Create a new route log.

        Args:
            route_log_data: Route log data to create
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Created route log

        Raises:
            RouteLogOperationException: If creation fails
        """
        if connection:
            return await self._create_route_log(route_log_data, connection)

        async with self.db_pool.acquire() as conn:
            return await self._create_route_log(route_log_data, conn)

    async def _get_route_log_by_id(
        self, route_log_id: int, connection: asyncpg.Connection
    ) -> RouteLogInDB:
        """
        Private method to get a route log by ID with a provided connection.

        Args:
            route_log_id: ID of the route log
            connection: Database connection

        Returns:
            Route log

        Raises:
            RouteLogNotFoundException: If route log not found
            RouteLogOperationException: If retrieval fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            row = await connection.fetchrow(
                """
                SELECT id, route_assignment_id, co_worker_id, date, start_time, end_time,
                       created_at, updated_at
                FROM route_logs
                WHERE id = $1
                """,
                route_log_id,
            )

            if not row:
                raise RouteLogNotFoundException(route_log_id=route_log_id)

            return RouteLogInDB(**dict(row))

        except RouteLogNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to get route log by id",
                route_log_id=route_log_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RouteLogOperationException(
                message=f"Failed to get route log: {str(e)}",
                operation="get",
            ) from e

    async def get_route_log_by_id(
        self, route_log_id: int, connection: Optional[asyncpg.Connection] = None
    ) -> RouteLogInDB:
        """
        Get a route log by ID.

        Args:
            route_log_id: ID of the route log
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Route log

        Raises:
            RouteLogNotFoundException: If route log not found
            RouteLogOperationException: If retrieval fails
        """
        if connection:
            return await self._get_route_log_by_id(route_log_id, connection)

        async with self.db_pool.acquire() as conn:
            return await self._get_route_log_by_id(route_log_id, conn)

    async def _list_route_logs(
        self,
        connection: asyncpg.Connection,
        route_assignment_id: Optional[int] = None,
        co_worker_id: Optional[UUID] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[RouteLogListItem]:
        """
        Private method to list route logs with a provided connection.

        Args:
            connection: Database connection
            route_assignment_id: Filter by route assignment ID
            co_worker_id: Filter by co-worker ID
            date_from: Filter by start date (inclusive)
            date_to: Filter by end date (inclusive)
            limit: Maximum number of route logs to return
            offset: Number of route logs to skip

        Returns:
            List of route logs

        Raises:
            RouteLogOperationException: If listing fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Build dynamic query
            query = """
                SELECT id, route_assignment_id, co_worker_id, date, start_time, end_time
                FROM route_logs
            """
            params = []
            param_count = 0
            conditions = []

            # Add WHERE conditions
            if route_assignment_id is not None:
                param_count += 1
                conditions.append(f"route_assignment_id = ${param_count}")
                params.append(route_assignment_id)

            if co_worker_id is not None:
                param_count += 1
                conditions.append(f"co_worker_id = ${param_count}")
                params.append(co_worker_id)

            if date_from is not None:
                param_count += 1
                conditions.append(f"date >= ${param_count}")
                params.append(date_from)

            if date_to is not None:
                param_count += 1
                conditions.append(f"date <= ${param_count}")
                params.append(date_to)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            # Add ordering
            query += " ORDER BY date DESC, start_time DESC"

            # Add limit and offset
            if limit is not None:
                param_count += 1
                query += f" LIMIT ${param_count}"
                params.append(limit)

            if offset is not None:
                param_count += 1
                query += f" OFFSET ${param_count}"
                params.append(offset)

            rows = await connection.fetch(query, *params)

            return [RouteLogListItem(**dict(row)) for row in rows]

        except Exception as e:
            logger.error(
                "Failed to list route logs",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RouteLogOperationException(
                message=f"Failed to list route logs: {str(e)}",
                operation="list",
            ) from e

    async def list_route_logs(
        self,
        route_assignment_id: Optional[int] = None,
        co_worker_id: Optional[UUID] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        limit: int = 20,
        offset: int = 0,
        connection: Optional[asyncpg.Connection] = None,
    ) -> list[RouteLogListItem]:
        """
        List all route logs with optional filtering.

        Args:
            route_assignment_id: Filter by route assignment ID
            co_worker_id: Filter by co-worker ID
            date_from: Filter by start date (inclusive)
            date_to: Filter by end date (inclusive)
            limit: Maximum number of route logs to return
            offset: Number of route logs to skip
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            List of route logs

        Raises:
            RouteLogOperationException: If listing fails
        """
        if connection:
            return await self._list_route_logs(
                connection, route_assignment_id, co_worker_id, date_from, date_to, limit, offset
            )

        async with self.db_pool.acquire() as conn:
            return await self._list_route_logs(
                conn, route_assignment_id, co_worker_id, date_from, date_to, limit, offset
            )

    async def _count_route_logs(
        self,
        connection: asyncpg.Connection,
        route_assignment_id: Optional[int] = None,
        co_worker_id: Optional[UUID] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> int:
        """
        Private method to count route logs with a provided connection.

        Args:
            connection: Database connection
            route_assignment_id: Filter by route assignment ID
            co_worker_id: Filter by co-worker ID
            date_from: Filter by start date (inclusive)
            date_to: Filter by end date (inclusive)

        Returns:
            Count of route logs

        Raises:
            RouteLogOperationException: If counting fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Build dynamic query
            query = "SELECT COUNT(*) FROM route_logs"
            params = []
            param_count = 0
            conditions = []

            if route_assignment_id is not None:
                param_count += 1
                conditions.append(f"route_assignment_id = ${param_count}")
                params.append(route_assignment_id)

            if co_worker_id is not None:
                param_count += 1
                conditions.append(f"co_worker_id = ${param_count}")
                params.append(co_worker_id)

            if date_from is not None:
                param_count += 1
                conditions.append(f"date >= ${param_count}")
                params.append(date_from)

            if date_to is not None:
                param_count += 1
                conditions.append(f"date <= ${param_count}")
                params.append(date_to)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            count = await connection.fetchval(query, *params)
            return count or 0

        except Exception as e:
            logger.error(
                "Failed to count route logs",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RouteLogOperationException(
                message=f"Failed to count route logs: {str(e)}",
                operation="count",
            ) from e

    async def count_route_logs(
        self,
        route_assignment_id: Optional[int] = None,
        co_worker_id: Optional[UUID] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        connection: Optional[asyncpg.Connection] = None,
    ) -> int:
        """
        Count route logs with optional filtering.

        Args:
            route_assignment_id: Filter by route assignment ID
            co_worker_id: Filter by co-worker ID
            date_from: Filter by start date (inclusive)
            date_to: Filter by end date (inclusive)
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Count of route logs

        Raises:
            RouteLogOperationException: If counting fails
        """
        if connection:
            return await self._count_route_logs(
                connection, route_assignment_id, co_worker_id, date_from, date_to
            )

        async with self.db_pool.acquire() as conn:
            return await self._count_route_logs(
                conn, route_assignment_id, co_worker_id, date_from, date_to
            )

    async def _update_route_log(
        self,
        route_log_id: int,
        route_log_data: RouteLogUpdate,
        connection: asyncpg.Connection,
    ) -> RouteLogInDB:
        """
        Private method to update a route log with a provided connection.

        Args:
            route_log_id: ID of the route log to update
            route_log_data: Route log data to update
            connection: Database connection

        Returns:
            Updated route log

        Raises:
            RouteLogNotFoundException: If route log not found
            RouteLogOperationException: If update fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Check if route log exists
            await self._get_route_log_by_id(route_log_id, connection)

            # Build dynamic update query
            update_fields = []
            params = []
            param_count = 0

            if route_log_data.co_worker_id is not None:
                param_count += 1
                update_fields.append(f"co_worker_id = ${param_count}")
                params.append(route_log_data.co_worker_id)

            if route_log_data.date is not None:
                param_count += 1
                update_fields.append(f"date = ${param_count}")
                params.append(route_log_data.date)

            if route_log_data.start_time is not None:
                param_count += 1
                update_fields.append(f"start_time = ${param_count}")
                params.append(route_log_data.start_time)

            if route_log_data.end_time is not None:
                param_count += 1
                update_fields.append(f"end_time = ${param_count}")
                params.append(route_log_data.end_time)

            if not update_fields:
                # No fields to update, return current route log
                return await self._get_route_log_by_id(route_log_id, connection)

            param_count += 1
            params.append(route_log_id)

            query = f"""
                UPDATE route_logs
                SET {", ".join(update_fields)}
                WHERE id = ${param_count}
                RETURNING id, route_assignment_id, co_worker_id, date, start_time, end_time,
                          created_at, updated_at
            """

            row = await connection.fetchrow(query, *params)

            if not row:
                raise RouteLogNotFoundException(route_log_id=route_log_id)

            logger.info(
                "Route log updated successfully",
                route_log_id=route_log_id,
                company_id=str(self.company_id),
            )

            return RouteLogInDB(**dict(row))

        except RouteLogNotFoundException:
            raise
        except asyncpg.ForeignKeyViolationError as e:
            if "fk_route_logs_co_worker_id" in str(e):
                raise RouteLogOperationException(
                    message=f"Co-worker with id {route_log_data.co_worker_id} not found",
                    operation="update",
                ) from e
            else:
                raise RouteLogOperationException(
                    message=f"Failed to update route log: {str(e)}",
                    operation="update",
                ) from e
        except asyncpg.CheckViolationError as e:
            if "check_valid_time_range" in str(e):
                raise RouteLogOperationException(
                    message="End time must be after start time",
                    operation="update",
                ) from e
            else:
                raise RouteLogOperationException(
                    message=f"Failed to update route log: {str(e)}",
                    operation="update",
                ) from e
        except Exception as e:
            logger.error(
                "Failed to update route log",
                route_log_id=route_log_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RouteLogOperationException(
                message=f"Failed to update route log: {str(e)}",
                operation="update",
            ) from e

    async def update_route_log(
        self,
        route_log_id: int,
        route_log_data: RouteLogUpdate,
        connection: Optional[asyncpg.Connection] = None,
    ) -> RouteLogInDB:
        """
        Update an existing route log.

        Args:
            route_log_id: ID of the route log to update
            route_log_data: Route log data to update
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Updated route log

        Raises:
            RouteLogNotFoundException: If route log not found
            RouteLogOperationException: If update fails
        """
        if connection:
            return await self._update_route_log(route_log_id, route_log_data, connection)

        async with self.db_pool.acquire() as conn:
            return await self._update_route_log(route_log_id, route_log_data, conn)

    async def _delete_route_log(
        self, route_log_id: int, connection: asyncpg.Connection
    ) -> None:
        """
        Private method to delete a route log with a provided connection.

        Args:
            route_log_id: ID of the route log to delete
            connection: Database connection

        Raises:
            RouteLogNotFoundException: If route log not found
            RouteLogOperationException: If deletion fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Check if route log exists
            await self._get_route_log_by_id(route_log_id, connection)

            # Delete route log
            result = await connection.execute(
                "DELETE FROM route_logs WHERE id = $1",
                route_log_id,
            )

            if result == "DELETE 0":
                raise RouteLogNotFoundException(route_log_id=route_log_id)

            logger.info(
                "Route log deleted successfully",
                route_log_id=route_log_id,
                company_id=str(self.company_id),
            )

        except RouteLogNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to delete route log",
                route_log_id=route_log_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RouteLogOperationException(
                message=f"Failed to delete route log: {str(e)}",
                operation="delete",
            ) from e

    async def delete_route_log(
        self, route_log_id: int, connection: Optional[asyncpg.Connection] = None
    ) -> None:
        """
        Delete a route log.

        Args:
            route_log_id: ID of the route log to delete
            connection: Optional database connection. If not provided, a new one is acquired.

        Raises:
            RouteLogNotFoundException: If route log not found
            RouteLogOperationException: If deletion fails
        """
        if connection:
            return await self._delete_route_log(route_log_id, connection)

        async with self.db_pool.acquire() as conn:
            return await self._delete_route_log(route_log_id, conn)

    async def _get_route_logs_by_route_assignment(
        self,
        route_assignment_id: int,
        connection: asyncpg.Connection,
    ) -> list[RouteLogListItem]:
        """
        Private method to get all route logs for a specific route assignment.

        Args:
            route_assignment_id: ID of the route assignment
            connection: Database connection

        Returns:
            List of route logs

        Raises:
            RouteLogOperationException: If retrieval fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            rows = await connection.fetch(
                """
                SELECT id, route_assignment_id, co_worker_id, date, start_time, end_time
                FROM route_logs
                WHERE route_assignment_id = $1
                ORDER BY date DESC, start_time DESC
                """,
                route_assignment_id,
            )

            return [RouteLogListItem(**dict(row)) for row in rows]

        except Exception as e:
            logger.error(
                "Failed to get route logs by route assignment",
                route_assignment_id=route_assignment_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RouteLogOperationException(
                message=f"Failed to get route logs by route assignment: {str(e)}",
                operation="get_by_route_assignment",
            ) from e

    async def get_route_logs_by_route_assignment(
        self,
        route_assignment_id: int,
        connection: Optional[asyncpg.Connection] = None,
    ) -> list[RouteLogListItem]:
        """
        Get all route logs for a specific route assignment.

        Args:
            route_assignment_id: ID of the route assignment
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            List of route logs

        Raises:
            RouteLogOperationException: If retrieval fails
        """
        if connection:
            return await self._get_route_logs_by_route_assignment(route_assignment_id, connection)

        async with self.db_pool.acquire() as conn:
            return await self._get_route_logs_by_route_assignment(route_assignment_id, conn)

