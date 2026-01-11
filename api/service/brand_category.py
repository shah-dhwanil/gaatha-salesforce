"""
Service layer for Brand Category entity operations.

This service provides business logic for brand categories, including visibility and margin management,
acting as an intermediary between the API layer and the repository layer.
"""

from api.models.brand_category import BrandCategoryMarginAddOrUpdate
from typing import Optional
from uuid import UUID

import structlog

from api.database import DatabasePool
from api.exceptions.brand_category import (
    BrandCategoryAlreadyExistsException,
    BrandCategoryNotFoundException,
)
from api.models.brand_category import (
    BrandCategoryCreate,
    BrandCategoryDetailItem,
    BrandCategoryListItem,
    BrandCategoryMarginInDB,
    BrandCategoryUpdate,
)
from api.repository.brand_category import BrandCategoryRepository

logger = structlog.get_logger(__name__)


class BrandCategoryService:
    """
    Service for managing Brand Category business logic.

    This service handles business logic, validation, and orchestration
    for brand category operations including visibility and margin management
    in a multi-tenant environment.
    """

    def __init__(self, db_pool: DatabasePool, company_id: UUID) -> None:
        """
        Initialize the BrandCategoryService.

        Args:
            db_pool: Database pool instance for connection management
            company_id: UUID of the company (tenant) for schema isolation
        """
        self.db_pool = db_pool
        self.company_id = company_id
        self.repository = BrandCategoryRepository(db_pool, company_id)
        logger.debug(
            "BrandCategoryService initialized",
            company_id=str(company_id),
        )

    async def create_brand_category(
        self, brand_category_data: BrandCategoryCreate
    ) -> BrandCategoryDetailItem:
        """
        Create a new brand category.

        Args:
            brand_category_data: Brand category data to create

        Returns:
            Created brand category with full details

        Raises:
            BrandCategoryAlreadyExistsException: If brand category with same name/code exists
            BrandCategoryOperationException: If creation fails
        """
        try:
            logger.info(
                "Creating brand category",
                brand_category_name=brand_category_data.name,
                brand_category_code=brand_category_data.code,
                company_id=str(self.company_id),
            )

            # Create brand category using repository
            brand_category = await self.repository.create_brand_category(
                brand_category_data
            )

            # Fetch full details to return
            brand_category_detail = await self.repository.get_brand_category_by_id(
                brand_category.id
            )

            logger.info(
                "Brand category created successfully",
                brand_category_id=brand_category.id,
                brand_category_name=brand_category.name,
                company_id=str(self.company_id),
            )

            return brand_category_detail

        except (BrandCategoryAlreadyExistsException, BrandCategoryNotFoundException):
            raise
        except Exception as e:
            logger.error(
                "Failed to create brand category in service",
                brand_category_name=brand_category_data.name,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def get_brand_category_by_id(
        self, brand_category_id: int
    ) -> BrandCategoryDetailItem:
        """
        Get a brand category by ID with full details.

        Args:
            brand_category_id: ID of the brand category

        Returns:
            Brand category with full details

        Raises:
            BrandCategoryNotFoundException: If brand category not found
            BrandCategoryOperationException: If retrieval fails
        """
        try:
            logger.debug(
                "Getting brand category by ID",
                brand_category_id=brand_category_id,
                company_id=str(self.company_id),
            )

            brand_category = await self.repository.get_brand_category_by_id(
                brand_category_id
            )

            return brand_category

        except BrandCategoryNotFoundException:
            logger.warning(
                "Brand category not found",
                brand_category_id=brand_category_id,
                company_id=str(self.company_id),
            )
            raise
        except Exception as e:
            logger.error(
                "Failed to get brand category in service",
                brand_category_id=brand_category_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def get_brand_category_by_code(self, code: str) -> BrandCategoryDetailItem:
        """
        Get a brand category by code with full details.

        Args:
            code: Code of the brand category

        Returns:
            Brand category with full details

        Raises:
            BrandCategoryNotFoundException: If brand category not found
            BrandCategoryOperationException: If retrieval fails
        """
        try:
            logger.debug(
                "Getting brand category by code",
                brand_category_code=code,
                company_id=str(self.company_id),
            )

            brand_category = await self.repository.get_brand_category_by_code(code)

            return brand_category

        except BrandCategoryNotFoundException:
            logger.warning(
                "Brand category not found",
                brand_category_code=code,
                company_id=str(self.company_id),
            )
            raise
        except Exception as e:
            logger.error(
                "Failed to get brand category in service",
                brand_category_code=code,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def list_brand_categories(
        self,
        brand_id: Optional[int] = None,
        is_active: Optional[bool] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[BrandCategoryListItem]:
        """
        List brand categories with minimal data.

        Args:
            brand_id: Filter by brand ID
            is_active: Filter by active status
            limit: Maximum number of brand categories to return
            offset: Number of brand categories to skip

        Returns:
            List of brand categories

        Raises:
            BrandCategoryOperationException: If listing fails
        """
        try:
            logger.debug(
                "Listing brand categories",
                brand_id=brand_id,
                is_active=is_active,
                limit=limit,
                offset=offset,
                company_id=str(self.company_id),
            )

            brand_categories = await self.repository.list_brand_categories(
                brand_id, is_active, limit, offset
            )

            logger.debug(
                "Brand categories listed successfully",
                count=len(brand_categories),
                company_id=str(self.company_id),
            )

            return brand_categories

        except Exception as e:
            logger.error(
                "Failed to list brand categories in service",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def update_brand_category(
        self, brand_category_id: int, brand_category_data: BrandCategoryUpdate
    ) -> BrandCategoryDetailItem:
        """
        Update a brand category.

        Args:
            brand_category_id: ID of the brand category to update
            brand_category_data: Brand category data to update

        Returns:
            Updated brand category with full details

        Raises:
            BrandCategoryNotFoundException: If brand category not found
            BrandCategoryAlreadyExistsException: If updated name/code conflicts
            BrandCategoryOperationException: If update fails
        """
        try:
            logger.info(
                "Updating brand category",
                brand_category_id=brand_category_id,
                company_id=str(self.company_id),
            )

            # Update brand category using repository
            await self.repository.update_brand_category(
                brand_category_id, brand_category_data
            )

            # Fetch full details to return
            brand_category_detail = await self.repository.get_brand_category_by_id(
                brand_category_id
            )

            logger.info(
                "Brand category updated successfully",
                brand_category_id=brand_category_id,
                company_id=str(self.company_id),
            )

            return brand_category_detail

        except (BrandCategoryNotFoundException, BrandCategoryAlreadyExistsException):
            raise
        except Exception as e:
            logger.error(
                "Failed to update brand category in service",
                brand_category_id=brand_category_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def delete_brand_category(self, brand_category_id: int) -> None:
        """
        Soft delete a brand category.

        Args:
            brand_category_id: ID of the brand category to delete

        Raises:
            BrandCategoryNotFoundException: If brand category not found
            BrandCategoryOperationException: If deletion fails
        """
        try:
            logger.info(
                "Deleting brand category",
                brand_category_id=brand_category_id,
                company_id=str(self.company_id),
            )

            await self.repository.delete_brand_category(brand_category_id)

            logger.info(
                "Brand category deleted successfully",
                brand_category_id=brand_category_id,
                company_id=str(self.company_id),
            )

        except BrandCategoryNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to delete brand category in service",
                brand_category_id=brand_category_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    # ==================== Visibility Management ====================

    async def add_brand_category_visibility(
        self, brand_category_id: int, area_id: Optional[int]
    ) -> None:
        """
        Add visibility for a brand category in a specific area.

        Args:
            brand_category_id: ID of the brand category
            area_id: ID of the area (None for global visibility)

        Raises:
            BrandCategoryNotFoundException: If brand category not found
            BrandCategoryAlreadyExistsException: If visibility already exists
            BrandCategoryOperationException: If operation fails
        """
        try:
            logger.info(
                "Adding brand category visibility",
                brand_category_id=brand_category_id,
                area_id=area_id,
                company_id=str(self.company_id),
            )

            await self.repository.add_brand_category_visibility(
                brand_category_id, area_id
            )

            logger.info(
                "Brand category visibility added successfully",
                brand_category_id=brand_category_id,
                area_id=area_id,
                company_id=str(self.company_id),
            )

        except (BrandCategoryNotFoundException, BrandCategoryAlreadyExistsException):
            raise
        except Exception as e:
            logger.error(
                "Failed to add brand category visibility in service",
                brand_category_id=brand_category_id,
                area_id=area_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def remove_brand_category_visibility(
        self, brand_category_id: int, area_id: Optional[int]
    ) -> None:
        """
        Remove visibility for a brand category in a specific area.

        Args:
            brand_category_id: ID of the brand category
            area_id: ID of the area (None for global visibility)

        Raises:
            BrandCategoryNotFoundException: If brand category or visibility not found
            BrandCategoryOperationException: If operation fails
        """
        try:
            logger.info(
                "Removing brand category visibility",
                brand_category_id=brand_category_id,
                area_id=area_id,
                company_id=str(self.company_id),
            )

            await self.repository.remove_brand_category_visibility(
                brand_category_id, area_id
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
                "Failed to remove brand category visibility in service",
                brand_category_id=brand_category_id,
                area_id=area_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    # ==================== Margin Management ====================

    async def add_brand_category_margin(
        self,
        brand_category_id: int,
        area_id: Optional[int],
        margins: BrandCategoryMarginAddOrUpdate,
    ) -> "BrandCategoryMarginInDB":
        """
        Add or update margin configuration for a brand category in a specific area.

        Args:
            brand_category_id: ID of the brand category
            area_id: ID of the area (None for global margin)
            margins: Margin configuration

        Returns:
            Created or updated margin configuration

        Raises:
            BrandCategoryNotFoundException: If brand category not found
            BrandCategoryOperationException: If operation fails
        """
        try:
            logger.info(
                "Adding brand category margin",
                brand_category_id=brand_category_id,
                area_id=area_id,
                company_id=str(self.company_id),
            )

            margin = await self.repository.add_brand_category_margin(
                brand_category_id, area_id, margins
            )

            logger.info(
                "Brand category margin added successfully",
                brand_category_id=brand_category_id,
                area_id=area_id,
                margin_id=margin.id,
                company_id=str(self.company_id),
            )

            return margin

        except BrandCategoryNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to add brand category margin in service",
                brand_category_id=brand_category_id,
                area_id=area_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def remove_brand_category_margin(
        self, brand_category_id: int, area_id: Optional[int]
    ) -> None:
        """
        Remove margin configuration for a brand category in a specific area.

        Args:
            brand_category_id: ID of the brand category
            area_id: ID of the area (None for global margin)

        Raises:
            BrandCategoryNotFoundException: If brand category or margin not found
            BrandCategoryOperationException: If operation fails
        """
        try:
            logger.info(
                "Removing brand category margin",
                brand_category_id=brand_category_id,
                area_id=area_id,
                company_id=str(self.company_id),
            )

            await self.repository.remove_brand_category_margin(
                brand_category_id, area_id
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
                "Failed to remove brand category margin in service",
                brand_category_id=brand_category_id,
                area_id=area_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise
