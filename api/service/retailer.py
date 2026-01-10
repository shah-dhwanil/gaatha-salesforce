"""
Service layer for Retailer entity operations.

This service provides business logic for retailers, acting as an intermediary
between the API layer and the repository layer.
"""

from typing import Optional
from uuid import UUID

import structlog

from api.database import DatabasePool
from api.exceptions.retailer import (
    RetailerAlreadyExistsException,
    RetailerNotFoundException,
    RetailerOperationException,
    RetailerValidationException,
)
from api.models.retailer import (
    RetailerCreate,
    RetailerDetailItem,
    RetailerListItem,
    RetailerResponse,
    RetailerUpdate,
)
from api.models.user import UserCreate, UserUpdate
from api.repository.retailer import RetailerRepository
from api.repository.company import CompanyRepository
from api.service.user import UserService
from api.repository.route import RouteRepository

logger = structlog.get_logger(__name__)


class RetailerService:
    """
    Service for managing Retailer business logic.

    This service handles business logic, validation, and orchestration
    for retailer operations in a multi-tenant environment.
    """

    def __init__(self, db_pool: DatabasePool, company_id: UUID) -> None:
        """
        Initialize the RetailerService.

        Args:
            db_pool: Database pool instance for connection management
            company_id: UUID of the company (tenant) for schema isolation
        """
        self.db_pool = db_pool
        self.company_id = company_id
        self.repository = RetailerRepository(db_pool, company_id)
        self.company_repository = CompanyRepository(db_pool)
        self.route_repository = RouteRepository(db_pool, company_id)
        self.user_service = UserService(db_pool)
        logger.debug(
            "RetailerService initialized",
            company_id=str(company_id),
        )

    async def create_retailer(
        self, retailer_data: RetailerCreate
    ) -> RetailerResponse:
        """
        Create a new retailer.

        Args:
            retailer_data: Retailer data to create

        Returns:
            Created retailer

        Raises:
            RetailerAlreadyExistsException: If retailer with unique constraint already exists
            RetailerValidationException: If validation fails
            RetailerOperationException: If creation fails
        """
        user_data = None
        try:
            async with self.db_pool.acquire() as conn:
                serial_number = await self.repository.get_serial_number(conn)
                company = await self.company_repository.get_company_by_id(self.company_id)
                code = f"{company.name[:4].upper()}_RETAIL_{serial_number}"
                route = await self.route_repository.get_route_by_id(retailer_data.route_id, conn)
                user = UserCreate(
                    username=code,
                    name=retailer_data.name,
                    contact_no=retailer_data.mobile_number,
                    company_id=self.company_id,
                    area_id=route.area_id,
                    role="RETAILER",
                    is_super_admin=False,
                    bank_details=retailer_data.bank_details,
                )
                user_data = await self.user_service.create_user(user)
                retailer = await self.repository.create_retailer(retailer_data, user_data.id, code, conn)
                logger.info(
                    "Retailer created successfully",
                    retailer_id=str(retailer.id),
                    retailer_name=retailer.name,
                    retailer_code=code,
                    company_id=str(self.company_id),
                )
                return RetailerResponse(**retailer.model_dump())
        except (RetailerAlreadyExistsException, RetailerValidationException) as e:
            if user_data is not None:
                await self.user_service.delete_user(user_data.id)
            logger.error(
                "Failed to create retailer in service",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise e
        except Exception as e:
            if user_data is not None:
                await self.user_service.delete_user(user_data.id)
            logger.error(
                "Failed to create retailer in service",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RetailerOperationException(
                message=f"Failed to create retailer: {str(e)}",
                operation="create_retailer",
            ) from e

    async def get_retailer_by_id(self, retailer_id: UUID) -> RetailerDetailItem:
        """
        Get a retailer by ID with full details including joined data.

        Args:
            retailer_id: ID of the retailer

        Returns:
            Retailer with detailed information (including category_name, route_name)

        Raises:
            RetailerNotFoundException: If retailer not found
            RetailerOperationException: If retrieval fails
        """
        try:
            logger.debug(
                "Getting retailer by ID",
                retailer_id=str(retailer_id),
                company_id=str(self.company_id),
            )

            retailer = await self.repository.get_retailer_by_id(retailer_id)

            return retailer

        except RetailerNotFoundException:
            logger.warning(
                "Retailer not found",
                retailer_id=str(retailer_id),
                company_id=str(self.company_id),
            )
            raise
        except Exception as e:
            logger.error(
                "Failed to get retailer in service",
                retailer_id=str(retailer_id),
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def get_retailer_by_code(self, code: str) -> RetailerDetailItem:
        """
        Get a retailer by code with full details including joined data.

        Args:
            code: Code of the retailer

        Returns:
            Retailer with detailed information (including category_name, route_name)

        Raises:
            RetailerNotFoundException: If retailer not found
            RetailerOperationException: If retrieval fails
        """
        try:
            logger.debug(
                "Getting retailer by code",
                retailer_code=code,
                company_id=str(self.company_id),
            )

            retailer = await self.repository.get_retailer_by_code(code)

            return retailer

        except RetailerNotFoundException:
            logger.warning(
                "Retailer not found",
                retailer_code=code,
                company_id=str(self.company_id),
            )
            raise
        except Exception as e:
            logger.error(
                "Failed to get retailer by code in service",
                retailer_code=code,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def list_retailers(
        self,
        route_id: Optional[int] = None,
        category_id: Optional[int] = None,
        is_active: Optional[bool] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[RetailerListItem], int]:
        """
        List all retailers with optional filtering and return total count.

        Returns optimized list view with fields: name, contact_person_name,
        mobile_number, address, route_name, route_id, code.

        Args:
            route_id: Filter by route ID
            category_id: Filter by category ID
            is_active: Filter by active status
            limit: Maximum number of retailers to return (default: 20, max: 100)
            offset: Number of retailers to skip (default: 0)

        Returns:
            Tuple of (list of retailers with minimal data, total count)

        Raises:
            RetailerValidationException: If validation fails
            RetailerOperationException: If listing fails
        """
        try:
            logger.debug(
                "Listing retailers",
                route_id=route_id,
                category_id=category_id,
                is_active=is_active,
                limit=limit,
                offset=offset,
                company_id=str(self.company_id),
            )

            # Validate pagination parameters
            if limit < 1 or limit > 100:
                raise RetailerValidationException(
                    message="Limit must be between 1 and 100",
                    field="limit",
                    value=limit,
                )

            if offset < 0:
                raise RetailerValidationException(
                    message="Offset must be non-negative",
                    field="offset",
                    value=offset,
                )

            # Get retailers and count in parallel for better performance
            async with self.db_pool.acquire() as conn:
                retailers = await self.repository.list_retailers(
                    route_id=route_id,
                    category_id=category_id,
                    is_active=is_active,
                    limit=limit,
                    offset=offset,
                    connection=conn,
                )
                total_count = await self.repository.count_retailers(
                    route_id=route_id,
                    category_id=category_id,
                    is_active=is_active,
                    connection=conn,
                )

            logger.debug(
                "Retailers listed successfully",
                count=len(retailers),
                total_count=total_count,
                company_id=str(self.company_id),
            )

            return retailers, total_count

        except RetailerValidationException:
            raise
        except Exception as e:
            logger.error(
                "Failed to list retailers in service",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def update_retailer(
        self, retailer_id: UUID, retailer_data: RetailerUpdate
    ) -> RetailerResponse:
        """
        Update an existing retailer.

        Note: Retailer code cannot be updated (it's immutable).

        Args:
            retailer_id: ID of the retailer to update
            retailer_data: Retailer data to update

        Returns:
            Updated retailer

        Raises:
            RetailerNotFoundException: If retailer not found
            RetailerValidationException: If validation fails
            RetailerOperationException: If update fails
        """
        try:
            logger.info(
                "Updating retailer",
                retailer_id=str(retailer_id),
                company_id=str(self.company_id),
            )

            # Validate at least one field is provided for update
            if not any(
                [
                    retailer_data.name,
                    retailer_data.contact_person_name,
                    retailer_data.mobile_number,
                    retailer_data.email,
                    retailer_data.gst_no,
                    retailer_data.pan_no,
                    retailer_data.license_no,
                    retailer_data.address,
                    retailer_data.category_id is not None,
                    retailer_data.pin_code,
                    retailer_data.map_link,
                    retailer_data.route_id is not None,
                    retailer_data.is_type_a is not None,
                    retailer_data.is_type_b is not None,
                    retailer_data.is_type_c is not None,
                ]
            ):
                raise RetailerValidationException(
                    message="At least one field must be provided for update",
                )

            # Validate retailer type constraint when updating types
            if any(field is not None for field in [retailer_data.is_type_a, retailer_data.is_type_b, retailer_data.is_type_c]):
                # If updating type fields, we need to ensure exactly one is true
                # Get current retailer state
                async with self.db_pool.acquire() as conn:
                    current_retailer = await self.repository.get_retailer_by_id(retailer_id, conn)
                    
                    # Determine final state of type fields
                    final_type_a = retailer_data.is_type_a if retailer_data.is_type_a is not None else current_retailer.is_type_a
                    final_type_b = retailer_data.is_type_b if retailer_data.is_type_b is not None else current_retailer.is_type_b
                    final_type_c = retailer_data.is_type_c if retailer_data.is_type_c is not None else current_retailer.is_type_c
                    
                    # Check if exactly one is true
                    type_count = sum([final_type_a, final_type_b, final_type_c])
                    if type_count != 1:
                        raise RetailerValidationException(
                            message="Exactly one of is_type_a, is_type_b, or is_type_c must be true",
                        )

            if retailer_data.mobile_number is not None:
                await self.user_service.update_user(retailer_id, UserUpdate(contact_no=retailer_data.mobile_number), self.company_id)
            if retailer_data.name is not None:
                await self.user_service.update_user(retailer_id, UserUpdate(name=retailer_data.name), self.company_id)
            # Update retailer using repository
            retailer = await self.repository.update_retailer(
                retailer_id, retailer_data
            )

            logger.info(
                "Retailer updated successfully",
                retailer_id=str(retailer_id),
                company_id=str(self.company_id),
            )

            return RetailerResponse(**retailer.model_dump())

        except (RetailerNotFoundException, RetailerValidationException):
            raise
        except Exception as e:
            logger.error(
                "Failed to update retailer in service",
                retailer_id=str(retailer_id),
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def delete_retailer(self, retailer_id: UUID) -> None:
        """
        Soft delete a retailer by setting is_active to False.

        Args:
            retailer_id: ID of the retailer to delete

        Raises:
            RetailerNotFoundException: If retailer not found
            RetailerOperationException: If deletion fails
        """
        try:
            logger.info(
                "Deleting retailer",
                retailer_id=str(retailer_id),
                company_id=str(self.company_id),
            )

            # Soft delete retailer using repository
            await self.repository.delete_retailer(retailer_id)

            logger.info(
                "Retailer deleted successfully",
                retailer_id=str(retailer_id),
                company_id=str(self.company_id),
            )

        except RetailerNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to delete retailer in service",
                retailer_id=str(retailer_id),
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def get_retailers_by_route(self, route_id: int) -> list[RetailerListItem]:
        """
        Get all active retailers for a specific route.

        Args:
            route_id: ID of the route

        Returns:
            List of retailers (optimized list view)

        Raises:
            RetailerOperationException: If retrieval fails
        """
        try:
            logger.debug(
                "Getting retailers by route",
                route_id=route_id,
                company_id=str(self.company_id),
            )

            retailers = await self.repository.get_retailers_by_route(route_id)

            logger.debug(
                "Retailers retrieved by route successfully",
                route_id=route_id,
                count=len(retailers),
                company_id=str(self.company_id),
            )

            return retailers

        except Exception as e:
            logger.error(
                "Failed to get retailers by route in service",
                route_id=route_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def check_retailer_exists(self, retailer_id: UUID) -> bool:
        """
        Check if a retailer exists.

        Args:
            retailer_id: ID of the retailer to check

        Returns:
            True if retailer exists, False otherwise
        """
        try:
            await self.repository.get_retailer_by_id(retailer_id)
            return True
        except RetailerNotFoundException:
            return False

    async def check_retailer_exists_by_code(self, code: str) -> bool:
        """
        Check if a retailer exists by code.

        Args:
            code: Code of the retailer to check

        Returns:
            True if retailer exists, False otherwise
        """
        try:
            await self.repository.get_retailer_by_code(code)
            return True
        except RetailerNotFoundException:
            return False

    async def get_active_retailers_count(
        self,
        route_id: Optional[int] = None,
        category_id: Optional[int] = None,
    ) -> int:
        """
        Get count of active retailers, optionally filtered by route and category.

        Args:
            route_id: Optional filter by route ID
            category_id: Optional filter by category ID

        Returns:
            Count of active retailers

        Raises:
            RetailerOperationException: If counting fails
        """
        try:
            logger.debug(
                "Getting active retailers count",
                route_id=route_id,
                category_id=category_id,
                company_id=str(self.company_id),
            )

            count = await self.repository.count_retailers(
                route_id=route_id,
                category_id=category_id,
                is_active=True,
            )

            return count

        except Exception as e:
            logger.error(
                "Failed to get active retailers count in service",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def get_all_active_retailers_by_route(
        self, route_id: int
    ) -> list[RetailerListItem]:
        """
        Get all active retailers for a route without pagination.

        Args:
            route_id: ID of the route

        Returns:
            List of all active retailers for the route

        Raises:
            RetailerOperationException: If retrieval fails
        """
        try:
            logger.debug(
                "Getting all active retailers by route",
                route_id=route_id,
                company_id=str(self.company_id),
            )

            retailers = await self.repository.list_retailers(
                route_id=route_id,
                is_active=True,
                limit=100,
                offset=0,
            )

            return retailers

        except Exception as e:
            logger.error(
                "Failed to get all active retailers by route in service",
                route_id=route_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def get_all_active_retailers_by_category(
        self, category_id: int
    ) -> list[RetailerListItem]:
        """
        Get all active retailers for a category without pagination.

        Args:
            category_id: ID of the category

        Returns:
            List of all active retailers for the category

        Raises:
            RetailerOperationException: If retrieval fails
        """
        try:
            logger.debug(
                "Getting all active retailers by category",
                category_id=category_id,
                company_id=str(self.company_id),
            )

            retailers = await self.repository.list_retailers(
                category_id=category_id,
                is_active=True,
                limit=100,
                offset=0,
            )

            return retailers

        except Exception as e:
            logger.error(
                "Failed to get all active retailers by category in service",
                category_id=category_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def validate_retailer_unique_fields(
        self, retailer_data: RetailerCreate
    ) -> dict[str, bool]:
        """
        Validate if retailer unique fields already exist.

        This is a helper method for bulk validation before creating retailers.

        Args:
            retailer_data: Retailer data to validate

        Returns:
            Dictionary with validation results for each unique field

        Example:
            {
                "code_exists": False,
                "gst_no_exists": True,
                "pan_no_exists": False,
                ...
            }
        """
        try:
            validation_results = {
                "code_exists": await self.check_retailer_exists_by_code(
                    retailer_data.code
                ),
            }

            logger.debug(
                "Retailer unique fields validated",
                retailer_code=retailer_data.code,
                validation_results=validation_results,
                company_id=str(self.company_id),
            )

            return validation_results

        except Exception as e:
            logger.error(
                "Failed to validate retailer unique fields",
                retailer_code=retailer_data.code,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def verify_retailer(self, retailer_id: UUID) -> RetailerResponse:
        """
        Verify a retailer by setting is_verified to True.

        Args:
            retailer_id: ID of the retailer to verify

        Returns:
            Updated retailer

        Raises:
            RetailerNotFoundException: If retailer not found
            RetailerOperationException: If verification fails
        """
        try:
            logger.info(
                "Verifying retailer",
                retailer_id=str(retailer_id),
                company_id=str(self.company_id),
            )

            update_data = RetailerUpdate(is_verified=True)
            retailer = await self.repository.update_retailer(
                retailer_id, update_data
            )

            logger.info(
                "Retailer verified successfully",
                retailer_id=str(retailer_id),
                company_id=str(self.company_id),
            )

            return RetailerResponse(**retailer.model_dump())

        except RetailerNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to verify retailer in service",
                retailer_id=str(retailer_id),
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def unverify_retailer(self, retailer_id: UUID) -> RetailerResponse:
        """
        Unverify a retailer by setting is_verified to False.

        Args:
            retailer_id: ID of the retailer to unverify

        Returns:
            Updated retailer

        Raises:
            RetailerNotFoundException: If retailer not found
            RetailerOperationException: If unverification fails
        """
        try:
            logger.info(
                "Unverifying retailer",
                retailer_id=str(retailer_id),
                company_id=str(self.company_id),
            )

            update_data = RetailerUpdate(is_verified=False)
            retailer = await self.repository.update_retailer(
                retailer_id, update_data
            )

            logger.info(
                "Retailer unverified successfully",
                retailer_id=str(retailer_id),
                company_id=str(self.company_id),
            )

            return RetailerResponse(**retailer.model_dump())

        except RetailerNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to unverify retailer in service",
                retailer_id=str(retailer_id),
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def get_verified_retailers_count(
        self,
        route_id: Optional[int] = None,
        category_id: Optional[int] = None,
    ) -> int:
        """
        Get count of verified retailers, optionally filtered by route and category.

        Args:
            route_id: Optional filter by route ID
            category_id: Optional filter by category ID

        Returns:
            Count of verified retailers

        Raises:
            RetailerOperationException: If counting fails
        """
        try:
            logger.debug(
                "Getting verified retailers count",
                route_id=route_id,
                category_id=category_id,
                company_id=str(self.company_id),
            )

            # Get all active retailers and filter by is_verified
            retailers, _ = await self.list_retailers(
                route_id=route_id,
                category_id=category_id,
                is_active=True,
                limit=100,
                offset=0,
            )

            verified_count = sum(1 for r in retailers if r.is_verified)

            return verified_count

        except Exception as e:
            logger.error(
                "Failed to get verified retailers count in service",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

