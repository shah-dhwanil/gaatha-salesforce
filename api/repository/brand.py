"""
Repository for Brand entity operations.

This repository handles all database operations for brands in a multi-tenant architecture.
Brands are stored per tenant schema and include related entities:
- brand: main brand information
- brand_visibility: area-based visibility settings
- brand_margins: area-based margin configurations
"""

from api.models.brand import BrandMarginAddOrUpdate
import json
from typing import Optional
from uuid import UUID

import asyncpg
import structlog

from api.database import DatabasePool
from api.exceptions.brand import (
    BrandAlreadyExistsException,
    BrandNotFoundException,
    BrandOperationException,
)
from api.models.brand import (
    BrandCreate,
    BrandDetailItem,
    BrandInDB,
    BrandListItem,
    BrandMarginInDB,
    BrandMargins,
    BrandUpdate,
)
from api.models.area import AreaListItem
from api.models.docuemnts import DocumentInDB
from api.repository.utils import get_schema_name, set_search_path

logger = structlog.get_logger(__name__)


class BrandRepository:
    """
    Repository for managing Brand entities in a multi-tenant database.

    This repository provides methods for CRUD operations on brands,
    handling schema-per-tenant isolation using asyncpg.
    Treats brand, brand_visibility, and brand_margins as a single unit.
    """

    def __init__(self, db_pool: DatabasePool, company_id: UUID) -> None:
        """
        Initialize the BrandRepository.

        Args:
            db_pool: Database pool instance for connection management
            company_id: UUID of the company (tenant) for schema isolation
        """
        self.db_pool = db_pool
        self.company_id = company_id
        self.schema_name = get_schema_name(company_id)

    async def _create_brand(
        self, brand_data: BrandCreate, connection: asyncpg.Connection
    ) -> BrandInDB:
        """
        Private method to create a brand with a provided connection.

        Args:
            brand_data: Brand data to create
            connection: Database connection

        Returns:
            Created brand

        Raises:
            AlreadyExistsException: If brand with same name/code exists
            OperationException: If creation fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Convert logo to JSON if provided
            logo_json = brand_data.logo.model_dump_json() if brand_data.logo else None

            # Insert the brand
            row = await connection.fetchrow(
                """
                INSERT INTO brand (name, code, for_general, for_modern, for_horeca, logo)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id, name, code, for_general, for_modern, for_horeca, logo, 
                          is_active, is_deleted, created_at, updated_at
                """,
                brand_data.name,
                brand_data.code,
                brand_data.for_general,
                brand_data.for_modern,
                brand_data.for_horeca,
                logo_json,
            )

            brand_id = row["id"]

            # Handle brand visibility (area_id list)
            # If area_id is provided as a list, create visibility records for each area
            # If area_id is None or empty, create a single visibility record with area_id=NULL
            if brand_data.area_id and len(brand_data.area_id) > 0:
                for area_id in brand_data.area_id:
                    await connection.execute(
                        """
                        INSERT INTO brand_visibility (brand_id, area_id)
                        VALUES ($1, $2)
                        """,
                        brand_id,
                        area_id,
                    )
            else:
                # Create a visibility record with NULL area_id (visible to all)
                await connection.execute(
                    """
                    INSERT INTO brand_visibility (brand_id, area_id)
                    VALUES ($1, NULL)
                    """,
                    brand_id,
                )

            # Handle brand margins
            if brand_data.margins and len(brand_data.margins) > 0:
                for margin_data in brand_data.margins:
                    margins_json = margin_data.margins.model_dump_json()
                    area_id = margin_data.area_id if margin_data.area_id else None

                    await connection.execute(
                        """
                        INSERT INTO brand_margins (brand_id, area_id, margins, name)
                        VALUES ($1, $2, $3, $4)
                        """,
                        brand_id,
                        area_id,
                        margins_json,
                        margin_data.name,
                    )
            logger.info(
                "Brand created successfully",
                brand_id=brand_id,
                brand_name=brand_data.name,
                company_id=str(self.company_id),
            )

            return BrandInDB(
                id=row["id"],
                name=row["name"],
                code=row["code"],
                for_general=row["for_general"],
                for_modern=row["for_modern"],
                for_horeca=row["for_horeca"],
                logo=DocumentInDB.model_validate_json(row["logo"])
                if row["logo"]
                else None,
                is_active=row["is_active"],
                is_deleted=row["is_deleted"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

        except asyncpg.UniqueViolationError as e:
            if "uniq_brand_code" in str(e):
                raise BrandAlreadyExistsException(
                    brand_code=brand_data.code,
                )
            elif "uniq_brand_name" in str(e):
                raise BrandAlreadyExistsException(
                    brand_name=brand_data.name,
                )
            else:
                raise BrandOperationException(
                    message=f"Failed to create brand: {str(e)}",
                    operation="create",
                ) from e
        except asyncpg.ForeignKeyViolationError as e:
            if "area_id" in str(e):
                raise BrandOperationException(
                    message="One or more area IDs not found",
                    operation="create",
                ) from e
            raise BrandOperationException(
                message=f"Failed to create brand: {str(e)}",
                operation="create",
            ) from e
        except Exception as e:
            logger.error(
                "Failed to create brand",
                brand_name=brand_data.name,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise BrandOperationException(
                message=f"Failed to create brand: {str(e)}",
                operation="create",
            ) from e

    async def create_brand(
        self, brand_data: BrandCreate, connection: Optional[asyncpg.Connection] = None
    ) -> BrandInDB:
        """
        Create a new brand.

        Args:
            brand_data: Brand data to create
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Created brand

        Raises:
            AlreadyExistsException: If brand with same name/code exists
            OperationException: If creation fails
        """
        if connection:
            return await self._create_brand(brand_data, connection)

        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                return await self._create_brand(brand_data, conn)

    async def _get_brand_by_id(
        self, brand_id: int, connection: asyncpg.Connection
    ) -> BrandDetailItem:
        """
        Private method to get a brand by ID with a provided connection.
        Returns detailed brand information with areas, visibility, and margins.

        Args:
            brand_id: ID of the brand
            connection: Database connection

        Returns:
            Detailed brand information

        Raises:
            NotFoundException: If brand not found
            OperationException: If retrieval fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Get brand basic information
            row = await connection.fetchrow(
                """
                SELECT id, name, code, for_general, for_modern, for_horeca, logo,
                       is_active, is_deleted, created_at, updated_at
                FROM brand
                WHERE id = $1 AND is_deleted = FALSE
                """,
                brand_id,
            )

            if not row:
                raise BrandNotFoundException(
                    brand_id=brand_id,
                )

            brand_dict = dict(row)

            # Parse logo JSON to DocumentInDB
            if brand_dict.get("logo"):
                brand_dict["logo"] = DocumentInDB(**brand_dict["logo"])

            # Get areas associated with brand visibility
            area_rows = await connection.fetch(
                """
                SELECT DISTINCT a.id, a.name, a.type, a.is_active
                FROM brand_visibility bv
                LEFT JOIN areas a ON bv.area_id = a.id
                WHERE bv.brand_id = $1 AND bv.is_active = TRUE
                """,
                brand_id,
            )

            areas = []
            for area_row in area_rows:
                if area_row["id"]:  # Only add if area exists (not NULL)
                    areas.append(AreaListItem(**dict(area_row)))

            # Get all margins for the brand
            margin_rows = await connection.fetch(
                """
                SELECT id,name, area_id, margins, is_active, created_at, updated_at
                FROM brand_margins
                WHERE brand_id = $1 AND is_active = TRUE
                ORDER BY area_id NULLS FIRST
                """,
                brand_id,
            )

            margins = []
            for margin_row in margin_rows:
                margin_dict = dict(margin_row)
                # Parse margins JSONB to BrandMargins model
                if margin_dict.get("margins"):
                    margin_dict["margins"] = BrandMargins.model_validate_json(
                        margin_dict["margins"]
                    )
                margins.append(BrandMarginInDB(**margin_dict))

            brand_dict["area"] = areas if areas else None
            brand_dict["margins"] = margins if margins else None

            logger.info(
                "Brand retrieved successfully",
                brand_id=brand_id,
                company_id=str(self.company_id),
            )

            return BrandDetailItem(
                id=brand_dict["id"],
                name=brand_dict["name"],
                code=brand_dict["code"],
                for_general=brand_dict["for_general"],
                for_modern=brand_dict["for_modern"],
                for_horeca=brand_dict["for_horeca"],
                logo=DocumentInDB.model_validate_json(brand_dict["logo"])
                if brand_dict.get("logo")
                else None,
                area=brand_dict["area"],
                margins=brand_dict["margins"],
                is_active=brand_dict["is_active"],
                is_deleted=brand_dict["is_deleted"],
                created_at=brand_dict["created_at"],
                updated_at=brand_dict["updated_at"],
            )

        except BrandNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to get brand by id",
                brand_id=brand_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise BrandOperationException(
                message=f"Failed to get brand: {str(e)}",
                operation="get",
            ) from e

    async def get_brand_by_id(
        self, brand_id: int, connection: Optional[asyncpg.Connection] = None
    ) -> BrandDetailItem:
        """
        Get a brand by ID with detailed information.

        Args:
            brand_id: ID of the brand
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Detailed brand information

        Raises:
            NotFoundException: If brand not found
            OperationException: If retrieval fails
        """
        if connection:
            return await self._get_brand_by_id(brand_id, connection)

        async with self.db_pool.acquire() as conn:
            return await self._get_brand_by_id(brand_id, conn)

    async def _get_brand_by_code(
        self, code: str, connection: asyncpg.Connection
    ) -> BrandDetailItem:
        """
        Private method to get a brand by code with a provided connection.
        Returns detailed brand information with areas, visibility, and margins.

        Args:
            code: Code of the brand
            connection: Database connection

        Returns:
            Detailed brand information

        Raises:
            NotFoundException: If brand not found
            OperationException: If retrieval fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Get brand ID first
            row = await connection.fetchrow(
                """
                SELECT id
                FROM brand
                WHERE code = $1 AND is_deleted = FALSE
                """,
                code,
            )

            if not row:
                raise BrandNotFoundException(
                    brand_code=code,
                )

            # Reuse the get_brand_by_id logic
            return await self._get_brand_by_id(row["id"], connection)

        except BrandNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to get brand by code",
                brand_code=code,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise BrandOperationException(
                message=f"Failed to get brand: {str(e)}",
                operation="get",
            ) from e

    async def get_brand_by_code(
        self, code: str, connection: Optional[asyncpg.Connection] = None
    ) -> BrandDetailItem:
        """
        Get a brand by code with detailed information.

        Args:
            code: Code of the brand
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Detailed brand information

        Raises:
            NotFoundException: If brand not found
            OperationException: If retrieval fails
        """
        if connection:
            return await self._get_brand_by_code(code, connection)

        async with self.db_pool.acquire() as conn:
            return await self._get_brand_by_code(code, conn)

    async def _list_brands(
        self,
        connection: asyncpg.Connection,
        is_active: Optional[bool] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[BrandListItem]:
        """
        Private method to list brands with a provided connection.
        Returns minimal data with counts for categories and products.

        Args:
            connection: Database connection
            is_active: Filter by active status
            limit: Maximum number of brands to return
            offset: Number of brands to skip

        Returns:
            List of brands with minimal data

        Raises:
            OperationException: If listing fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Build query to get brand list with category and product counts
            query = """
                SELECT 
                    b.id,
                    b.name,
                    b.code,
                    b.is_active,
                    b.created_at,
                    COALESCE(COUNT(DISTINCT bc.id), 0) as no_of_categories,
                    COALESCE(COUNT(DISTINCT p.id), 0) as no_of_products
                FROM brand b
                LEFT JOIN brand_categories bc ON b.id = bc.brand_id AND bc.is_active = TRUE
                LEFT JOIN products p ON b.id = p.brand_id AND p.is_active = TRUE
                WHERE b.is_deleted = FALSE
            """
            params = []
            param_count = 0

            # Add WHERE clause if filtering by is_active
            if is_active is not None:
                param_count += 1
                query += f" AND b.is_active = ${param_count}"
                params.append(is_active)

            # Add grouping
            query += " GROUP BY b.id, b.name, b.code, b.is_active, b.created_at"

            # Add ordering
            query += " ORDER BY b.name ASC"

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

            return [BrandListItem(**dict(row)) for row in rows]

        except Exception as e:
            logger.error(
                "Failed to list brands",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise BrandOperationException(
                message=f"Failed to list brands: {str(e)}",
                operation="list",
            ) from e

    async def list_brands(
        self,
        is_active: Optional[bool] = None,
        limit: int = 20,
        offset: int = 0,
        connection: Optional[asyncpg.Connection] = None,
    ) -> list[BrandListItem]:
        """
        List brands with minimal data.

        Args:
            is_active: Filter by active status
            limit: Maximum number of brands to return
            offset: Number of brands to skip
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            List of brands with minimal data

        Raises:
            OperationException: If listing fails
        """
        if connection:
            return await self._list_brands(connection, is_active, limit, offset)

        async with self.db_pool.acquire() as conn:
            return await self._list_brands(conn, is_active, limit, offset)

    async def _update_brand(
        self, brand_id: int, brand_data: BrandUpdate, connection: asyncpg.Connection
    ) -> BrandInDB:
        """
        Private method to update a brand with a provided connection.

        Args:
            brand_id: ID of the brand to update
            brand_data: Brand data to update
            connection: Database connection

        Returns:
            Updated brand

        Raises:
            NotFoundException: If brand not found
            OperationException: If update fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Build dynamic update query
            update_fields = []
            params = [brand_id]
            param_count = 1

            if brand_data.name is not None:
                param_count += 1
                update_fields.append(f"name = ${param_count}")
                params.append(brand_data.name)

            if brand_data.code is not None:
                param_count += 1
                update_fields.append(f"code = ${param_count}")
                params.append(brand_data.code)

            if brand_data.for_general is not None:
                param_count += 1
                update_fields.append(f"for_general = ${param_count}")
                params.append(brand_data.for_general)

            if brand_data.for_modern is not None:
                param_count += 1
                update_fields.append(f"for_modern = ${param_count}")
                params.append(brand_data.for_modern)

            if brand_data.for_horeca is not None:
                param_count += 1
                update_fields.append(f"for_horeca = ${param_count}")
                params.append(brand_data.for_horeca)

            if brand_data.logo is not None:
                param_count += 1
                logo_json = (
                    json.dumps(brand_data.logo.model_dump())
                    if brand_data.logo
                    else None
                )
                update_fields.append(f"logo = ${param_count}")
                params.append(logo_json)

            if brand_data.is_active is not None:
                param_count += 1
                update_fields.append(f"is_active = ${param_count}")
                params.append(brand_data.is_active)

            if not update_fields:
                # No fields to update, just return current brand
                return await self._get_brand_by_id(brand_id, connection)

            query = f"""
                UPDATE brand
                SET {", ".join(update_fields)}
                WHERE id = $1 AND is_deleted = FALSE
                RETURNING id, name, code, for_general, for_modern, for_horeca, logo,
                          is_active, is_deleted, created_at, updated_at
            """

            row = await connection.fetchrow(query, *params)

            if not row:
                raise BrandNotFoundException(
                    brand_id=brand_id,
                )

            logger.info(
                "Brand updated successfully",
                brand_id=brand_id,
                company_id=str(self.company_id),
            )

            return BrandInDB(**dict(row))

        except asyncpg.UniqueViolationError as e:
            if "uniq_brand_code" in str(e):
                raise BrandAlreadyExistsException(
                    brand_code=brand_data.code,
                )
            elif "uniq_brand_name" in str(e):
                raise BrandAlreadyExistsException(
                    brand_name=brand_data.name,
                )
            raise BrandOperationException(
                message=f"Failed to update brand: {str(e)}",
                operation="update",
            ) from e
        except BrandNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to update brand",
                brand_id=brand_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise BrandOperationException(
                message=f"Failed to update brand: {str(e)}",
                operation="update",
            ) from e

    async def update_brand(
        self,
        brand_id: int,
        brand_data: BrandUpdate,
        connection: Optional[asyncpg.Connection] = None,
    ) -> BrandInDB:
        """
        Update a brand.

        Args:
            brand_id: ID of the brand to update
            brand_data: Brand data to update
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Updated brand

        Raises:
            NotFoundException: If brand not found
            OperationException: If update fails
        """
        if connection:
            return await self._update_brand(brand_id, brand_data, connection)

        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                return await self._update_brand(brand_id, brand_data, conn)

    async def _delete_brand(
        self, brand_id: int, connection: asyncpg.Connection
    ) -> None:
        """
        Private method to soft delete a brand with a provided connection.

        Args:
            brand_id: ID of the brand to delete
            connection: Database connection

        Raises:
            NotFoundException: If brand not found
            OperationException: If deletion fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            result = await connection.execute(
                """
                UPDATE brand
                SET is_deleted = TRUE, is_active = FALSE
                WHERE id = $1 AND is_deleted = FALSE
                """,
                brand_id,
            )

            if result == "UPDATE 0":
                raise BrandNotFoundException(
                    brand_id=brand_id,
                )

            logger.info(
                "Brand deleted successfully",
                brand_id=brand_id,
                company_id=str(self.company_id),
            )

        except BrandNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to delete brand",
                brand_id=brand_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise BrandOperationException(
                message=f"Failed to delete brand: {str(e)}",
                operation="delete",
            ) from e

    async def delete_brand(
        self, brand_id: int, connection: Optional[asyncpg.Connection] = None
    ) -> None:
        """
        Soft delete a brand.

        Args:
            brand_id: ID of the brand to delete
            connection: Optional database connection. If not provided, a new one is acquired.

        Raises:
            NotFoundException: If brand not found
            OperationException: If deletion fails
        """
        if connection:
            return await self._delete_brand(brand_id, connection)

        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                return await self._delete_brand(brand_id, conn)

    # ==================== Brand Visibility Methods ====================

    async def _add_brand_visibility(
        self,
        brand_id: int,
        area_id: Optional[int],
        connection: asyncpg.Connection,
    ) -> None:
        """
        Private method to add visibility for a brand in a specific area.

        Args:
            brand_id: ID of the brand
            area_id: ID of the area (None for global visibility)
            connection: Database connection

        Raises:
            BrandNotFoundException: If brand not found
            BrandAlreadyExistsException: If visibility already exists
            BrandOperationException: If operation fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Check if brand exists
            brand_exists = await connection.fetchval(
                "SELECT EXISTS(SELECT 1 FROM brand WHERE id = $1 AND is_deleted = FALSE)",
                brand_id,
            )
            if not brand_exists:
                raise BrandNotFoundException(brand_id=brand_id)

            # Check if area exists (if area_id is provided)
            if area_id is not None:
                area_exists = await connection.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM areas WHERE id = $1)",
                    area_id,
                )
                if not area_exists:
                    raise BrandOperationException(
                        message=f"Area with ID {area_id} not found",
                        operation="add_visibility",
                    )

            # Try to insert or reactivate existing visibility
            await connection.execute(
                """
                INSERT INTO brand_visibility (brand_id, area_id, is_active)
                VALUES ($1, $2, TRUE)
                ON CONFLICT (brand_id, area_id) 
                WHERE is_active = TRUE
                DO UPDATE SET is_active = TRUE
                """,
                brand_id,
                area_id,
            )

            logger.info(
                "Brand visibility added successfully",
                brand_id=brand_id,
                area_id=area_id,
                company_id=str(self.company_id),
            )

        except BrandNotFoundException:
            raise
        except asyncpg.UniqueViolationError:
            raise BrandAlreadyExistsException(
                message=f"Visibility for brand {brand_id} in area {area_id} already exists",
            )
        except Exception as e:
            logger.error(
                "Failed to add brand visibility",
                brand_id=brand_id,
                area_id=area_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise BrandOperationException(
                message=f"Failed to add brand visibility: {str(e)}",
                operation="add_visibility",
            ) from e

    async def add_brand_visibility(
        self,
        brand_id: int,
        area_id: Optional[int],
        connection: Optional[asyncpg.Connection] = None,
    ) -> None:
        """
        Add visibility for a brand in a specific area.

        Args:
            brand_id: ID of the brand
            area_id: ID of the area (None for global visibility)
            connection: Optional database connection. If not provided, a new one is acquired.

        Raises:
            BrandNotFoundException: If brand not found
            BrandAlreadyExistsException: If visibility already exists
            BrandOperationException: If operation fails
        """
        if connection:
            return await self._add_brand_visibility(brand_id, area_id, connection)

        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                return await self._add_brand_visibility(brand_id, area_id, conn)

    async def _remove_brand_visibility(
        self,
        brand_id: int,
        area_id: Optional[int],
        connection: asyncpg.Connection,
    ) -> None:
        """
        Private method to remove visibility for a brand in a specific area.

        Args:
            brand_id: ID of the brand
            area_id: ID of the area (None for global visibility)
            connection: Database connection

        Raises:
            BrandNotFoundException: If brand or visibility not found
            BrandOperationException: If operation fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Check if brand exists
            brand_exists = await connection.fetchval(
                "SELECT EXISTS(SELECT 1 FROM brand WHERE id = $1 AND is_deleted = FALSE)",
                brand_id,
            )
            if not brand_exists:
                raise BrandNotFoundException(brand_id=brand_id)

            # Soft delete the visibility
            result = await connection.execute(
                """
                UPDATE brand_visibility
                SET is_active = FALSE
                WHERE brand_id = $1 AND area_id IS NOT DISTINCT FROM $2 AND is_active = TRUE
                """,
                brand_id,
                area_id,
            )

            if result == "UPDATE 0":
                area_desc = (
                    "global visibility" if area_id is None else f"area {area_id}"
                )
                raise BrandNotFoundException(
                    message=f"Visibility for brand {brand_id} in {area_desc} not found",
                )

            logger.info(
                "Brand visibility removed successfully",
                brand_id=brand_id,
                area_id=area_id,
                company_id=str(self.company_id),
            )

        except BrandNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to remove brand visibility",
                brand_id=brand_id,
                area_id=area_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise BrandOperationException(
                message=f"Failed to remove brand visibility: {str(e)}",
                operation="remove_visibility",
            ) from e

    async def remove_brand_visibility(
        self,
        brand_id: int,
        area_id: Optional[int],
        connection: Optional[asyncpg.Connection] = None,
    ) -> None:
        """
        Remove visibility for a brand in a specific area.

        Args:
            brand_id: ID of the brand
            area_id: ID of the area (None for global visibility)
            connection: Optional database connection. If not provided, a new one is acquired.

        Raises:
            BrandNotFoundException: If brand or visibility not found
            BrandOperationException: If operation fails
        """
        if connection:
            return await self._remove_brand_visibility(brand_id, area_id, connection)

        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                return await self._remove_brand_visibility(brand_id, area_id, conn)

    # ==================== Brand Margin Methods ====================

    async def _add_brand_margin(
        self,
        brand_id: int,
        area_id: Optional[int],
        margins: BrandMarginAddOrUpdate,
        connection: asyncpg.Connection,
    ) -> BrandMarginInDB:
        """
        Private method to add or update margin configuration for a brand in a specific area.

        Args:
            brand_id: ID of the brand
            area_id: ID of the area (None for global margin)
            margins: Margin configuration
            connection: Database connection

        Returns:
            Created or updated margin configuration

        Raises:
            BrandNotFoundException: If brand not found
            BrandOperationException: If operation fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Check if brand exists and get brand name
            brand_row = await connection.fetchrow(
                "SELECT name FROM brand WHERE id = $1 AND is_deleted = FALSE",
                brand_id,
            )
            if not brand_row:
                raise BrandNotFoundException(brand_id=brand_id)

            brand_name = brand_row["name"]

            # Check if area exists (if area_id is provided)
            if area_id is not None:
                area_exists = await connection.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM areas WHERE id = $1)",
                    area_id,
                )
                if not area_exists:
                    raise BrandOperationException(
                        message=f"Area with ID {area_id} not found",
                        operation="add_margin",
                    )

            # Check if margin exists for this brand and area
            existing_margin = await connection.fetchrow(
                """
                SELECT id FROM brand_margins
                WHERE brand_id = $1 AND area_id IS NOT DISTINCT FROM $2 AND is_active = TRUE
                """,
                brand_id,
                area_id,
            )

            if existing_margin:
                # Update existing margin
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
                params.append(brand_id)
                param_count += 1
                params.append(area_id)
                param_count += 1
                query = f"""
                    UPDATE brand_margins
                    SET {", ".join(update_fields)}
                    WHERE brand_id = ${param_count - 1} AND area_id IS NOT DISTINCT FROM ${param_count} AND is_active = TRUE
                    RETURNING id,name, area_id, margins, is_active, created_at, updated_at
                """
                row = await connection.fetchrow(query, *params)
            else:
                row = await connection.fetchrow(
                    """
                    INSERT INTO brand_margins (brand_id, area_id, margins, name)
                    VALUES ($1, $2, $3, $4)
                    RETURNING id, name, area_id, margins, is_active, created_at, updated_at
                    """,
                    brand_id,
                    area_id,
                    margins_json,
                    margins.name,
                )

            logger.info(
                "Brand margin added/updated successfully",
                brand_id=brand_id,
                area_id=area_id,
                company_id=str(self.company_id),
            )

            return BrandMarginInDB(
                id=row["id"],
                area_id=row["area_id"],
                name=margins.name,
                margins=BrandMargins.model_validate_json(row["margins"]),
                is_active=row["is_active"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

        except BrandNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to add brand margin",
                brand_id=brand_id,
                area_id=area_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise BrandOperationException(
                message=f"Failed to add brand margin: {str(e)}",
                operation="add_margin",
            ) from e

    async def add_brand_margin(
        self,
        brand_id: int,
        area_id: Optional[int],
        margins: BrandMargins,
        connection: Optional[asyncpg.Connection] = None,
    ) -> BrandMarginInDB:
        """
        Add or update margin configuration for a brand in a specific area.

        Args:
            brand_id: ID of the brand
            area_id: ID of the area (None for global margin)
            margins: Margin configuration
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Created or updated margin configuration

        Raises:
            BrandNotFoundException: If brand not found
            BrandOperationException: If operation fails
        """
        if connection:
            return await self._add_brand_margin(brand_id, area_id, margins, connection)

        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                return await self._add_brand_margin(brand_id, area_id, margins, conn)

    async def _remove_brand_margin(
        self,
        brand_id: int,
        area_id: Optional[int],
        connection: asyncpg.Connection,
    ) -> None:
        """
        Private method to remove margin configuration for a brand in a specific area.

        Args:
            brand_id: ID of the brand
            area_id: ID of the area (None for global margin)
            connection: Database connection

        Raises:
            BrandNotFoundException: If brand or margin not found
            BrandOperationException: If operation fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Check if brand exists
            brand_exists = await connection.fetchval(
                "SELECT EXISTS(SELECT 1 FROM brand WHERE id = $1 AND is_deleted = FALSE)",
                brand_id,
            )
            if not brand_exists:
                raise BrandNotFoundException(brand_id=brand_id)

            # Soft delete the margin
            result = await connection.execute(
                """
                UPDATE brand_margins
                SET is_active = FALSE
                WHERE brand_id = $1 AND area_id IS NOT DISTINCT FROM $2 AND is_active = TRUE
                """,
                brand_id,
                area_id,
            )

            if result == "UPDATE 0":
                area_desc = "global margin" if area_id is None else f"area {area_id}"
                raise BrandNotFoundException(
                    message=f"Margin for brand {brand_id} in {area_desc} not found",
                )

            logger.info(
                "Brand margin removed successfully",
                brand_id=brand_id,
                area_id=area_id,
                company_id=str(self.company_id),
            )

        except BrandNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to remove brand margin",
                brand_id=brand_id,
                area_id=area_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise BrandOperationException(
                message=f"Failed to remove brand margin: {str(e)}",
                operation="remove_margin",
            ) from e

    async def remove_brand_margin(
        self,
        brand_id: int,
        area_id: Optional[int],
        connection: Optional[asyncpg.Connection] = None,
    ) -> None:
        """
        Remove margin configuration for a brand in a specific area.

        Args:
            brand_id: ID of the brand
            area_id: ID of the area (None for global margin)
            connection: Optional database connection. If not provided, a new one is acquired.

        Raises:
            BrandNotFoundException: If brand or margin not found
            BrandOperationException: If operation fails
        """
        if connection:
            return await self._remove_brand_margin(brand_id, area_id, connection)

        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                return await self._remove_brand_margin(brand_id, area_id, conn)
