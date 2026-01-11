"""
Repository for Company entity operations.

This repository handles all database operations for companies in the salesforce schema.
Companies are stored in the public salesforce schema (not tenant-specific).
"""

from typing import Optional
from uuid import UUID

import asyncpg
import structlog

from api.database import DatabasePool
from api.exceptions.company import (
    CompanyAlreadyExistsException,
    CompanyNotFoundException,
    CompanyOperationException,
)
from api.models.company import (
    CompanyCreate,
    CompanyInDB,
    CompanyListItem,
    CompanyUpdate,
)

logger = structlog.get_logger(__name__)


class CompanyRepository:
    """
    Repository for managing Company entities in the salesforce schema.

    This repository provides methods for CRUD operations on companies.
    All methods raise exceptions when records are not found.
    """

    def __init__(self, db_pool: DatabasePool) -> None:
        """
        Initialize the CompanyRepository.

        Args:
            db_pool: Database pool instance for connection management
        """
        self.db_pool = db_pool

    async def _create_company(
        self, company_data: CompanyCreate, connection: asyncpg.Connection
    ) -> CompanyInDB:
        """
        Private method to create a company with a provided connection.

        Args:
            company_data: Company data to create
            connection: Database connection

        Returns:
            Created company

        Raises:
            CompanyAlreadyExistsException: If company with same GST/CIN exists
            CompanyOperationException: If creation fails
        """
        try:
            # Insert the company
            row = await connection.fetchrow(
                """
                INSERT INTO salesforce.company (name, gst_no, cin_no, address)
                VALUES ($1, $2, $3, $4)
                RETURNING id, name, gst_no, cin_no, address, is_active, created_at, updated_at
                """,
                company_data.name,
                company_data.gst_no,
                company_data.cin_no,
                company_data.address,
            )

            logger.info(
                "Company created successfully",
                company_id=str(row["id"]),
                company_name=company_data.name,
            )

            return CompanyInDB(**dict(row))

        except asyncpg.UniqueViolationError as e:
            if "uniq_company_gst_no" in str(e):
                raise CompanyAlreadyExistsException(gst_no=company_data.gst_no)
            elif "uniq_company_cin_no" in str(e):
                raise CompanyAlreadyExistsException(cin_no=company_data.cin_no)
            else:
                raise CompanyOperationException(
                    message=f"Failed to create company: {str(e)}",
                    operation="create",
                ) from e
        except Exception as e:
            logger.error(
                "Failed to create company",
                company_name=company_data.name,
                error=str(e),
            )
            raise CompanyOperationException(
                message=f"Failed to create company: {str(e)}",
                operation="create",
            ) from e

    async def create_company(
        self,
        company_data: CompanyCreate,
        connection: Optional[asyncpg.Connection] = None,
    ) -> CompanyInDB:
        """
        Create a new company.

        Args:
            company_data: Company data to create
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Created company

        Raises:
            CompanyAlreadyExistsException: If company with same GST/CIN exists
            CompanyOperationException: If creation fails
        """
        if connection:
            return await self._create_company(company_data, connection)

        async with self.db_pool.acquire() as conn:
            return await self._create_company(company_data, conn)

    async def _get_company_by_id(
        self, company_id: UUID, connection: asyncpg.Connection
    ) -> CompanyInDB:
        """
        Private method to get a company by ID with a provided connection.

        Args:
            company_id: UUID of the company
            connection: Database connection

        Returns:
            Company

        Raises:
            CompanyNotFoundException: If company not found
            CompanyOperationException: If retrieval fails
        """
        try:
            row = await connection.fetchrow(
                """
                SELECT id, name, gst_no, cin_no, address, is_active, created_at, updated_at
                FROM salesforce.company
                WHERE id = $1
                """,
                company_id,
            )

            if not row:
                raise CompanyNotFoundException(company_id=company_id)

            return CompanyInDB(**dict(row))

        except CompanyNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to get company by id",
                company_id=str(company_id),
                error=str(e),
            )
            raise CompanyOperationException(
                message=f"Failed to get company: {str(e)}",
                operation="get",
            ) from e

    async def get_company_by_id(
        self, company_id: UUID, connection: Optional[asyncpg.Connection] = None
    ) -> CompanyInDB:
        """
        Get a company by ID.

        Args:
            company_id: UUID of the company
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Company

        Raises:
            CompanyNotFoundException: If company not found
            CompanyOperationException: If retrieval fails
        """
        if connection:
            return await self._get_company_by_id(company_id, connection)

        async with self.db_pool.acquire() as conn:
            return await self._get_company_by_id(company_id, conn)

    async def _get_company_by_gst(
        self, gst_no: str, connection: asyncpg.Connection
    ) -> CompanyInDB:
        """
        Private method to get a company by GST number with a provided connection.

        Args:
            gst_no: GST number of the company
            connection: Database connection

        Returns:
            Company

        Raises:
            CompanyNotFoundException: If company not found
            CompanyOperationException: If retrieval fails
        """
        try:
            row = await connection.fetchrow(
                """
                SELECT id, name, gst_no, cin_no, address, is_active, created_at, updated_at
                FROM salesforce.company
                WHERE gst_no = $1 AND is_active = true
                """,
                gst_no,
            )

            if not row:
                raise CompanyNotFoundException(gst_no=gst_no)

            return CompanyInDB(**dict(row))

        except CompanyNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to get company by GST",
                gst_no=gst_no,
                error=str(e),
            )
            raise CompanyOperationException(
                message=f"Failed to get company: {str(e)}",
                operation="get",
            ) from e

    async def get_company_by_gst(
        self, gst_no: str, connection: Optional[asyncpg.Connection] = None
    ) -> CompanyInDB:
        """
        Get a company by GST number.

        Args:
            gst_no: GST number of the company
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Company

        Raises:
            CompanyNotFoundException: If company not found
            CompanyOperationException: If retrieval fails
        """
        if connection:
            return await self._get_company_by_gst(gst_no, connection)

        async with self.db_pool.acquire() as conn:
            return await self._get_company_by_gst(gst_no, conn)

    async def _get_company_by_cin(
        self, cin_no: str, connection: asyncpg.Connection
    ) -> CompanyInDB:
        """
        Private method to get a company by CIN number with a provided connection.

        Args:
            cin_no: CIN number of the company
            connection: Database connection

        Returns:
            Company

        Raises:
            CompanyNotFoundException: If company not found
            CompanyOperationException: If retrieval fails
        """
        try:
            row = await connection.fetchrow(
                """
                SELECT id, name, gst_no, cin_no, address, is_active, created_at, updated_at
                FROM salesforce.company
                WHERE cin_no = $1 AND is_active = true
                """,
                cin_no,
            )

            if not row:
                raise CompanyNotFoundException(cin_no=cin_no)

            return CompanyInDB(**dict(row))

        except CompanyNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to get company by CIN",
                cin_no=cin_no,
                error=str(e),
            )
            raise CompanyOperationException(
                message=f"Failed to get company: {str(e)}",
                operation="get",
            ) from e

    async def get_company_by_cin(
        self, cin_no: str, connection: Optional[asyncpg.Connection] = None
    ) -> CompanyInDB:
        """
        Get a company by CIN number.

        Args:
            cin_no: CIN number of the company
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Company

        Raises:
            CompanyNotFoundException: If company not found
            CompanyOperationException: If retrieval fails
        """
        if connection:
            return await self._get_company_by_cin(cin_no, connection)

        async with self.db_pool.acquire() as conn:
            return await self._get_company_by_cin(cin_no, conn)

    async def _list_companies(
        self,
        connection: asyncpg.Connection,
        is_active: Optional[bool] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[CompanyListItem]:
        """
        Private method to list companies with a provided connection.
        Returns minimal data to optimize performance.

        Args:
            connection: Database connection
            is_active: Filter by active status
            limit: Maximum number of companies to return
            offset: Number of companies to skip

        Returns:
            List of companies with minimal data

        Raises:
            CompanyOperationException: If listing fails
        """
        try:
            # Only select minimal fields for list view
            query = """
                SELECT id, name, is_active
                FROM salesforce.company     
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

            return [CompanyListItem(**dict(row)) for row in rows]

        except Exception as e:
            logger.error(
                "Failed to list companies",
                error=str(e),
            )
            raise CompanyOperationException(
                message=f"Failed to list companies: {str(e)}",
                operation="list",
            )

    async def list_companies(
        self,
        is_active: Optional[bool] = None,
        limit: int = 20,
        offset: int = 0,
        connection: Optional[asyncpg.Connection] = None,
    ) -> list[CompanyListItem]:
        """
        List all companies with optional filtering.
        Returns minimal data to optimize performance.

        Args:
            is_active: Filter by active status
            limit: Maximum number of companies to return
            offset: Number of companies to skip
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            List of companies with minimal data

        Raises:
            CompanyOperationException: If listing fails
        """
        if connection:
            return await self._list_companies(connection, is_active, limit, offset)

        async with self.db_pool.acquire() as conn:
            return await self._list_companies(conn, is_active, limit, offset)

    async def _count_companies(
        self,
        connection: asyncpg.Connection,
        is_active: Optional[bool] = None,
    ) -> int:
        """
        Private method to count companies with a provided connection.

        Args:
            connection: Database connection
            is_active: Filter by active status

        Returns:
            Count of companies

        Raises:
            CompanyOperationException: If counting fails
        """
        try:
            if is_active is not None:
                count = await connection.fetchval(
                    "SELECT COUNT(*) FROM salesforce.company WHERE is_active = $1",
                    is_active,
                )
            else:
                count = await connection.fetchval(
                    "SELECT COUNT(*) FROM salesforce.company"
                )

            return count or 0

        except Exception as e:
            logger.error(
                "Failed to count companies",
                error=str(e),
            )
            raise CompanyOperationException(
                message=f"Failed to count companies: {str(e)}",
                operation="count",
            )

    async def count_companies(
        self,
        is_active: Optional[bool] = None,
        connection: Optional[asyncpg.Connection] = None,
    ) -> int:
        """
        Count companies with optional filtering.

        Args:
            is_active: Filter by active status
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Count of companies

        Raises:
            CompanyOperationException: If counting fails
        """
        if connection:
            return await self._count_companies(connection, is_active)

        async with self.db_pool.acquire() as conn:
            return await self._count_companies(conn, is_active)

    async def _update_company(
        self,
        company_id: UUID,
        company_data: CompanyUpdate,
        connection: asyncpg.Connection,
    ) -> CompanyInDB:
        """
        Private method to update a company with a provided connection.

        Args:
            company_id: UUID of the company to update
            company_data: Company data to update
            connection: Database connection

        Returns:
            Updated company

        Raises:
            CompanyNotFoundException: If company not found
            CompanyOperationException: If update fails
        """
        try:
            # Check if company exists
            await self._get_company_by_id(company_id, connection)

            # Build dynamic update query
            update_fields = []
            params = []
            param_count = 0

            if company_data.name is not None:
                param_count += 1
                update_fields.append(f"name = ${param_count}")
                params.append(company_data.name)

            if company_data.address is not None:
                param_count += 1
                update_fields.append(f"address = ${param_count}")
                params.append(company_data.address)

            if company_data.gst_no is not None:
                param_count += 1
                update_fields.append(f"gst_no = ${param_count}")
                params.append(company_data.gst_no)

            if company_data.cin_no is not None:
                param_count += 1
                update_fields.append(f"cin_no = ${param_count}")
                params.append(company_data.cin_no)

            if not update_fields:
                # No fields to update, return current company
                return await self._get_company_by_id(company_id, connection)

            param_count += 1
            params.append(company_id)

            query = f"""
                UPDATE salesforce.company
                SET {", ".join(update_fields)}
                WHERE id = ${param_count}
                RETURNING id, name, gst_no, cin_no, address, is_active, created_at, updated_at
            """
            row = await connection.fetchrow(query, *params)

            if not row:
                raise CompanyNotFoundException(company_id=company_id)

            logger.info(
                "Company updated successfully",
                company_id=str(company_id),
            )

            return CompanyInDB(**dict(row))
        except asyncpg.UniqueViolationError as e:
            if e.constraint == "uniq_company_gst_no":
                raise CompanyAlreadyExistsException(gst_no=company_data.gst_no)
            elif e.constraint == "uniq_company_cin_no":
                raise CompanyAlreadyExistsException(cin_no=company_data.cin_no)
            else:
                raise CompanyOperationException(
                    message=f"Failed to update company: {str(e)}",
                    operation="update",
                ) from e
        except Exception as e:
            logger.error(
                "Failed to update company",
                company_id=str(company_id),
                error=str(e),
            )
            raise CompanyOperationException(
                message=f"Failed to update company: {str(e)}",
                operation="update",
            )

    async def update_company(
        self,
        company_id: UUID,
        company_data: CompanyUpdate,
        connection: Optional[asyncpg.Connection] = None,
    ) -> CompanyInDB:
        """
        Update an existing company.

        Args:
            company_id: UUID of the company to update
            company_data: Company data to update
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Updated company

        Raises:
            CompanyNotFoundException: If company not found
            CompanyOperationException: If update fails
        """
        if connection:
            return await self._update_company(company_id, company_data, connection)

        async with self.db_pool.acquire() as conn:
            return await self._update_company(company_id, company_data, conn)

    async def _delete_company(
        self, company_id: UUID, connection: asyncpg.Connection
    ) -> CompanyInDB:
        """
        Private method to soft delete a company (set is_active=False) with a provided connection.

        Args:
            company_id: UUID of the company to soft delete
            connection: Database connection

        Returns:
            Updated company with is_active=False

        Raises:
            CompanyNotFoundException: If company not found
            CompanyOperationException: If soft deletion fails
        """
        try:
            # Check if company exists
            await self._get_company_by_id(company_id, connection)

            # Soft delete company
            await connection.execute(
                "UPDATE salesforce.company SET is_active = FALSE WHERE id = $1",
                company_id,
            )

            logger.info(
                "Company soft deleted successfully",
                company_id=str(company_id),
            )

            return await self._get_company_by_id(company_id, connection)

        except CompanyNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to soft delete company",
                company_id=str(company_id),
                error=str(e),
            )
            raise CompanyOperationException(
                message=f"Failed to soft delete company: {str(e)}",
                operation="soft_delete",
            ) from e

    async def delete_company(
        self, company_id: UUID, connection: Optional[asyncpg.Connection] = None
    ) -> None:
        """
        Delete a company by setting is_active to False.

        Args:
            company_id: UUID of the company to delete
            connection: Optional database connection. If not provided, a new one is acquired.
        """
        if connection:
            return await self._delete_company(company_id, connection)

        async with self.db_pool.acquire() as conn:
            return await self._delete_company(company_id, conn)
