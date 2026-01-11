"""
Repository for Area entity operations.

This repository handles all database operations for areas in the hierarchy
(NATION, ZONE, REGION, AREA, DIVISION) in a multi-tenant architecture.
Areas are stored per tenant schema.
"""

from typing import Optional
from uuid import UUID

import asyncpg
import structlog

from api.database import DatabasePool
from api.exceptions.area import (
    AreaAlreadyExistsException,
    AreaNotFoundException,
    AreaOperationException,
)
from api.models.area import AreaCreate, AreaInDB, AreaListItem, AreaUpdate
from api.repository.utils import get_schema_name, set_search_path

logger = structlog.get_logger(__name__)


class AreaRepository:
    """
    Repository for managing Area entities in a multi-tenant database.

    This repository provides methods for CRUD operations on areas,
    handling schema-per-tenant isolation using asyncpg.
    All methods raise exceptions when records are not found.
    """

    def __init__(self, db_pool: DatabasePool, company_id: UUID) -> None:
        """
        Initialize the AreaRepository.

        Args:
            db_pool: Database pool instance for connection management
            company_id: UUID of the company (tenant) for schema isolation
        """
        self.db_pool = db_pool
        self.company_id = company_id
        self.schema_name = get_schema_name(company_id)

    async def _create_area(
        self, area_data: AreaCreate, connection: asyncpg.Connection
    ) -> AreaInDB:
        """
        Private method to create an area with a provided connection.

        Args:
            area_data: Area data to create
            connection: Database connection

        Returns:
            Created area

        Raises:
            AreaAlreadyExistsException: If area with the same name and type already exists
            AreaOperationException: If creation fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Insert the area
            row = await connection.fetchrow(
                """
                INSERT INTO areas (name, type, area_id, region_id, zone_id, nation_id)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id, name, type, area_id, region_id, zone_id, nation_id, 
                          is_active, created_at, updated_at
                """,
                area_data.name,
                area_data.type,
                area_data.area_id,
                area_data.region_id,
                area_data.zone_id,
                area_data.nation_id,
            )

            logger.info(
                "Area created successfully",
                area_id=row["id"],
                area_name=area_data.name,
                area_type=area_data.type,
                company_id=str(self.company_id),
            )
            return AreaInDB(**dict(row))
        except asyncpg.UniqueViolationError as e:
            if "uniq_area_name_type" in str(e):
                raise AreaAlreadyExistsException(
                    area_name=area_data.name, area_type=area_data.type
                )
            elif "pk_areas" in str(e):
                raise AreaNotFoundException(
                    area_name=area_data.name, area_type=area_data.type
                )
            else:
                raise AreaOperationException(
                    message=f"Failed to create area: {str(e)}",
                    operation="create",
                ) from e
        except asyncpg.ForeignKeyViolationError as e:
            if "area_id" in str(e):
                raise AreaNotFoundException(area_id=area_data.area_id)
            elif "region_id" in str(e):
                raise AreaNotFoundException(area_id=area_data.region_id)
            elif "zone_id" in str(e):
                raise AreaNotFoundException(area_id=area_data.zone_id)
            elif "nation_id" in str(e):
                raise AreaNotFoundException(area_id=area_data.nation_id)
            else:
                raise AreaNotFoundException(area_id=area_data.id) from e
        except Exception as e:
            logger.error(
                "Failed to create area",
                area_name=area_data.name,
                area_type=area_data.type,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise AreaOperationException(
                message=f"Failed to create area: {str(e)}",
                operation="create",
            ) from e

    async def create_area(
        self, area_data: AreaCreate, connection: Optional[asyncpg.Connection] = None
    ) -> AreaInDB:
        """
        Create a new area.

        Args:
            area_data: Area data to create
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Created area

        Raises:
            AreaAlreadyExistsException: If area with the same name and type already exists
            AreaOperationException: If creation fails
        """
        if connection:
            return await self._create_area(area_data, connection)

        async with self.db_pool.acquire() as conn:
            return await self._create_area(area_data, conn)

    async def _get_area_by_id(
        self, area_id: int, connection: asyncpg.Connection
    ) -> AreaInDB:
        """
        Private method to get an area by ID with a provided connection.

        Args:
            area_id: ID of the area
            connection: Database connection

        Returns:
            Area

        Raises:
            AreaNotFoundException: If area not found
            AreaOperationException: If retrieval fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            row = await connection.fetchrow(
                """
                SELECT id, name, type, area_id, region_id, zone_id, nation_id,
                       is_active, created_at, updated_at
                FROM areas
                WHERE id = $1
                """,
                area_id,
            )

            if not row:
                raise AreaNotFoundException(area_id=area_id)

            return AreaInDB(**dict(row))

        except AreaNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to get area by id",
                area_id=area_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise AreaOperationException(
                message=f"Failed to get area: {str(e)}",
                operation="get",
            ) from e

    async def get_area_by_id(
        self, area_id: int, connection: Optional[asyncpg.Connection] = None
    ) -> AreaInDB:
        """
        Get an area by ID.

        Args:
            area_id: ID of the area
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Area

        Raises:
            AreaNotFoundException: If area not found
            AreaOperationException: If retrieval fails
        """
        if connection:
            return await self._get_area_by_id(area_id, connection)

        async with self.db_pool.acquire() as conn:
            return await self._get_area_by_id(area_id, conn)

    async def _get_area_by_name_and_type(
        self, name: str, area_type: str, connection: asyncpg.Connection
    ) -> AreaInDB:
        """
        Private method to get an area by name and type with a provided connection.

        Args:
            name: Name of the area
            area_type: Type of the area (NATION, ZONE, REGION, AREA, DIVISION)
            connection: Database connection

        Returns:
            Area

        Raises:
            AreaNotFoundException: If area not found
            AreaOperationException: If retrieval fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            row = await connection.fetchrow(
                """
                SELECT id, name, type, area_id, region_id, zone_id, nation_id,
                       is_active, created_at, updated_at
                FROM areas
                WHERE name = $1 AND type = $2 AND is_active = true
                """,
                name,
                area_type,
            )

            if not row:
                raise AreaNotFoundException(area_name=name, area_type=area_type)

            return AreaInDB(**dict(row))

        except AreaNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to get area by name and type",
                area_name=name,
                area_type=area_type,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise AreaOperationException(
                message=f"Failed to get area: {str(e)}",
                operation="get",
            ) from e

    async def get_area_by_name_and_type(
        self, name: str, area_type: str, connection: Optional[asyncpg.Connection] = None
    ) -> AreaInDB:
        """
        Get an area by name and type.

        Args:
            name: Name of the area
            area_type: Type of the area (NATION, ZONE, REGION, AREA, DIVISION)
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Area

        Raises:
            AreaNotFoundException: If area not found
            AreaOperationException: If retrieval fails
        """
        if connection:
            return await self._get_area_by_name_and_type(name, area_type, connection)

        async with self.db_pool.acquire() as conn:
            return await self._get_area_by_name_and_type(name, area_type, conn)

    async def _list_areas(
        self,
        connection: asyncpg.Connection,
        area_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        parent_id: Optional[int] = None,
        parent_type: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[AreaListItem]:
        """
        Private method to list areas with a provided connection.
        Returns minimal data to optimize performance.

        Args:
            connection: Database connection
            area_type: Filter by area type (NATION, ZONE, REGION, AREA, DIVISION)
            is_active: Filter by active status
            parent_id: Filter by parent area ID
            parent_type: Filter by parent type (nation_id, zone_id, region_id, area_id)
            limit: Maximum number of areas to return
            offset: Number of areas to skip

        Returns:
            List of areas with minimal data

        Raises:
            AreaOperationException: If listing fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Build dynamic query
            query = """
                SELECT id, name, type, is_active
                FROM areas     
            """
            params = []
            param_count = 0
            conditions = []

            # Add WHERE conditions
            if area_type is not None:
                param_count += 1
                conditions.append(f"type = ${param_count}")
                params.append(area_type)

            if is_active is not None:
                param_count += 1
                conditions.append(f"is_active = ${param_count}")
                params.append(is_active)

            if parent_id is not None and parent_type is not None:
                # Map parent_type to column name
                parent_column_map = {
                    "nation": "nation_id",
                    "zone": "zone_id",
                    "region": "region_id",
                    "area": "area_id",
                }
                if parent_type.lower() in parent_column_map:
                    param_count += 1
                    column_name = parent_column_map[parent_type.lower()]
                    conditions.append(f"{column_name} = ${param_count}")
                    params.append(parent_id)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            # Add ordering
            query += " ORDER BY name ASC"

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

            return [AreaListItem(**dict(row)) for row in rows]

        except Exception as e:
            logger.error(
                "Failed to list areas",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise AreaOperationException(
                message=f"Failed to list areas: {str(e)}",
                operation="list",
            ) from e

    async def list_areas(
        self,
        area_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        parent_id: Optional[int] = None,
        parent_type: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
        connection: Optional[asyncpg.Connection] = None,
    ) -> list[AreaListItem]:
        """
        List all areas with optional filtering.
        Returns minimal data to optimize performance.

        Args:
            area_type: Filter by area type (NATION, ZONE, REGION, AREA, DIVISION)
            is_active: Filter by active status
            parent_id: Filter by parent area ID
            parent_type: Filter by parent type (nation, zone, region, area)
            limit: Maximum number of areas to return
            offset: Number of areas to skip
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            List of areas with minimal data

        Raises:
            AreaOperationException: If listing fails
        """
        if connection:
            return await self._list_areas(
                connection, area_type, is_active, parent_id, parent_type, limit, offset
            )

        async with self.db_pool.acquire() as conn:
            return await self._list_areas(
                conn, area_type, is_active, parent_id, parent_type, limit, offset
            )

    async def _count_areas(
        self,
        connection: asyncpg.Connection,
        area_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        parent_id: Optional[int] = None,
        parent_type: Optional[str] = None,
    ) -> int:
        """
        Private method to count areas with a provided connection.

        Args:
            connection: Database connection
            area_type: Filter by area type
            is_active: Filter by active status
            parent_id: Filter by parent area ID
            parent_type: Filter by parent type (nation, zone, region, area)

        Returns:
            Count of areas

        Raises:
            AreaOperationException: If counting fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Build dynamic query
            query = "SELECT COUNT(*) FROM areas"
            params = []
            param_count = 0
            conditions = []

            if area_type is not None:
                param_count += 1
                conditions.append(f"type = ${param_count}")
                params.append(area_type)

            if is_active is not None:
                param_count += 1
                conditions.append(f"is_active = ${param_count}")
                params.append(is_active)

            if parent_id is not None and parent_type is not None:
                parent_column_map = {
                    "nation": "nation_id",
                    "zone": "zone_id",
                    "region": "region_id",
                    "area": "area_id",
                }
                if parent_type.lower() in parent_column_map:
                    param_count += 1
                    column_name = parent_column_map[parent_type.lower()]
                    conditions.append(f"{column_name} = ${param_count}")
                    params.append(parent_id)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            count = await connection.fetchval(query, *params)
            return count or 0

        except Exception as e:
            logger.error(
                "Failed to count areas",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise AreaOperationException(
                message=f"Failed to count areas: {str(e)}",
                operation="count",
            ) from e

    async def count_areas(
        self,
        area_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        parent_id: Optional[int] = None,
        parent_type: Optional[str] = None,
        connection: Optional[asyncpg.Connection] = None,
    ) -> int:
        """
        Count areas with optional filtering.

        Args:
            area_type: Filter by area type
            is_active: Filter by active status
            parent_id: Filter by parent area ID
            parent_type: Filter by parent type (nation, zone, region, area)
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Count of areas

        Raises:
            AreaOperationException: If counting fails
        """
        if connection:
            return await self._count_areas(
                connection, area_type, is_active, parent_id, parent_type
            )

        async with self.db_pool.acquire() as conn:
            return await self._count_areas(
                conn, area_type, is_active, parent_id, parent_type
            )

    async def _update_area(
        self,
        area_id: int,
        area_data: AreaUpdate,
        connection: asyncpg.Connection,
    ) -> AreaInDB:
        """
        Private method to update an area with a provided connection.

        Args:
            area_id: ID of the area to update
            area_data: Area data to update
            connection: Database connection

        Returns:
            Updated area

        Raises:
            AreaNotFoundException: If area not found
            AreaOperationException: If update fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Check if area exists
            await self._get_area_by_id(area_id, connection)

            # Build dynamic update query
            update_fields = []
            params = []
            param_count = 0

            if area_data.name is not None:
                param_count += 1
                update_fields.append(f"name = ${param_count}")
                params.append(area_data.name)

            if area_data.type is not None:
                param_count += 1
                update_fields.append(f"type = ${param_count}")
                params.append(area_data.type)

            if area_data.area_id is not None:
                param_count += 1
                update_fields.append(f"area_id = ${param_count}")
                params.append(area_data.area_id)

            if area_data.region_id is not None:
                param_count += 1
                update_fields.append(f"region_id = ${param_count}")
                params.append(area_data.region_id)

            if area_data.zone_id is not None:
                param_count += 1
                update_fields.append(f"zone_id = ${param_count}")
                params.append(area_data.zone_id)

            if area_data.nation_id is not None:
                param_count += 1
                update_fields.append(f"nation_id = ${param_count}")
                params.append(area_data.nation_id)

            if not update_fields:
                # No fields to update, return current area
                return await self._get_area_by_id(area_id, connection)

            param_count += 1
            params.append(area_id)

            query = f"""
                UPDATE areas
                SET {", ".join(update_fields)}
                WHERE id = ${param_count}
                RETURNING id, name, type, area_id, region_id, zone_id, nation_id,
                          is_active, created_at, updated_at
            """

            row = await connection.fetchrow(query, *params)

            if not row:
                raise AreaNotFoundException(area_id=area_id)

            logger.info(
                "Area updated successfully",
                area_id=area_id,
                company_id=str(self.company_id),
            )

            return AreaInDB(**dict(row))

        except (AreaNotFoundException, AreaAlreadyExistsException):
            raise
        except asyncpg.UniqueViolationError:
            raise AreaAlreadyExistsException(
                area_name=area_data.name, area_type=area_data.type
            )
        except Exception as e:
            logger.error(
                "Failed to update area",
                area_id=area_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise AreaOperationException(
                message=f"Failed to update area: {str(e)}",
                operation="update",
            ) from e

    async def update_area(
        self,
        area_id: int,
        area_data: AreaUpdate,
        connection: Optional[asyncpg.Connection] = None,
    ) -> AreaInDB:
        """
        Update an existing area.

        Args:
            area_id: ID of the area to update
            area_data: Area data to update
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Updated area

        Raises:
            AreaNotFoundException: If area not found
            AreaOperationException: If update fails
        """
        if connection:
            return await self._update_area(area_id, area_data, connection)

        async with self.db_pool.acquire() as conn:
            return await self._update_area(area_id, area_data, conn)

    async def _delete_area(
        self, area_id: int, connection: asyncpg.Connection
    ) -> AreaInDB:
        """
        Private method to soft delete an area (set is_active=False) with a provided connection.

        Args:
            area_id: ID of the area to soft delete
            connection: Database connection

        Returns:
            Updated area with is_active=False

        Raises:
            AreaNotFoundException: If area not found
            AreaOperationException: If soft deletion fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Check if area exists
            await self._get_area_by_id(area_id, connection)

            # Soft delete area
            await connection.execute(
                "UPDATE areas SET is_active = FALSE WHERE id = $1",
                area_id,
            )

            logger.info(
                "Area soft deleted successfully",
                area_id=area_id,
                company_id=str(self.company_id),
            )

            return await self._get_area_by_id(area_id, connection)

        except AreaNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to soft delete area",
                area_id=area_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise AreaOperationException(
                message=f"Failed to soft delete area: {str(e)}",
                operation="soft_delete",
            ) from e

    async def delete_area(
        self, area_id: int, connection: Optional[asyncpg.Connection] = None
    ) -> None:
        """
        Delete an area by setting is_active to False.

        Args:
            area_id: ID of the area to delete
            connection: Optional database connection. If not provided, a new one is acquired.
        """
        if connection:
            return await self._delete_area(area_id, connection)

        async with self.db_pool.acquire() as conn:
            return await self._delete_area(area_id, conn)

    async def _get_areas_by_parent(
        self,
        parent_id: int,
        parent_type: str,
        connection: asyncpg.Connection,
    ) -> list[AreaInDB]:
        """
        Private method to get all child areas of a parent area.

        Args:
            parent_id: ID of the parent area
            parent_type: Type of parent (nation, zone, region, area)
            connection: Database connection

        Returns:
            List of child areas

        Raises:
            AreaOperationException: If retrieval fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Map parent_type to column name
            parent_column_map = {
                "nation": "nation_id",
                "zone": "zone_id",
                "region": "region_id",
                "area": "area_id",
            }

            if parent_type.lower() not in parent_column_map:
                raise AreaOperationException(
                    message=f"Invalid parent type: {parent_type}",
                    operation="get_by_parent",
                )

            column_name = parent_column_map[parent_type.lower()]

            rows = await connection.fetch(
                f"""
                SELECT id, name, type, area_id, region_id, zone_id, nation_id,
                       is_active, created_at, updated_at
                FROM areas
                WHERE {column_name} = $1 AND is_active = true
                ORDER BY name ASC
                """,
                parent_id,
            )

            return [AreaInDB(**dict(row)) for row in rows]

        except AreaOperationException:
            raise
        except Exception as e:
            logger.error(
                "Failed to get areas by parent",
                parent_id=parent_id,
                parent_type=parent_type,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise AreaOperationException(
                message=f"Failed to get areas by parent: {str(e)}",
                operation="get_by_parent",
            ) from e

    async def get_areas_by_parent(
        self,
        parent_id: int,
        parent_type: str,
        connection: Optional[asyncpg.Connection] = None,
    ) -> list[AreaInDB]:
        """
        Get all child areas of a parent area.

        Args:
            parent_id: ID of the parent area
            parent_type: Type of parent (nation, zone, region, area)
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            List of child areas

        Raises:
            AreaOperationException: If retrieval fails
        """
        if connection:
            return await self._get_areas_by_parent(parent_id, parent_type, connection)

        async with self.db_pool.acquire() as conn:
            return await self._get_areas_by_parent(parent_id, parent_type, conn)
