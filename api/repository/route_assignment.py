"""
Repository for RouteAssignment entity operations.

This repository handles all database operations for route assignments in a multi-tenant architecture.
Route assignments are stored per tenant schema and link users to routes for specific days.
"""

from datetime import date
from typing import Optional
from uuid import UUID

import asyncpg
import structlog

from api.database import DatabasePool
from api.exceptions.route import RouteNotFoundException
from api.exceptions.user import UserNotFoundException
from api.exceptions.route_assignment import (
    InvalidDateRangeException,
    RouteAssignmentAlreadyExistsException,
    RouteAssignmentNotFoundException,
    RouteAssignmentOperationException,
)
from api.models.route_assignment import (
    RouteAssignmentCreate,
    RouteAssignmentDetailItem,
    RouteAssignmentInDB,
    RouteAssignmentListItem,
    RouteAssignmentUpdate,
)
from api.repository.utils import get_schema_name, set_search_path

logger = structlog.get_logger(__name__)


class RouteAssignmentRepository:
    """
    Repository for managing RouteAssignment entities in a multi-tenant database.

    This repository provides methods for CRUD operations on route assignments,
    handling schema-per-tenant isolation using asyncpg.
    All methods raise exceptions when records are not found.
    """

    def __init__(self, db_pool: DatabasePool, company_id: UUID) -> None:
        """
        Initialize the RouteAssignmentRepository.

        Args:
            db_pool: Database pool instance for connection management
            company_id: UUID of the company (tenant) for schema isolation
        """
        self.db_pool = db_pool
        self.company_id = company_id
        self.schema_name = get_schema_name(company_id)

    async def _create_route_assignment(
        self, assignment_data: RouteAssignmentCreate, connection: asyncpg.Connection
    ) -> RouteAssignmentInDB:
        """
        Private method to create a route assignment with a provided connection.

        Args:
            assignment_data: Route assignment data to create
            connection: Database connection

        Returns:
            Created route assignment

        Raises:
            RouteAssignmentAlreadyExistsException: If active assignment already exists for route and user
            RouteAssignmentOperationException: If creation fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Insert the route assignment
            row = await connection.fetchrow(
                """
                INSERT INTO route_assignment (route_id, user_id, from_date, to_date, day, is_active)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id, route_id, user_id, from_date, to_date, day, is_active, created_at, updated_at
                """,
                assignment_data.route_id,
                assignment_data.user_id,
                assignment_data.from_date,
                assignment_data.to_date,
                assignment_data.day,
                assignment_data.is_active,
            )

            logger.info(
                "Route assignment created successfully",
                assignment_id=row["id"],
                route_id=assignment_data.route_id,
                user_id=str(assignment_data.user_id),
                company_id=str(self.company_id),
            )
            return RouteAssignmentInDB(**dict(row))
        except asyncpg.UniqueViolationError as e:
            if "uniq_route_user_active" in str(e):
                raise RouteAssignmentAlreadyExistsException(
                    route_id=assignment_data.route_id,
                    user_id=assignment_data.user_id,
                )
            else:
                raise RouteAssignmentOperationException(
                    message=f"Failed to create route assignment: {str(e)}",
                    operation="create",
                ) from e
        except asyncpg.ForeignKeyViolationError as e:
            if "fk_route_assignment_route_id" in str(e):
                raise RouteNotFoundException(
                    message=f"Route with id {assignment_data.route_id} not found",
                    operation="create",
                ) from e
            elif "fk_route_assignment_user_id" in str(e):
                raise UserNotFoundException(
                    message=f"User with id {assignment_data.user_id} not found",
                    operation="create",
                ) from e
            else:
                raise RouteAssignmentOperationException(
                    message=f"Failed to create route assignment: {str(e)}",
                    operation="create",
                ) from e
        except asyncpg.CheckViolationError as e:
            if "check_valid_date_range" in str(e):
                raise InvalidDateRangeException(
                    message="End date must be greater than or equal to start date"
                )
            elif "check_day_valid" in str(e):
                raise RouteAssignmentOperationException(
                    message="Day must be between 0 and 6",
                    operation="create",
                ) from e
            else:
                raise RouteAssignmentOperationException(
                    message=f"Failed to create route assignment: {str(e)}",
                    operation="create",
                ) from e
        except Exception as e:
            logger.error(
                "Failed to create route assignment",
                route_id=assignment_data.route_id,
                user_id=str(assignment_data.user_id),
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RouteAssignmentOperationException(
                message=f"Failed to create route assignment: {str(e)}",
                operation="create",
            ) from e

    async def create_route_assignment(
        self,
        assignment_data: RouteAssignmentCreate,
        connection: Optional[asyncpg.Connection] = None,
    ) -> RouteAssignmentInDB:
        """
        Create a new route assignment.

        Args:
            assignment_data: Route assignment data to create
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Created route assignment

        Raises:
            RouteAssignmentAlreadyExistsException: If active assignment already exists
            RouteAssignmentOperationException: If creation fails
        """
        if connection:
            return await self._create_route_assignment(assignment_data, connection)

        async with self.db_pool.acquire() as conn:
            return await self._create_route_assignment(assignment_data, conn)

    async def _get_route_assignment_by_id(
        self, assignment_id: int, connection: asyncpg.Connection
    ) -> RouteAssignmentDetailItem:
        """
        Private method to get a route assignment by ID with a provided connection.

        Args:
            assignment_id: ID of the route assignment
            connection: Database connection

        Returns:
            Route assignment

        Raises:
            RouteAssignmentNotFoundException: If route assignment not found
            RouteAssignmentOperationException: If retrieval fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            row = await connection.fetchrow(
                """
                SELECT ra.id, ra.route_id, r.name as route_name, r.code as route_code,
                       ra.user_id, u.name as user_name, u.username as user_username,
                       ra.from_date, ra.to_date, ra.day, ra.is_active, ra.created_at, ra.updated_at
                FROM route_assignment ra
                INNER JOIN routes r ON ra.route_id = r.id
                INNER JOIN members m ON ra.user_id = m.id
                INNER JOIN salesforce.users u ON m.id = u.id
                WHERE ra.id = $1
                """,
                assignment_id,
            )

            if not row:
                raise RouteAssignmentNotFoundException(assignment_id=assignment_id)

            return RouteAssignmentDetailItem(**dict(row))

        except RouteAssignmentNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to get route assignment by id",
                assignment_id=assignment_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RouteAssignmentOperationException(
                message=f"Failed to get route assignment: {str(e)}",
                operation="get",
            ) from e

    async def get_route_assignment_by_id(
        self, assignment_id: int, connection: Optional[asyncpg.Connection] = None
    ) -> RouteAssignmentDetailItem:
        """
        Get a route assignment by ID.

        Args:
            assignment_id: ID of the route assignment
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Route assignment

        Raises:
            RouteAssignmentNotFoundException: If route assignment not found
            RouteAssignmentOperationException: If retrieval fails
        """
        if connection:
            return await self._get_route_assignment_by_id(assignment_id, connection)

        async with self.db_pool.acquire() as conn:
            return await self._get_route_assignment_by_id(assignment_id, conn)

    async def _list_route_assignments(
        self,
        connection: asyncpg.Connection,
        route_id: Optional[int] = None,
        user_id: Optional[UUID] = None,
        day: Optional[int] = None,
        is_active: Optional[bool] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[RouteAssignmentListItem]:
        """
        Private method to list route assignments with a provided connection.
        Returns minimal data to optimize performance.

        Args:
            connection: Database connection
            route_id: Filter by route ID
            user_id: Filter by user ID
            day: Filter by day of week
            is_active: Filter by active status
            from_date: Filter by assignments starting from this date
            to_date: Filter by assignments ending before this date
            limit: Maximum number of assignments to return
            offset: Number of assignments to skip

        Returns:
            List of route assignments with minimal data

        Raises:
            RouteAssignmentOperationException: If listing fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Build dynamic query
            query = """
                SELECT ra.id, ra.route_id, r.name as route_name, r.code as route_code,
                       ra.user_id, u.name as user_name,
                       ra.from_date, ra.to_date, ra.day, ra.is_active
                FROM route_assignment ra
                INNER JOIN routes r ON ra.route_id = r.id
                INNER JOIN members m ON ra.user_id = m.id
                INNER JOIN salesforce.users u ON m.id = u.id
            """
            params = []
            param_count = 0
            conditions = []

            # Add WHERE conditions
            if route_id is not None:
                param_count += 1
                conditions.append(f"ra.route_id = ${param_count}")
                params.append(route_id)

            if user_id is not None:
                param_count += 1
                conditions.append(f"ra.user_id = ${param_count}")
                params.append(user_id)

            if day is not None:
                param_count += 1
                conditions.append(f"ra.day = ${param_count}")
                params.append(day)

            if is_active is not None:
                param_count += 1
                conditions.append(f"ra.is_active = ${param_count}")
                params.append(is_active)

            if from_date is not None:
                param_count += 1
                conditions.append(f"ra.from_date >= ${param_count}")
                params.append(from_date)

            if to_date is not None:
                param_count += 1
                conditions.append(
                    f"(ra.to_date IS NULL OR ra.to_date <= ${param_count})"
                )
                params.append(to_date)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            # Add ordering
            query += " ORDER BY ra.from_date DESC, ra.id DESC"

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

            return [RouteAssignmentListItem(**dict(row)) for row in rows]

        except Exception as e:
            logger.error(
                "Failed to list route assignments",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RouteAssignmentOperationException(
                message=f"Failed to list route assignments: {str(e)}",
                operation="list",
            ) from e

    async def list_route_assignments(
        self,
        route_id: Optional[int] = None,
        user_id: Optional[UUID] = None,
        day: Optional[int] = None,
        is_active: Optional[bool] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        limit: int = 20,
        offset: int = 0,
        connection: Optional[asyncpg.Connection] = None,
    ) -> list[RouteAssignmentListItem]:
        """
        List all route assignments with optional filtering.
        Returns minimal data to optimize performance.

        Args:
            route_id: Filter by route ID
            user_id: Filter by user ID
            day: Filter by day of week
            is_active: Filter by active status
            from_date: Filter by assignments starting from this date
            to_date: Filter by assignments ending before this date
            limit: Maximum number of assignments to return
            offset: Number of assignments to skip
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            List of route assignments with minimal data

        Raises:
            RouteAssignmentOperationException: If listing fails
        """
        if connection:
            return await self._list_route_assignments(
                connection,
                route_id,
                user_id,
                day,
                is_active,
                from_date,
                to_date,
                limit,
                offset,
            )

        async with self.db_pool.acquire() as conn:
            return await self._list_route_assignments(
                conn,
                route_id,
                user_id,
                day,
                is_active,
                from_date,
                to_date,
                limit,
                offset,
            )

    async def _count_route_assignments(
        self,
        connection: asyncpg.Connection,
        route_id: Optional[int] = None,
        user_id: Optional[UUID] = None,
        day: Optional[int] = None,
        is_active: Optional[bool] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> int:
        """
        Private method to count route assignments with a provided connection.

        Args:
            connection: Database connection
            route_id: Filter by route ID
            user_id: Filter by user ID
            day: Filter by day of week
            is_active: Filter by active status
            from_date: Filter by assignments starting from this date
            to_date: Filter by assignments ending before this date

        Returns:
            Count of route assignments

        Raises:
            RouteAssignmentOperationException: If counting fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Build dynamic query
            query = "SELECT COUNT(*) FROM route_assignment ra"
            params = []
            param_count = 0
            conditions = []

            if route_id is not None:
                param_count += 1
                conditions.append(f"ra.route_id = ${param_count}")
                params.append(route_id)

            if user_id is not None:
                param_count += 1
                conditions.append(f"ra.user_id = ${param_count}")
                params.append(user_id)

            if day is not None:
                param_count += 1
                conditions.append(f"ra.day = ${param_count}")
                params.append(day)

            if is_active is not None:
                param_count += 1
                conditions.append(f"ra.is_active = ${param_count}")
                params.append(is_active)

            if from_date is not None:
                param_count += 1
                conditions.append(f"ra.from_date >= ${param_count}")
                params.append(from_date)

            if to_date is not None:
                param_count += 1
                conditions.append(
                    f"(ra.to_date IS NULL OR ra.to_date <= ${param_count})"
                )
                params.append(to_date)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            count = await connection.fetchval(query, *params)
            return count or 0

        except Exception as e:
            logger.error(
                "Failed to count route assignments",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RouteAssignmentOperationException(
                message=f"Failed to count route assignments: {str(e)}",
                operation="count",
            ) from e

    async def count_route_assignments(
        self,
        route_id: Optional[int] = None,
        user_id: Optional[UUID] = None,
        day: Optional[int] = None,
        is_active: Optional[bool] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        connection: Optional[asyncpg.Connection] = None,
    ) -> int:
        """
        Count route assignments with optional filtering.

        Args:
            route_id: Filter by route ID
            user_id: Filter by user ID
            day: Filter by day of week
            is_active: Filter by active status
            from_date: Filter by assignments starting from this date
            to_date: Filter by assignments ending before this date
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Count of route assignments

        Raises:
            RouteAssignmentOperationException: If counting fails
        """
        if connection:
            return await self._count_route_assignments(
                connection, route_id, user_id, day, is_active, from_date, to_date
            )

        async with self.db_pool.acquire() as conn:
            return await self._count_route_assignments(
                conn, route_id, user_id, day, is_active, from_date, to_date
            )

    async def _update_route_assignment(
        self,
        assignment_id: int,
        assignment_data: RouteAssignmentUpdate,
        connection: asyncpg.Connection,
    ) -> RouteAssignmentInDB:
        """
        Private method to update a route assignment with a provided connection.

        Args:
            assignment_id: ID of the route assignment to update
            assignment_data: Route assignment data to update
            connection: Database connection

        Returns:
            Updated route assignment

        Raises:
            RouteAssignmentNotFoundException: If route assignment not found
            RouteAssignmentOperationException: If update fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Check if assignment exists
            await self._get_route_assignment_by_id(assignment_id, connection)

            # Build dynamic update query
            update_fields = []
            params = []
            param_count = 0

            if assignment_data.from_date is not None:
                param_count += 1
                update_fields.append(f"from_date = ${param_count}")
                params.append(assignment_data.from_date)

            if assignment_data.to_date is not None:
                param_count += 1
                update_fields.append(f"to_date = ${param_count}")
                params.append(assignment_data.to_date)

            if assignment_data.day is not None:
                param_count += 1
                update_fields.append(f"day = ${param_count}")
                params.append(assignment_data.day)

            if not update_fields:
                # No fields to update, fetch and return current assignment
                row = await connection.fetchrow(
                    """
                    SELECT id, route_id, user_id, from_date, to_date, day, is_active, created_at, updated_at
                    FROM route_assignment
                    WHERE id = $1
                    """,
                    assignment_id,
                )
                return RouteAssignmentInDB(**dict(row))

            param_count += 1
            params.append(assignment_id)

            query = f"""
                UPDATE route_assignment
                SET {", ".join(update_fields)}
                WHERE id = ${param_count}
                RETURNING id, route_id, user_id, from_date, to_date, day, is_active, created_at, updated_at
            """

            row = await connection.fetchrow(query, *params)

            if not row:
                raise RouteAssignmentNotFoundException(assignment_id=assignment_id)

            logger.info(
                "Route assignment updated successfully",
                assignment_id=assignment_id,
                company_id=str(self.company_id),
            )

            return RouteAssignmentInDB(**dict(row))

        except (
            RouteAssignmentNotFoundException,
            RouteAssignmentAlreadyExistsException,
        ):
            raise
        except asyncpg.CheckViolationError as e:
            if "check_valid_date_range" in str(e):
                raise InvalidDateRangeException(
                    message="End date must be greater than or equal to start date"
                )
            elif "check_day_valid" in str(e):
                raise RouteAssignmentOperationException(
                    message="Day must be between 0 and 6",
                    operation="update",
                ) from e
            else:
                raise RouteAssignmentOperationException(
                    message=f"Failed to update route assignment: {str(e)}",
                    operation="update",
                ) from e
        except Exception as e:
            logger.error(
                "Failed to update route assignment",
                assignment_id=assignment_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RouteAssignmentOperationException(
                message=f"Failed to update route assignment: {str(e)}",
                operation="update",
            ) from e

    async def update_route_assignment(
        self,
        assignment_id: int,
        assignment_data: RouteAssignmentUpdate,
        connection: Optional[asyncpg.Connection] = None,
    ) -> RouteAssignmentInDB:
        """
        Update an existing route assignment.

        Args:
            assignment_id: ID of the route assignment to update
            assignment_data: Route assignment data to update
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Updated route assignment

        Raises:
            RouteAssignmentNotFoundException: If route assignment not found
            RouteAssignmentOperationException: If update fails
        """
        if connection:
            return await self._update_route_assignment(
                assignment_id, assignment_data, connection
            )

        async with self.db_pool.acquire() as conn:
            return await self._update_route_assignment(
                assignment_id, assignment_data, conn
            )

    async def _delete_route_assignment(
        self, assignment_id: int, connection: asyncpg.Connection
    ) -> RouteAssignmentInDB:
        """
        Private method to soft delete a route assignment (set is_active=False) with a provided connection.

        Args:
            assignment_id: ID of the route assignment to soft delete
            connection: Database connection

        Returns:
            Updated route assignment with is_active=False

        Raises:
            RouteAssignmentNotFoundException: If route assignment not found
            RouteAssignmentOperationException: If soft deletion fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Check if assignment exists
            await self._get_route_assignment_by_id(assignment_id, connection)

            # Soft delete assignment
            row = await connection.fetchrow(
                """
                UPDATE route_assignment
                SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
                WHERE id = $1
                RETURNING id, route_id, user_id, from_date, to_date, day, is_active, created_at, updated_at
                """,
                assignment_id,
            )

            logger.info(
                "Route assignment soft deleted successfully",
                assignment_id=assignment_id,
                company_id=str(self.company_id),
            )

            return RouteAssignmentInDB(**dict(row))

        except RouteAssignmentNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to soft delete route assignment",
                assignment_id=assignment_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RouteAssignmentOperationException(
                message=f"Failed to soft delete route assignment: {str(e)}",
                operation="soft_delete",
            ) from e

    async def delete_route_assignment(
        self, assignment_id: int, connection: Optional[asyncpg.Connection] = None
    ) -> RouteAssignmentInDB:
        """
        Delete a route assignment by setting is_active to False.

        Args:
            assignment_id: ID of the route assignment to delete
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Updated route assignment with is_active=False

        Raises:
            RouteAssignmentNotFoundException: If route assignment not found
            RouteAssignmentOperationException: If soft deletion fails
        """
        if connection:
            return await self._delete_route_assignment(assignment_id, connection)

        async with self.db_pool.acquire() as conn:
            return await self._delete_route_assignment(assignment_id, conn)

    async def _get_assignments_by_route(
        self,
        route_id: int,
        connection: asyncpg.Connection,
        is_active: Optional[bool] = True,
    ) -> list[RouteAssignmentListItem]:
        """
        Private method to get all assignments for a specific route.

        Args:
            route_id: ID of the route
            connection: Database connection
            is_active: Filter by active status (defaults to True)

        Returns:
            List of route assignments

        Raises:
            RouteAssignmentOperationException: If retrieval fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            query = """
                SELECT ra.id, ra.route_id, r.name as route_name, r.code as route_code,
                       ra.user_id, u.name as user_name,
                       ra.from_date, ra.to_date, ra.day, ra.is_active
                FROM route_assignment ra
                INNER JOIN routes r ON ra.route_id = r.id
                INNER JOIN members m ON ra.user_id = m.id
                INNER JOIN salesforce.users u ON m.id = u.id
                WHERE ra.route_id = $1
            """
            params = [route_id]

            if is_active is not None:
                query += " AND ra.is_active = $2"
                params.append(is_active)

            query += " ORDER BY ra.from_date DESC, ra.day ASC"

            rows = await connection.fetch(query, *params)

            return [RouteAssignmentListItem(**dict(row)) for row in rows]

        except Exception as e:
            logger.error(
                "Failed to get assignments by route",
                route_id=route_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RouteAssignmentOperationException(
                message=f"Failed to get assignments by route: {str(e)}",
                operation="get_by_route",
            ) from e

    async def get_assignments_by_route(
        self,
        route_id: int,
        is_active: Optional[bool] = True,
        connection: Optional[asyncpg.Connection] = None,
    ) -> list[RouteAssignmentListItem]:
        """
        Get all assignments for a specific route.

        Args:
            route_id: ID of the route
            is_active: Filter by active status (defaults to True)
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            List of route assignments

        Raises:
            RouteAssignmentOperationException: If retrieval fails
        """
        if connection:
            return await self._get_assignments_by_route(route_id, connection, is_active)

        async with self.db_pool.acquire() as conn:
            return await self._get_assignments_by_route(route_id, conn, is_active)

    async def _get_assignments_by_user(
        self,
        user_id: UUID,
        connection: asyncpg.Connection,
        is_active: Optional[bool] = True,
    ) -> list[RouteAssignmentListItem]:
        """
        Private method to get all assignments for a specific user.

        Args:
            user_id: ID of the user
            connection: Database connection
            is_active: Filter by active status (defaults to True)

        Returns:
            List of route assignments

        Raises:
            RouteAssignmentOperationException: If retrieval fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            query = """
                SELECT ra.id, ra.route_id, r.name as route_name, r.code as route_code,
                       ra.user_id, u.name as user_name,
                       ra.from_date, ra.to_date, ra.day, ra.is_active
                FROM route_assignment ra
                INNER JOIN routes r ON ra.route_id = r.id
                INNER JOIN members m ON ra.user_id = m.id
                INNER JOIN salesforce.users u ON m.id = u.id
                WHERE ra.user_id = $1
            """
            params = [user_id]

            if is_active is not None:
                query += " AND ra.is_active = $2"
                params.append(is_active)

            query += " ORDER BY ra.from_date DESC, ra.day ASC"

            rows = await connection.fetch(query, *params)

            return [RouteAssignmentListItem(**dict(row)) for row in rows]

        except Exception as e:
            logger.error(
                "Failed to get assignments by user",
                user_id=str(user_id),
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RouteAssignmentOperationException(
                message=f"Failed to get assignments by user: {str(e)}",
                operation="get_by_user",
            ) from e

    async def get_assignments_by_user(
        self,
        user_id: UUID,
        is_active: Optional[bool] = True,
        connection: Optional[asyncpg.Connection] = None,
    ) -> list[RouteAssignmentListItem]:
        """
        Get all assignments for a specific user.

        Args:
            user_id: ID of the user
            is_active: Filter by active status (defaults to True)
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            List of route assignments

        Raises:
            RouteAssignmentOperationException: If retrieval fails
        """
        if connection:
            return await self._get_assignments_by_user(user_id, connection, is_active)

        async with self.db_pool.acquire() as conn:
            return await self._get_assignments_by_user(user_id, conn, is_active)
