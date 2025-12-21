from uuid import UUID
from api.database import DatabasePool
from typing import Optional
from asyncpg import Connection, UniqueViolationError
import structlog
from api.exceptions.role import RoleAlreadyExistsException, RoleNotFoundException
from api.models.role import RoleInDB
from api.repository.utils import get_schema_name, set_search_path

logger = structlog.get_logger(__name__)


class RoleRepository:
    """Repository for managing role data in company-specific schemas.

    This repository handles role operations in a multi-tenant architecture where:
    - Role information is stored in company-specific schemas (named by company_id)

    Attributes:
        db_pool: Database connection pool for executing queries
    """

    def __init__(self, db_pool: DatabasePool):
        """Initialize the RoleRepository with a database pool.

        Args:
            db_pool: DatabasePool instance for managing database connections
        """
        self.db_pool = db_pool
        logger.debug("RoleRepository initialized")

    async def __create_role(
        self,
        connection: Connection,
        company_id: UUID,
        name: str,
        description: Optional[str] = None,
        permissions: Optional[list[str]] = None,
    ) -> RoleInDB:
        """Create a new role in the database.

        Creates role record in company-specific roles table.

        Args:
            connection: Database connection
            company_id: UUID of the company the role belongs to
            name: Name of the role
            description: Optional description of the role
            permissions: Optional list of permissions for the role

        Returns:
            RoleInDB: Created role object with all details

        Raises:
            RoleAlreadyExistsException: If role name already exists
        """
        logger.debug(
            "Creating new role",
            name=name,
            company_id=str(company_id),
            has_description=description is not None,
            permission_count=len(permissions) if permissions else 0,
        )

        query = """
        INSERT INTO roles (name, description, permissions) 
        VALUES ($1, $2, $3)
        RETURNING *;
        """

        try:
            await set_search_path(connection, get_schema_name(company_id))
            rs = await connection.fetchrow(query, name, description, permissions or [])
            logger.debug(
                "Role record created in company schema",
                name=name,
                schema=get_schema_name(company_id),
            )
        except UniqueViolationError as e:
            logger.error(
                "Role creation failed - role name already exists",
                name=name,
                error=str(e),
            )
            raise RoleAlreadyExistsException(
                field="name", message="Role with this name already exists."
            ) from e

        logger.info("Role created successfully", name=name)
        if rs is None:
            logger.error("Role creation failed - no record returned", name=name)
            raise Exception("Role creation failed, no record returned.")
        return RoleInDB(
            name=rs["name"],
            description=rs["description"],
            permissions=rs["permissions"],
            is_active=rs["is_active"],
            created_at=rs["created_at"],
            updated_at=rs["updated_at"],
        )

    async def __get_role_by_name(
        self, connection: Connection, company_id: UUID, name: str
    ) -> RoleInDB:
        """Retrieve a role by name.

        Queries company-specific roles table.

        Args:
            connection: Database connection
            company_id: UUID of the company
            name: Role name to search for

        Returns:
            RoleInDB: Complete role object

        Raises:
            RoleNotFoundException: If role not found
        """
        logger.debug("Fetching role by name", name=name, company_id=str(company_id))

        find_role_query = """
        SELECT name, description, permissions, is_active, created_at, updated_at
        FROM roles
        WHERE name = $1;
        """

        await set_search_path(connection, get_schema_name(company_id))
        rs = await connection.fetchrow(find_role_query, name)

        if rs:
            logger.debug(
                "Role found in company schema",
                name=name,
                company_id=str(company_id),
            )
            return RoleInDB(
                name=rs["name"],
                description=rs["description"],
                permissions=rs["permissions"],
                is_active=rs["is_active"],
                created_at=rs["created_at"],
                updated_at=rs["updated_at"],
            )

        logger.warning("Role not found", name=name, company_id=str(company_id))
        raise RoleNotFoundException(field="name")

    async def __get_roles_by_company_id(
        self, connection: Connection, company_id: UUID, limit: int = 10, offset: int = 0
    ) -> tuple[list[RoleInDB], int]:
        """Retrieve roles by company ID with pagination.

        Fetches roles from company-specific roles table with pagination support.

        Args:
            connection: Database connection
            company_id: UUID of the company
            limit: Maximum number of records to return (default: 10)
            offset: Number of records to skip (default: 0)

        Returns:
            tuple: (list of RoleInDB objects, total count of roles)
        """
        logger.debug(
            "Fetching roles for company with pagination",
            company_id=str(company_id),
            limit=limit,
            offset=offset,
        )

        await set_search_path(connection, get_schema_name(company_id))

        # Get total count
        count_query = """
        SELECT COUNT(*) as total
        FROM roles
        WHERE is_active = TRUE;
        """
        count_result = await connection.fetchrow(count_query)
        total_count = count_result["total"] if count_result else 0

        # Get paginated roles
        find_roles_query = """
        SELECT name, description, permissions, is_active, created_at, updated_at
        FROM roles
        WHERE is_active = TRUE
        ORDER BY created_at DESC
        LIMIT $1 OFFSET $2;
        """

        rs = await connection.fetch(find_roles_query, limit, offset)

        roles = []
        for record in rs:
            roles.append(
                RoleInDB(
                    name=record["name"],
                    description=record["description"],
                    permissions=record["permissions"],
                    is_active=record["is_active"],
                    created_at=record["created_at"],
                    updated_at=record["updated_at"],
                )
            )

        logger.debug(
            "Roles fetched for company with pagination",
            company_id=str(company_id),
            role_count=len(roles),
            total_count=total_count,
        )
        return roles, total_count

    async def __update_role(
        self,
        connection: Connection,
        company_id: UUID,
        name: str,
        description: Optional[str] = None,
        permissions: Optional[list[str]] = None,
    ) -> RoleInDB:
        """Update role details.

        Updates role in company-specific roles table.
        Note: Role name cannot be updated as it's the primary key.

        Args:
            connection: Database connection
            company_id: UUID of the company for schema context
            name: Name of the role to update (identifier only, cannot be changed)
            description: New description (optional)
            permissions: New permissions list (optional)

        Returns:
            RoleInDB: Updated role object

        Raises:
            ValueError: If no fields provided for update
        """
        logger.debug(
            "Updating role",
            name=name,
            company_id=str(company_id),
            has_description=description is not None,
            has_permissions=permissions is not None,
        )

        update_fields = []
        update_values = []

        if description is not None:
            update_fields.append(f"description = ${len(update_values) + 2}")
            update_values.append(description)
        if permissions is not None:
            update_fields.append(f"permissions = ${len(update_values) + 2}")
            update_values.append(permissions)

        if not update_fields:
            logger.error("No fields provided for update", name=name)
            raise ValueError("At least one field must be provided for update")

        await set_search_path(connection, get_schema_name(company_id))

        update_query = f"""
        UPDATE roles
        SET {", ".join(update_fields)}
        WHERE name = $1
        RETURNING *;
        """

        rs = await connection.fetchrow(update_query, name, *update_values)

        if not rs:
            logger.warning("Role not found for update", name=name)
            raise RoleNotFoundException(field="name")

        logger.info("Role updated successfully", name=name)
        return RoleInDB(
            name=rs["name"],
            description=rs["description"],
            permissions=rs["permissions"],
            is_active=rs["is_active"],
            created_at=rs["created_at"],
            updated_at=rs["updated_at"],
        )

    async def __delete_role(
        self, connection: Connection, company_id: UUID, name: str
    ) -> None:
        """Delete a role from the database (soft delete).

        Marks role as inactive in company-specific roles table.

        Args:
            connection: Database connection
            company_id: UUID of the company for schema context
            name: Name of the role to delete
        """
        logger.debug(
            "Soft deleting role",
            name=name,
            company_id=str(company_id),
        )

        delete_role_query = """
        UPDATE roles
        SET is_active = FALSE
        WHERE name = $1;
        """

        await set_search_path(connection, get_schema_name(company_id))
        result = await connection.execute(delete_role_query, name)

        if result == "UPDATE 0":
            logger.warning("Role not found for deletion", name=name)
            raise RoleNotFoundException(field="name")

        logger.info("Role soft deleted successfully", name=name)

    async def create_role(
        self,
        company_id: UUID,
        name: str,
        description: Optional[str] = None,
        permissions: Optional[list[str]] = None,
        *,
        connection: Optional[Connection] = None,
    ) -> RoleInDB:
        """Create a new role in the database.

        Public interface for role creation. Manages connection pooling if needed.

        Args:
            company_id: Company UUID
            name: Role name
            description: Optional role description
            permissions: Optional list of permissions
            connection: Optional existing connection (for transactions)

        Returns:
            RoleInDB: Created role object
        """
        logger.info("create_role called", name=name, company_id=str(company_id))
        if connection is None:
            async with self.db_pool.acquire() as conn:
                return await self.__create_role(
                    conn, company_id, name, description, permissions
                )
        return await self.__create_role(
            connection, company_id, name, description, permissions
        )

    async def get_role_by_name(
        self, company_id: UUID, name: str, *, connection: Optional[Connection] = None
    ) -> RoleInDB:
        """Retrieve a role by name.

        Public interface for fetching role by name.

        Args:
            company_id: Company UUID
            name: Role name to search for
            connection: Optional existing connection

        Returns:
            RoleInDB: Role object with complete details
        """
        logger.info("get_role_by_name called", name=name, company_id=str(company_id))
        if connection is None:
            async with self.db_pool.acquire() as conn:
                return await self.__get_role_by_name(conn, company_id, name)
        return await self.__get_role_by_name(connection, company_id, name)

    async def get_roles_by_company_id(
        self,
        company_id: UUID,
        limit: int = 10,
        offset: int = 0,
        *,
        connection: Optional[Connection] = None,
    ) -> tuple[list[RoleInDB], int]:
        """Retrieve roles by company ID with pagination.

        Public interface for fetching company roles with pagination.

        Args:
            company_id: Company UUID
            limit: Maximum number of records to return (default: 10)
            offset: Number of records to skip (default: 0)
            connection: Optional existing connection

        Returns:
            tuple: (list of RoleInDB objects, total count of roles)
        """
        logger.info(
            "get_roles_by_company_id called",
            company_id=str(company_id),
            limit=limit,
            offset=offset,
        )
        if connection is None:
            async with self.db_pool.acquire() as conn:
                return await self.__get_roles_by_company_id(
                    conn, company_id, limit, offset
                )
        return await self.__get_roles_by_company_id(
            connection, company_id, limit, offset
        )

    async def update_role(
        self,
        company_id: UUID,
        name: str,
        description: Optional[str] = None,
        permissions: Optional[list[str]] = None,
        *,
        connection: Optional[Connection] = None,
    ) -> RoleInDB:
        """Update role details.

        Public interface for updating role information.
        Note: Role name cannot be updated as it's the primary key.
        Only description and permissions can be modified.

        Args:
            company_id: Company UUID
            name: Role name (identifier only, cannot be changed)
            description: New description (optional)
            permissions: New permissions list (optional)
            connection: Optional existing connection

        Returns:
            RoleInDB: Updated role object
        """
        logger.info("update_role called", name=name, company_id=str(company_id))
        if connection is None:
            async with self.db_pool.acquire() as conn:
                return await self.__update_role(
                    conn, company_id, name, description, permissions
                )
        return await self.__update_role(
            connection, company_id, name, description, permissions
        )

    async def delete_role(
        self,
        company_id: UUID,
        name: str,
        *,
        connection: Optional[Connection] = None,
    ) -> None:
        """Delete a role from the database (soft delete).

        Public interface for soft-deleting roles.

        Args:
            company_id: Company UUID
            name: Role name to delete
            connection: Optional existing connection
        """
        logger.info(
            "delete_role called",
            name=name,
            company_id=str(company_id),
        )
        if connection is None:
            async with self.db_pool.acquire() as conn:
                return await self.__delete_role(conn, company_id, name)
        return await self.__delete_role(connection, company_id, name)
