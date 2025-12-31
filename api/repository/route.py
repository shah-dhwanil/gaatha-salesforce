"""
Repository for Route entity operations.

This repository handles all database operations for routes in a multi-tenant architecture.
Routes are stored per tenant schema and are associated with areas.
"""

from typing import Optional
from uuid import UUID

import asyncpg
import structlog

from api.database import DatabasePool
from api.exceptions.route import (
    RouteAlreadyExistsException,
    RouteNotFoundException,
    RouteOperationException,
)
from api.models.route import RouteCreate, RouteDetailItem, RouteInDB, RouteListItem, RouteUpdate
from api.repository.utils import get_schema_name, set_search_path

logger = structlog.get_logger(__name__)


class RouteRepository:
    """
    Repository for managing Route entities in a multi-tenant database.

    This repository provides methods for CRUD operations on routes,
    handling schema-per-tenant isolation using asyncpg.
    All methods raise exceptions when records are not found.
    """

    def __init__(self, db_pool: DatabasePool, company_id: UUID) -> None:
        """
        Initialize the RouteRepository.

        Args:
            db_pool: Database pool instance for connection management
            company_id: UUID of the company (tenant) for schema isolation
        """
        self.db_pool = db_pool
        self.company_id = company_id
        self.schema_name = get_schema_name(company_id)

    async def _create_route(
        self, route_data: RouteCreate, connection: asyncpg.Connection
    ) -> RouteInDB:
        """
        Private method to create a route with a provided connection.

        Args:
            route_data: Route data to create
            connection: Database connection

        Returns:
            Created route

        Raises:
            RouteAlreadyExistsException: If route with the same code already exists
            RouteOperationException: If creation fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Insert the route
            row = await connection.fetchrow(
                """
                INSERT INTO routes (name, code, area_id, is_general, is_modern, is_horeca, is_active)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id, name, code, area_id, is_general, is_modern, is_horeca,
                          is_active, created_at, updated_at
                """,
                route_data.name,
                route_data.code,
                route_data.area_id,
                route_data.is_general,
                route_data.is_modern,
                route_data.is_horeca,
                route_data.is_active,
            )

            logger.info(
                "Route created successfully",
                route_id=row["id"],
                route_code=route_data.code,
                route_name=route_data.name,
                company_id=str(self.company_id),
            )
            return RouteInDB(**dict(row))
        except asyncpg.UniqueViolationError as e:
            if "uniq_routes_code" in str(e):
                raise RouteAlreadyExistsException(route_code=route_data.code)
            else:
                raise RouteOperationException(
                    message=f"Failed to create route: {str(e)}",
                    operation="create",
                ) from e
        except asyncpg.ForeignKeyViolationError as e:
            if "fk_routes_area_id" in str(e):
                raise RouteOperationException(
                    message=f"Area with id {route_data.area_id} not found",
                    operation="create",
                ) from e
            else:
                raise RouteOperationException(
                    message=f"Failed to create route: {str(e)}",
                    operation="create",
                ) from e
        except Exception as e:
            logger.error(
                "Failed to create route",
                route_code=route_data.code,
                route_name=route_data.name,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RouteOperationException(
                message=f"Failed to create route: {str(e)}",
                operation="create",
            ) from e

    async def create_route(
        self, route_data: RouteCreate, connection: Optional[asyncpg.Connection] = None
    ) -> RouteInDB:
        """
        Create a new route.

        Args:
            route_data: Route data to create
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Created route

        Raises:
            RouteAlreadyExistsException: If route with the same code already exists
            RouteOperationException: If creation fails
        """
        if connection:
            return await self._create_route(route_data, connection)

        async with self.db_pool.acquire() as conn:
            return await self._create_route(route_data, conn)

    async def _get_route_by_id(
        self, route_id: int, connection: asyncpg.Connection
    ) -> RouteDetailItem:
        """
        Private method to get a route by ID with a provided connection.

        Args:
            route_id: ID of the route
            connection: Database connection

        Returns:
            Route

        Raises:
            RouteNotFoundException: If route not found
            RouteOperationException: If retrieval fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            row = await connection.fetchrow(
                """
                SELECT rs.id, rs.name, rs.code, rs.area_id, d.name as division_name, a.name as area_name, r.name as region_name, z.name as zone_name, n.name as nation_name, 
                    rs.is_general, rs.is_modern, rs.is_horeca, rs.is_active, rs.created_at, rs.updated_at
                FROM routes rs
                INNER JOIN areas d ON rs.area_id = d.id
                INNER JOIN areas a ON a.id = d.area_id 
                INNER JOIN areas r ON r.id = a.region_id 
                INNER JOIN areas z ON z.id = r.zone_id 
                INNER JOIN areas n ON n.id = z.nation_id 
                WHERE rs.id = $1
                """,
                route_id,
            )

            if not row:
                raise RouteNotFoundException(route_id=route_id)

            return RouteDetailItem(**dict(row))

        except RouteNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to get route by id",
                route_id=route_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RouteOperationException(
                message=f"Failed to get route: {str(e)}",
                operation="get",
            ) from e

    async def get_route_by_id(
        self, route_id: int, connection: Optional[asyncpg.Connection] = None
    ) -> RouteDetailItem:
        """
        Get a route by ID.

        Args:
            route_id: ID of the route
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Route

        Raises:
            RouteNotFoundException: If route not found
            RouteOperationException: If retrieval fails
        """
        if connection:
            return await self._get_route_by_id(route_id, connection)

        async with self.db_pool.acquire() as conn:
            return await self._get_route_by_id(route_id, conn)

    async def _get_route_by_code(
        self, code: str, connection: asyncpg.Connection
    ) -> RouteDetailItem:
        """
        Private method to get a route by code with a provided connection.

        Args:
            code: Code of the route
            connection: Database connection

        Returns:
            Route

        Raises:
            RouteNotFoundException: If route not found
            RouteOperationException: If retrieval fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            row = await connection.fetchrow(
                """
                SELECT rs.id, rs.name, rs.code, rs.area_id, d.name as division_name, a.name as area_name, r.name as region_name, z.name as zone_name, n.name as nation_name, 
                    rs.is_general, rs.is_modern, rs.is_horeca, rs.is_active, rs.created_at, rs.updated_at
                FROM routes rs
                INNER JOIN areas d ON rs.area_id = d.id
                INNER JOIN areas a ON a.id = d.area_id 
                INNER JOIN areas r ON r.id = a.region_id 
                INNER JOIN areas z ON z.id = r.zone_id 
                INNER JOIN areas n ON n.id = z.nation_id 
                WHERE code = $1 AND is_active = true
                """,
                code,
            )

            if not row:
                raise RouteNotFoundException(route_code=code)

            return RouteDetailItem(**dict(row))

        except RouteNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to get route by code",
                route_code=code,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RouteOperationException(
                message=f"Failed to get route: {str(e)}",
                operation="get",
            ) from e

    async def get_route_by_code(
        self, code: str, connection: Optional[asyncpg.Connection] = None
    ) -> RouteDetailItem:
        """
        Get a route by code.

        Args:
            code: Code of the route
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Route

        Raises:
            RouteNotFoundException: If route not found
            RouteOperationException: If retrieval fails
        """
        if connection:
            return await self._get_route_by_code(code, connection)

        async with self.db_pool.acquire() as conn:
            return await self._get_route_by_code(code, conn)

    async def _list_routes(
        self,
        connection: asyncpg.Connection,
        area_id: Optional[int] = None,
        is_active: Optional[bool] = None,
        is_general: Optional[bool] = None,
        is_modern: Optional[bool] = None,
        is_horeca: Optional[bool] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[RouteListItem]:
        """
        Private method to list routes with a provided connection.
        Returns minimal data to optimize performance including retailer count per route.

        Args:
            connection: Database connection
            area_id: Filter by area ID
            is_active: Filter by active status
            is_general: Filter by general status
            is_modern: Filter by modern status
            is_horeca: Filter by horeca status
            limit: Maximum number of routes to return
            offset: Number of routes to skip

        Returns:
            List of routes with minimal data including retailer count

        Raises:
            RouteOperationException: If listing fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Build dynamic query
            query = """
                SELECT rs.id, rs.name, rs.code, rs.is_general, rs.is_modern, rs.is_horeca, rs.area_id,
                       d.name as division_name, a.name as area_name, r.name as region_name, rs.is_active,
                       COUNT(ret.id) as retailer_count
                FROM routes rs
                INNER JOIN areas d ON rs.area_id = d.id
                INNER JOIN areas a ON a.id = d.area_id
                INNER JOIN areas r ON r.id = a.region_id
                LEFT JOIN retailer ret ON ret.route_id = rs.id AND ret.is_active = true

            """
            params = []
            param_count = 0
            conditions = []

            # Add WHERE conditions
            if area_id is not None:
                param_count += 1
                conditions.append(f"rs.area_id = ${param_count}")
                params.append(area_id)

            if is_active is not None:
                param_count += 1
                conditions.append(f"rs.is_active = ${param_count}")
                params.append(is_active)

            if is_general is not None:
                param_count += 1
                conditions.append(f"rs.is_general = ${param_count}")
                params.append(is_general)

            if is_modern is not None:
                param_count += 1
                conditions.append(f"rs.is_modern = ${param_count}")
                params.append(is_modern)

            if is_horeca is not None:
                param_count += 1
                conditions.append(f"rs.is_horeca = ${param_count}")
                params.append(is_horeca)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            # Add GROUP BY clause for aggregation
            query += """
                GROUP BY rs.id, rs.name, rs.code, rs.is_general, rs.is_modern, rs.is_horeca,
                         rs.area_id, d.name, a.name, r.name, rs.is_active
            """

            # Add ordering
            query += " ORDER BY rs.code ASC"

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

            return [RouteListItem(**dict(row)) for row in rows]

        except Exception as e:
            logger.error(
                "Failed to list routes",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RouteOperationException(
                message=f"Failed to list routes: {str(e)}",
                operation="list",
            ) from e

    async def list_routes(
        self,
        area_id: Optional[int] = None,
        is_active: Optional[bool] = None,
        is_general: Optional[bool] = None,
        is_modern: Optional[bool] = None,
        is_horeca: Optional[bool] = None,
        limit: int = 20,
        offset: int = 0,
        connection: Optional[asyncpg.Connection] = None,
    ) -> list[RouteListItem]:
        """
        List all routes with optional filtering.
        Returns minimal data to optimize performance including retailer count per route.

        Args:
            area_id: Filter by area ID
            is_active: Filter by active status
            is_general: Filter by general status
            is_modern: Filter by modern status
            is_horeca: Filter by horeca status
            limit: Maximum number of routes to return
            offset: Number of routes to skip
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            List of routes with minimal data including retailer count

        Raises:
            RouteOperationException: If listing fails
        """
        if connection:
            return await self._list_routes(
                connection, area_id, is_active, is_general, is_modern, is_horeca, limit, offset
            )

        async with self.db_pool.acquire() as conn:
            return await self._list_routes(
                conn, area_id, is_active, is_general, is_modern, is_horeca, limit, offset
            )

    async def _count_routes(
        self,
        connection: asyncpg.Connection,
        area_id: Optional[int] = None,
        is_active: Optional[bool] = None,
        is_general: Optional[bool] = None,
        is_modern: Optional[bool] = None,
        is_horeca: Optional[bool] = None,
    ) -> int:
        """
        Private method to count routes with a provided connection.

        Args:
            connection: Database connection
            area_id: Filter by area ID
            is_active: Filter by active status
            is_general: Filter by general status
            is_modern: Filter by modern status
            is_horeca: Filter by horeca status

        Returns:
            Count of routes

        Raises:
            RouteOperationException: If counting fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Build dynamic query
            query = "SELECT COUNT(*) FROM routes"
            params = []
            param_count = 0
            conditions = []

            if area_id is not None:
                param_count += 1
                conditions.append(f"area_id = ${param_count}")
                params.append(area_id)

            if is_active is not None:
                param_count += 1
                conditions.append(f"is_active = ${param_count}")
                params.append(is_active)

            if is_general is not None:
                param_count += 1
                conditions.append(f"is_general = ${param_count}")
                params.append(is_general)

            if is_modern is not None:
                param_count += 1
                conditions.append(f"is_modern = ${param_count}")
                params.append(is_modern)

            if is_horeca is not None:
                param_count += 1
                conditions.append(f"is_horeca = ${param_count}")
                params.append(is_horeca)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            count = await connection.fetchval(query, *params)
            return count or 0

        except Exception as e:
            logger.error(
                "Failed to count routes",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RouteOperationException(
                message=f"Failed to count routes: {str(e)}",
                operation="count",
            ) from e

    async def count_routes(
        self,
        area_id: Optional[int] = None,
        is_active: Optional[bool] = None,
        is_general: Optional[bool] = None,
        is_modern: Optional[bool] = None,
        is_horeca: Optional[bool] = None,
        connection: Optional[asyncpg.Connection] = None,
    ) -> int:
        """
        Count routes with optional filtering.

        Args:
            area_id: Filter by area ID
            is_active: Filter by active status
            is_general: Filter by general status
            is_modern: Filter by modern status
            is_horeca: Filter by horeca status
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Count of routes

        Raises:
            RouteOperationException: If counting fails
        """
        if connection:
            return await self._count_routes(
                connection, area_id, is_active, is_general, is_modern, is_horeca
            )

        async with self.db_pool.acquire() as conn:
            return await self._count_routes(
                conn, area_id, is_active, is_general, is_modern, is_horeca
            )

    async def _update_route(
        self,
        route_id: int,
        route_data: RouteUpdate,
        connection: asyncpg.Connection,
    ) -> RouteInDB:
        """
        Private method to update a route with a provided connection.

        Args:
            route_id: ID of the route to update
            route_data: Route data to update
            connection: Database connection

        Returns:
            Updated route

        Raises:
            RouteNotFoundException: If route not found
            RouteOperationException: If update fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Check if route exists
            await self._get_route_by_id(route_id, connection)

            # Build dynamic update query
            update_fields = []
            params = []
            param_count = 0

            if route_data.name is not None:
                param_count += 1
                update_fields.append(f"name = ${param_count}")
                params.append(route_data.name)
            
            if route_data.area_id is not None:
                param_count += 1
                update_fields.append(f"area_id = ${param_count}")
                params.append(route_data.area_id)

            if route_data.is_general is not None:
                param_count += 1
                update_fields.append(f"is_general = ${param_count}")
                params.append(route_data.is_general)

            if route_data.is_modern is not None:
                param_count += 1
                update_fields.append(f"is_modern = ${param_count}")
                params.append(route_data.is_modern)

            if route_data.is_horeca is not None:
                param_count += 1
                update_fields.append(f"is_horeca = ${param_count}")
                params.append(route_data.is_horeca)

            if not update_fields:
                # No fields to update, return current route
                return await self._get_route_by_id(route_id, connection)

            param_count += 1
            params.append(route_id)

            query = f"""
                UPDATE routes
                SET {", ".join(update_fields)}
                WHERE id = ${param_count}
                RETURNING id, name, code, area_id, is_general, is_modern, is_horeca,
                          is_active, created_at, updated_at
            """

            row = await connection.fetchrow(query, *params)

            if not row:
                raise RouteNotFoundException(route_id=route_id)

            logger.info(
                "Route updated successfully",
                route_id=route_id,
                company_id=str(self.company_id),
            )

            return RouteInDB(**dict(row))

        except (RouteNotFoundException, RouteAlreadyExistsException):
            raise
        except Exception as e:
            logger.error(
                "Failed to update route",
                route_id=route_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RouteOperationException(
                message=f"Failed to update route: {str(e)}",
                operation="update",
            ) from e

    async def update_route(
        self,
        route_id: int,
        route_data: RouteUpdate,
        connection: Optional[asyncpg.Connection] = None,
    ) -> RouteInDB:
        """
        Update an existing route.

        Args:
            route_id: ID of the route to update
            route_data: Route data to update
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Updated route

        Raises:
            RouteNotFoundException: If route not found
            RouteOperationException: If update fails
        """
        if connection:
            return await self._update_route(route_id, route_data, connection)

        async with self.db_pool.acquire() as conn:
            return await self._update_route(route_id, route_data, conn)

    async def _delete_route(
        self, route_id: int, connection: asyncpg.Connection
    ) -> RouteInDB:
        """
        Private method to soft delete a route (set is_active=False) with a provided connection.

        Args:
            route_id: ID of the route to soft delete
            connection: Database connection

        Returns:
            Updated route with is_active=False

        Raises:
            RouteNotFoundException: If route not found
            RouteOperationException: If soft deletion fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Check if route exists
            await self._get_route_by_id(route_id, connection)

            # Soft delete route
            await connection.execute(
                "UPDATE routes SET is_active = FALSE WHERE id = $1",
                route_id,
            )

            logger.info(
                "Route soft deleted successfully",
                route_id=route_id,
                company_id=str(self.company_id),
            )

            return await self._get_route_by_id(route_id, connection)

        except RouteNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to soft delete route",
                route_id=route_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RouteOperationException(
                message=f"Failed to soft delete route: {str(e)}",
                operation="soft_delete",
            ) from e

    async def delete_route(
        self, route_id: int, connection: Optional[asyncpg.Connection] = None
    ) -> None:
        """
        Delete a route by setting is_active to False.

        Args:
            route_id: ID of the route to delete
            connection: Optional database connection. If not provided, a new one is acquired.
        """
        if connection:
            return await self._delete_route(route_id, connection)

        async with self.db_pool.acquire() as conn:
            return await self._delete_route(route_id, conn)

    async def _get_routes_by_area(
        self,
        area_id: int,
        connection: asyncpg.Connection,
    ) -> list[RouteListItem]:
        """
        Private method to get all routes for a specific area.

        Args:
            area_id: ID of the area
            connection: Database connection

        Returns:
            List of routes

        Raises:
            RouteOperationException: If retrieval fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            rows = await connection.fetch(
                """
                SELECT rs.id, rs.name, rs.code, rs.area_id, d.name as division_name, a.name as area_name, r.name as region_name,
                    rs.is_general, rs.is_modern, rs.is_horeca, rs.is_active
                FROM routes rs
                INNER JOIN areas d ON rs.area_id = d.id
                INNER JOIN areas a ON a.id = d.area_id
                INNER JOIN areas r ON r.id = a.region_id
                WHERE rs.area_id = $1 AND rs.is_active = true
                ORDER BY rs.code ASC
                """,
                area_id,
            )

            return [RouteListItem(**dict(row)) for row in rows]

        except Exception as e:
            logger.error(
                "Failed to get routes by area",
                area_id=area_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RouteOperationException(
                message=f"Failed to get routes by area: {str(e)}",
                operation="get_by_area",
            ) from e

    async def get_routes_by_area(
        self,
        area_id: int,
        connection: Optional[asyncpg.Connection] = None,
    ) -> list[RouteListItem]:
        """
        Get all routes for a specific area.

        Args:
            area_id: ID of the area
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            List of routes

        Raises:
            RouteOperationException: If retrieval fails
        """
        if connection:
            return await self._get_routes_by_area(area_id, connection)

        async with self.db_pool.acquire() as conn:
            return await self._get_routes_by_area(area_id, conn)

