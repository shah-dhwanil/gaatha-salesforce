"""
Repository for Role entity operations.

This repository handles all database operations for roles in a multi-tenant
architecture using schema-per-tenant approach with asyncpg.
"""

from typing import Optional
from uuid import UUID

import asyncpg
import structlog

from api.database import DatabasePool
from api.exceptions.role import (
    RoleAlreadyExistsException,
    RoleNotFoundException,
    RoleOperationException,
)
from api.models.role import RoleCreate, RoleInDB, RoleListItem, RoleUpdate
from api.repository.utils import get_schema_name, set_search_path

logger = structlog.get_logger(__name__)


class RoleRepository:
    """
    Repository for managing Role entities in a multi-tenant database.

    This repository provides methods for CRUD operations on roles,
    handling schema-per-tenant isolation using asyncpg.
    All methods raise exceptions when records are not found.
    """

    def __init__(self, db_pool: DatabasePool, company_id: UUID) -> None:
        """
        Initialize the RoleRepository.

        Args:
            db_pool: Database pool instance for connection management
            company_id: UUID of the company (tenant) for schema isolation
        """
        self.db_pool = db_pool
        self.company_id = company_id
        self.schema_name = get_schema_name(company_id)

    async def _create_role(
        self, role_data: RoleCreate, connection: asyncpg.Connection
    ) -> RoleInDB:
        """
        Private method to create a role with a provided connection.

        Args:
            role_data: Role data to create
            connection: Database connection

        Returns:
            Created role

        Raises:
            RoleAlreadyExistsException: If role with the same name already exists
            RoleOperationException: If creation fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Check if role already exists
            existing_role = await connection.fetchrow(
                """
                SELECT name FROM roles WHERE name = $1
                """,
                role_data.name,
            )

            if existing_role:
                raise RoleAlreadyExistsException(role_name=role_data.name)

            # Insert the role
            row = await connection.fetchrow(
                """
                INSERT INTO roles (name, description, permissions, is_active)
                VALUES ($1, $2, $3, $4)
                RETURNING name, description, permissions, is_active, created_at, updated_at
                """,
                role_data.name,
                role_data.description,
                role_data.permissions,
                role_data.is_active,
            )

            logger.info(
                "Role created successfully",
                role_name=role_data.name,
                company_id=str(self.company_id),
            )

            return RoleInDB(**dict(row))

        except RoleAlreadyExistsException:
            raise
        except Exception as e:
            logger.error(
                "Failed to create role",
                role_name=role_data.name,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RoleOperationException(
                message=f"Failed to create role: {str(e)}",
                operation="create",
            ) from e

    async def create_role(
        self, role_data: RoleCreate, connection: Optional[asyncpg.Connection] = None
    ) -> RoleInDB:
        """
        Create a new role.

        Args:
            role_data: Role data to create
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Created role

        Raises:
            RoleAlreadyExistsException: If role with the same name already exists
            RoleOperationException: If creation fails
        """
        if connection:
            return await self._create_role(role_data, connection)

        async with self.db_pool.acquire() as conn:
            return await self._create_role(role_data, conn)

    async def _get_role_by_name(
        self, role_name: str, connection: asyncpg.Connection
    ) -> RoleInDB:
        """
        Private method to get a role by name with a provided connection.

        Args:
            role_name: Name of the role
            connection: Database connection

        Returns:
            Role

        Raises:
            RoleNotFoundException: If role not found
            RoleOperationException: If retrieval fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            row = await connection.fetchrow(
                """
                SELECT name, description, permissions, is_active, created_at, updated_at
                FROM roles
                WHERE name = $1
                """,
                role_name,
            )

            if not row:
                raise RoleNotFoundException(role_name=role_name)

            return RoleInDB(**dict(row))

        except RoleNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to get role by name",
                role_name=role_name,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RoleOperationException(
                message=f"Failed to get role: {str(e)}",
                operation="get",
            ) from e

    async def get_role_by_name(
        self, role_name: str, connection: Optional[asyncpg.Connection] = None
    ) -> RoleInDB:
        """
        Get a role by name.

        Args:
            role_name: Name of the role
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Role

        Raises:
            RoleNotFoundException: If role not found
            RoleOperationException: If retrieval fails
        """
        if connection:
            return await self._get_role_by_name(role_name, connection)

        async with self.db_pool.acquire() as conn:
            return await self._get_role_by_name(role_name, conn)

    async def _list_roles(
        self,
        connection: asyncpg.Connection,
        is_active: Optional[bool] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[RoleListItem]:
        """
        Private method to list roles with a provided connection.
        Returns minimal data to optimize performance.

        Args:
            connection: Database connection
            is_active: Filter by active status
            limit: Maximum number of roles to return
            offset: Number of roles to skip

        Returns:
            List of roles with minimal data

        Raises:
            RoleOperationException: If listing fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Only select minimal fields for list view
            query = """
                SELECT name, description, is_active
                FROM roles     
            """
            params = []
            param_count = 0

            # Add WHERE clause if filtering by is_active
            if is_active is not None:
                param_count += 1
                query += f" WHERE is_active = ${param_count}"
                params.append(is_active)

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

            return [RoleListItem(**dict(row)) for row in rows]

        except Exception as e:
            logger.error(
                "Failed to list roles",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RoleOperationException(
                message=f"Failed to list roles: {str(e)}",
                operation="list",
            )

    async def list_roles(
        self,
        is_active: Optional[bool] = None,
        limit: int = 20,
        offset: int = 0,
        connection: Optional[asyncpg.Connection] = None,
    ) -> list[RoleListItem]:
        """
        List all roles with optional filtering.
        Returns minimal data to optimize performance.

        Args:
            is_active: Filter by active status
            limit: Maximum number of roles to return
            offset: Number of roles to skip
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            List of roles with minimal data

        Raises:
            RoleOperationException: If listing fails
        """
        if connection:
            return await self._list_roles(connection, is_active, limit, offset)

        async with self.db_pool.acquire() as conn:
            return await self._list_roles(conn, is_active, limit, offset)

    async def _count_roles(
        self,
        connection: asyncpg.Connection,
        is_active: Optional[bool] = None,
    ) -> int:
        """
        Private method to count roles with a provided connection.

        Args:
            connection: Database connection
            is_active: Filter by active status

        Returns:
            Count of roles

        Raises:
            RoleOperationException: If counting fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            if is_active is not None:
                count = await connection.fetchval(
                    "SELECT COUNT(*) FROM roles WHERE is_active = $1",
                    is_active,
                )
            else:
                count = await connection.fetchval("SELECT COUNT(*) FROM roles")

            return count or 0

        except Exception as e:
            logger.error(
                "Failed to count roles",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RoleOperationException(
                message=f"Failed to count roles: {str(e)}",
                operation="count",
            )

    async def count_roles(
        self,
        is_active: Optional[bool] = None,
        connection: Optional[asyncpg.Connection] = None,
    ) -> int:
        """
        Count roles with optional filtering.

        Args:
            is_active: Filter by active status
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Count of roles

        Raises:
            RoleOperationException: If counting fails
        """
        if connection:
            return await self._count_roles(connection, is_active)

        async with self.db_pool.acquire() as conn:
            return await self._count_roles(conn, is_active)

    async def _update_role(
        self,
        role_name: str,
        role_data: RoleUpdate,
        connection: asyncpg.Connection,
    ) -> RoleInDB:
        """
        Private method to update a role with a provided connection.

        Args:
            role_name: Name of the role to update
            role_data: Role data to update
            connection: Database connection

        Returns:
            Updated role

        Raises:
            RoleNotFoundException: If role not found
            RoleOperationException: If update fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Check if role exists
            await self._get_role_by_name(role_name, connection)

            # Build dynamic update query
            update_fields = []
            params = []
            param_count = 0

            if role_data.description is not None:
                param_count += 1
                update_fields.append(f"description = ${param_count}")
                params.append(role_data.description)

            if role_data.permissions is not None:
                param_count += 1
                update_fields.append(f"permissions = ${param_count}")
                params.append(role_data.permissions)

            if not update_fields:
                # No fields to update, return current role
                return await self._get_role_by_name(role_name, connection)

            param_count += 1
            params.append(role_name)

            query = f"""
                UPDATE roles
                SET {", ".join(update_fields)}
                WHERE name = ${param_count}
                RETURNING name, description, permissions, is_active, created_at, updated_at
            """

            row = await connection.fetchrow(query, *params)

            if not row:
                raise RoleNotFoundException(role_name=role_name)

            logger.info(
                "Role updated successfully",
                role_name=role_name,
                company_id=str(self.company_id),
            )

            return RoleInDB(**dict(row))

        except RoleNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to update role",
                role_name=role_name,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RoleOperationException(
                message=f"Failed to update role: {str(e)}",
                operation="update",
            )

    async def update_role(
        self,
        role_name: str,
        role_data: RoleUpdate,
        connection: Optional[asyncpg.Connection] = None,
    ) -> RoleInDB:
        """
        Update an existing role.

        Args:
            role_name: Name of the role to update
            role_data: Role data to update
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Updated role

        Raises:
            RoleNotFoundException: If role not found
            RoleOperationException: If update fails
        """
        if connection:
            return await self._update_role(role_name, role_data, connection)

        async with self.db_pool.acquire() as conn:
            return await self._update_role(role_name, role_data, conn)

    async def _delete_role(
        self, role_name: str, connection: asyncpg.Connection
    ) -> RoleInDB:
        """
        Private method to soft delete a role (set is_active=False) with a provided connection.

        Args:
            role_name: Name of the role to soft delete
            connection: Database connection

        Returns:
            Updated role with is_active=False

        Raises:
            RoleNotFoundException: If role not found
            RoleOperationException: If soft deletion fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Check if role exists
            await self._get_role_by_name(role_name, connection)

            # Soft delete role
            await connection.execute(
                "UPDATE roles SET is_active = FALSE WHERE name = $1",
                role_name,
            )

            logger.info(
                "Role soft deleted successfully",
                role_name=role_name,
                company_id=str(self.company_id),
            )

            return await self._get_role_by_name(role_name, connection)

        except RoleNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to soft delete role",
                role_name=role_name,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RoleOperationException(
                message=f"Failed to soft delete role: {str(e)}",
                operation="soft_delete",
            ) from e

    async def delete_role(
        self, role_name: str, connection: Optional[asyncpg.Connection] = None
    ) -> None:
        """
        Delete a role by setting is_active to False.
        """
        if connection:
            return await self._delete_role(role_name, connection)

        async with self.db_pool.acquire() as conn:
            return await self._delete_role(role_name, conn)

    async def _bulk_create_roles(
        self, roles_data: list[RoleCreate], connection: asyncpg.Connection
    ) -> list[RoleInDB]:
        """
        Private method to bulk create roles with a provided connection.

        Args:
            roles_data: List of role data to create
            connection: Database connection

        Returns:
            List of created roles

        Raises:
            RoleAlreadyExistsException: If any role already exists
            RoleOperationException: If creation fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Check for duplicates in input
            role_names = [role.name for role in roles_data]
            if len(role_names) != len(set(role_names)):
                raise RoleOperationException(
                    message="Duplicate role names in input data",
                    operation="bulk_create",
                )

            # Check if any roles already exist
            existing_roles = await connection.fetch(
                """
                SELECT name FROM roles WHERE name = ANY($1)
                """,
                role_names,
            )

            if existing_roles:
                existing_names = [row["name"] for row in existing_roles]
                raise RoleAlreadyExistsException(
                    role_name=", ".join(existing_names),
                    message=f"Roles already exist: {', '.join(existing_names)}",
                )

            # Prepare data for bulk insert
            values = [
                (
                    role.name,
                    role.description,
                    role.permissions,
                    role.is_active,
                )
                for role in roles_data
            ]

            # Bulk insert
            rows = await connection.fetch(
                """
                INSERT INTO roles (name, description, permissions, is_active)
                SELECT * FROM UNNEST($1::varchar[], $2::text[], $3::varchar[][], $4::boolean[])
                RETURNING name, description, permissions, is_active, created_at, updated_at
                """,
                [v[0] for v in values],
                [v[1] for v in values],
                [v[2] for v in values],
                [v[3] for v in values],
            )

            logger.info(
                "Roles bulk created successfully",
                count=len(rows),
                company_id=str(self.company_id),
            )

            return [RoleInDB(**dict(row)) for row in rows]

        except (RoleAlreadyExistsException, RoleOperationException):
            raise
        except Exception as e:
            logger.error(
                "Failed to bulk create roles",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RoleOperationException(
                message=f"Failed to bulk create roles: {str(e)}",
                operation="bulk_create",
            )

    async def bulk_create_roles(
        self,
        roles_data: list[RoleCreate],
        connection: Optional[asyncpg.Connection] = None,
    ) -> list[RoleInDB]:
        """
        Bulk create multiple roles.

        Args:
            roles_data: List of role data to create
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            List of created roles

        Raises:
            RoleAlreadyExistsException: If any role already exists
            RoleOperationException: If creation fails
        """
        if connection:
            return await self._bulk_create_roles(roles_data, connection)

        async with self.db_pool.transaction() as conn:
            return await self._bulk_create_roles(roles_data, conn)
