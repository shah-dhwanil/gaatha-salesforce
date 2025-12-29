"""
Service layer for Company entity operations.

This service provides business logic for companies, including schema creation
and migration application for multi-tenant architecture.
"""

import asyncio
from typing import Optional
from uuid import UUID

import asyncpg
import structlog

from api.database import DatabasePool
from api.exceptions.company import (
    CompanyAlreadyExistsException,
    CompanyNotFoundException,
    CompanyOperationException,
    CompanyValidationException,
)
from api.migrations import MigrationManager
from api.models.company import (
    CompanyCreate,
    CompanyInDB,
    CompanyListItem,
    CompanyResponse,
    CompanyUpdate,
)
from api.repository.company import CompanyRepository
from api.repository.utils import get_schema_name
from api.settings.database import DatabaseConfig

logger = structlog.get_logger(__name__)


class CompanyService:
    """
    Service for managing Company business logic.

    This service handles business logic, validation, orchestration,
    schema creation, and migration application for company operations.
    """

    def __init__(self, db_pool: DatabasePool, db_config: DatabaseConfig) -> None:
        """
        Initialize the CompanyService.

        Args:
            db_pool: Database pool instance for connection management
            db_config: Database configuration for migrations
        """
        self.db_pool = db_pool
        self.db_config = db_config
        self.repository = CompanyRepository(db_pool)
        logger.debug("CompanyService initialized")

    async def _create_schema(
        self, schema_name: str, connection: asyncpg.Connection
    ) -> None:
        """
        Create a new schema for the company.

        Args:
            schema_name: Name of the schema to create
            connection: Database connection

        Raises:
            CompanyOperationException: If schema creation fails
        """
        try:
            logger.info("Creating schema", schema_name=schema_name)
            
            # Create schema
            await connection.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"')
            
            logger.info("Schema created successfully", schema_name=schema_name)

        except Exception as e:
            logger.error(
                "Failed to create schema",
                schema_name=schema_name,
                error=str(e),
            )
            raise CompanyOperationException(
                message=f"Failed to create schema: {str(e)}",
                operation="create_schema",
            ) from e

    def _apply_migrations(self, schema_name: str) -> None:
        """
        Apply migrations to the newly created schema.

        Args:
            schema_name: Name of the schema to apply migrations to

        Raises:
            CompanyOperationException: If migration application fails
        """
        try:
            logger.info("Applying migrations to schema", schema_name=schema_name)

            # Apply company-specific migrations
            MigrationManager.apply_company_migrations(
                config=self.db_config,
                schema_name=schema_name,
            )

            logger.info(
                "Migrations applied successfully",
                schema_name=schema_name,
            )

        except Exception as e:
            logger.error(
                "Failed to apply migrations",
                schema_name=schema_name,
                error=str(e),
            )
            raise CompanyOperationException(
                message=f"Failed to apply migrations: {str(e)}",
                operation="apply_migrations",
            ) from e

    async def create_company(self, company_data: CompanyCreate) -> CompanyResponse:
        """
        Create a new company with schema and migrations.

        This method:
        1. Creates the company record in the salesforce schema
        2. Creates a dedicated schema for the company
        3. Applies all migrations to the new schema

        Args:
            company_data: Company data to create

        Returns:
            Created company

        Raises:
            CompanyAlreadyExistsException: If company with same GST/CIN exists
            CompanyValidationException: If validation fails
            CompanyOperationException: If creation fails
        """
        company: Optional[CompanyInDB] = None
        schema_name: Optional[str] = None

        try:
            logger.info(
                "Creating company with schema",
                company_name=company_data.name,
                gst_no=company_data.gst_no,
            )

            # Use transaction for company creation and schema creation
            async with self.db_pool.transaction() as conn:
                # 1. Create company record
                company = await self.repository.create_company(company_data, conn)
                schema_name = get_schema_name(company.id)

                # 2. Create schema for the company
                await self._create_schema(schema_name, conn)

            # 3. Apply migrations (outside transaction as yoyo manages its own)
            await asyncio.to_thread(self._apply_migrations, schema_name)

            logger.info(
                "Company created successfully with schema and migrations",
                company_id=str(company.id),
                company_name=company.name,
                schema_name=schema_name,
            )

            return CompanyResponse(**company.model_dump())

        except CompanyAlreadyExistsException:
            logger.warning(
                "Company already exists",
                gst_no=company_data.gst_no,
                cin_no=company_data.cin_no,
            )
            raise
        except CompanyValidationException:
            raise
        except CompanyOperationException:
            raise
        except Exception as e:
            logger.error(
                "Failed to create company in service",
                company_name=company_data.name,
                error=str(e),
            )
            
            # Attempt cleanup if company was created but migrations failed
            if company and schema_name:
                try:
                    logger.warning(
                        "Attempting to cleanup after failed company creation",
                        company_id=str(company.id),
                        schema_name=schema_name,
                    )
                    async with self.db_pool.acquire() as conn:
                        # Drop schema if it was created
                        await conn.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')
                    logger.info("Cleanup completed successfully")
                except Exception as cleanup_error:
                    logger.error(
                        "Failed to cleanup after error",
                        error=str(cleanup_error),
                    )
            
            raise CompanyOperationException(
                message=f"Failed to create company: {str(e)}",
                operation="create",
            ) from e

    async def get_company_by_id(self, company_id: UUID) -> CompanyResponse:
        """
        Get a company by ID.

        Args:
            company_id: UUID of the company

        Returns:
            Company

        Raises:
            CompanyNotFoundException: If company not found
            CompanyOperationException: If retrieval fails
        """
        try:
            logger.debug("Getting company by id", company_id=str(company_id))

            company = await self.repository.get_company_by_id(company_id)

            return CompanyResponse(**company.model_dump())

        except CompanyNotFoundException:
            logger.warning("Company not found", company_id=str(company_id))
            raise
        except Exception as e:
            logger.error(
                "Failed to get company in service",
                company_id=str(company_id),
                error=str(e),
            )
            raise

    async def get_company_by_gst(self, gst_no: str) -> CompanyResponse:
        """
        Get a company by GST number.

        Args:
            gst_no: GST number of the company

        Returns:
            Company

        Raises:
            CompanyNotFoundException: If company not found
            CompanyOperationException: If retrieval fails
        """
        try:
            logger.debug("Getting company by GST", gst_no=gst_no)

            company = await self.repository.get_company_by_gst(gst_no)

            return CompanyResponse(**company.model_dump())

        except CompanyNotFoundException:
            logger.warning("Company not found", gst_no=gst_no)
            raise
        except Exception as e:
            logger.error(
                "Failed to get company by GST in service",
                gst_no=gst_no,
                error=str(e),
            )
            raise

    async def get_company_by_cin(self, cin_no: str) -> CompanyResponse:
        """
        Get a company by CIN number.

        Args:
            cin_no: CIN number of the company

        Returns:
            Company

        Raises:
            CompanyNotFoundException: If company not found
            CompanyOperationException: If retrieval fails
        """
        try:
            logger.debug("Getting company by CIN", cin_no=cin_no)

            company = await self.repository.get_company_by_cin(cin_no)

            return CompanyResponse(**company.model_dump())

        except CompanyNotFoundException:
            logger.warning("Company not found", cin_no=cin_no)
            raise
        except Exception as e:
            logger.error(
                "Failed to get company by CIN in service",
                cin_no=cin_no,
                error=str(e),
            )
            raise

    async def list_companies(
        self,
        is_active: Optional[bool] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[CompanyListItem], int]:
        """
        List all companies with optional filtering and return total count.

        Args:
            is_active: Filter by active status
            limit: Maximum number of companies to return (default: 20)
            offset: Number of companies to skip (default: 0)

        Returns:
            Tuple of (list of companies with minimal data, total count)

        Raises:
            CompanyValidationException: If validation fails
            CompanyOperationException: If listing fails
        """
        try:
            logger.debug(
                "Listing companies",
                is_active=is_active,
                limit=limit,
                offset=offset,
            )

            # Validate pagination parameters
            if limit < 1 or limit > 100:
                raise CompanyValidationException(
                    message="Limit must be between 1 and 100",
                    field="limit",
                    value=limit,
                )

            if offset < 0:
                raise CompanyValidationException(
                    message="Offset must be non-negative",
                    field="offset",
                    value=offset,
                )

            # Get companies and count in parallel for better performance
            async with self.db_pool.acquire() as conn:
                companies = await self.repository.list_companies(
                    is_active=is_active,
                    limit=limit,
                    offset=offset,
                    connection=conn,
                )
                total_count = await self.repository.count_companies(
                    is_active=is_active,
                    connection=conn,
                )

            logger.debug(
                "Companies listed successfully",
                count=len(companies),
                total_count=total_count,
            )

            return companies, total_count

        except CompanyValidationException:
            raise
        except Exception as e:
            logger.error(
                "Failed to list companies in service",
                error=str(e),
            )
            raise

    async def update_company(
        self, company_id: UUID, company_data: CompanyUpdate
    ) -> CompanyResponse:
        """
        Update an existing company.

        Note: GST and CIN numbers cannot be updated.

        Args:
            company_id: UUID of the company to update
            company_data: Company data to update

        Returns:
            Updated company

        Raises:
            CompanyNotFoundException: If company not found
            CompanyValidationException: If validation fails
            CompanyOperationException: If update fails
        """
        try:
            logger.info(
                "Updating company",
                company_id=str(company_id),
            )

            # Additional business logic validation
            if not company_data.name and not company_data.address:
                raise CompanyValidationException(
                    message="At least one field must be provided for update",
                )

            # Update company using repository
            company = await self.repository.update_company(company_id, company_data)

            logger.info(
                "Company updated successfully",
                company_id=str(company_id),
            )

            return CompanyResponse(**company.model_dump())

        except (CompanyNotFoundException, CompanyValidationException):
            raise
        except Exception as e:
            logger.error(
                "Failed to update company in service",
                company_id=str(company_id),
                error=str(e),
            )
            raise

    async def delete_company(self, company_id: UUID) -> None:
        """
        Soft delete a company by setting is_active to False.

        Note: This does NOT drop the schema. The schema remains for data retention.

        Args:
            company_id: UUID of the company to delete

        Raises:
            CompanyNotFoundException: If company not found
            CompanyOperationException: If deletion fails
        """
        try:
            logger.info(
                "Soft deleting company",
                company_id=str(company_id),
            )

            # Soft delete company using repository
            await self.repository.delete_company(company_id)

            logger.info(
                "Company soft deleted successfully (schema retained)",
                company_id=str(company_id),
            )

        except CompanyNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to soft delete company in service",
                company_id=str(company_id),
                error=str(e),
            )
            raise

    async def check_company_exists(self, company_id: UUID) -> bool:
        """
        Check if a company exists.

        Args:
            company_id: UUID of the company to check

        Returns:
            True if company exists, False otherwise
        """
        try:
            await self.repository.get_company_by_id(company_id)
            return True
        except CompanyNotFoundException:
            return False

    async def get_active_companies_count(self) -> int:
        """
        Get count of active companies.

        Returns:
            Count of active companies

        Raises:
            CompanyOperationException: If counting fails
        """
        try:
            logger.debug("Getting active companies count")

            count = await self.repository.count_companies(is_active=True)

            return count

        except Exception as e:
            logger.error(
                "Failed to get active companies count in service",
                error=str(e),
            )
            raise

    async def get_company_schema_name(self, company_id: UUID) -> str:
        """
        Get the schema name for a company.

        Args:
            company_id: UUID of the company

        Returns:
            Schema name

        Raises:
            CompanyNotFoundException: If company not found
        """
        # Verify company exists
        await self.get_company_by_id(company_id)
        
        return get_schema_name(company_id)

