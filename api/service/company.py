"""
Company service module for business logic.

This service provides business logic layer for company operations,
acting as an intermediary between API handlers and the company repository.
It handles validation, business rules, and coordinates repository operations.
"""

import asyncio
from api.repository.utils import get_schema_name
from api.settings.settings import get_settings
from api.migrations import MigrationManager
from uuid import UUID
from typing import Optional
import structlog

from api.repository.company import CompanyRepository
from api.models.company import CompanyInDB
from api.exceptions.company import (
    CompanyNotFoundException,
)

logger = structlog.get_logger(__name__)


class CompanyService:
    """Service class for company business logic.

    This service handles business logic and validation for company operations,
    coordinating between the API layer and the CompanyRepository.

    Attributes:
        company_repository: Repository for company data operations
    """

    def __init__(self, company_repository: CompanyRepository):
        """Initialize the CompanyService with a repository.

        Args:
            company_repository: CompanyRepository instance for data operations
        """
        self.company_repository = company_repository
        logger.debug("CompanyService initialized")

    async def create_company(
        self,
        name: str,
        gst_no: str,
        cin_no: str,
        address: str,
    ) -> CompanyInDB:
        """Create a new company with validation.

        Validates input data and creates a new company through the repository.

        Args:
            name: Name of the company
            gst_no: GST number (required, must be 15 characters)
            cin_no: CIN number (required, must be 21 characters)
            address: Company address (required)

        Returns:
            CompanyInDB: Created company object with all details

        Raises:
            CompanyAlreadyExistsException: If GST or CIN number already exists
            ValueError: If validation fails
        """
        logger.info(
            "Creating company",
            name=name,
            gst_no=gst_no,
            cin_no=cin_no,
        )

        # Validate input data
        if not name or not name.strip():
            raise ValueError("Company name cannot be empty")

        if not gst_no or not gst_no.strip():
            raise ValueError("GST number cannot be empty")

        if not cin_no or not cin_no.strip():
            raise ValueError("CIN number cannot be empty")

        if not address or not address.strip():
            raise ValueError("Address cannot be empty")

        # Validate GST number format
        gst_no_stripped = gst_no.strip()
        if len(gst_no_stripped) != 15:
            raise ValueError("GST number must be exactly 15 characters")

        # Validate CIN number format
        cin_no_stripped = cin_no.strip()
        if len(cin_no_stripped) != 21:
            raise ValueError("CIN number must be exactly 21 characters")

        # Strip address
        address_stripped = address.strip()
        async with self.company_repository.db_pool.transaction() as conn:
            # Create company through repository
            company = await self.company_repository.create_company(
                name=name.strip(),
                gst_no=gst_no_stripped,
                cin_no=cin_no_stripped,
                address=address_stripped,
                connection=conn,
            )
            await self.company_repository.create_company_schema(
                company.id, connection=conn
            )
            await asyncio.to_thread(
                MigrationManager.apply_company_migrations,
                get_settings().POSTGRES,
                get_schema_name(company.id),
                "create_company",
            )
        logger.info(
            "Company created successfully", company_id=str(company.id), name=name
        )
        return company

    async def get_company_by_id(self, company_id: UUID) -> CompanyInDB:
        """Retrieve a company by ID.

        Args:
            company_id: UUID of the company

        Returns:
            CompanyInDB: Company object with complete details

        Raises:
            CompanyNotFoundException: If company not found
        """
        logger.info("Fetching company by ID", company_id=str(company_id))

        company = await self.company_repository.get_company_by_id(company_id)

        logger.info("Company retrieved by ID", company_id=str(company_id))
        return company

    async def get_company_by_gst_no(self, gst_no: str) -> CompanyInDB:
        """Retrieve a company by GST number.

        Args:
            gst_no: GST number to search for

        Returns:
            CompanyInDB: Company object with complete details

        Raises:
            CompanyNotFoundException: If company not found
            ValueError: If GST number is empty
        """
        logger.info("Fetching company by GST number", gst_no=gst_no)

        if not gst_no or not gst_no.strip():
            raise ValueError("GST number cannot be empty")

        company = await self.company_repository.get_company_by_gst_no(gst_no.strip())

        logger.info(
            "Company retrieved by GST number", company_id=str(company.id), gst_no=gst_no
        )
        return company

    async def get_company_by_cin_no(self, cin_no: str) -> CompanyInDB:
        """Retrieve a company by CIN number.

        Args:
            cin_no: CIN number to search for

        Returns:
            CompanyInDB: Company object with complete details

        Raises:
            CompanyNotFoundException: If company not found
            ValueError: If CIN number is empty
        """
        logger.info("Fetching company by CIN number", cin_no=cin_no)

        if not cin_no or not cin_no.strip():
            raise ValueError("CIN number cannot be empty")

        company = await self.company_repository.get_company_by_cin_no(cin_no.strip())

        logger.info(
            "Company retrieved by CIN number", company_id=str(company.id), cin_no=cin_no
        )
        return company

    async def get_all_companies(self) -> list[CompanyInDB]:
        """Retrieve all active companies.

        Returns:
            list[CompanyInDB]: List of all active companies
        """
        logger.info("Fetching all companies")

        companies = await self.company_repository.get_all_companies()

        logger.info(
            "Companies retrieved",
            company_count=len(companies),
        )
        return companies

    async def update_company(
        self,
        company_id: UUID,
        name: Optional[str] = None,
        gst_no: Optional[str] = None,
        cin_no: Optional[str] = None,
        address: Optional[str] = None,
    ) -> CompanyInDB:
        """Update company details with validation.

        Args:
            company_id: UUID of the company to update
            name: New name (optional)
            gst_no: New GST number (optional)
            cin_no: New CIN number (optional)
            address: New address (optional)

        Returns:
            CompanyInDB: Updated company object

        Raises:
            CompanyNotFoundException: If company not found
            CompanyAlreadyExistsException: If GST or CIN already exists
            ValueError: If no fields provided or validation fails
        """
        logger.info(
            "Updating company",
            company_id=str(company_id),
        )

        # Validate at least one field is provided
        if name is None and gst_no is None and cin_no is None and address is None:
            raise ValueError("At least one field must be provided for update")

        # Validate non-empty strings
        if name is not None and not name.strip():
            raise ValueError("Company name cannot be empty")

        # Validate GST number format if provided
        if gst_no is not None:
            gst_no_stripped = gst_no.strip()
            if len(gst_no_stripped) != 15:
                raise ValueError("GST number must be exactly 15 characters")
        else:
            gst_no_stripped = None

        # Validate CIN number format if provided
        if cin_no is not None:
            cin_no_stripped = cin_no.strip()
            if len(cin_no_stripped) != 21:
                raise ValueError("CIN number must be exactly 21 characters")
        else:
            cin_no_stripped = None

        # Strip whitespace from string fields
        name_stripped = name.strip() if name is not None else None
        address_stripped = address.strip() if address is not None else None

        company = await self.company_repository.update_company(
            company_id=company_id,
            name=name_stripped,
            gst_no=gst_no_stripped,
            cin_no=cin_no_stripped,
            address=address_stripped,
        )

        logger.info("Company updated successfully", company_id=str(company_id))
        return company

    async def delete_company(self, company_id: UUID) -> None:
        """Soft delete a company.

        Marks the company as inactive rather than permanently deleting.

        Args:
            company_id: UUID of the company to delete

        Raises:
            CompanyNotFoundException: If company not found
        """
        logger.info(
            "Deleting company",
            company_id=str(company_id),
        )

        await self.company_repository.delete_company(company_id)

        logger.info("Company deleted successfully", company_id=str(company_id))

    async def check_company_exists_by_id(self, company_id: UUID) -> bool:
        """Check if a company exists by ID.

        Useful for validation before attempting operations.

        Args:
            company_id: Company UUID to check

        Returns:
            bool: True if company exists, False otherwise
        """
        logger.debug("Checking if company exists by ID", company_id=str(company_id))

        try:
            await self.company_repository.get_company_by_id(company_id)
            logger.debug("Company exists", company_id=str(company_id))
            return True
        except CompanyNotFoundException:
            logger.debug("Company does not exist", company_id=str(company_id))
            return False

    async def check_company_exists_by_gst(self, gst_no: str) -> bool:
        """Check if a company exists by GST number.

        Useful for validation before attempting operations.

        Args:
            gst_no: GST number to check

        Returns:
            bool: True if company exists, False otherwise
        """
        logger.debug("Checking if company exists by GST", gst_no=gst_no)

        if not gst_no or not gst_no.strip():
            return False

        try:
            await self.company_repository.get_company_by_gst_no(gst_no.strip())
            logger.debug("Company exists with GST number", gst_no=gst_no)
            return True
        except CompanyNotFoundException:
            logger.debug("Company does not exist with GST number", gst_no=gst_no)
            return False

    async def check_company_exists_by_cin(self, cin_no: str) -> bool:
        """Check if a company exists by CIN number.

        Useful for validation before attempting operations.

        Args:
            cin_no: CIN number to check

        Returns:
            bool: True if company exists, False otherwise
        """
        logger.debug("Checking if company exists by CIN", cin_no=cin_no)

        if not cin_no or not cin_no.strip():
            return False

        try:
            await self.company_repository.get_company_by_cin_no(cin_no.strip())
            logger.debug("Company exists with CIN number", cin_no=cin_no)
            return True
        except CompanyNotFoundException:
            logger.debug("Company does not exist with CIN number", cin_no=cin_no)
            return False

    async def get_active_companies(self) -> list[CompanyInDB]:
        """Retrieve only active companies.

        This is an alias for get_all_companies since the repository
        already filters for active companies.

        Returns:
            list[CompanyInDB]: List of active companies
        """
        logger.info("Fetching active companies")

        companies = await self.company_repository.get_all_companies()

        logger.info(
            "Active companies retrieved",
            company_count=len(companies),
        )
        return companies
