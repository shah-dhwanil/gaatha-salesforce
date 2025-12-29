"""
Service layer for ShopCategory entity operations.

This service provides business logic for shop categories, acting as an intermediary
between the API layer and the repository layer.
"""

from typing import Optional
from uuid import UUID

import structlog

from api.database import DatabasePool
from api.exceptions.shop_category import (
    ShopCategoryAlreadyExistsException,
    ShopCategoryNotFoundException,
    ShopCategoryOperationException,
    ShopCategoryValidationException,
)
from api.models.shop_category import (
    ShopCategoryCreate,
    ShopCategoryInDB,
    ShopCategoryListItem,
    ShopCategoryResponse,
    ShopCategoryUpdate,
)
from api.repository.shop_category import ShopCategoryRepository

logger = structlog.get_logger(__name__)


class ShopCategoryService:
    """
    Service for managing ShopCategory business logic.

    This service handles business logic, validation, and orchestration
    for shop category operations in a multi-tenant environment.
    """

    def __init__(self, db_pool: DatabasePool, company_id: UUID) -> None:
        """
        Initialize the ShopCategoryService.

        Args:
            db_pool: Database pool instance for connection management
            company_id: UUID of the company (tenant) for schema isolation
        """
        self.db_pool = db_pool
        self.company_id = company_id
        self.repository = ShopCategoryRepository(db_pool, company_id)
        logger.debug(
            "ShopCategoryService initialized",
            company_id=str(company_id),
        )

    async def create_shop_category(
        self, shop_category_data: ShopCategoryCreate
    ) -> ShopCategoryResponse:
        """
        Create a new shop category.

        Args:
            shop_category_data: Shop category data to create

        Returns:
            Created shop category

        Raises:
            ShopCategoryAlreadyExistsException: If shop category with the same name already exists
            ShopCategoryValidationException: If validation fails
            ShopCategoryOperationException: If creation fails
        """
        try:
            logger.info(
                "Creating shop category",
                shop_category_name=shop_category_data.name,
                company_id=str(self.company_id),
            )

            # Create shop category using repository
            shop_category = await self.repository.create_shop_category(
                shop_category_data
            )

            logger.info(
                "Shop category created successfully",
                shop_category_id=shop_category.id,
                shop_category_name=shop_category.name,
                company_id=str(self.company_id),
            )

            return ShopCategoryResponse(**shop_category.model_dump())

        except (ShopCategoryAlreadyExistsException, ShopCategoryValidationException):
            raise
        except Exception as e:
            logger.error(
                "Failed to create shop category in service",
                shop_category_name=shop_category_data.name,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def get_shop_category_by_id(
        self, shop_category_id: int
    ) -> ShopCategoryResponse:
        """
        Get a shop category by ID.

        Args:
            shop_category_id: ID of the shop category

        Returns:
            Shop category

        Raises:
            ShopCategoryNotFoundException: If shop category not found
            ShopCategoryOperationException: If retrieval fails
        """
        try:
            logger.debug(
                "Getting shop category by ID",
                shop_category_id=shop_category_id,
                company_id=str(self.company_id),
            )

            shop_category = await self.repository.get_shop_category_by_id(
                shop_category_id
            )

            return ShopCategoryResponse(**shop_category.model_dump())

        except ShopCategoryNotFoundException:
            logger.warning(
                "Shop category not found",
                shop_category_id=shop_category_id,
                company_id=str(self.company_id),
            )
            raise
        except Exception as e:
            logger.error(
                "Failed to get shop category in service",
                shop_category_id=shop_category_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def get_shop_category_by_name(
        self, shop_category_name: str
    ) -> ShopCategoryResponse:
        """
        Get a shop category by name.

        Args:
            shop_category_name: Name of the shop category

        Returns:
            Shop category

        Raises:
            ShopCategoryNotFoundException: If shop category not found
            ShopCategoryOperationException: If retrieval fails
        """
        try:
            logger.debug(
                "Getting shop category by name",
                shop_category_name=shop_category_name,
                company_id=str(self.company_id),
            )

            shop_category = await self.repository.get_shop_category_by_name(
                shop_category_name
            )

            return ShopCategoryResponse(**shop_category.model_dump())

        except ShopCategoryNotFoundException:
            logger.warning(
                "Shop category not found",
                shop_category_name=shop_category_name,
                company_id=str(self.company_id),
            )
            raise
        except Exception as e:
            logger.error(
                "Failed to get shop category in service",
                shop_category_name=shop_category_name,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def list_shop_categories(
        self,
        is_active: Optional[bool] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[ShopCategoryListItem], int]:
        """
        List all shop categories with optional filtering and return total count.

        Args:
            is_active: Filter by active status
            limit: Maximum number of shop categories to return (default: 20)
            offset: Number of shop categories to skip (default: 0)

        Returns:
            Tuple of (list of shop categories with minimal data, total count)

        Raises:
            ShopCategoryValidationException: If validation fails
            ShopCategoryOperationException: If listing fails
        """
        try:
            logger.debug(
                "Listing shop categories",
                is_active=is_active,
                limit=limit,
                offset=offset,
                company_id=str(self.company_id),
            )

            # Validate pagination parameters
            if limit < 1 or limit > 100:
                raise ShopCategoryValidationException(
                    message="Limit must be between 1 and 100",
                    field="limit",
                    value=limit,
                )

            if offset < 0:
                raise ShopCategoryValidationException(
                    message="Offset must be non-negative",
                    field="offset",
                    value=offset,
                )

            # Get shop categories and count in parallel for better performance
            async with self.db_pool.acquire() as conn:
                shop_categories = await self.repository.list_shop_categories(
                    is_active=is_active,
                    limit=limit,
                    offset=offset,
                    connection=conn,
                )
                total_count = await self.repository.count_shop_categories(
                    is_active=is_active,
                    connection=conn,
                )

            logger.debug(
                "Shop categories listed successfully",
                count=len(shop_categories),
                total_count=total_count,
                company_id=str(self.company_id),
            )

            return shop_categories, total_count

        except ShopCategoryValidationException:
            raise
        except Exception as e:
            logger.error(
                "Failed to list shop categories in service",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def update_shop_category(
        self, shop_category_id: int, shop_category_data: ShopCategoryUpdate
    ) -> ShopCategoryResponse:
        """
        Update an existing shop category.

        Args:
            shop_category_id: ID of the shop category to update
            shop_category_data: Shop category data to update

        Returns:
            Updated shop category

        Raises:
            ShopCategoryNotFoundException: If shop category not found
            ShopCategoryValidationException: If validation fails
            ShopCategoryOperationException: If update fails
        """
        try:
            logger.info(
                "Updating shop category",
                shop_category_id=shop_category_id,
                company_id=str(self.company_id),
            )

            # Additional business logic validation
            if not shop_category_data.name:
                raise ShopCategoryValidationException(
                    message="At least one field must be provided for update",
                )

            # Update shop category using repository
            shop_category = await self.repository.update_shop_category(
                shop_category_id, shop_category_data
            )

            logger.info(
                "Shop category updated successfully",
                shop_category_id=shop_category_id,
                company_id=str(self.company_id),
            )

            return ShopCategoryResponse(**shop_category.model_dump())

        except (ShopCategoryNotFoundException, ShopCategoryValidationException):
            raise
        except Exception as e:
            logger.error(
                "Failed to update shop category in service",
                shop_category_id=shop_category_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def delete_shop_category(self, shop_category_id: int) -> None:
        """
        Soft delete a shop category by setting is_active to False.

        Args:
            shop_category_id: ID of the shop category to delete

        Raises:
            ShopCategoryNotFoundException: If shop category not found
            ShopCategoryValidationException: If shop category is protected
            ShopCategoryOperationException: If deletion fails
        """
        try:
            logger.info(
                "Deleting shop category",
                shop_category_id=shop_category_id,
                company_id=str(self.company_id),
            )

            # Soft delete shop category using repository
            await self.repository.delete_shop_category(shop_category_id)

            logger.info(
                "Shop category deleted successfully",
                shop_category_id=shop_category_id,
                company_id=str(self.company_id),
            )

        except (ShopCategoryNotFoundException, ShopCategoryValidationException):
            raise
        except Exception as e:
            logger.error(
                "Failed to delete shop category in service",
                shop_category_id=shop_category_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def bulk_create_shop_categories(
        self, shop_categories_data: list[ShopCategoryCreate]
    ) -> list[ShopCategoryResponse]:
        """
        Bulk create multiple shop categories in a transaction.

        Args:
            shop_categories_data: List of shop category data to create

        Returns:
            List of created shop categories

        Raises:
            ShopCategoryAlreadyExistsException: If any shop category already exists
            ShopCategoryValidationException: If validation fails
            ShopCategoryOperationException: If creation fails
        """
        try:
            logger.info(
                "Bulk creating shop categories",
                count=len(shop_categories_data),
                company_id=str(self.company_id),
            )

            # Validate input
            if not shop_categories_data:
                raise ShopCategoryValidationException(
                    message="At least one shop category must be provided",
                )

            # Bulk create shop categories using repository (in transaction)
            shop_categories = await self.repository.bulk_create_shop_categories(
                shop_categories_data
            )

            logger.info(
                "Shop categories bulk created successfully",
                count=len(shop_categories),
                company_id=str(self.company_id),
            )

            return [
                ShopCategoryResponse(**shop_category.model_dump())
                for shop_category in shop_categories
            ]

        except (
            ShopCategoryAlreadyExistsException,
            ShopCategoryValidationException,
            ShopCategoryOperationException,
        ):
            raise
        except Exception as e:
            logger.error(
                "Failed to bulk create shop categories in service",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def check_shop_category_exists(self, shop_category_id: int) -> bool:
        """
        Check if a shop category exists.

        Args:
            shop_category_id: ID of the shop category to check

        Returns:
            True if shop category exists, False otherwise
        """
        try:
            await self.repository.get_shop_category_by_id(shop_category_id)
            return True
        except ShopCategoryNotFoundException:
            return False

    async def check_shop_category_exists_by_name(
        self, shop_category_name: str
    ) -> bool:
        """
        Check if a shop category exists by name.

        Args:
            shop_category_name: Name of the shop category to check

        Returns:
            True if shop category exists, False otherwise
        """
        try:
            await self.repository.get_shop_category_by_name(shop_category_name)
            return True
        except ShopCategoryNotFoundException:
            return False

    async def get_active_shop_categories_count(self) -> int:
        """
        Get count of active shop categories.

        Returns:
            Count of active shop categories

        Raises:
            ShopCategoryOperationException: If counting fails
        """
        try:
            logger.debug(
                "Getting active shop categories count",
                company_id=str(self.company_id),
            )

            count = await self.repository.count_shop_categories(is_active=True)

            return count

        except Exception as e:
            logger.error(
                "Failed to get active shop categories count in service",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def get_all_active_shop_categories(self) -> list[ShopCategoryListItem]:
        """
        Get all active shop categories without pagination.

        Returns:
            List of all active shop categories

        Raises:
            ShopCategoryOperationException: If retrieval fails
        """
        try:
            logger.debug(
                "Getting all active shop categories",
                company_id=str(self.company_id),
            )

            shop_categories = await self.repository.list_shop_categories(
                is_active=True, limit=100, offset=0
            )

            return shop_categories

        except Exception as e:
            logger.error(
                "Failed to get all active shop categories in service",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

