"""
Service layer for Brand entity operations.

This service provides business logic for brands, including visibility and margin management,
acting as an intermediary between the API layer and the repository layer.
"""

from api.models.brand import BrandMarginAddOrUpdate
from typing import Optional
from uuid import UUID

import structlog

from api.database import DatabasePool
from api.exceptions.brand import (
    BrandAlreadyExistsException,
    BrandNotFoundException,
)
from api.models.brand import (
    BrandCreate,
    BrandDetailItem,
    BrandListItem,
    BrandMarginInDB,
    BrandUpdate,
)
from api.repository.brand import BrandRepository

logger = structlog.get_logger(__name__)


class BrandService:
    """
    Service for managing Brand business logic.

    This service handles business logic, validation, and orchestration
    for brand operations including visibility and margin management
    in a multi-tenant environment.
    """

    def __init__(self, db_pool: DatabasePool, company_id: UUID) -> None:
        """
        Initialize the BrandService.

        Args:
            db_pool: Database pool instance for connection management
            company_id: UUID of the company (tenant) for schema isolation
        """
        self.db_pool = db_pool
        self.company_id = company_id
        self.repository = BrandRepository(db_pool, company_id)
        logger.debug(
            "BrandService initialized",
            company_id=str(company_id),
        )

    async def create_brand(self, brand_data: BrandCreate) -> BrandDetailItem:
        """
        Create a new brand.

        Args:
            brand_data: Brand data to create

        Returns:
            Created brand with full details

        Raises:
            BrandAlreadyExistsException: If brand with same name/code exists
            BrandOperationException: If creation fails
        """
        try:
            logger.info(
                "Creating brand",
                brand_name=brand_data.name,
                brand_code=brand_data.code,
                company_id=str(self.company_id),
            )

            # Create brand using repository
            brand = await self.repository.create_brand(brand_data)

            # Fetch full details to return
            brand_detail = await self.repository.get_brand_by_id(brand.id)

            logger.info(
                "Brand created successfully",
                brand_id=brand.id,
                brand_name=brand.name,
                company_id=str(self.company_id),
            )

            return brand_detail

        except (BrandAlreadyExistsException, BrandNotFoundException):
            raise
        except Exception as e:
            logger.error(
                "Failed to create brand in service",
                brand_name=brand_data.name,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def get_brand_by_id(self, brand_id: int) -> BrandDetailItem:
        """
        Get a brand by ID with full details.

        Args:
            brand_id: ID of the brand

        Returns:
            Brand with full details

        Raises:
            BrandNotFoundException: If brand not found
            BrandOperationException: If retrieval fails
        """
        try:
            logger.debug(
                "Getting brand by ID",
                brand_id=brand_id,
                company_id=str(self.company_id),
            )

            brand = await self.repository.get_brand_by_id(brand_id)

            return brand

        except BrandNotFoundException:
            logger.warning(
                "Brand not found",
                brand_id=brand_id,
                company_id=str(self.company_id),
            )
            raise
        except Exception as e:
            logger.error(
                "Failed to get brand in service",
                brand_id=brand_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def get_brand_by_code(self, code: str) -> BrandDetailItem:
        """
        Get a brand by code with full details.

        Args:
            code: Code of the brand

        Returns:
            Brand with full details

        Raises:
            BrandNotFoundException: If brand not found
            BrandOperationException: If retrieval fails
        """
        try:
            logger.debug(
                "Getting brand by code",
                brand_code=code,
                company_id=str(self.company_id),
            )

            brand = await self.repository.get_brand_by_code(code)

            return brand

        except BrandNotFoundException:
            logger.warning(
                "Brand not found",
                brand_code=code,
                company_id=str(self.company_id),
            )
            raise
        except Exception as e:
            logger.error(
                "Failed to get brand in service",
                brand_code=code,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def list_brands(
        self,
        is_active: Optional[bool] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[BrandListItem]:
        """
        List brands with minimal data.

        Args:
            is_active: Filter by active status
            limit: Maximum number of brands to return
            offset: Number of brands to skip

        Returns:
            List of brands

        Raises:
            BrandOperationException: If listing fails
        """
        try:
            logger.debug(
                "Listing brands",
                is_active=is_active,
                limit=limit,
                offset=offset,
                company_id=str(self.company_id),
            )

            brands = await self.repository.list_brands(is_active, limit, offset)

            logger.debug(
                "Brands listed successfully",
                count=len(brands),
                company_id=str(self.company_id),
            )

            return brands

        except Exception as e:
            logger.error(
                "Failed to list brands in service",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def update_brand(
        self, brand_id: int, brand_data: BrandUpdate
    ) -> BrandDetailItem:
        """
        Update a brand.

        Args:
            brand_id: ID of the brand to update
            brand_data: Brand data to update

        Returns:
            Updated brand with full details

        Raises:
            BrandNotFoundException: If brand not found
            BrandAlreadyExistsException: If updated name/code conflicts
            BrandOperationException: If update fails
        """
        try:
            logger.info(
                "Updating brand",
                brand_id=brand_id,
                company_id=str(self.company_id),
            )

            # Update brand using repository
            await self.repository.update_brand(brand_id, brand_data)

            # Fetch full details to return
            brand_detail = await self.repository.get_brand_by_id(brand_id)

            logger.info(
                "Brand updated successfully",
                brand_id=brand_id,
                company_id=str(self.company_id),
            )

            return brand_detail

        except (BrandNotFoundException, BrandAlreadyExistsException):
            raise
        except Exception as e:
            logger.error(
                "Failed to update brand in service",
                brand_id=brand_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def delete_brand(self, brand_id: int) -> None:
        """
        Soft delete a brand.

        Args:
            brand_id: ID of the brand to delete

        Raises:
            BrandNotFoundException: If brand not found
            BrandOperationException: If deletion fails
        """
        try:
            logger.info(
                "Deleting brand",
                brand_id=brand_id,
                company_id=str(self.company_id),
            )

            await self.repository.delete_brand(brand_id)

            logger.info(
                "Brand deleted successfully",
                brand_id=brand_id,
                company_id=str(self.company_id),
            )

        except BrandNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to delete brand in service",
                brand_id=brand_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    # ==================== Visibility Management ====================

    async def add_brand_visibility(self, brand_id: int, area_id: Optional[int]) -> None:
        """
        Add visibility for a brand in a specific area.

        Args:
            brand_id: ID of the brand
            area_id: ID of the area (None for global visibility)

        Raises:
            BrandNotFoundException: If brand not found
            BrandAlreadyExistsException: If visibility already exists
            BrandOperationException: If operation fails
        """
        try:
            logger.info(
                "Adding brand visibility",
                brand_id=brand_id,
                area_id=area_id,
                company_id=str(self.company_id),
            )

            await self.repository.add_brand_visibility(brand_id, area_id)

            logger.info(
                "Brand visibility added successfully",
                brand_id=brand_id,
                area_id=area_id,
                company_id=str(self.company_id),
            )

        except (BrandNotFoundException, BrandAlreadyExistsException):
            raise
        except Exception as e:
            logger.error(
                "Failed to add brand visibility in service",
                brand_id=brand_id,
                area_id=area_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def remove_brand_visibility(
        self, brand_id: int, area_id: Optional[int]
    ) -> None:
        """
        Remove visibility for a brand in a specific area.

        Args:
            brand_id: ID of the brand
            area_id: ID of the area (None for global visibility)

        Raises:
            BrandNotFoundException: If brand or visibility not found
            BrandOperationException: If operation fails
        """
        try:
            logger.info(
                "Removing brand visibility",
                brand_id=brand_id,
                area_id=area_id,
                company_id=str(self.company_id),
            )

            await self.repository.remove_brand_visibility(brand_id, area_id)

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
                "Failed to remove brand visibility in service",
                brand_id=brand_id,
                area_id=area_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    # ==================== Margin Management ====================

    async def add_brand_margin(
        self, brand_id: int, area_id: Optional[int], margins: BrandMarginAddOrUpdate
    ) -> BrandMarginInDB:
        """
        Add or update margin configuration for a brand in a specific area.

        Args:
            brand_id: ID of the brand
            area_id: ID of the area (None for global margin)
            margins: Margin configuration

        Returns:
            Created or updated margin configuration

        Raises:
            BrandNotFoundException: If brand not found
            BrandOperationException: If operation fails
        """
        try:
            logger.info(
                "Adding brand margin",
                brand_id=brand_id,
                area_id=area_id,
                company_id=str(self.company_id),
            )

            margin = await self.repository.add_brand_margin(brand_id, area_id, margins)

            logger.info(
                "Brand margin added successfully",
                brand_id=brand_id,
                area_id=area_id,
                margin_id=margin.id,
                company_id=str(self.company_id),
            )

            return margin

        except BrandNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to add brand margin in service",
                brand_id=brand_id,
                area_id=area_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def remove_brand_margin(self, brand_id: int, area_id: Optional[int]) -> None:
        """
        Remove margin configuration for a brand in a specific area.

        Args:
            brand_id: ID of the brand
            area_id: ID of the area (None for global margin)

        Raises:
            BrandNotFoundException: If brand or margin not found
            BrandOperationException: If operation fails
        """
        try:
            logger.info(
                "Removing brand margin",
                brand_id=brand_id,
                area_id=area_id,
                company_id=str(self.company_id),
            )

            await self.repository.remove_brand_margin(brand_id, area_id)

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
                "Failed to remove brand margin in service",
                brand_id=brand_id,
                area_id=area_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise
