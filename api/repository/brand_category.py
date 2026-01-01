"""
Repository for Brand Category entity operations.

This repository handles all database operations for brand categories in a multi-tenant architecture.
Brand categories are stored per tenant schema and include related entities:
- brand_categories: main brand category information
- brand_category_visibility: area-based visibility settings
- brand_category_margins: area-based margin configurations
"""

from api.models.brand_category import BrandCategoryMarginAddOrUpdate
import json
from typing import Optional
from uuid import UUID

import asyncpg
import structlog

from api.database import DatabasePool
from api.exceptions.brand_category import (
    BrandCategoryAlreadyExistsException,
    BrandCategoryNotFoundException,
    BrandCategoryOperationException,
)
from api.models.brand_category import (
    BrandCategoryCreate,
    BrandCategoryDetailItem,
    BrandCategoryInDB,
    BrandCategoryListItem,
    BrandCategoryMarginInDB,
    BrandCategoryMargins,
    BrandCategoryUpdate,
)
from api.models.area import AreaListItem
from api.models.docuemnts import DocumentInDB
from api.repository.utils import get_schema_name, set_search_path

logger = structlog.get_logger(__name__)


class BrandCategoryRepository:
    """
    Repository for managing Brand Category entities in a multi-tenant database.

    This repository provides methods for CRUD operations on brand categories,
    handling schema-per-tenant isolation using asyncpg.
    Treats brand_categories, brand_category_visibility, and brand_category_margins as a single unit.
    """

    def __init__(self, db_pool: DatabasePool, company_id: UUID) -> None:
        """
        Initialize the BrandCategoryRepository.

        Args:
            db_pool: Database pool instance for connection management
            company_id: UUID of the company (tenant) for schema isolation
        """
        self.db_pool = db_pool
        self.company_id = company_id
        self.schema_name = get_schema_name(company_id)

    async def _create_brand_category(
        self, brand_category_data: BrandCategoryCreate, connection: asyncpg.Connection
    ) -> BrandCategoryInDB:
        """
        Private method to create a brand category with a provided connection.

        Args:
            brand_category_data: Brand category data to create
            connection: Database connection

        Returns:
            Created brand category

        Raises:
            AlreadyExistsException: If brand category with same name/code exists
            OperationException: If creation fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Convert logo to JSON if provided
            logo_json = brand_category_data.logo.model_dump_json() if brand_category_data.logo else None

            # Insert the brand category
            row = await connection.fetchrow(
                """
                INSERT INTO brand_categories (name, code, brand_id, parent_category_id, for_general, for_modern, for_horeca, logo)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id, name, code, brand_id, parent_category_id, for_general, for_modern, for_horeca, logo, 
                          is_active, is_deleted, created_at, updated_at
                """,
                brand_category_data.name,
                brand_category_data.code,
                brand_category_data.brand_id,
                brand_category_data.parent_category_id,
                brand_category_data.for_general,
                brand_category_data.for_modern,
                brand_category_data.for_horeca,
                logo_json,
            )

            brand_category_id = row["id"]

            # Handle brand category visibility (area_id list)
            # If area_id is provided as a list, create visibility records for each area
            # If area_id is None or empty, create a single visibility record with area_id=NULL
            if brand_category_data.area_id and len(brand_category_data.area_id) > 0:
                for area_id in brand_category_data.area_id:
                    await connection.execute(
                        """
                        INSERT INTO brand_category_visibility (brand_category_id, area_id)
                        VALUES ($1, $2)
                        """,
                        brand_category_id,
                        area_id,
                    )
            else:
                # Create a visibility record with NULL area_id (visible to all)
                await connection.execute(
                    """
                    INSERT INTO brand_category_visibility (brand_category_id, area_id)
                    VALUES ($1, NULL)
                    """,
                    brand_category_id,
                )

            # Handle brand category margins
            # If margins is provided as a list, create margin records for each
            # If margins is None or empty, create a single margin record with NULL area_id and NULL margins
            if brand_category_data.margins and len(brand_category_data.margins) > 0:
                for margin_data in brand_category_data.margins:
                    margins_json = margin_data.margins.model_dump_json()
                    area_id = margin_data.area_id if margin_data.area_id else None
                    
                    await connection.execute(
                        """
                        INSERT INTO brand_category_margins (brand_category_id, area_id, margins)
                        VALUES ($1, $2, $3)
                        """,
                        brand_category_id,
                        area_id,
                        margins_json,
                    )
            else:
                # Create a default margins record with NULL area_id and NULL margins
                await connection.execute(
                    """
                    INSERT INTO brand_category_margins (brand_category_id, area_id, margins)
                    VALUES ($1, NULL, NULL)
                    """,
                    brand_category_id,
                )

            logger.info(
                "Brand category created successfully",
                brand_category_id=brand_category_id,
                brand_category_name=brand_category_data.name,
                company_id=str(self.company_id),
            )

            return BrandCategoryInDB(
                id=row["id"],
                name=row["name"],
                code=row["code"],
                brand_id=row["brand_id"],
                parent_category_id=row["parent_category_id"],
                for_general=row["for_general"],
                for_modern=row["for_modern"],
                for_horeca=row["for_horeca"],
                logo=DocumentInDB.model_validate_json(row["logo"]) if row["logo"] else None,
                is_active=row["is_active"],
                is_deleted=row["is_deleted"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

        except asyncpg.UniqueViolationError as e:
            if "uniq_brand_categories_code" in str(e):
                raise BrandCategoryAlreadyExistsException(
                    brand_category_code=brand_category_data.code,
                )
            elif "uniq_brand_categories_name" in str(e):
                raise BrandCategoryAlreadyExistsException(
                    brand_category_name=brand_category_data.name,
                )
            else:
                raise BrandCategoryOperationException(
                    message=f"Failed to create brand category: {str(e)}",
                    operation="create",
                ) from e
        except asyncpg.ForeignKeyViolationError as e:
            if "area_id" in str(e):
                raise BrandCategoryOperationException(
                    message="One or more area IDs not found",
                    operation="create",
                ) from e
            if "brand_id" in str(e):
                raise BrandCategoryOperationException(
                    message="Brand ID not found",
                    operation="create",
                ) from e
            raise BrandCategoryOperationException(
                message=f"Failed to create brand category: {str(e)}",
                operation="create",
            ) from e
        except Exception as e:
            logger.error(
                "Failed to create brand category",
                brand_category_name=brand_category_data.name,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise BrandCategoryOperationException(
                message=f"Failed to create brand category: {str(e)}",
                operation="create",
            ) from e

    async def create_brand_category(
        self, brand_category_data: BrandCategoryCreate, connection: Optional[asyncpg.Connection] = None
    ) -> BrandCategoryInDB:
        """
        Create a new brand category.

        Args:
            brand_category_data: Brand category data to create
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Created brand category

        Raises:
            AlreadyExistsException: If brand category with same name/code exists
            OperationException: If creation fails
        """
        if connection:
            return await self._create_brand_category(brand_category_data, connection)

        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                return await self._create_brand_category(brand_category_data, conn)

    async def _get_brand_category_by_id(
        self, brand_category_id: int, connection: asyncpg.Connection
    ) -> BrandCategoryDetailItem:
        """
        Private method to get a brand category by ID with a provided connection.
        Returns detailed brand category information with areas, visibility, and margins.

        Args:
            brand_category_id: ID of the brand category
            connection: Database connection

        Returns:
            Detailed brand category information

        Raises:
            NotFoundException: If brand category not found
            OperationException: If retrieval fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Get brand category basic information with parent category name
            row = await connection.fetchrow(
                """
                SELECT bc.id, bc.name, bc.code, bc.brand_id, bc.parent_category_id, 
                       pc.name as parent_category_name,
                       bc.for_general, bc.for_modern, bc.for_horeca, bc.logo,
                       bc.is_active, bc.is_deleted, bc.created_at, bc.updated_at
                FROM brand_categories bc
                LEFT JOIN brand_categories pc ON bc.parent_category_id = pc.id AND pc.is_deleted = FALSE
                WHERE bc.id = $1 AND bc.is_deleted = FALSE
                """,
                brand_category_id,
            )

            if not row:
                raise BrandCategoryNotFoundException(
                    brand_category_id=brand_category_id,
                )

            brand_category_dict = dict(row)

            # Parse logo JSON to DocumentInDB
            if brand_category_dict.get("logo"):
                brand_category_dict["logo"] = DocumentInDB.model_validate_json(brand_category_dict["logo"])

            # Get areas associated with brand category visibility
            area_rows = await connection.fetch(
                """
                SELECT DISTINCT a.id, a.name, a.type, a.is_active
                FROM brand_category_visibility bcv
                LEFT JOIN areas a ON bcv.area_id = a.id
                WHERE bcv.brand_category_id = $1 AND bcv.is_active = TRUE
                """,
                brand_category_id,
            )

            areas = []
            for area_row in area_rows:
                if area_row["id"]:  # Only add if area exists (not NULL)
                    areas.append(AreaListItem(**dict(area_row)))

            # Get all margins for the brand category
            margin_rows = await connection.fetch(
                """
                SELECT id,name, area_id, margins, is_active, created_at, updated_at
                FROM brand_category_margins
                WHERE brand_category_id = $1 AND is_active = TRUE
                ORDER BY area_id NULLS FIRST
                """,
                brand_category_id,
            )

            margins = []
            for margin_row in margin_rows:
                margin_dict = dict(margin_row)
                
                # Parse margins JSON to BrandCategoryMargins
                if margin_dict.get("margins"):
                    margin_dict["margins"] = BrandCategoryMargins.model_validate_json(margin_dict["margins"])
                else:
                    margin_dict["margins"] = None

                margins.append(BrandCategoryMarginInDB(**margin_dict))

            return BrandCategoryDetailItem(
                **brand_category_dict,
                area=areas if areas else None,
                margins=margins if margins else None,
            )

        except BrandCategoryNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to get brand category by ID",
                brand_category_id=brand_category_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise BrandCategoryOperationException(
                message=f"Failed to get brand category: {str(e)}",
                operation="get",
            ) from e

    async def get_brand_category_by_id(
        self, brand_category_id: int, connection: Optional[asyncpg.Connection] = None
    ) -> BrandCategoryDetailItem:
        """
        Get a brand category by ID.

        Args:
            brand_category_id: ID of the brand category
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Detailed brand category information

        Raises:
            NotFoundException: If brand category not found
            OperationException: If retrieval fails
        """
        if connection:
            return await self._get_brand_category_by_id(brand_category_id, connection)

        async with self.db_pool.acquire() as conn:
            return await self._get_brand_category_by_id(brand_category_id, conn)

    async def _get_brand_category_by_code(
        self, brand_category_code: str, connection: asyncpg.Connection
    ) -> BrandCategoryDetailItem:
        """
        Private method to get a brand category by code with a provided connection.

        Args:
            brand_category_code: Code of the brand category
            connection: Database connection

        Returns:
            Detailed brand category information

        Raises:
            NotFoundException: If brand category not found
            OperationException: If retrieval fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Get brand category by code to get the ID
            row = await connection.fetchrow(
                """
                SELECT id
                FROM brand_categories
                WHERE code = $1 AND is_deleted = FALSE
                """,
                brand_category_code,
            )

            if not row:
                raise BrandCategoryNotFoundException(
                    brand_category_code=brand_category_code,
                )

            # Reuse the _get_brand_category_by_id method
            return await self._get_brand_category_by_id(row["id"], connection)

        except BrandCategoryNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to get brand category by code",
                brand_category_code=brand_category_code,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise BrandCategoryOperationException(
                message=f"Failed to get brand category: {str(e)}",
                operation="get",
            ) from e

    async def get_brand_category_by_code(
        self, brand_category_code: str, connection: Optional[asyncpg.Connection] = None
    ) -> BrandCategoryDetailItem:
        """
        Get a brand category by code.

        Args:
            brand_category_code: Code of the brand category
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Detailed brand category information

        Raises:
            NotFoundException: If brand category not found
            OperationException: If retrieval fails
        """
        if connection:
            return await self._get_brand_category_by_code(brand_category_code, connection)

        async with self.db_pool.acquire() as conn:
            return await self._get_brand_category_by_code(brand_category_code, conn)

    async def _list_brand_categories(
        self,
        connection: asyncpg.Connection,
        brand_id: Optional[int] = None,
        is_active: Optional[bool] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[BrandCategoryListItem]:
        """
        Private method to list brand categories with a provided connection.
        Returns minimal data with count for products.

        Args:
            connection: Database connection
            brand_id: Filter by brand ID
            is_active: Filter by active status
            limit: Maximum number of brand categories to return
            offset: Number of brand categories to skip

        Returns:
            List of brand categories with minimal data

        Raises:
            OperationException: If listing fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Build query to get brand category list with product counts
            query = """
                SELECT 
                    bc.id,
                    bc.name,
                    bc.code,
                    bc.is_active,
                    bc.created_at,
                    COALESCE(COUNT(DISTINCT p.id), 0) as no_of_products
                FROM brand_categories bc
                LEFT JOIN products p ON bc.id = p.brand_category_id AND p.is_active = TRUE
                WHERE bc.is_deleted = FALSE
            """
            params = []
            param_count = 0

            # Add WHERE clause if filtering by brand_id
            if brand_id is not None:
                param_count += 1
                query += f" AND bc.brand_id = ${param_count}"
                params.append(brand_id)

            # Add WHERE clause if filtering by is_active
            if is_active is not None:
                param_count += 1
                query += f" AND bc.is_active = ${param_count}"
                params.append(is_active)

            # Add grouping
            query += " GROUP BY bc.id, bc.name, bc.code, bc.is_active, bc.created_at"

            # Add ordering
            query += " ORDER BY bc.name ASC"

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

            return [BrandCategoryListItem(**dict(row)) for row in rows]

        except Exception as e:
            logger.error(
                "Failed to list brand categories",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise BrandCategoryOperationException(
                message=f"Failed to list brand categories: {str(e)}",
                operation="list",
            ) from e

    async def list_brand_categories(
        self,
        brand_id: Optional[int] = None,
        is_active: Optional[bool] = None,
        limit: int = 20,
        offset: int = 0,
        connection: Optional[asyncpg.Connection] = None,
    ) -> list[BrandCategoryListItem]:
        """
        List brand categories with minimal data.

        Args:
            brand_id: Filter by brand ID
            is_active: Filter by active status
            limit: Maximum number of brand categories to return
            offset: Number of brand categories to skip
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            List of brand categories with minimal data

        Raises:
            OperationException: If listing fails
        """
        if connection:
            return await self._list_brand_categories(connection, brand_id, is_active, limit, offset)

        async with self.db_pool.acquire() as conn:
            return await self._list_brand_categories(conn, brand_id, is_active, limit, offset)

    async def _update_brand_category(
        self, brand_category_id: int, brand_category_data: BrandCategoryUpdate, connection: asyncpg.Connection
    ) -> BrandCategoryInDB:
        """
        Private method to update a brand category with a provided connection.

        Args:
            brand_category_id: ID of the brand category to update
            brand_category_data: Brand category data to update
            connection: Database connection

        Returns:
            Updated brand category

        Raises:
            NotFoundException: If brand category not found
            OperationException: If update fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Build dynamic update query
            update_fields = []
            params = [brand_category_id]
            param_count = 1

            if brand_category_data.name is not None:
                param_count += 1
                update_fields.append(f"name = ${param_count}")
                params.append(brand_category_data.name)

            if brand_category_data.code is not None:
                param_count += 1
                update_fields.append(f"code = ${param_count}")
                params.append(brand_category_data.code)

            if brand_category_data.brand_id is not None:
                param_count += 1
                update_fields.append(f"brand_id = ${param_count}")
                params.append(brand_category_data.brand_id)

            if brand_category_data.parent_category_id is not None:
                param_count += 1
                update_fields.append(f"parent_category_id = ${param_count}")
                params.append(brand_category_data.parent_category_id)

            if brand_category_data.for_general is not None:
                param_count += 1
                update_fields.append(f"for_general = ${param_count}")
                params.append(brand_category_data.for_general)

            if brand_category_data.for_modern is not None:
                param_count += 1
                update_fields.append(f"for_modern = ${param_count}")
                params.append(brand_category_data.for_modern)

            if brand_category_data.for_horeca is not None:
                param_count += 1
                update_fields.append(f"for_horeca = ${param_count}")
                params.append(brand_category_data.for_horeca)

            if brand_category_data.logo is not None:
                param_count += 1
                logo_json = brand_category_data.logo.model_dump_json() if brand_category_data.logo else None
                update_fields.append(f"logo = ${param_count}")
                params.append(logo_json)

            if brand_category_data.is_active is not None:
                param_count += 1
                update_fields.append(f"is_active = ${param_count}")
                params.append(brand_category_data.is_active)

            if not update_fields:
                # No fields to update, just return the existing brand category
                return await self._get_brand_category_by_id(brand_category_id, connection)

            # Build and execute update query
            update_query = f"""
                UPDATE brand_categories
                SET {', '.join(update_fields)}
                WHERE id = $1 AND is_deleted = FALSE
                RETURNING id, name, code, brand_id, parent_category_id, for_general, for_modern, for_horeca, logo,
                          is_active, is_deleted, created_at, updated_at
            """

            row = await connection.fetchrow(update_query, *params)

            if not row:
                raise BrandCategoryNotFoundException(
                    brand_category_id=brand_category_id,
                )

            logger.info(
                "Brand category updated successfully",
                brand_category_id=brand_category_id,
                company_id=str(self.company_id),
            )

            return BrandCategoryInDB(
                id=row["id"],
                name=row["name"],
                code=row["code"],
                brand_id=row["brand_id"],
                parent_category_id=row["parent_category_id"],
                for_general=row["for_general"],
                for_modern=row["for_modern"],
                for_horeca=row["for_horeca"],
                logo=DocumentInDB.model_validate_json(row["logo"]) if row["logo"] else None,
                is_active=row["is_active"],
                is_deleted=row["is_deleted"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

        except BrandCategoryNotFoundException:
            raise
        except asyncpg.UniqueViolationError as e:
            if "uniq_brand_categories_code" in str(e):
                raise BrandCategoryAlreadyExistsException(
                    brand_category_code=brand_category_data.code,
                )
            elif "uniq_brand_categories_name" in str(e):
                raise BrandCategoryAlreadyExistsException(
                    brand_category_name=brand_category_data.name,
                )
            else:
                raise BrandCategoryOperationException(
                    message=f"Failed to update brand category: {str(e)}",
                    operation="update",
                ) from e
        except asyncpg.ForeignKeyViolationError as e:
            if "brand_id" in str(e):
                raise BrandCategoryOperationException(
                    message="Brand ID not found",
                    operation="update",
                ) from e
            raise BrandCategoryOperationException(
                message=f"Failed to update brand category: {str(e)}",
                operation="update",
            ) from e
        except Exception as e:
            logger.error(
                "Failed to update brand category",
                brand_category_id=brand_category_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise BrandCategoryOperationException(
                message=f"Failed to update brand category: {str(e)}",
                operation="update",
            ) from e

    async def update_brand_category(
        self, brand_category_id: int, brand_category_data: BrandCategoryUpdate,
        connection: Optional[asyncpg.Connection] = None
    ) -> BrandCategoryInDB:
        """
        Update a brand category.

        Args:
            brand_category_id: ID of the brand category to update
            brand_category_data: Brand category data to update
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Updated brand category

        Raises:
            NotFoundException: If brand category not found
            OperationException: If update fails
        """
        if connection:
            return await self._update_brand_category(brand_category_id, brand_category_data, connection)

        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                return await self._update_brand_category(brand_category_id, brand_category_data, conn)

    async def _delete_brand_category(
        self, brand_category_id: int, connection: asyncpg.Connection
    ) -> None:
        """
        Private method to soft delete a brand category with a provided connection.

        Args:
            brand_category_id: ID of the brand category to delete
            connection: Database connection

        Raises:
            NotFoundException: If brand category not found
            OperationException: If deletion fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Soft delete the brand category
            result = await connection.execute(
                """
                UPDATE brand_categories
                SET is_deleted = TRUE, is_active = FALSE
                WHERE id = $1 AND is_deleted = FALSE
                """,
                brand_category_id,
            )

            if result == "UPDATE 0":
                raise BrandCategoryNotFoundException(
                    brand_category_id=brand_category_id,
                )

            logger.info(
                "Brand category deleted successfully",
                brand_category_id=brand_category_id,
                company_id=str(self.company_id),
            )

        except BrandCategoryNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to delete brand category",
                brand_category_id=brand_category_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise BrandCategoryOperationException(
                message=f"Failed to delete brand category: {str(e)}",
                operation="delete",
            ) from e

    async def delete_brand_category(
        self, brand_category_id: int, connection: Optional[asyncpg.Connection] = None
    ) -> None:
        """
        Soft delete a brand category.

        Args:
            brand_category_id: ID of the brand category to delete
            connection: Optional database connection. If not provided, a new one is acquired.

        Raises:
            NotFoundException: If brand category not found
            OperationException: If deletion fails
        """
        if connection:
            await self._delete_brand_category(brand_category_id, connection)
        else:
            async with self.db_pool.acquire() as conn:
                async with conn.transaction():
                    await self._delete_brand_category(brand_category_id, conn)

    # ==================== Brand Category Visibility Methods ====================

    async def _add_brand_category_visibility(
        self,
        brand_category_id: int,
        area_id: Optional[int],
        connection: asyncpg.Connection,
    ) -> None:
        """
        Private method to add visibility for a brand category in a specific area.

        Args:
            brand_category_id: ID of the brand category
            area_id: ID of the area (None for global visibility)
            connection: Database connection

        Raises:
            BrandCategoryNotFoundException: If brand category not found
            BrandCategoryAlreadyExistsException: If visibility already exists
            BrandCategoryOperationException: If operation fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Check if brand category exists
            brand_category_exists = await connection.fetchval(
                "SELECT EXISTS(SELECT 1 FROM brand_categories WHERE id = $1 AND is_deleted = FALSE)",
                brand_category_id,
            )
            if not brand_category_exists:
                raise BrandCategoryNotFoundException(brand_category_id=brand_category_id)

            # Check if area exists (if area_id is provided)
            if area_id is not None:
                area_exists = await connection.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM areas WHERE id = $1)",
                    area_id,
                )
                if not area_exists:
                    raise BrandCategoryOperationException(
                        message=f"Area with ID {area_id} not found",
                        operation="add_visibility",
                    )

            # Try to insert or reactivate existing visibility
            await connection.execute(
                """
                INSERT INTO brand_category_visibility (brand_category_id, area_id, is_active)
                VALUES ($1, $2, TRUE)
                ON CONFLICT (brand_category_id, area_id) 
                WHERE is_active = TRUE
                DO UPDATE SET is_active = TRUE
                """,
                brand_category_id,
                area_id,
            )

            logger.info(
                "Brand category visibility added successfully",
                brand_category_id=brand_category_id,
                area_id=area_id,
                company_id=str(self.company_id),
            )

        except BrandCategoryNotFoundException:
            raise
        except asyncpg.UniqueViolationError:
            raise BrandCategoryAlreadyExistsException(
                message=f"Visibility for brand category {brand_category_id} in area {area_id} already exists",
            )
        except Exception as e:
            logger.error(
                "Failed to add brand category visibility",
                brand_category_id=brand_category_id,
                area_id=area_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise BrandCategoryOperationException(
                message=f"Failed to add brand category visibility: {str(e)}",
                operation="add_visibility",
            ) from e

    async def add_brand_category_visibility(
        self,
        brand_category_id: int,
        area_id: Optional[int],
        connection: Optional[asyncpg.Connection] = None,
    ) -> None:
        """
        Add visibility for a brand category in a specific area.

        Args:
            brand_category_id: ID of the brand category
            area_id: ID of the area (None for global visibility)
            connection: Optional database connection. If not provided, a new one is acquired.

        Raises:
            BrandCategoryNotFoundException: If brand category not found
            BrandCategoryAlreadyExistsException: If visibility already exists
            BrandCategoryOperationException: If operation fails
        """
        if connection:
            return await self._add_brand_category_visibility(brand_category_id, area_id, connection)

        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                return await self._add_brand_category_visibility(brand_category_id, area_id, conn)

    async def _remove_brand_category_visibility(
        self,
        brand_category_id: int,
        area_id: Optional[int],
        connection: asyncpg.Connection,
    ) -> None:
        """
        Private method to remove visibility for a brand category in a specific area.

        Args:
            brand_category_id: ID of the brand category
            area_id: ID of the area (None for global visibility)
            connection: Database connection

        Raises:
            BrandCategoryNotFoundException: If brand category or visibility not found
            BrandCategoryOperationException: If operation fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Check if brand category exists
            brand_category_exists = await connection.fetchval(
                "SELECT EXISTS(SELECT 1 FROM brand_categories WHERE id = $1 AND is_deleted = FALSE)",
                brand_category_id,
            )
            if not brand_category_exists:
                raise BrandCategoryNotFoundException(brand_category_id=brand_category_id)

            # Soft delete the visibility
            result = await connection.execute(
                """
                UPDATE brand_category_visibility
                SET is_active = FALSE
                WHERE brand_category_id = $1 AND area_id IS NOT DISTINCT FROM $2 AND is_active = TRUE
                """,
                brand_category_id,
                area_id,
            )

            if result == "UPDATE 0":
                area_desc = "global visibility" if area_id is None else f"area {area_id}"
                raise BrandCategoryNotFoundException(
                    message=f"Visibility for brand category {brand_category_id} in {area_desc} not found",
                )

            logger.info(
                "Brand category visibility removed successfully",
                brand_category_id=brand_category_id,
                area_id=area_id,
                company_id=str(self.company_id),
            )

        except BrandCategoryNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to remove brand category visibility",
                brand_category_id=brand_category_id,
                area_id=area_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise BrandCategoryOperationException(
                message=f"Failed to remove brand category visibility: {str(e)}",
                operation="remove_visibility",
            ) from e

    async def remove_brand_category_visibility(
        self,
        brand_category_id: int,
        area_id: Optional[int],
        connection: Optional[asyncpg.Connection] = None,
    ) -> None:
        """
        Remove visibility for a brand category in a specific area.

        Args:
            brand_category_id: ID of the brand category
            area_id: ID of the area (None for global visibility)
            connection: Optional database connection. If not provided, a new one is acquired.

        Raises:
            BrandCategoryNotFoundException: If brand category or visibility not found
            BrandCategoryOperationException: If operation fails
        """
        if connection:
            return await self._remove_brand_category_visibility(brand_category_id, area_id, connection)

        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                return await self._remove_brand_category_visibility(brand_category_id, area_id, conn)

    # ==================== Brand Category Margin Methods ====================

    async def _add_brand_category_margin(
        self,
        brand_category_id: int,
        area_id: Optional[int],
        margins: BrandCategoryMarginAddOrUpdate,
        connection: asyncpg.Connection,
    ) -> BrandCategoryMarginInDB:
        """
        Private method to add or update margin configuration for a brand category in a specific area.

        Args:
            brand_category_id: ID of the brand category
            area_id: ID of the area (None for global margin)
            margins: Margin configuration
            connection: Database connection

        Returns:
            Created or updated margin configuration

        Raises:
            BrandCategoryNotFoundException: If brand category not found
            BrandCategoryOperationException: If operation fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Check if brand category exists and get brand category name
            brand_category_row = await connection.fetchrow(
                "SELECT name FROM brand_categories WHERE id = $1 AND is_deleted = FALSE",
                brand_category_id,
            )
            if not brand_category_row:
                raise BrandCategoryNotFoundException(brand_category_id=brand_category_id)

            brand_category_name = brand_category_row["name"]

            # Check if area exists (if area_id is provided)
            if area_id is not None:
                area_exists = await connection.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM areas WHERE id = $1)",
                    area_id,
                )
                if not area_exists:
                    raise BrandCategoryOperationException(
                        message=f"Area with ID {area_id} not found",
                        operation="add_margin",
                    )
            # Check if margin exists for this brand category and area
            existing_margin = await connection.fetchrow(
                """
                SELECT id FROM brand_category_margins
                WHERE brand_category_id = $1 AND area_id IS NOT DISTINCT FROM $2 AND is_active = TRUE
                """,
                brand_category_id,
                area_id,
            )

            if existing_margin:
                params = []
                param_count = 0
                update_fields = []
                if margins.margins is not None:
                    param_count += 1
                    update_fields.append(f"margins = ${param_count}")
                    margins_json = json.dumps(margins.margins.model_dump())
                    params.append(margins_json)
                if margins.name is not None:
                    param_count += 1
                    update_fields.append(f"name = ${param_count}")
                    params.append(margins.name)
                params.append(brand_category_id)
                param_count += 1
                params.append(area_id)
                param_count += 1
                query = f"""
                    UPDATE brand_category_margins
                    SET {', '.join(update_fields)}
                    WHERE brand_category_id = ${param_count - 1} AND area_id IS NOT DISTINCT FROM ${param_count} AND is_active = TRUE
                    RETURNING id,name, area_id, margins, is_active, created_at, updated_at
                """
                row = await connection.fetchrow(query, *params)
            else:
                row = await connection.fetchrow(
                    """
                    INSERT INTO brand_category_margins (brand_category_id,name, area_id, margins)
                    VALUES ($1, $2, $3, $4)
                    RETURNING id,name, area_id, margins, is_active, created_at, updated_at
                    """,
                    brand_category_id,
                    margins.name,
                    area_id,
                    margins_json,
                )

            logger.info(
                "Brand category margin added/updated successfully",
                brand_category_id=brand_category_id,
                area_id=area_id,
                company_id=str(self.company_id),
            )

            return BrandCategoryMarginInDB(
                id=row["id"],
                area_id=row["area_id"],
                name=row["name"],
                margins=BrandCategoryMargins.model_validate_json(row["margins"]) if row["margins"] else None,
                is_active=row["is_active"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

        except BrandCategoryNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to add brand category margin",
                brand_category_id=brand_category_id,
                area_id=area_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise BrandCategoryOperationException(
                message=f"Failed to add brand category margin: {str(e)}",
                operation="add_margin",
            ) from e

    async def add_brand_category_margin(
        self,
        brand_category_id: int,
        area_id: Optional[int],
        margins: BrandCategoryMarginAddOrUpdate,
        connection: Optional[asyncpg.Connection] = None,
    ) -> BrandCategoryMarginInDB:
        """
        Add or update margin configuration for a brand category in a specific area.

        Args:
            brand_category_id: ID of the brand category
            area_id: ID of the area (None for global margin)
            margins: Margin configuration
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Created or updated margin configuration

        Raises:
            BrandCategoryNotFoundException: If brand category not found
            BrandCategoryOperationException: If operation fails
        """
        if connection:
            return await self._add_brand_category_margin(brand_category_id, area_id, margins, connection)

        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                return await self._add_brand_category_margin(brand_category_id, area_id, margins, conn)

    async def _remove_brand_category_margin(
        self,
        brand_category_id: int,
        area_id: Optional[int],
        connection: asyncpg.Connection,
    ) -> None:
        """
        Private method to remove margin configuration for a brand category in a specific area.

        Args:
            brand_category_id: ID of the brand category
            area_id: ID of the area (None for global margin)
            connection: Database connection

        Raises:
            BrandCategoryNotFoundException: If brand category or margin not found
            BrandCategoryOperationException: If operation fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Check if brand category exists
            brand_category_exists = await connection.fetchval(
                "SELECT EXISTS(SELECT 1 FROM brand_categories WHERE id = $1 AND is_deleted = FALSE)",
                brand_category_id,
            )
            if not brand_category_exists:
                raise BrandCategoryNotFoundException(brand_category_id=brand_category_id)

            # Soft delete the margin
            result = await connection.execute(
                """
                UPDATE brand_category_margins
                SET is_active = FALSE
                WHERE brand_category_id = $1 AND area_id IS NOT DISTINCT FROM $2 AND is_active = TRUE
                """,
                brand_category_id,
                area_id,
            )

            if result == "UPDATE 0":
                area_desc = "global margin" if area_id is None else f"area {area_id}"
                raise BrandCategoryNotFoundException(
                    message=f"Margin for brand category {brand_category_id} in {area_desc} not found",
                )

            logger.info(
                "Brand category margin removed successfully",
                brand_category_id=brand_category_id,
                area_id=area_id,
                company_id=str(self.company_id),
            )

        except BrandCategoryNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to remove brand category margin",
                brand_category_id=brand_category_id,
                area_id=area_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise BrandCategoryOperationException(
                message=f"Failed to remove brand category margin: {str(e)}",
                operation="remove_margin",
            ) from e

    async def remove_brand_category_margin(
        self,
        brand_category_id: int,
        area_id: Optional[int],
        connection: Optional[asyncpg.Connection] = None,
    ) -> None:
        """
        Remove margin configuration for a brand category in a specific area.

        Args:
            brand_category_id: ID of the brand category
            area_id: ID of the area (None for global margin)
            connection: Optional database connection. If not provided, a new one is acquired.

        Raises:
            BrandCategoryNotFoundException: If brand category or margin not found
            BrandCategoryOperationException: If operation fails
        """
        if connection:
            return await self._remove_brand_category_margin(brand_category_id, area_id, connection)

        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                return await self._remove_brand_category_margin(brand_category_id, area_id, conn)
