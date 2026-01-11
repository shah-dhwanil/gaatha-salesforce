"""
Repository for Distributor entity operations.

This repository handles all database operations for distributors in a multi-tenant
architecture using schema-per-tenant approach with asyncpg.
"""

from typing import Optional
from uuid import UUID

import asyncpg
import structlog

from api.database import DatabasePool
from api.exceptions.distributor import (
    DistributorAlreadyExistsException,
    DistributorNotFoundException,
    DistributorOperationException,
)
from api.models.distributor import (
    DistributorCreate,
    DistributorDetailItem,
    DistributorInDB,
    DistributorListItem,
    DistributorRouteDetail,
    DistributorUpdate,
)
from api.models.user import BankDetails
from api.repository.utils import get_schema_name, set_search_path

logger = structlog.get_logger(__name__)


class DistributorRepository:
    """
    Repository for managing Distributor entities in a multi-tenant database.

    This repository provides methods for CRUD operations on distributors,
    handling schema-per-tenant isolation using asyncpg.
    All methods raise exceptions when records are not found.
    """

    def __init__(self, db_pool: DatabasePool, company_id: UUID) -> None:
        """
        Initialize the DistributorRepository.

        Args:
            db_pool: Database pool instance for connection management
            company_id: UUID of the company (tenant) for schema isolation
        """
        self.db_pool = db_pool
        self.company_id = company_id
        self.schema_name = get_schema_name(company_id)

    async def _create_distributor(
        self,
        distributor_data: DistributorCreate,
        d_id: UUID,
        d_code: str,
        connection: asyncpg.Connection,
    ) -> DistributorInDB:
        """
        Private method to create a distributor with a provided connection.

        Args:
            distributor_data: Distributor data to create
            d_id: Distributor ID
            d_code: Distributor code
            connection: Database connection

        Returns:
            Created distributor

        Raises:
            DistributorAlreadyExistsException: If distributor with the same code/email/gst/pan/license/mobile already exists
            DistributorOperationException: If creation fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Prepare documents and store_images as JSON
            documents_json = None
            if distributor_data.documents:
                documents_json = distributor_data.documents.model_dump()

            store_images_json = None
            if distributor_data.store_images:
                store_images_json = distributor_data.store_images.model_dump()

            # Insert the distributor
            row = await connection.fetchrow(
                """
                INSERT INTO distributor (
                    id, name, code, contact_person_name, mobile_number, email,
                    gst_no, pan_no, license_no, address, pin_code, map_link,
                    documents, store_images, vehicle_3, vehicle_4, salesman_count,
                    area_id, for_general, for_modern, for_horeca
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21)
                RETURNING id, name, code, contact_person_name, mobile_number, email,
                          gst_no, pan_no, license_no, address, pin_code, map_link,
                          documents, store_images, vehicle_3, vehicle_4, salesman_count,
                          area_id, for_general, for_modern, for_horeca,
                          is_active, created_at, updated_at
                """,
                d_id,
                distributor_data.name,
                d_code,
                distributor_data.contact_person_name,
                distributor_data.mobile_number,
                distributor_data.email,
                distributor_data.gst_no,
                distributor_data.pan_no,
                distributor_data.license_no,
                distributor_data.address,
                distributor_data.pin_code,
                distributor_data.map_link,
                documents_json,
                store_images_json,
                distributor_data.vehicle_3,
                distributor_data.vehicle_4,
                distributor_data.salesman_count,
                distributor_data.area_id,
                distributor_data.for_general,
                distributor_data.for_modern,
                distributor_data.for_horeca,
            )

            # Insert distributor routes if provided
            if distributor_data.route_ids:
                for route_id in distributor_data.route_ids:
                    await connection.execute(
                        """
                        INSERT INTO distributor_routes (distributor_id, route_id)
                        VALUES ($1, $2)
                        """,
                        d_id,
                        route_id,
                    )

            logger.info(
                "Distributor created successfully",
                distributor_id=row["id"],
                distributor_code=d_code,
                distributor_name=distributor_data.name,
                company_id=str(self.company_id),
            )

            return DistributorInDB(**dict(row))

        except asyncpg.UniqueViolationError as e:
            error_msg = str(e)
            if "uniq_distributor_code" in error_msg:
                raise DistributorAlreadyExistsException(
                    distributor_code=distributor_data.code,
                    field="code",
                    value=d_code,
                )
            elif "uniq_distributor_gst_no" in error_msg:
                raise DistributorAlreadyExistsException(
                    field="gst_no",
                    value=distributor_data.gst_no,
                )
            elif "uniq_distributor_pan_no" in error_msg:
                raise DistributorAlreadyExistsException(
                    field="pan_no",
                    value=distributor_data.pan_no,
                )
            elif "uniq_distributor_license_no" in error_msg:
                raise DistributorAlreadyExistsException(
                    field="license_no",
                    value=distributor_data.license_no,
                )
            elif "uniq_distributor_mobile_number" in error_msg:
                raise DistributorAlreadyExistsException(
                    field="mobile_number",
                    value=distributor_data.mobile_number,
                )
            elif "uniq_distributor_email" in error_msg:
                raise DistributorAlreadyExistsException(
                    field="email",
                    value=distributor_data.email,
                )
            else:
                raise DistributorOperationException(
                    message=f"Failed to create distributor: {error_msg}",
                    operation="create",
                ) from e
        except asyncpg.ForeignKeyViolationError as e:
            error_msg = str(e)
            if "fk_distributor_area_id" in error_msg:
                raise DistributorOperationException(
                    message=f"Area with id {distributor_data.area_id} not found",
                    operation="create",
                ) from e
            else:
                raise DistributorOperationException(
                    message=f"Failed to create distributor: {error_msg}",
                    operation="create",
                ) from e
        except Exception as e:
            logger.error(
                "Failed to create distributor",
                distributor_code=d_code,
                distributor_name=distributor_data.name,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise DistributorOperationException(
                message=f"Failed to create distributor: {str(e)}",
                operation="create",
            ) from e

    async def create_distributor(
        self,
        distributor_data: DistributorCreate,
        d_id: UUID,
        d_code: str,
        connection: Optional[asyncpg.Connection] = None,
    ) -> DistributorInDB:
        """
        Create a new distributor.

        Args:
            distributor_data: Distributor data to create
            d_id: Distributor ID
            d_code: Distributor code
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Created distributor

        Raises:
            DistributorAlreadyExistsException: If distributor with the same code already exists
            DistributorOperationException: If creation fails
        """
        if connection:
            return await self._create_distributor(
                distributor_data, d_id, d_code, connection
            )

        async with self.db_pool.acquire() as conn:
            return await self._create_distributor(distributor_data, d_id, d_code, conn)

    async def _get_distributor_by_id(
        self, distributor_id: UUID, connection: asyncpg.Connection
    ) -> DistributorDetailItem:
        """
        Private method to get a distributor by ID with a provided connection.

        Args:
            distributor_id: ID of the distributor
            connection: Database connection

        Returns:
            Distributor with details

        Raises:
            DistributorNotFoundException: If distributor not found
            DistributorOperationException: If retrieval fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            row = await connection.fetchrow(
                """
                SELECT 
                    d.id, d.name, d.code, d.contact_person_name, d.mobile_number,
                    d.email, d.gst_no, d.pan_no, d.license_no, d.address,
                    d.pin_code, d.map_link, d.documents, d.store_images,
                    d.vehicle_3, d.vehicle_4, d.salesman_count, d.area_id,
                    a.name as area_name, d.for_general, d.for_modern, d.for_horeca,
                    d.is_active, d.created_at, d.updated_at,
                    m.bank_details
                FROM distributor d
                INNER JOIN areas a ON d.area_id = a.id
                INNER JOIN members m ON d.id = m.id
                WHERE d.id = $1
                """,
                distributor_id,
            )

            if not row:
                raise DistributorNotFoundException(distributor_id=distributor_id)

            # Fetch route details
            route_rows = await connection.fetch(
                """
                SELECT 
                    r.id, r.name, r.is_general, r.is_modern, r.is_horeca
                FROM routes r
                INNER JOIN distributor_routes dr ON r.id = dr.route_id
                WHERE dr.distributor_id = $1 AND dr.is_active = true AND r.is_active = true
                ORDER BY r.name
                """,
                distributor_id,
            )

            # Convert route data to DistributorRouteDetail objects
            routes = []
            for route_row in route_rows:
                route_type = (
                    "general"
                    if route_row["is_general"]
                    else "modern"
                    if route_row["is_modern"]
                    else "horeca"
                )
                routes.append(
                    DistributorRouteDetail(
                        id=route_row["id"],
                        name=route_row["name"],
                        type=route_type,
                    )
                )

            distributor_data = DistributorDetailItem(
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
                pin_code=row["pin_code"],
                map_link=row["map_link"],
                documents=row["documents"],
                store_images=row["store_images"],
                vehicle_3=row["vehicle_3"],
                vehicle_4=row["vehicle_4"],
                salesman_count=row["salesman_count"],
                area_id=row["area_id"],
                area_name=row["area_name"],
                for_general=row["for_general"],
                for_modern=row["for_modern"],
                for_horeca=row["for_horeca"],
                bank_details=BankDetails.model_validate_json(row["bank_details"]),
                routes=routes,
                is_active=row["is_active"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            return distributor_data

        except DistributorNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to get distributor by id",
                distributor_id=str(distributor_id),
                error=str(e),
                company_id=str(self.company_id),
            )
            raise DistributorOperationException(
                message=f"Failed to get distributor: {str(e)}",
                operation="get",
            ) from e

    async def get_distributor_by_id(
        self, distributor_id: UUID, connection: Optional[asyncpg.Connection] = None
    ) -> DistributorDetailItem:
        """
        Get a distributor by ID.

        Args:
            distributor_id: ID of the distributor
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Distributor with details

        Raises:
            DistributorNotFoundException: If distributor not found
            DistributorOperationException: If retrieval fails
        """
        if connection:
            return await self._get_distributor_by_id(distributor_id, connection)

        async with self.db_pool.acquire() as conn:
            return await self._get_distributor_by_id(distributor_id, conn)

    async def _get_distributor_by_code(
        self, code: str, connection: asyncpg.Connection
    ) -> DistributorDetailItem:
        """
        Private method to get a distributor by code with a provided connection.

        Args:
            code: Code of the distributor
            connection: Database connection

        Returns:
            Distributor with details

        Raises:
            DistributorNotFoundException: If distributor not found
            DistributorOperationException: If retrieval fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            row = await connection.fetchrow(
                """
                SELECT 
                    d.id, d.name, d.code, d.contact_person_name, d.mobile_number,
                    d.email, d.gst_no, d.pan_no, d.license_no, d.address,
                    d.pin_code, d.map_link, d.documents, d.store_images,
                    d.vehicle_3, d.vehicle_4, d.salesman_count, d.area_id,
                    a.name as area_name, d.for_general, d.for_modern, d.for_horeca,
                    d.is_active, d.created_at, d.updated_at,
                    m.bank_details
                FROM distributor d
                INNER JOIN areas a ON d.area_id = a.id
                INNER JOIN members m ON d.id = m.id
                WHERE d.code = $1 AND d.is_active = true
                """,
                code,
            )

            if not row:
                raise DistributorNotFoundException(distributor_code=code)

            # Fetch route details
            route_rows = await connection.fetch(
                """
                SELECT 
                    r.id, r.name, r.is_general, r.is_modern, r.is_horeca
                FROM routes r
                INNER JOIN distributor_routes dr ON r.id = dr.route_id
                WHERE dr.distributor_id = $1 AND dr.is_active = true AND r.is_active = true
                ORDER BY r.name
                """,
                row["id"],
            )

            # Convert route data to DistributorRouteDetail objects
            routes = []
            for route_row in route_rows:
                route_type = (
                    "general"
                    if route_row["is_general"]
                    else "modern"
                    if route_row["is_modern"]
                    else "horeca"
                )
                routes.append(
                    DistributorRouteDetail(
                        id=route_row["id"],
                        name=route_row["name"],
                        type=route_type,
                    )
                )

            distributor_data = DistributorDetailItem(
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
                pin_code=row["pin_code"],
                map_link=row["map_link"],
                documents=row["documents"],
                store_images=row["store_images"],
                vehicle_3=row["vehicle_3"],
                vehicle_4=row["vehicle_4"],
                salesman_count=row["salesman_count"],
                area_id=row["area_id"],
                area_name=row["area_name"],
                for_general=row["for_general"],
                for_modern=row["for_modern"],
                for_horeca=row["for_horeca"],
                bank_details=BankDetails.model_validate_json(row["bank_details"]),
                routes=routes,
                is_active=row["is_active"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            return distributor_data

        except DistributorNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to get distributor by code",
                distributor_code=code,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise DistributorOperationException(
                message=f"Failed to get distributor: {str(e)}",
                operation="get",
            ) from e

    async def get_distributor_by_code(
        self, code: str, connection: Optional[asyncpg.Connection] = None
    ) -> DistributorDetailItem:
        """
        Get a distributor by code.

        Args:
            code: Code of the distributor
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Distributor with details

        Raises:
            DistributorNotFoundException: If distributor not found
            DistributorOperationException: If retrieval fails
        """
        if connection:
            return await self._get_distributor_by_code(code, connection)

        async with self.db_pool.acquire() as conn:
            return await self._get_distributor_by_code(code, conn)

    async def _list_distributors(
        self,
        connection: asyncpg.Connection,
        area_id: Optional[int] = None,
        is_active: Optional[bool] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[DistributorListItem]:
        """
        Private method to list distributors with a provided connection.
        Returns minimal data to optimize performance.

        Args:
            connection: Database connection
            area_id: Filter by area ID
            is_active: Filter by active status
            limit: Maximum number of distributors to return
            offset: Number of distributors to skip

        Returns:
            List of distributors with minimal data

        Raises:
            DistributorOperationException: If listing fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Build dynamic query
            query = """
                SELECT 
                    d.id, d.name, d.code, d.contact_person_name,
                    d.mobile_number, d.address, d.area_id,
                    a.name as area_name, d.is_active,
                    COUNT(r.id) as route_count
                FROM distributor d
                INNER JOIN areas a ON d.area_id = a.id
                LEFT JOIN distributor_routes dr ON d.id = dr.distributor_id AND dr.is_active = true
                LEFT JOIN routes r ON r.id = dr.route_id and r.is_active = true
            """
            params = []
            param_count = 0
            conditions = []

            # Add WHERE conditions
            if area_id is not None:
                param_count += 1
                conditions.append(f"d.area_id = ${param_count}")
                params.append(area_id)

            if is_active is not None:
                param_count += 1
                conditions.append(f"d.is_active = ${param_count}")
                params.append(is_active)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            # Add GROUP BY
            query += """
                GROUP BY d.id, d.name, d.code, d.contact_person_name,
                         d.mobile_number, d.address, d.area_id, a.name, d.is_active
            """

            # Add ordering
            query += " ORDER BY d.code ASC"

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

            return [DistributorListItem(**dict(row)) for row in rows]

        except Exception as e:
            logger.error(
                "Failed to list distributors",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise DistributorOperationException(
                message=f"Failed to list distributors: {str(e)}",
                operation="list",
            ) from e

    async def list_distributors(
        self,
        area_id: Optional[int] = None,
        is_active: Optional[bool] = None,
        limit: int = 20,
        offset: int = 0,
        connection: Optional[asyncpg.Connection] = None,
    ) -> list[DistributorListItem]:
        """
        List all distributors with optional filtering.
        Returns minimal data to optimize performance.

        Args:
            area_id: Filter by area ID
            is_active: Filter by active status
            limit: Maximum number of distributors to return
            offset: Number of distributors to skip
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            List of distributors with minimal data

        Raises:
            DistributorOperationException: If listing fails
        """
        if connection:
            return await self._list_distributors(
                connection, area_id, is_active, limit, offset
            )

        async with self.db_pool.acquire() as conn:
            return await self._list_distributors(
                conn, area_id, is_active, limit, offset
            )

    async def _count_distributors(
        self,
        connection: asyncpg.Connection,
        area_id: Optional[int] = None,
        is_active: Optional[bool] = None,
    ) -> int:
        """
        Private method to count distributors with a provided connection.

        Args:
            connection: Database connection
            area_id: Filter by area ID
            is_active: Filter by active status

        Returns:
            Count of distributors

        Raises:
            DistributorOperationException: If counting fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Build dynamic query
            query = "SELECT COUNT(*) FROM distributor"
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

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            count = await connection.fetchval(query, *params)
            return count or 0

        except Exception as e:
            logger.error(
                "Failed to count distributors",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise DistributorOperationException(
                message=f"Failed to count distributors: {str(e)}",
                operation="count",
            ) from e

    async def count_distributors(
        self,
        area_id: Optional[int] = None,
        is_active: Optional[bool] = None,
        connection: Optional[asyncpg.Connection] = None,
    ) -> int:
        """
        Count distributors with optional filtering.

        Args:
            area_id: Filter by area ID
            is_active: Filter by active status
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Count of distributors

        Raises:
            DistributorOperationException: If counting fails
        """
        if connection:
            return await self._count_distributors(connection, area_id, is_active)

        async with self.db_pool.acquire() as conn:
            return await self._count_distributors(conn, area_id, is_active)

    async def _update_distributor(
        self,
        distributor_id: UUID,
        distributor_data: DistributorUpdate,
        connection: asyncpg.Connection,
    ) -> DistributorInDB:
        """
        Private method to update a distributor with a provided connection.

        Args:
            distributor_id: ID of the distributor to update
            distributor_data: Distributor data to update
            connection: Database connection

        Returns:
            Updated distributor

        Raises:
            DistributorNotFoundException: If distributor not found
            DistributorOperationException: If update fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Build dynamic update query
            update_fields = []
            params = []
            param_count = 0

            if distributor_data.name is not None:
                param_count += 1
                update_fields.append(f"name = ${param_count}")
                params.append(distributor_data.name)

            if distributor_data.contact_person_name is not None:
                param_count += 1
                update_fields.append(f"contact_person_name = ${param_count}")
                params.append(distributor_data.contact_person_name)

            if distributor_data.mobile_number is not None:
                param_count += 1
                update_fields.append(f"mobile_number = ${param_count}")
                params.append(distributor_data.mobile_number)

            if distributor_data.email is not None:
                param_count += 1
                update_fields.append(f"email = ${param_count}")
                params.append(distributor_data.email)

            if distributor_data.gst_no is not None:
                param_count += 1
                update_fields.append(f"gst_no = ${param_count}")
                params.append(distributor_data.gst_no)

            if distributor_data.pan_no is not None:
                param_count += 1
                update_fields.append(f"pan_no = ${param_count}")
                params.append(distributor_data.pan_no)

            if distributor_data.license_no is not None:
                param_count += 1
                update_fields.append(f"license_no = ${param_count}")
                params.append(distributor_data.license_no)

            if distributor_data.address is not None:
                param_count += 1
                update_fields.append(f"address = ${param_count}")
                params.append(distributor_data.address)

            if distributor_data.pin_code is not None:
                param_count += 1
                update_fields.append(f"pin_code = ${param_count}")
                params.append(distributor_data.pin_code)

            if distributor_data.map_link is not None:
                param_count += 1
                update_fields.append(f"map_link = ${param_count}")
                params.append(distributor_data.map_link)

            if distributor_data.vehicle_3 is not None:
                param_count += 1
                update_fields.append(f"vehicle_3 = ${param_count}")
                params.append(distributor_data.vehicle_3)

            if distributor_data.vehicle_4 is not None:
                param_count += 1
                update_fields.append(f"vehicle_4 = ${param_count}")
                params.append(distributor_data.vehicle_4)

            if distributor_data.salesman_count is not None:
                param_count += 1
                update_fields.append(f"salesman_count = ${param_count}")
                params.append(distributor_data.salesman_count)

            if distributor_data.area_id is not None:
                param_count += 1
                update_fields.append(f"area_id = ${param_count}")
                params.append(distributor_data.area_id)

            if distributor_data.for_general is not None:
                param_count += 1
                update_fields.append(f"for_general = ${param_count}")
                params.append(distributor_data.for_general)

            if distributor_data.for_modern is not None:
                param_count += 1
                update_fields.append(f"for_modern = ${param_count}")
                params.append(distributor_data.for_modern)

            if distributor_data.for_horeca is not None:
                param_count += 1
                update_fields.append(f"for_horeca = ${param_count}")
                params.append(distributor_data.for_horeca)

            if not update_fields:
                # No fields to update, return current distributor
                current_distributor = await self._get_distributor_by_id(
                    distributor_id, connection
                )
                # Convert to DistributorInDB by fetching without joins
                row = await connection.fetchrow(
                    """
                    SELECT id, name, code, contact_person_name, mobile_number, email,
                           gst_no, pan_no, license_no, address, pin_code, map_link,
                           documents, store_images, vehicle_3, vehicle_4, salesman_count,
                           area_id, for_general, for_modern, for_horeca,
                           is_active, created_at, updated_at
                    FROM distributor
                    WHERE id = $1
                    """,
                    distributor_id,
                )
                return DistributorInDB(**dict(row))

            param_count += 1
            params.append(distributor_id)

            query = f"""
                UPDATE distributor
                SET {", ".join(update_fields)}
                WHERE id = ${param_count}
                RETURNING id, name, code, contact_person_name, mobile_number, email,
                          gst_no, pan_no, license_no, address, pin_code, map_link,
                          documents, store_images, vehicle_3, vehicle_4, salesman_count,
                          area_id, for_general, for_modern, for_horeca,
                          is_active, created_at, updated_at
            """

            row = await connection.fetchrow(query, *params)

            if not row:
                raise DistributorNotFoundException(distributor_id=distributor_id)

            logger.info(
                "Distributor updated successfully",
                distributor_id=str(distributor_id),
                company_id=str(self.company_id),
            )

            return DistributorInDB(**dict(row))

        except (DistributorNotFoundException, DistributorAlreadyExistsException):
            raise
        except asyncpg.UniqueViolationError as e:
            error_msg = str(e)
            if "uniq_distributor_gst_no" in error_msg:
                raise DistributorAlreadyExistsException(
                    field="gst_no", value=distributor_data.gst_no
                )
            elif "uniq_distributor_pan_no" in error_msg:
                raise DistributorAlreadyExistsException(
                    field="pan_no", value=distributor_data.pan_no
                )
            elif "uniq_distributor_license_no" in error_msg:
                raise DistributorAlreadyExistsException(
                    field="license_no", value=distributor_data.license_no
                )
            elif "uniq_distributor_mobile_number" in error_msg:
                raise DistributorAlreadyExistsException(
                    field="mobile_number", value=distributor_data.mobile_number
                )
            elif "uniq_distributor_email" in error_msg:
                raise DistributorAlreadyExistsException(
                    field="email", value=distributor_data.email
                )
            else:
                raise DistributorOperationException(
                    message=f"Failed to update distributor: {error_msg}",
                    operation="update",
                ) from e
        except Exception as e:
            logger.error(
                "Failed to update distributor",
                distributor_id=str(distributor_id),
                error=str(e),
                company_id=str(self.company_id),
            )
            raise DistributorOperationException(
                message=f"Failed to update distributor: {str(e)}",
                operation="update",
            ) from e

    async def update_distributor(
        self,
        distributor_id: UUID,
        distributor_data: DistributorUpdate,
        connection: Optional[asyncpg.Connection] = None,
    ) -> DistributorInDB:
        """
        Update an existing distributor.

        Args:
            distributor_id: ID of the distributor to update
            distributor_data: Distributor data to update
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Updated distributor

        Raises:
            DistributorNotFoundException: If distributor not found
            DistributorOperationException: If update fails
        """
        if connection:
            return await self._update_distributor(
                distributor_id, distributor_data, connection
            )

        async with self.db_pool.acquire() as conn:
            return await self._update_distributor(
                distributor_id, distributor_data, conn
            )

    async def _delete_distributor(
        self, distributor_id: UUID, connection: asyncpg.Connection
    ) -> DistributorInDB:
        """
        Private method to soft delete a distributor (set is_active=False) with a provided connection.

        Args:
            distributor_id: ID of the distributor to soft delete
            connection: Database connection

        Returns:
            Updated distributor with is_active=False

        Raises:
            DistributorNotFoundException: If distributor not found
            DistributorOperationException: If soft deletion fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Check if distributor exists
            await self._get_distributor_by_id(distributor_id, connection)

            # Soft delete distributor
            await connection.execute(
                "UPDATE distributor SET is_active = FALSE WHERE id = $1",
                distributor_id,
            )

            logger.info(
                "Distributor soft deleted successfully",
                distributor_id=str(distributor_id),
                company_id=str(self.company_id),
            )

            # Fetch updated distributor
            row = await connection.fetchrow(
                """
                SELECT id, name, code, contact_person_name, mobile_number, email,
                       gst_no, pan_no, license_no, address, pin_code, map_link,
                       documents, store_images, vehicle_3, vehicle_4, salesman_count,
                       area_id, for_general, for_modern, for_horeca,
                       is_active, created_at, updated_at
                FROM distributor
                WHERE id = $1
                """,
                distributor_id,
            )

            return DistributorInDB(**dict(row))

        except DistributorNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to soft delete distributor",
                distributor_id=str(distributor_id),
                error=str(e),
                company_id=str(self.company_id),
            )
            raise DistributorOperationException(
                message=f"Failed to soft delete distributor: {str(e)}",
                operation="soft_delete",
            ) from e

    async def delete_distributor(
        self, distributor_id: UUID, connection: Optional[asyncpg.Connection] = None
    ) -> None:
        """
        Delete a distributor by setting is_active to False.

        Args:
            distributor_id: ID of the distributor to delete
            connection: Optional database connection. If not provided, a new one is acquired.
        """
        if connection:
            return await self._delete_distributor(distributor_id, connection)

        async with self.db_pool.acquire() as conn:
            return await self._delete_distributor(distributor_id, conn)

    async def _add_distributor_route(
        self, distributor_id: UUID, route_id: int, connection: asyncpg.Connection
    ) -> None:
        """
        Private method to add a route to a distributor.

        Args:
            distributor_id: ID of the distributor
            route_id: ID of the route to add
            connection: Database connection

        Raises:
            DistributorOperationException: If operation fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            await connection.execute(
                """
                INSERT INTO distributor_routes (distributor_id, route_id)
                VALUES ($1, $2)
                ON CONFLICT (distributor_id, route_id, is_active) 
                WHERE is_active = true
                DO NOTHING
                """,
                distributor_id,
                route_id,
            )

            logger.info(
                "Route added to distributor successfully",
                distributor_id=str(distributor_id),
                route_id=route_id,
                company_id=str(self.company_id),
            )

        except Exception as e:
            logger.error(
                "Failed to add route to distributor",
                distributor_id=str(distributor_id),
                route_id=route_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise DistributorOperationException(
                message=f"Failed to add route to distributor: {str(e)}",
                operation="add_route",
            ) from e

    async def add_distributor_route(
        self,
        distributor_id: UUID,
        route_id: int,
        connection: Optional[asyncpg.Connection] = None,
    ) -> None:
        """
        Add a route to a distributor.

        Args:
            distributor_id: ID of the distributor
            route_id: ID of the route to add
            connection: Optional database connection. If not provided, a new one is acquired.

        Raises:
            DistributorOperationException: If operation fails
        """
        if connection:
            return await self._add_distributor_route(
                distributor_id, route_id, connection
            )

        async with self.db_pool.acquire() as conn:
            return await self._add_distributor_route(distributor_id, route_id, conn)

    async def _remove_distributor_route(
        self, distributor_id: UUID, route_id: int, connection: asyncpg.Connection
    ) -> None:
        """
        Private method to remove a route from a distributor.

        Args:
            distributor_id: ID of the distributor
            route_id: ID of the route to remove
            connection: Database connection

        Raises:
            DistributorOperationException: If operation fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            await connection.execute(
                """
                UPDATE distributor_routes
                SET is_active = FALSE
                WHERE distributor_id = $1 AND route_id = $2
                """,
                distributor_id,
                route_id,
            )

            logger.info(
                "Route removed from distributor successfully",
                distributor_id=str(distributor_id),
                route_id=route_id,
                company_id=str(self.company_id),
            )

        except Exception as e:
            logger.error(
                "Failed to remove route from distributor",
                distributor_id=str(distributor_id),
                route_id=route_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise DistributorOperationException(
                message=f"Failed to remove route from distributor: {str(e)}",
                operation="remove_route",
            ) from e

    async def remove_distributor_route(
        self,
        distributor_id: UUID,
        route_id: int,
        connection: Optional[asyncpg.Connection] = None,
    ) -> None:
        """
        Remove a route from a distributor.

        Args:
            distributor_id: ID of the distributor
            route_id: ID of the route to remove
            connection: Optional database connection. If not provided, a new one is acquired.

        Raises:
            DistributorOperationException: If operation fails
        """
        if connection:
            return await self._remove_distributor_route(
                distributor_id, route_id, connection
            )

        async with self.db_pool.acquire() as conn:
            return await self._remove_distributor_route(distributor_id, route_id, conn)

    async def get_serial_number(self, connection: asyncpg.Connection) -> int:
        """
        Get the next serial number for a distributor.

        Args:
            connection: Database connection

        Returns:
            Next serial number
        """
        try:
            await set_search_path(connection, self.schema_name)
            value = await connection.fetchval(
                "SELECT nextval('distributor_id_seq')",
            )
            return value
        except Exception as e:
            logger.error(
                "Failed to get serial number",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise DistributorOperationException(
                message=f"Failed to get serial number: {str(e)}",
                operation="get_serial_number",
            ) from e
