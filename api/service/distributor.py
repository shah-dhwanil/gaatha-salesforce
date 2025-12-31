"""
Service layer for Distributor entity operations.

This service provides business logic for distributors, acting as an intermediary
between the API layer and the repository layer.
"""

from typing import Optional
from uuid import UUID

import structlog

from api.database import DatabasePool
from api.exceptions.distributor import (
    DistributorAlreadyExistsException,
    DistributorNotFoundException,
    DistributorOperationException,
    DistributorValidationException,
)
from api.models.distributor import (
    DistributorCreate,
    DistributorDetailItem,
    DistributorListItem,
    DistributorResponse,
    DistributorUpdate,
)
from api.models.user import UserCreate, UserUpdate
from api.repository.distributor import DistributorRepository
from api.repository.company import CompanyRepository
from api.repository.area import AreaRepository
from api.service.user import UserService

logger = structlog.get_logger(__name__)


class DistributorService:
    """
    Service for managing Distributor business logic.

    This service handles business logic, validation, and orchestration
    for distributor operations in a multi-tenant environment.
    """

    def __init__(self, db_pool: DatabasePool, company_id: UUID) -> None:
        """
        Initialize the DistributorService.

        Args:
            db_pool: Database pool instance for connection management
            company_id: UUID of the company (tenant) for schema isolation
        """
        self.db_pool = db_pool
        self.company_id = company_id
        self.repository = DistributorRepository(db_pool, company_id)
        self.company_repository = CompanyRepository(db_pool)
        self.area_repository = AreaRepository(db_pool, company_id)
        self.user_service = UserService(db_pool)
        logger.debug(
            "DistributorService initialized",
            company_id=str(company_id),
        )

    async def create_distributor(
        self, distributor_data: DistributorCreate
    ) -> DistributorResponse:
        """
        Create a new distributor.

        Args:
            distributor_data: Distributor data to create

        Returns:
            Created distributor

        Raises:
            DistributorAlreadyExistsException: If distributor with unique constraint already exists
            DistributorValidationException: If validation fails
            DistributorOperationException: If creation fails
        """
        user_data = None
        try:
            async with self.db_pool.acquire() as conn:
                serial_number = await self.repository.get_serial_number(conn)
                company = await self.company_repository.get_company_by_id(self.company_id)
                code = f"{company.name[:4].upper()}_DIST_{serial_number}"
                
                # Get area to validate and use in user creation
                area = await self.area_repository.get_area_by_id(distributor_data.area_id, conn)
                
                user = UserCreate(
                    username=code,
                    name=distributor_data.name,
                    contact_no=distributor_data.mobile_number,
                    company_id=self.company_id,
                    area_id=distributor_data.area_id,
                    role="DISTRIBUTOR",
                    is_super_admin=False,
                    bank_details=distributor_data.bank_details,
                )
                user_data = await self.user_service.create_user(user)
                distributor = await self.repository.create_distributor(
                    distributor_data, user_data.id, code, conn
                )
                logger.info(
                    "Distributor created successfully",
                    distributor_id=str(distributor.id),
                    distributor_name=distributor.name,
                    distributor_code=code,
                    company_id=str(self.company_id),
                )
                return DistributorResponse(**distributor.model_dump())
        except (DistributorAlreadyExistsException, DistributorValidationException) as e:
            if user_data is not None:
                await self.user_service.delete_user(user_data.id)
            logger.error(
                "Failed to create distributor in service",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise e
        except Exception as e:
            if user_data is not None:
                await self.user_service.delete_user(user_data.id)
            logger.error(
                "Failed to create distributor in service",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise DistributorOperationException(
                message=f"Failed to create distributor: {str(e)}",
                operation="create_distributor",
            ) from e

    async def get_distributor_by_id(self, distributor_id: UUID) -> DistributorDetailItem:
        """
        Get a distributor by ID with full details including joined data.

        Args:
            distributor_id: ID of the distributor

        Returns:
            Distributor with detailed information (including area_name, route details)

        Raises:
            DistributorNotFoundException: If distributor not found
            DistributorOperationException: If retrieval fails
        """
        try:
            logger.debug(
                "Getting distributor by ID",
                distributor_id=str(distributor_id),
                company_id=str(self.company_id),
            )

            distributor = await self.repository.get_distributor_by_id(distributor_id)

            return distributor

        except DistributorNotFoundException:
            logger.warning(
                "Distributor not found",
                distributor_id=str(distributor_id),
                company_id=str(self.company_id),
            )
            raise
        except Exception as e:
            logger.error(
                "Failed to get distributor in service",
                distributor_id=str(distributor_id),
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def get_distributor_by_code(self, code: str) -> DistributorDetailItem:
        """
        Get a distributor by code with full details including joined data.

        Args:
            code: Code of the distributor

        Returns:
            Distributor with detailed information (including area_name, route details)

        Raises:
            DistributorNotFoundException: If distributor not found
            DistributorOperationException: If retrieval fails
        """
        try:
            logger.debug(
                "Getting distributor by code",
                distributor_code=code,
                company_id=str(self.company_id),
            )

            distributor = await self.repository.get_distributor_by_code(code)

            return distributor

        except DistributorNotFoundException:
            logger.warning(
                "Distributor not found",
                distributor_code=code,
                company_id=str(self.company_id),
            )
            raise
        except Exception as e:
            logger.error(
                "Failed to get distributor by code in service",
                distributor_code=code,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def list_distributors(
        self,
        area_id: Optional[int] = None,
        is_active: Optional[bool] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[DistributorListItem], int]:
        """
        List all distributors with optional filtering and return total count.

        Returns optimized list view with fields: name, code, contact_person_name,
        mobile_number, address, area_name, area_id, route_count.

        Args:
            area_id: Filter by area ID
            is_active: Filter by active status
            limit: Maximum number of distributors to return (default: 20, max: 100)
            offset: Number of distributors to skip (default: 0)

        Returns:
            Tuple of (list of distributors with minimal data, total count)

        Raises:
            DistributorValidationException: If validation fails
            DistributorOperationException: If listing fails
        """
        try:
            logger.debug(
                "Listing distributors",
                area_id=area_id,
                is_active=is_active,
                limit=limit,
                offset=offset,
                company_id=str(self.company_id),
            )

            # Validate pagination parameters
            if limit < 1 or limit > 100:
                raise DistributorValidationException(
                    message="Limit must be between 1 and 100",
                    field="limit",
                    value=limit,
                )

            if offset < 0:
                raise DistributorValidationException(
                    message="Offset must be non-negative",
                    field="offset",
                    value=offset,
                )

            # Get distributors and count in parallel for better performance
            async with self.db_pool.acquire() as conn:
                distributors = await self.repository.list_distributors(
                    area_id=area_id,
                    is_active=is_active,
                    limit=limit,
                    offset=offset,
                    connection=conn,
                )
                total_count = await self.repository.count_distributors(
                    area_id=area_id,
                    is_active=is_active,
                    connection=conn,
                )

            logger.debug(
                "Distributors listed successfully",
                count=len(distributors),
                total_count=total_count,
                company_id=str(self.company_id),
            )

            return distributors, total_count

        except DistributorValidationException:
            raise
        except Exception as e:
            logger.error(
                "Failed to list distributors in service",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def update_distributor(
        self, distributor_id: UUID, distributor_data: DistributorUpdate
    ) -> DistributorResponse:
        """
        Update an existing distributor.

        Note: Distributor code cannot be updated (it's immutable).

        Args:
            distributor_id: ID of the distributor to update
            distributor_data: Distributor data to update

        Returns:
            Updated distributor

        Raises:
            DistributorNotFoundException: If distributor not found
            DistributorValidationException: If validation fails
            DistributorOperationException: If update fails
        """
        try:
            logger.info(
                "Updating distributor",
                distributor_id=str(distributor_id),
                company_id=str(self.company_id),
            )

            # Validate at least one field is provided for update
            if not any(
                [
                    distributor_data.name,
                    distributor_data.contact_person_name,
                    distributor_data.mobile_number,
                    distributor_data.email,
                    distributor_data.gst_no,
                    distributor_data.pan_no,
                    distributor_data.license_no,
                    distributor_data.address,
                    distributor_data.pin_code,
                    distributor_data.map_link,
                    distributor_data.vehicle_3 is not None,
                    distributor_data.vehicle_4 is not None,
                    distributor_data.salesman_count is not None,
                    distributor_data.area_id is not None,
                    distributor_data.for_general is not None,
                    distributor_data.for_modern is not None,
                    distributor_data.for_horeca is not None,
                ]
            ):
                raise DistributorValidationException(
                    message="At least one field must be provided for update",
                )
            
            # Update user data if mobile number or contact person name is changed
            if distributor_data.mobile_number is not None:
                await self.user_service.update_user(
                    distributor_id, 
                    UserUpdate(contact_no=distributor_data.mobile_number), 
                    self.company_id
                )
            if distributor_data.name is not None:
                await self.user_service.update_user(
                    distributor_id, 
                    UserUpdate(name=distributor_data.name), 
                    self.company_id
                )
            
            # Update distributor using repository
            distributor = await self.repository.update_distributor(
                distributor_id, distributor_data
            )

            logger.info(
                "Distributor updated successfully",
                distributor_id=str(distributor_id),
                company_id=str(self.company_id),
            )

            return DistributorResponse(**distributor.model_dump())

        except (DistributorNotFoundException, DistributorValidationException):
            raise
        except Exception as e:
            logger.error(
                "Failed to update distributor in service",
                distributor_id=str(distributor_id),
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def delete_distributor(self, distributor_id: UUID) -> None:
        """
        Soft delete a distributor by setting is_active to False.

        Args:
            distributor_id: ID of the distributor to delete

        Raises:
            DistributorNotFoundException: If distributor not found
            DistributorOperationException: If deletion fails
        """
        try:
            logger.info(
                "Deleting distributor",
                distributor_id=str(distributor_id),
                company_id=str(self.company_id),
            )

            # Soft delete distributor using repository
            await self.repository.delete_distributor(distributor_id)

            logger.info(
                "Distributor deleted successfully",
                distributor_id=str(distributor_id),
                company_id=str(self.company_id),
            )

        except DistributorNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to delete distributor in service",
                distributor_id=str(distributor_id),
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def add_distributor_route(
        self, distributor_id: UUID, route_id: int
    ) -> None:
        """
        Add a route to a distributor.

        Args:
            distributor_id: ID of the distributor
            route_id: ID of the route to add

        Raises:
            DistributorNotFoundException: If distributor not found
            DistributorOperationException: If operation fails
        """
        try:
            logger.info(
                "Adding route to distributor",
                distributor_id=str(distributor_id),
                route_id=route_id,
                company_id=str(self.company_id),
            )

            # Verify distributor exists
            await self.repository.get_distributor_by_id(distributor_id)

            # Add route to distributor
            await self.repository.add_distributor_route(distributor_id, route_id)

            logger.info(
                "Route added to distributor successfully",
                distributor_id=str(distributor_id),
                route_id=route_id,
                company_id=str(self.company_id),
            )

        except DistributorNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to add route to distributor in service",
                distributor_id=str(distributor_id),
                route_id=route_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def remove_distributor_route(
        self, distributor_id: UUID, route_id: int
    ) -> None:
        """
        Remove a route from a distributor.

        Args:
            distributor_id: ID of the distributor
            route_id: ID of the route to remove

        Raises:
            DistributorNotFoundException: If distributor not found
            DistributorOperationException: If operation fails
        """
        try:
            logger.info(
                "Removing route from distributor",
                distributor_id=str(distributor_id),
                route_id=route_id,
                company_id=str(self.company_id),
            )

            # Verify distributor exists
            await self.repository.get_distributor_by_id(distributor_id)

            # Remove route from distributor
            await self.repository.remove_distributor_route(distributor_id, route_id)

            logger.info(
                "Route removed from distributor successfully",
                distributor_id=str(distributor_id),
                route_id=route_id,
                company_id=str(self.company_id),
            )

        except DistributorNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to remove route from distributor in service",
                distributor_id=str(distributor_id),
                route_id=route_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def check_distributor_exists(self, distributor_id: UUID) -> bool:
        """
        Check if a distributor exists.

        Args:
            distributor_id: ID of the distributor to check

        Returns:
            True if distributor exists, False otherwise
        """
        try:
            await self.repository.get_distributor_by_id(distributor_id)
            return True
        except DistributorNotFoundException:
            return False

    async def check_distributor_exists_by_code(self, code: str) -> bool:
        """
        Check if a distributor exists by code.

        Args:
            code: Code of the distributor to check

        Returns:
            True if distributor exists, False otherwise
        """
        try:
            await self.repository.get_distributor_by_code(code)
            return True
        except DistributorNotFoundException:
            return False

    async def get_active_distributors_count(
        self,
        area_id: Optional[int] = None,
    ) -> int:
        """
        Get count of active distributors, optionally filtered by area.

        Args:
            area_id: Optional filter by area ID

        Returns:
            Count of active distributors

        Raises:
            DistributorOperationException: If counting fails
        """
        try:
            logger.debug(
                "Getting active distributors count",
                area_id=area_id,
                company_id=str(self.company_id),
            )

            count = await self.repository.count_distributors(
                area_id=area_id,
                is_active=True,
            )

            return count

        except Exception as e:
            logger.error(
                "Failed to get active distributors count in service",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def get_all_active_distributors_by_area(
        self, area_id: int
    ) -> list[DistributorListItem]:
        """
        Get all active distributors for an area without pagination.

        Args:
            area_id: ID of the area

        Returns:
            List of all active distributors for the area

        Raises:
            DistributorOperationException: If retrieval fails
        """
        try:
            logger.debug(
                "Getting all active distributors by area",
                area_id=area_id,
                company_id=str(self.company_id),
            )

            distributors = await self.repository.list_distributors(
                area_id=area_id,
                is_active=True,
                limit=100,
                offset=0,
            )

            return distributors

        except Exception as e:
            logger.error(
                "Failed to get all active distributors by area in service",
                area_id=area_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def validate_distributor_unique_fields(
        self, distributor_data: DistributorCreate
    ) -> dict[str, bool]:
        """
        Validate if distributor unique fields already exist.

        This is a helper method for bulk validation before creating distributors.

        Args:
            distributor_data: Distributor data to validate

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
            # Generate code to check
            company = await self.company_repository.get_company_by_id(self.company_id)
            async with self.db_pool.acquire() as conn:
                serial_number = await self.repository.get_serial_number(conn)
            code = f"{company.name[:4].upper()}_DIST_{serial_number}"
            
            validation_results = {
                "code_exists": await self.check_distributor_exists_by_code(code),
            }

            logger.debug(
                "Distributor unique fields validated",
                validation_results=validation_results,
                company_id=str(self.company_id),
            )

            return validation_results

        except Exception as e:
            logger.error(
                "Failed to validate distributor unique fields",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def get_distributors_by_trade_type(
        self,
        for_general: Optional[bool] = None,
        for_modern: Optional[bool] = None,
        for_horeca: Optional[bool] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[DistributorListItem], int]:
        """
        Get distributors filtered by trade types.

        Note: This is a specialized query that requires additional filtering.
        For now, we get all distributors and filter in-memory.
        In production, this should be moved to the repository layer.

        Args:
            for_general: Filter by general trade flag
            for_modern: Filter by modern trade flag
            for_horeca: Filter by HORECA trade flag
            limit: Maximum number of distributors to return
            offset: Number of distributors to skip

        Returns:
            Tuple of (list of distributors, total count)

        Raises:
            DistributorValidationException: If validation fails
            DistributorOperationException: If retrieval fails
        """
        try:
            logger.debug(
                "Getting distributors by trade type",
                for_general=for_general,
                for_modern=for_modern,
                for_horeca=for_horeca,
                company_id=str(self.company_id),
            )

            # Get all active distributors
            all_distributors, total = await self.list_distributors(
                is_active=True,
                limit=100,
                offset=0,
            )

            # Filter by trade types
            filtered_distributors = []
            for dist_item in all_distributors:
                # Get full details to access trade flags
                dist = await self.repository.get_distributor_by_id(dist_item.id)
                
                match = True
                if for_general is not None and dist.for_general != for_general:
                    match = False
                if for_modern is not None and dist.for_modern != for_modern:
                    match = False
                if for_horeca is not None and dist.for_horeca != for_horeca:
                    match = False
                
                if match:
                    filtered_distributors.append(dist_item)

            # Apply pagination
            paginated = filtered_distributors[offset:offset + limit]
            
            return paginated, len(filtered_distributors)

        except Exception as e:
            logger.error(
                "Failed to get distributors by trade type in service",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

