"""
Repository for Retailer entity operations.

This repository handles all database operations for retailers in a multi-tenant
architecture using schema-per-tenant approach with asyncpg.
"""

from typing import Optional
from uuid import UUID

import asyncpg
import structlog

from api.database import DatabasePool
from api.exceptions.retailer import (
    RetailerAlreadyExistsException,
    RetailerNotFoundException,
    RetailerOperationException,
)
from api.models.retailer import (
    RetailerCreate,
    RetailerDetailItem,
    RetailerInDB,
    RetailerListItem,
    RetailerUpdate,
)
from api.models.user import BankDetails
from api.repository.utils import get_schema_name, set_search_path

logger = structlog.get_logger(__name__)


class RetailerRepository:
    """
    Repository for managing Retailer entities in a multi-tenant database.

    This repository provides methods for CRUD operations on retailers,
    handling schema-per-tenant isolation using asyncpg.
    All methods raise exceptions when records are not found.
    """

    def __init__(self, db_pool: DatabasePool, company_id: UUID) -> None:
        """
        Initialize the RetailerRepository.

        Args:
            db_pool: Database pool instance for connection management
            company_id: UUID of the company (tenant) for schema isolation
        """
        self.db_pool = db_pool
        self.company_id = company_id
        self.schema_name = get_schema_name(company_id)

    async def _create_retailer(
        self,
        retailer_data: RetailerCreate,
        r_id: UUID,
        r_code: str,
        connection: asyncpg.Connection,
    ) -> RetailerInDB:
        """
        Private method to create a retailer with a provided connection.

        Args:
            retailer_data: Retailer data to create
            r_id: Retailer ID
            r_code: Retailer code
            connection: Database connection

        Returns:
            Created retailer

        Raises:
            RetailerAlreadyExistsException: If retailer with the same code/email/gst/pan/license/mobile already exists
            RetailerOperationException: If creation fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Prepare documents and store_images as JSON
            documents_json = None
            if retailer_data.documents:
                documents_json = retailer_data.documents.model_dump()

            store_images_json = None
            if retailer_data.store_images:
                store_images_json = retailer_data.store_images.model_dump()

            # Insert the retailer
            row = await connection.fetchrow(
                """
                INSERT INTO retailer (
                    id,name, code, contact_person_name, mobile_number, email,
                    gst_no, pan_no, license_no, address, category_id,
                    pin_code, map_link, documents, store_images, route_id,
                    is_type_a, is_type_b, is_type_c
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19)
                RETURNING id, name, code, contact_person_name, mobile_number, email,
                          gst_no, pan_no, license_no, address, category_id,
                          pin_code, map_link, documents, store_images, route_id,
                          is_verified, is_active, is_type_a, is_type_b, is_type_c,
                          created_at, updated_at
                """,
                r_id,
                retailer_data.name,
                r_code,
                retailer_data.contact_person_name,
                retailer_data.mobile_number,
                retailer_data.email,
                retailer_data.gst_no,
                retailer_data.pan_no,
                retailer_data.license_no,
                retailer_data.address,
                retailer_data.category_id,
                retailer_data.pin_code,
                retailer_data.map_link,
                documents_json,
                store_images_json,
                retailer_data.route_id,
                retailer_data.is_type_a,
                retailer_data.is_type_b,
                retailer_data.is_type_c,
            )

            logger.info(
                "Retailer created successfully",
                retailer_id=row["id"],
                retailer_code=r_code,
                retailer_name=retailer_data.name,
                company_id=str(self.company_id),
            )

            return RetailerInDB(**dict(row))

        except asyncpg.UniqueViolationError as e:
            error_msg = str(e)
            if "uniq_retailer_code" in error_msg:
                raise RetailerAlreadyExistsException(
                    retailer_code=retailer_data.code,
                    field="code",
                    value=retailer_data.code,
                )
            elif "uniq_retailer_gst_no" in error_msg:
                raise RetailerAlreadyExistsException(
                    field="gst_no",
                    value=retailer_data.gst_no,
                )
            elif "uniq_retailer_pan_no" in error_msg:
                raise RetailerAlreadyExistsException(
                    field="pan_no",
                    value=retailer_data.pan_no,
                )
            elif "uniq_retailer_license_no" in error_msg:
                raise RetailerAlreadyExistsException(
                    field="license_no",
                    value=retailer_data.license_no,
                )
            elif "uniq_retailer_mobile_number" in error_msg:
                raise RetailerAlreadyExistsException(
                    field="mobile_number",
                    value=retailer_data.mobile_number,
                )
            elif "uniq_retailer_email" in error_msg:
                raise RetailerAlreadyExistsException(
                    field="email",
                    value=retailer_data.email,
                )
            else:
                raise RetailerOperationException(
                    message=f"Failed to create retailer: {error_msg}",
                    operation="create",
                ) from e
        except asyncpg.ForeignKeyViolationError as e:
            error_msg = str(e)
            if "fk_retailer_shop_category" in error_msg:
                raise RetailerOperationException(
                    message=f"Shop category with id {retailer_data.category_id} not found",
                    operation="create",
                ) from e
            elif "fk_retailer_route" in error_msg:
                raise RetailerOperationException(
                    message=f"Route with id {retailer_data.route_id} not found",
                    operation="create",
                ) from e
            else:
                raise RetailerOperationException(
                    message=f"Failed to create retailer: {error_msg}",
                    operation="create",
                ) from e
        except Exception as e:
            logger.error(
                "Failed to create retailer",
                retailer_code=retailer_data.code,
                retailer_name=retailer_data.name,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RetailerOperationException(
                message=f"Failed to create retailer: {str(e)}",
                operation="create",
            ) from e

    async def create_retailer(
        self,
        retailer_data: RetailerCreate,
        r_id: UUID,
        r_code: str,
        connection: Optional[asyncpg.Connection] = None,
    ) -> RetailerInDB:
        """
        Create a new retailer.

        Args:
            retailer_data: Retailer data to create
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Created retailer

        Raises:
            RetailerAlreadyExistsException: If retailer with the same code already exists
            RetailerOperationException: If creation fails
        """
        if connection:
            return await self._create_retailer(retailer_data, r_id, r_code, connection)

        async with self.db_pool.acquire() as conn:
            return await self._create_retailer(retailer_data, r_id, r_code, conn)

    async def _get_retailer_by_id(
        self, retailer_id: UUID, connection: asyncpg.Connection
    ) -> RetailerDetailItem:
        """
        Private method to get a retailer by ID with a provided connection.

        Args:
            retailer_id: ID of the retailer
            connection: Database connection

        Returns:
            Retailer with details

        Raises:
            RetailerNotFoundException: If retailer not found
            RetailerOperationException: If retrieval fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            row = await connection.fetchrow(
                """
                SELECT 
                    r.id, r.name, r.code, r.contact_person_name, r.mobile_number,
                    r.email, r.gst_no, r.pan_no, r.license_no, r.address,
                    r.category_id, sc.name as category_name, r.pin_code, r.map_link,
                    r.documents, r.store_images, r.route_id, rt.name as route_name,
                    r.is_verified, r.is_active, r.is_type_a, r.is_type_b, r.is_type_c,
                    r.created_at, r.updated_at,
                    m.bank_details
                FROM retailer r
                INNER JOIN shop_categories sc ON r.category_id = sc.id
                INNER JOIN routes rt ON r.route_id = rt.id
                INNER JOIN members m ON r.id = m.id
                WHERE r.id = $1
                """,
                retailer_id,
            )

            if not row:
                raise RetailerNotFoundException(retailer_id=retailer_id)

            retailer_data = RetailerDetailItem(
                id=row["id"],
                name=row["name"],
                code=row["code"],
                contact_person_name=row["contact_person_name"],
                mobile_number=row["mobile_number"],
                email=row["email"],
                gst_no=row["gst_no"],
                pan_no=row["pan_no"],
                license_no=row["license_no"],
                address=row["address"],
                category_id=row["category_id"],
                category_name=row["category_name"],
                pin_code=row["pin_code"],
                map_link=row["map_link"],
                route_id=row["route_id"],
                route_name=row["route_name"],
                is_verified=row["is_verified"],
                is_active=row["is_active"],
                is_type_a=row["is_type_a"],
                is_type_b=row["is_type_b"],
                is_type_c=row["is_type_c"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                bank_details=BankDetails.model_validate_json(row["bank_details"]),
            )
            return retailer_data

        except RetailerNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to get retailer by id",
                retailer_id=str(retailer_id),
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RetailerOperationException(
                message=f"Failed to get retailer: {str(e)}",
                operation="get",
            ) from e

    async def get_retailer_by_id(
        self, retailer_id: UUID, connection: Optional[asyncpg.Connection] = None
    ) -> RetailerDetailItem:
        """
        Get a retailer by ID.

        Args:
            retailer_id: ID of the retailer
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Retailer with details

        Raises:
            RetailerNotFoundException: If retailer not found
            RetailerOperationException: If retrieval fails
        """
        if connection:
            return await self._get_retailer_by_id(retailer_id, connection)

        async with self.db_pool.acquire() as conn:
            return await self._get_retailer_by_id(retailer_id, conn)

    async def _get_retailer_by_code(
        self, code: str, connection: asyncpg.Connection
    ) -> RetailerDetailItem:
        """
        Private method to get a retailer by code with a provided connection.

        Args:
            code: Code of the retailer
            connection: Database connection

        Returns:
            Retailer with details

        Raises:
            RetailerNotFoundException: If retailer not found
            RetailerOperationException: If retrieval fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            row = await connection.fetchrow(
                """
                SELECT 
                    r.id, r.name, r.code, r.contact_person_name, r.mobile_number,
                    r.email, r.gst_no, r.pan_no, r.license_no, r.address,
                    r.category_id, sc.name as category_name, r.pin_code, r.map_link,
                    r.documents, r.store_images, r.route_id, rt.name as route_name,
                    r.is_type_a, r.is_type_b, r.is_type_c,
                    r.is_verified, r.is_active, r.created_at, r.updated_at,
                    m.bank_details
                FROM retailer r
                INNER JOIN shop_categories sc ON r.category_id = sc.id
                INNER JOIN routes rt ON r.route_id = rt.id
                INNER JOIN members m ON r.id = m.id
                WHERE r.code = $1 AND r.is_active = true
                """,
                code,
            )

            if not row:
                raise RetailerNotFoundException(retailer_code=code)

            retailer_data = RetailerDetailItem(
                id=row["id"],
                name=row["name"],
                code=row["code"],
                contact_person_name=row["contact_person_name"],
                mobile_number=row["mobile_number"],
                email=row["email"],
                gst_no=row["gst_no"],
                pan_no=row["pan_no"],
                license_no=row["license_no"],
                address=row["address"],
                category_id=row["category_id"],
                category_name=row["category_name"],
                pin_code=row["pin_code"],
                map_link=row["map_link"],
                is_type_a=row["is_type_a"],
                is_type_b=row["is_type_b"],
                is_type_c=row["is_type_c"],
                route_id=row["route_id"],
                route_name=row["route_name"],
                is_verified=row["is_verified"],
                is_active=row["is_active"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                bank_details=BankDetails.model_validate_json(row["bank_details"]),
            )
            return retailer_data

        except RetailerNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to get retailer by code",
                retailer_code=code,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RetailerOperationException(
                message=f"Failed to get retailer: {str(e)}",
                operation="get",
            ) from e

    async def get_retailer_by_code(
        self, code: str, connection: Optional[asyncpg.Connection] = None
    ) -> RetailerDetailItem:
        """
        Get a retailer by code.

        Args:
            code: Code of the retailer
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Retailer with details

        Raises:
            RetailerNotFoundException: If retailer not found
            RetailerOperationException: If retrieval fails
        """
        if connection:
            return await self._get_retailer_by_code(code, connection)

        async with self.db_pool.acquire() as conn:
            return await self._get_retailer_by_code(code, conn)

    async def _list_retailers(
        self,
        connection: asyncpg.Connection,
        route_id: Optional[int] = None,
        category_id: Optional[int] = None,
        is_active: Optional[bool] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[RetailerListItem]:
        """
        Private method to list retailers with a provided connection.
        Returns minimal data to optimize performance.

        Args:
            connection: Database connection
            route_id: Filter by route ID
            category_id: Filter by category ID
            is_active: Filter by active status
            limit: Maximum number of retailers to return
            offset: Number of retailers to skip

        Returns:
            List of retailers with minimal data

        Raises:
            RetailerOperationException: If listing fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Build dynamic query
            query = """
                SELECT 
                    r.id, r.name, r.code, r.contact_person_name,
                    r.mobile_number, r.address, r.route_id,
                    rt.name as route_name, r.store_images, r.is_verified, r.is_active,
                    r.is_type_a, r.is_type_b, r.is_type_c
                FROM retailer r
                INNER JOIN routes rt ON r.route_id = rt.id
            """
            params = []
            param_count = 0
            conditions = []

            # Add WHERE conditions
            if route_id is not None:
                param_count += 1
                conditions.append(f"r.route_id = ${param_count}")
                params.append(route_id)

            if category_id is not None:
                param_count += 1
                conditions.append(f"r.category_id = ${param_count}")
                params.append(category_id)

            if is_active is not None:
                param_count += 1
                conditions.append(f"r.is_active = ${param_count}")
                params.append(is_active)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            # Add ordering
            query += " ORDER BY r.code ASC"

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

            return [RetailerListItem(**dict(row)) for row in rows]

        except Exception as e:
            logger.error(
                "Failed to list retailers",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RetailerOperationException(
                message=f"Failed to list retailers: {str(e)}",
                operation="list",
            ) from e

    async def list_retailers(
        self,
        route_id: Optional[int] = None,
        category_id: Optional[int] = None,
        is_active: Optional[bool] = None,
        limit: int = 20,
        offset: int = 0,
        connection: Optional[asyncpg.Connection] = None,
    ) -> list[RetailerListItem]:
        """
        List all retailers with optional filtering.
        Returns minimal data to optimize performance.

        Args:
            route_id: Filter by route ID
            category_id: Filter by category ID
            is_active: Filter by active status
            limit: Maximum number of retailers to return
            offset: Number of retailers to skip
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            List of retailers with minimal data

        Raises:
            RetailerOperationException: If listing fails
        """
        if connection:
            return await self._list_retailers(
                connection, route_id, category_id, is_active, limit, offset
            )

        async with self.db_pool.acquire() as conn:
            return await self._list_retailers(
                conn, route_id, category_id, is_active, limit, offset
            )

    async def _count_retailers(
        self,
        connection: asyncpg.Connection,
        route_id: Optional[int] = None,
        category_id: Optional[int] = None,
        is_active: Optional[bool] = None,
    ) -> int:
        """
        Private method to count retailers with a provided connection.

        Args:
            connection: Database connection
            route_id: Filter by route ID
            category_id: Filter by category ID
            is_active: Filter by active status

        Returns:
            Count of retailers

        Raises:
            RetailerOperationException: If counting fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Build dynamic query
            query = "SELECT COUNT(*) FROM retailer"
            params = []
            param_count = 0
            conditions = []

            if route_id is not None:
                param_count += 1
                conditions.append(f"route_id = ${param_count}")
                params.append(route_id)

            if category_id is not None:
                param_count += 1
                conditions.append(f"category_id = ${param_count}")
                params.append(category_id)

            if is_active is not None:
                param_count += 1
                conditions.append(f"is_active = ${param_count}")
                params.append(is_active)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            count = await connection.fetchval(query, *params)
            return count or 0

        except Exception as e:
            logger.error(
                "Failed to count retailers",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RetailerOperationException(
                message=f"Failed to count retailers: {str(e)}",
                operation="count",
            ) from e

    async def count_retailers(
        self,
        route_id: Optional[int] = None,
        category_id: Optional[int] = None,
        is_active: Optional[bool] = None,
        connection: Optional[asyncpg.Connection] = None,
    ) -> int:
        """
        Count retailers with optional filtering.

        Args:
            route_id: Filter by route ID
            category_id: Filter by category ID
            is_active: Filter by active status
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Count of retailers

        Raises:
            RetailerOperationException: If counting fails
        """
        if connection:
            return await self._count_retailers(
                connection, route_id, category_id, is_active
            )

        async with self.db_pool.acquire() as conn:
            return await self._count_retailers(conn, route_id, category_id, is_active)

    async def _update_retailer(
        self,
        retailer_id: UUID,
        retailer_data: RetailerUpdate,
        connection: asyncpg.Connection,
    ) -> RetailerInDB:
        """
        Private method to update a retailer with a provided connection.

        Args:
            retailer_id: ID of the retailer to update
            retailer_data: Retailer data to update
            connection: Database connection

        Returns:
            Updated retailer

        Raises:
            RetailerNotFoundException: If retailer not found
            RetailerOperationException: If update fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Build dynamic update query
            update_fields = []
            params = []
            param_count = 0

            if retailer_data.name is not None:
                param_count += 1
                update_fields.append(f"name = ${param_count}")
                params.append(retailer_data.name)

            if retailer_data.contact_person_name is not None:
                param_count += 1
                update_fields.append(f"contact_person_name = ${param_count}")
                params.append(retailer_data.contact_person_name)

            if retailer_data.mobile_number is not None:
                param_count += 1
                update_fields.append(f"mobile_number = ${param_count}")
                params.append(retailer_data.mobile_number)

            if retailer_data.email is not None:
                param_count += 1
                update_fields.append(f"email = ${param_count}")
                params.append(retailer_data.email)

            if retailer_data.gst_no is not None:
                param_count += 1
                update_fields.append(f"gst_no = ${param_count}")
                params.append(retailer_data.gst_no)

            if retailer_data.pan_no is not None:
                param_count += 1
                update_fields.append(f"pan_no = ${param_count}")
                params.append(retailer_data.pan_no)

            if retailer_data.license_no is not None:
                param_count += 1
                update_fields.append(f"license_no = ${param_count}")
                params.append(retailer_data.license_no)

            if retailer_data.address is not None:
                param_count += 1
                update_fields.append(f"address = ${param_count}")
                params.append(retailer_data.address)

            if retailer_data.category_id is not None:
                param_count += 1
                update_fields.append(f"category_id = ${param_count}")
                params.append(retailer_data.category_id)

            if retailer_data.pin_code is not None:
                param_count += 1
                update_fields.append(f"pin_code = ${param_count}")
                params.append(retailer_data.pin_code)

            if retailer_data.map_link is not None:
                param_count += 1
                update_fields.append(f"map_link = ${param_count}")
                params.append(retailer_data.map_link)

            if retailer_data.route_id is not None:
                param_count += 1
                update_fields.append(f"route_id = ${param_count}")
                params.append(retailer_data.route_id)

            if retailer_data.is_verified is not None:
                param_count += 1
                update_fields.append(f"is_verified = ${param_count}")
                params.append(retailer_data.is_verified)

            if retailer_data.is_type_a is not None:
                param_count += 1
                update_fields.append(f"is_type_a = ${param_count}")
                params.append(retailer_data.is_type_a)

            if retailer_data.is_type_b is not None:
                param_count += 1
                update_fields.append(f"is_type_b = ${param_count}")
                params.append(retailer_data.is_type_b)

            if retailer_data.is_type_c is not None:
                param_count += 1
                update_fields.append(f"is_type_c = ${param_count}")
                params.append(retailer_data.is_type_c)

            if not update_fields:
                # No fields to update, return current retailer
                # Convert to RetailerInDB by fetching without joins
                row = await connection.fetchrow(
                    """
                    SELECT id, name, code, contact_person_name, mobile_number, email,
                           gst_no, pan_no, license_no, address, category_id,
                           pin_code, map_link, documents, store_images, route_id,
                           is_verified, is_active, is_type_a, is_type_b, is_type_c,
                           created_at, updated_at
                    FROM retailer
                    WHERE id = $1
                    """,
                    retailer_id,
                )
                if not row:
                    raise RetailerNotFoundException(retailer_id=retailer_id)
                return RetailerInDB(**dict(row))

            param_count += 1
            params.append(retailer_id)

            query = f"""
                UPDATE retailer
                SET {", ".join(update_fields)}
                WHERE id = ${param_count}
                RETURNING id, name, code, contact_person_name, mobile_number, email,
                          gst_no, pan_no, license_no, address, category_id,
                          pin_code, map_link, documents, store_images, route_id,
                          is_verified, is_active, is_type_a, is_type_b, is_type_c,
                          created_at, updated_at
            """

            row = await connection.fetchrow(query, *params)

            if not row:
                raise RetailerNotFoundException(retailer_id=retailer_id)

            logger.info(
                "Retailer updated successfully",
                retailer_id=str(retailer_id),
                company_id=str(self.company_id),
            )

            return RetailerInDB(**dict(row))

        except (RetailerNotFoundException, RetailerAlreadyExistsException):
            raise
        except asyncpg.UniqueViolationError as e:
            error_msg = str(e)
            if "uniq_retailer_gst_no" in error_msg:
                raise RetailerAlreadyExistsException(
                    field="gst_no", value=retailer_data.gst_no
                )
            elif "uniq_retailer_pan_no" in error_msg:
                raise RetailerAlreadyExistsException(
                    field="pan_no", value=retailer_data.pan_no
                )
            elif "uniq_retailer_license_no" in error_msg:
                raise RetailerAlreadyExistsException(
                    field="license_no", value=retailer_data.license_no
                )
            elif "uniq_retailer_mobile_number" in error_msg:
                raise RetailerAlreadyExistsException(
                    field="mobile_number", value=retailer_data.mobile_number
                )
            elif "uniq_retailer_email" in error_msg:
                raise RetailerAlreadyExistsException(
                    field="email", value=retailer_data.email
                )
            else:
                raise RetailerOperationException(
                    message=f"Failed to update retailer: {error_msg}",
                    operation="update",
                ) from e
        except Exception as e:
            logger.error(
                "Failed to update retailer",
                retailer_id=str(retailer_id),
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RetailerOperationException(
                message=f"Failed to update retailer: {str(e)}",
                operation="update",
            ) from e

    async def update_retailer(
        self,
        retailer_id: UUID,
        retailer_data: RetailerUpdate,
        connection: Optional[asyncpg.Connection] = None,
    ) -> RetailerInDB:
        """
        Update an existing retailer.

        Args:
            retailer_id: ID of the retailer to update
            retailer_data: Retailer data to update
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Updated retailer

        Raises:
            RetailerNotFoundException: If retailer not found
            RetailerOperationException: If update fails
        """
        if connection:
            return await self._update_retailer(retailer_id, retailer_data, connection)

        async with self.db_pool.acquire() as conn:
            return await self._update_retailer(retailer_id, retailer_data, conn)

    async def _delete_retailer(
        self, retailer_id: UUID, connection: asyncpg.Connection
    ) -> RetailerInDB:
        """
        Private method to soft delete a retailer (set is_active=False) with a provided connection.

        Args:
            retailer_id: ID of the retailer to soft delete
            connection: Database connection

        Returns:
            Updated retailer with is_active=False

        Raises:
            RetailerNotFoundException: If retailer not found
            RetailerOperationException: If soft deletion fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Check if retailer exists
            await self._get_retailer_by_id(retailer_id, connection)

            # Soft delete retailer
            await connection.execute(
                "UPDATE retailer SET is_active = FALSE WHERE id = $1",
                retailer_id,
            )

            logger.info(
                "Retailer soft deleted successfully",
                retailer_id=str(retailer_id),
                company_id=str(self.company_id),
            )

            # Fetch updated retailer
            row = await connection.fetchrow(
                """
                SELECT id, name, code, contact_person_name, mobile_number, email,
                       gst_no, pan_no, license_no, address, category_id,
                       pin_code, map_link, documents, store_images, route_id,
                       is_verified, is_active, is_type_a, is_type_b, is_type_c,
                       created_at, updated_at
                FROM retailer
                WHERE id = $1
                """,
                retailer_id,
            )

            return RetailerInDB(**dict(row))

        except RetailerNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to soft delete retailer",
                retailer_id=str(retailer_id),
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RetailerOperationException(
                message=f"Failed to soft delete retailer: {str(e)}",
                operation="soft_delete",
            ) from e

    async def delete_retailer(
        self, retailer_id: UUID, connection: Optional[asyncpg.Connection] = None
    ) -> None:
        """
        Delete a retailer by setting is_active to False.

        Args:
            retailer_id: ID of the retailer to delete
            connection: Optional database connection. If not provided, a new one is acquired.
        """
        if connection:
            return await self._delete_retailer(retailer_id, connection)

        async with self.db_pool.acquire() as conn:
            return await self._delete_retailer(retailer_id, conn)

    async def _get_retailers_by_route(
        self,
        route_id: int,
        connection: asyncpg.Connection,
    ) -> list[RetailerListItem]:
        """
        Private method to get all retailers for a specific route.

        Args:
            route_id: ID of the route
            connection: Database connection

        Returns:
            List of retailers

        Raises:
            RetailerOperationException: If retrieval fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            rows = await connection.fetch(
                """
                SELECT 
                    r.id, r.name, r.code, r.contact_person_name,
                    r.mobile_number, r.address, r.route_id,
                    rt.name as route_name, r.store_images, r.is_verified, r.is_active,
                    r.is_type_a, r.is_type_b, r.is_type_c
                FROM retailer r
                INNER JOIN routes rt ON r.route_id = rt.id
                WHERE r.route_id = $1 AND r.is_active = true
                ORDER BY r.code ASC
                """,
                route_id,
            )

            return [RetailerListItem(**dict(row)) for row in rows]

        except Exception as e:
            logger.error(
                "Failed to get retailers by route",
                route_id=route_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RetailerOperationException(
                message=f"Failed to get retailers by route: {str(e)}",
                operation="get_by_route",
            ) from e

    async def get_retailers_by_route(
        self,
        route_id: int,
        connection: Optional[asyncpg.Connection] = None,
    ) -> list[RetailerListItem]:
        """
        Get all retailers for a specific route.

        Args:
            route_id: ID of the route
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            List of retailers

        Raises:
            RetailerOperationException: If retrieval fails
        """
        if connection:
            return await self._get_retailers_by_route(route_id, connection)

        async with self.db_pool.acquire() as conn:
            return await self._get_retailers_by_route(route_id, conn)

    async def get_serial_number(self, connection: asyncpg.Connection) -> int:
        """
        Get the next serial number for a retailer.

        Args:
            connection: Database connection

        Returns:
            Next serial number
        """
        try:
            await set_search_path(connection, self.schema_name)
            value = await connection.fetchval(
                "SELECT nextval('retailer_id_seq')",
            )
            return value
        except Exception as e:
            logger.error(
                "Failed to get serial number",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RetailerOperationException(
                message=f"Failed to get serial number: {str(e)}",
                operation="get_serial_number",
            ) from e
