"""
Repository for ShopCategory entity operations.

This repository handles all database operations for shop categories in a multi-tenant
architecture using schema-per-tenant approach with asyncpg.
"""

from typing import Optional
from uuid import UUID

import asyncpg
import structlog

from api.database import DatabasePool
from api.exceptions.shop_category import (
    ShopCategoryAlreadyExistsException,
    ShopCategoryNotFoundException,
    ShopCategoryOperationException,
)
from api.models.shop_category import (
    ShopCategoryCreate,
    ShopCategoryInDB,
    ShopCategoryListItem,
    ShopCategoryUpdate,
)
from api.repository.utils import get_schema_name, set_search_path

logger = structlog.get_logger(__name__)


class ShopCategoryRepository:
    """
    Repository for managing ShopCategory entities in a multi-tenant database.

    This repository provides methods for CRUD operations on shop categories,
    handling schema-per-tenant isolation using asyncpg.
    All methods raise exceptions when records are not found.
    """

    def __init__(self, db_pool: DatabasePool, company_id: UUID) -> None:
        """
        Initialize the ShopCategoryRepository.

        Args:
            db_pool: Database pool instance for connection management
            company_id: UUID of the company (tenant) for schema isolation
        """
        self.db_pool = db_pool
        self.company_id = company_id
        self.schema_name = get_schema_name(company_id)

    async def _create_shop_category(
        self, shop_category_data: ShopCategoryCreate, connection: asyncpg.Connection
    ) -> ShopCategoryInDB:
        """
        Private method to create a shop category with a provided connection.

        Args:
            shop_category_data: Shop category data to create
            connection: Database connection

        Returns:
            Created shop category

        Raises:
            ShopCategoryAlreadyExistsException: If shop category with the same name already exists
            ShopCategoryOperationException: If creation fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Check if shop category already exists
            existing_category = await connection.fetchrow(
                """
                SELECT name FROM shop_categories WHERE name = $1
                """,
                shop_category_data.name,
            )

            if existing_category:
                raise ShopCategoryAlreadyExistsException(
                    shop_category_name=shop_category_data.name
                )

            # Insert the shop category
            row = await connection.fetchrow(
                """
                INSERT INTO shop_categories (name)
                VALUES ($1)
                RETURNING id, name, is_active, created_at, updated_at
                """,
                shop_category_data.name,
            )

            logger.info(
                "Shop category created successfully",
                shop_category_id=row["id"],
                shop_category_name=shop_category_data.name,
                company_id=str(self.company_id),
            )

            return ShopCategoryInDB(**dict(row))

        except ShopCategoryAlreadyExistsException:
            raise
        except Exception as e:
            logger.error(
                "Failed to create shop category",
                shop_category_name=shop_category_data.name,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise ShopCategoryOperationException(
                message=f"Failed to create shop category: {str(e)}",
                operation="create",
            ) from e

    async def create_shop_category(
        self, shop_category_data: ShopCategoryCreate, connection: Optional[asyncpg.Connection] = None
    ) -> ShopCategoryInDB:
        """
        Create a new shop category.

        Args:
            shop_category_data: Shop category data to create
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Created shop category

        Raises:
            ShopCategoryAlreadyExistsException: If shop category with the same name already exists
            ShopCategoryOperationException: If creation fails
        """
        if connection:
            return await self._create_shop_category(shop_category_data, connection)

        async with self.db_pool.acquire() as conn:
            return await self._create_shop_category(shop_category_data, conn)

    async def _get_shop_category_by_id(
        self, shop_category_id: int, connection: asyncpg.Connection
    ) -> ShopCategoryInDB:
        """
        Private method to get a shop category by ID with a provided connection.

        Args:
            shop_category_id: ID of the shop category
            connection: Database connection

        Returns:
            Shop category

        Raises:
            ShopCategoryNotFoundException: If shop category not found
            ShopCategoryOperationException: If retrieval fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            row = await connection.fetchrow(
                """
                SELECT id, name, is_active, created_at, updated_at
                FROM shop_categories
                WHERE id = $1
                """,
                shop_category_id,
            )

            if not row:
                raise ShopCategoryNotFoundException(shop_category_id=shop_category_id)

            return ShopCategoryInDB(**dict(row))

        except ShopCategoryNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to get shop category by id",
                shop_category_id=shop_category_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise ShopCategoryOperationException(
                message=f"Failed to get shop category: {str(e)}",
                operation="get",
            ) from e

    async def get_shop_category_by_id(
        self, shop_category_id: int, connection: Optional[asyncpg.Connection] = None
    ) -> ShopCategoryInDB:
        """
        Get a shop category by ID.

        Args:
            shop_category_id: ID of the shop category
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Shop category

        Raises:
            ShopCategoryNotFoundException: If shop category not found
            ShopCategoryOperationException: If retrieval fails
        """
        if connection:
            return await self._get_shop_category_by_id(shop_category_id, connection)

        async with self.db_pool.acquire() as conn:
            return await self._get_shop_category_by_id(shop_category_id, conn)

    async def _get_shop_category_by_name(
        self, shop_category_name: str, connection: asyncpg.Connection
    ) -> ShopCategoryInDB:
        """
        Private method to get a shop category by name with a provided connection.

        Args:
            shop_category_name: Name of the shop category
            connection: Database connection

        Returns:
            Shop category

        Raises:
            ShopCategoryNotFoundException: If shop category not found
            ShopCategoryOperationException: If retrieval fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            row = await connection.fetchrow(
                """
                SELECT id, name, is_active, created_at, updated_at
                FROM shop_categories
                WHERE name = $1 AND is_active = true
                """,
                shop_category_name,
            )

            if not row:
                raise ShopCategoryNotFoundException(shop_category_name=shop_category_name)

            return ShopCategoryInDB(**dict(row))

        except ShopCategoryNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to get shop category by name",
                shop_category_name=shop_category_name,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise ShopCategoryOperationException(
                message=f"Failed to get shop category: {str(e)}",
                operation="get",
            ) from e

    async def get_shop_category_by_name(
        self, shop_category_name: str, connection: Optional[asyncpg.Connection] = None
    ) -> ShopCategoryInDB:
        """
        Get a shop category by name.

        Args:
            shop_category_name: Name of the shop category
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Shop category

        Raises:
            ShopCategoryNotFoundException: If shop category not found
            ShopCategoryOperationException: If retrieval fails
        """
        if connection:
            return await self._get_shop_category_by_name(shop_category_name, connection)

        async with self.db_pool.acquire() as conn:
            return await self._get_shop_category_by_name(shop_category_name, conn)

    async def _list_shop_categories(
        self,
        connection: asyncpg.Connection,
        is_active: Optional[bool] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[ShopCategoryListItem]:
        """
        Private method to list shop categories with a provided connection.
        Returns minimal data to optimize performance.

        Args:
            connection: Database connection
            is_active: Filter by active status
            limit: Maximum number of shop categories to return
            offset: Number of shop categories to skip

        Returns:
            List of shop categories with minimal data

        Raises:
            ShopCategoryOperationException: If listing fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Only select minimal fields for list view
            query = """
                SELECT id, name, is_active
                FROM shop_categories     
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

            return [ShopCategoryListItem(**dict(row)) for row in rows]

        except Exception as e:
            logger.error(
                "Failed to list shop categories",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise ShopCategoryOperationException(
                message=f"Failed to list shop categories: {str(e)}",
                operation="list",
            )

    async def list_shop_categories(
        self,
        is_active: Optional[bool] = None,
        limit: int = 20,
        offset: int = 0,
        connection: Optional[asyncpg.Connection] = None,
    ) -> list[ShopCategoryListItem]:
        """
        List all shop categories with optional filtering.
        Returns minimal data to optimize performance.

        Args:
            is_active: Filter by active status
            limit: Maximum number of shop categories to return
            offset: Number of shop categories to skip
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            List of shop categories with minimal data

        Raises:
            ShopCategoryOperationException: If listing fails
        """
        if connection:
            return await self._list_shop_categories(connection, is_active, limit, offset)

        async with self.db_pool.acquire() as conn:
            return await self._list_shop_categories(conn, is_active, limit, offset)

    async def _count_shop_categories(
        self,
        connection: asyncpg.Connection,
        is_active: Optional[bool] = None,
    ) -> int:
        """
        Private method to count shop categories with a provided connection.

        Args:
            connection: Database connection
            is_active: Filter by active status

        Returns:
            Count of shop categories

        Raises:
            ShopCategoryOperationException: If counting fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            if is_active is not None:
                count = await connection.fetchval(
                    "SELECT COUNT(*) FROM shop_categories WHERE is_active = $1",
                    is_active,
                )
            else:
                count = await connection.fetchval("SELECT COUNT(*) FROM shop_categories")

            return count or 0

        except Exception as e:
            logger.error(
                "Failed to count shop categories",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise ShopCategoryOperationException(
                message=f"Failed to count shop categories: {str(e)}",
                operation="count",
            )

    async def count_shop_categories(
        self,
        is_active: Optional[bool] = None,
        connection: Optional[asyncpg.Connection] = None,
    ) -> int:
        """
        Count shop categories with optional filtering.

        Args:
            is_active: Filter by active status
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Count of shop categories

        Raises:
            ShopCategoryOperationException: If counting fails
        """
        if connection:
            return await self._count_shop_categories(connection, is_active)

        async with self.db_pool.acquire() as conn:
            return await self._count_shop_categories(conn, is_active)

    async def _update_shop_category(
        self,
        shop_category_id: int,
        shop_category_data: ShopCategoryUpdate,
        connection: asyncpg.Connection,
    ) -> ShopCategoryInDB:
        """
        Private method to update a shop category with a provided connection.

        Args:
            shop_category_id: ID of the shop category to update
            shop_category_data: Shop category data to update
            connection: Database connection

        Returns:
            Updated shop category

        Raises:
            ShopCategoryNotFoundException: If shop category not found
            ShopCategoryOperationException: If update fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Check if shop category exists
            await self._get_shop_category_by_id(shop_category_id, connection)

            # Build dynamic update query
            update_fields = []
            params = []
            param_count = 0

            if shop_category_data.name is not None:
                param_count += 1
                update_fields.append(f"name = ${param_count}")
                params.append(shop_category_data.name)

            if not update_fields:
                # No fields to update, return current shop category
                return await self._get_shop_category_by_id(shop_category_id, connection)

            param_count += 1
            params.append(shop_category_id)

            query = f"""
                UPDATE shop_categories
                SET {", ".join(update_fields)}
                WHERE id = ${param_count}
                RETURNING id, name, is_active, created_at, updated_at
            """

            row = await connection.fetchrow(query, *params)

            if not row:
                raise ShopCategoryNotFoundException(shop_category_id=shop_category_id)

            logger.info(
                "Shop category updated successfully",
                shop_category_id=shop_category_id,
                company_id=str(self.company_id),
            )

            return ShopCategoryInDB(**dict(row))

        except ShopCategoryNotFoundException:
            raise
        except asyncpg.UniqueViolationError:
            raise ShopCategoryAlreadyExistsException(
                shop_category_name=shop_category_data.name
            )
        except Exception as e:
            logger.error(
                "Failed to update shop category",
                shop_category_id=shop_category_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise ShopCategoryOperationException(
                message=f"Failed to update shop category: {str(e)}",
                operation="update",
            )

    async def update_shop_category(
        self,
        shop_category_id: int,
        shop_category_data: ShopCategoryUpdate,
        connection: Optional[asyncpg.Connection] = None,
    ) -> ShopCategoryInDB:
        """
        Update an existing shop category.

        Args:
            shop_category_id: ID of the shop category to update
            shop_category_data: Shop category data to update
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Updated shop category

        Raises:
            ShopCategoryNotFoundException: If shop category not found
            ShopCategoryOperationException: If update fails
        """
        if connection:
            return await self._update_shop_category(shop_category_id, shop_category_data, connection)

        async with self.db_pool.acquire() as conn:
            return await self._update_shop_category(shop_category_id, shop_category_data, conn)

    async def _delete_shop_category(
        self, shop_category_id: int, connection: asyncpg.Connection
    ) -> ShopCategoryInDB:
        """
        Private method to soft delete a shop category (set is_active=False) with a provided connection.

        Args:
            shop_category_id: ID of the shop category to soft delete
            connection: Database connection

        Returns:
            Updated shop category with is_active=False

        Raises:
            ShopCategoryNotFoundException: If shop category not found
            ShopCategoryOperationException: If soft deletion fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Check if shop category exists
            await self._get_shop_category_by_id(shop_category_id, connection)

            # Soft delete shop category
            await connection.execute(
                "UPDATE shop_categories SET is_active = FALSE WHERE id = $1",
                shop_category_id,
            )

            logger.info(
                "Shop category soft deleted successfully",
                shop_category_id=shop_category_id,
                company_id=str(self.company_id),
            )

            return await self._get_shop_category_by_id(shop_category_id, connection)

        except ShopCategoryNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to soft delete shop category",
                shop_category_id=shop_category_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise ShopCategoryOperationException(
                message=f"Failed to soft delete shop category: {str(e)}",
                operation="soft_delete",
            ) from e

    async def delete_shop_category(
        self, shop_category_id: int, connection: Optional[asyncpg.Connection] = None
    ) -> None:
        """
        Delete a shop category by setting is_active to False.

        Args:
            shop_category_id: ID of the shop category to delete
            connection: Optional database connection. If not provided, a new one is acquired.
        """
        if connection:
            return await self._delete_shop_category(shop_category_id, connection)

        async with self.db_pool.acquire() as conn:
            return await self._delete_shop_category(shop_category_id, conn)

    async def _bulk_create_shop_categories(
        self, shop_categories_data: list[ShopCategoryCreate], connection: asyncpg.Connection
    ) -> list[ShopCategoryInDB]:
        """
        Private method to bulk create shop categories with a provided connection.

        Args:
            shop_categories_data: List of shop category data to create
            connection: Database connection

        Returns:
            List of created shop categories

        Raises:
            ShopCategoryAlreadyExistsException: If any shop category already exists
            ShopCategoryOperationException: If creation fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Check for duplicates in input
            category_names = [category.name for category in shop_categories_data]
            if len(category_names) != len(set(category_names)):
                raise ShopCategoryOperationException(
                    message="Duplicate shop category names in input data",
                    operation="bulk_create",
                )

            # Check if any shop categories already exist
            existing_categories = await connection.fetch(
                """
                SELECT name FROM shop_categories WHERE name = ANY($1)
                """,
                category_names,
            )

            if existing_categories:
                existing_names = [row["name"] for row in existing_categories]
                raise ShopCategoryAlreadyExistsException(
                    shop_category_name=", ".join(existing_names),
                )

            # Prepare data for bulk insert
            values = [(category.name,) for category in shop_categories_data]

            # Bulk insert
            rows = await connection.fetch(
                """
                INSERT INTO shop_categories (name)
                SELECT * FROM UNNEST($1::varchar[])
                RETURNING id, name, is_active, created_at, updated_at
                """,
                [v[0] for v in values],
            )

            logger.info(
                "Shop categories bulk created successfully",
                count=len(rows),
                company_id=str(self.company_id),
            )

            return [ShopCategoryInDB(**dict(row)) for row in rows]

        except (ShopCategoryAlreadyExistsException, ShopCategoryOperationException):
            raise
        except Exception as e:
            logger.error(
                "Failed to bulk create shop categories",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise ShopCategoryOperationException(
                message=f"Failed to bulk create shop categories: {str(e)}",
                operation="bulk_create",
            )

    async def bulk_create_shop_categories(
        self,
        shop_categories_data: list[ShopCategoryCreate],
        connection: Optional[asyncpg.Connection] = None,
    ) -> list[ShopCategoryInDB]:
        """
        Bulk create multiple shop categories.

        Args:
            shop_categories_data: List of shop category data to create
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            List of created shop categories

        Raises:
            ShopCategoryAlreadyExistsException: If any shop category already exists
            ShopCategoryOperationException: If creation fails
        """
        if connection:
            return await self._bulk_create_shop_categories(shop_categories_data, connection)

        async with self.db_pool.transaction() as conn:
            return await self._bulk_create_shop_categories(shop_categories_data, conn)

