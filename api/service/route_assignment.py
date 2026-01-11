"""
Service layer for RouteAssignment entity operations.

This service provides business logic for route assignments, acting as an intermediary
between the API layer and the repository layer.
"""

from datetime import date
from typing import Optional
from uuid import UUID

import structlog

from api.database import DatabasePool
from api.exceptions.route_assignment import (
    InvalidDateRangeException,
    RouteAssignmentAlreadyExistsException,
    RouteAssignmentNotFoundException,
    RouteAssignmentOperationException,
)
from api.models.route_assignment import (
    RouteAssignmentCreate,
    RouteAssignmentDetailItem,
    RouteAssignmentListItem,
    RouteAssignmentResponse,
    RouteAssignmentUpdate,
)
from api.repository.route_assignment import RouteAssignmentRepository

logger = structlog.get_logger(__name__)


class RouteAssignmentService:
    """
    Service for managing RouteAssignment business logic.

    This service handles business logic, validation, and orchestration
    for route assignment operations in a multi-tenant environment.
    """

    def __init__(self, db_pool: DatabasePool, company_id: UUID) -> None:
        """
        Initialize the RouteAssignmentService.

        Args:
            db_pool: Database pool instance for connection management
            company_id: UUID of the company (tenant) for schema isolation
        """
        self.db_pool = db_pool
        self.company_id = company_id
        self.repository = RouteAssignmentRepository(db_pool, company_id)
        logger.debug(
            "RouteAssignmentService initialized",
            company_id=str(company_id),
        )

    async def create_route_assignment(
        self, assignment_data: RouteAssignmentCreate
    ) -> RouteAssignmentResponse:
        """
        Create a new route assignment.

        Args:
            assignment_data: Route assignment data to create

        Returns:
            Created route assignment

        Raises:
            RouteAssignmentAlreadyExistsException: If active assignment already exists
            InvalidDateRangeException: If date range is invalid
            RouteAssignmentOperationException: If creation fails
        """
        try:
            logger.info(
                "Creating route assignment",
                route_id=assignment_data.route_id,
                user_id=str(assignment_data.user_id),
                from_date=str(assignment_data.from_date),
                day=assignment_data.day,
                company_id=str(self.company_id),
            )

            # Additional business logic validation
            if (
                assignment_data.to_date
                and assignment_data.to_date < assignment_data.from_date
            ):
                raise InvalidDateRangeException(
                    message="End date must be greater than or equal to start date"
                )

            # Create route assignment using repository
            assignment = await self.repository.create_route_assignment(assignment_data)

            logger.info(
                "Route assignment created successfully",
                assignment_id=assignment.id,
                route_id=assignment.route_id,
                user_id=str(assignment.user_id),
                company_id=str(self.company_id),
            )

            return RouteAssignmentResponse(**assignment.model_dump())

        except (
            RouteAssignmentAlreadyExistsException,
            InvalidDateRangeException,
            RouteAssignmentOperationException,
        ):
            raise
        except Exception as e:
            logger.error(
                "Failed to create route assignment in service",
                route_id=assignment_data.route_id,
                user_id=str(assignment_data.user_id),
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RouteAssignmentOperationException(
                message=f"Failed to create route assignment: {str(e)}",
                operation="create",
            ) from e

    async def get_route_assignment_by_id(
        self, assignment_id: int
    ) -> RouteAssignmentDetailItem:
        """
        Get a route assignment by ID with full details.

        Args:
            assignment_id: ID of the route assignment

        Returns:
            Route assignment with detailed information

        Raises:
            RouteAssignmentNotFoundException: If route assignment not found
            RouteAssignmentOperationException: If retrieval fails
        """
        try:
            logger.debug(
                "Getting route assignment by ID",
                assignment_id=assignment_id,
                company_id=str(self.company_id),
            )

            assignment = await self.repository.get_route_assignment_by_id(assignment_id)

            return assignment

        except RouteAssignmentNotFoundException:
            logger.warning(
                "Route assignment not found",
                assignment_id=assignment_id,
                company_id=str(self.company_id),
            )
            raise
        except Exception as e:
            logger.error(
                "Failed to get route assignment in service",
                assignment_id=assignment_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RouteAssignmentOperationException(
                message=f"Failed to get route assignment: {str(e)}",
                operation="get",
            ) from e

    async def list_route_assignments(
        self,
        route_id: Optional[int] = None,
        user_id: Optional[UUID] = None,
        day: Optional[int] = None,
        is_active: Optional[bool] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[RouteAssignmentListItem], int]:
        """
        List all route assignments with optional filtering and return total count.

        Args:
            route_id: Filter by route ID
            user_id: Filter by user ID
            day: Filter by day of week (0=Monday, 6=Sunday)
            is_active: Filter by active status
            from_date: Filter by assignments starting from this date
            to_date: Filter by assignments ending before this date
            limit: Maximum number of assignments to return (default: 20, max: 100)
            offset: Number of assignments to skip (default: 0)

        Returns:
            Tuple of (list of route assignments with minimal data, total count)

        Raises:
            RouteAssignmentOperationException: If listing fails
        """
        try:
            logger.debug(
                "Listing route assignments",
                route_id=route_id,
                user_id=str(user_id) if user_id else None,
                day=day,
                is_active=is_active,
                from_date=str(from_date) if from_date else None,
                to_date=str(to_date) if to_date else None,
                limit=limit,
                offset=offset,
                company_id=str(self.company_id),
            )

            # Validate pagination parameters
            if limit < 1 or limit > 100:
                raise RouteAssignmentOperationException(
                    message="Limit must be between 1 and 100",
                    operation="list",
                )

            if offset < 0:
                raise RouteAssignmentOperationException(
                    message="Offset must be non-negative",
                    operation="list",
                )

            # Validate day if provided
            if day is not None and (day < 0 or day > 6):
                raise RouteAssignmentOperationException(
                    message="Day must be between 0 (Monday) and 6 (Sunday)",
                    operation="list",
                )

            # Get assignments and count in parallel for better performance
            async with self.db_pool.acquire() as conn:
                assignments = await self.repository.list_route_assignments(
                    route_id=route_id,
                    user_id=user_id,
                    day=day,
                    is_active=is_active,
                    from_date=from_date,
                    to_date=to_date,
                    limit=limit,
                    offset=offset,
                    connection=conn,
                )
                total_count = await self.repository.count_route_assignments(
                    route_id=route_id,
                    user_id=user_id,
                    day=day,
                    is_active=is_active,
                    from_date=from_date,
                    to_date=to_date,
                    connection=conn,
                )

            logger.debug(
                "Route assignments listed successfully",
                count=len(assignments),
                total_count=total_count,
                company_id=str(self.company_id),
            )

            return assignments, total_count

        except RouteAssignmentOperationException:
            raise
        except Exception as e:
            logger.error(
                "Failed to list route assignments in service",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RouteAssignmentOperationException(
                message=f"Failed to list route assignments: {str(e)}",
                operation="list",
            ) from e

    async def update_route_assignment(
        self, assignment_id: int, assignment_data: RouteAssignmentUpdate
    ) -> RouteAssignmentResponse:
        """
        Update an existing route assignment.

        Note: Route ID and User ID cannot be updated.

        Args:
            assignment_id: ID of the route assignment to update
            assignment_data: Route assignment data to update

        Returns:
            Updated route assignment

        Raises:
            RouteAssignmentNotFoundException: If route assignment not found
            InvalidDateRangeException: If date range is invalid
            RouteAssignmentOperationException: If update fails
        """
        try:
            logger.info(
                "Updating route assignment",
                assignment_id=assignment_id,
                company_id=str(self.company_id),
            )

            # Validate at least one field is provided
            if not any(
                [
                    assignment_data.from_date is not None,
                    assignment_data.to_date is not None,
                    assignment_data.day is not None,
                ]
            ):
                raise RouteAssignmentOperationException(
                    message="At least one field must be provided for update",
                    operation="update",
                )

            # Additional business logic validation for date range
            if assignment_data.from_date and assignment_data.to_date:
                if assignment_data.to_date < assignment_data.from_date:
                    raise InvalidDateRangeException(
                        message="End date must be greater than or equal to start date"
                    )

            # Update route assignment using repository
            assignment = await self.repository.update_route_assignment(
                assignment_id, assignment_data
            )

            logger.info(
                "Route assignment updated successfully",
                assignment_id=assignment_id,
                company_id=str(self.company_id),
            )

            return RouteAssignmentResponse(**assignment.model_dump())

        except (
            RouteAssignmentNotFoundException,
            InvalidDateRangeException,
            RouteAssignmentOperationException,
        ):
            raise
        except Exception as e:
            logger.error(
                "Failed to update route assignment in service",
                assignment_id=assignment_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RouteAssignmentOperationException(
                message=f"Failed to update route assignment: {str(e)}",
                operation="update",
            ) from e

    async def delete_route_assignment(self, assignment_id: int) -> None:
        """
        Soft delete a route assignment by setting is_active to False.

        Args:
            assignment_id: ID of the route assignment to delete

        Raises:
            RouteAssignmentNotFoundException: If route assignment not found
            RouteAssignmentOperationException: If deletion fails
        """
        try:
            logger.info(
                "Deleting route assignment",
                assignment_id=assignment_id,
                company_id=str(self.company_id),
            )

            # Soft delete route assignment using repository
            await self.repository.delete_route_assignment(assignment_id)

            logger.info(
                "Route assignment deleted successfully",
                assignment_id=assignment_id,
                company_id=str(self.company_id),
            )

        except RouteAssignmentNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to delete route assignment in service",
                assignment_id=assignment_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RouteAssignmentOperationException(
                message=f"Failed to delete route assignment: {str(e)}",
                operation="delete",
            ) from e

    async def get_assignments_by_route(
        self, route_id: int, is_active: Optional[bool] = True
    ) -> list[RouteAssignmentListItem]:
        """
        Get all assignments for a specific route.

        Args:
            route_id: ID of the route
            is_active: Filter by active status (defaults to True)

        Returns:
            List of route assignments

        Raises:
            RouteAssignmentOperationException: If retrieval fails
        """
        try:
            logger.debug(
                "Getting assignments by route",
                route_id=route_id,
                is_active=is_active,
                company_id=str(self.company_id),
            )

            assignments = await self.repository.get_assignments_by_route(
                route_id=route_id,
                is_active=is_active,
            )

            logger.debug(
                "Assignments retrieved successfully",
                route_id=route_id,
                count=len(assignments),
                company_id=str(self.company_id),
            )

            return assignments

        except Exception as e:
            logger.error(
                "Failed to get assignments by route in service",
                route_id=route_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RouteAssignmentOperationException(
                message=f"Failed to get assignments by route: {str(e)}",
                operation="get_by_route",
            ) from e

    async def get_assignments_by_user(
        self, user_id: UUID, is_active: Optional[bool] = True
    ) -> list[RouteAssignmentListItem]:
        """
        Get all assignments for a specific user.

        Args:
            user_id: ID of the user
            is_active: Filter by active status (defaults to True)

        Returns:
            List of route assignments

        Raises:
            RouteAssignmentOperationException: If retrieval fails
        """
        try:
            logger.debug(
                "Getting assignments by user",
                user_id=str(user_id),
                is_active=is_active,
                company_id=str(self.company_id),
            )

            assignments = await self.repository.get_assignments_by_user(
                user_id=user_id,
                is_active=is_active,
            )

            logger.debug(
                "Assignments retrieved successfully",
                user_id=str(user_id),
                count=len(assignments),
                company_id=str(self.company_id),
            )

            return assignments

        except Exception as e:
            logger.error(
                "Failed to get assignments by user in service",
                user_id=str(user_id),
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RouteAssignmentOperationException(
                message=f"Failed to get assignments by user: {str(e)}",
                operation="get_by_user",
            ) from e

    async def check_assignment_exists(self, assignment_id: int) -> bool:
        """
        Check if a route assignment exists.

        Args:
            assignment_id: ID of the route assignment to check

        Returns:
            True if route assignment exists, False otherwise
        """
        try:
            await self.repository.get_route_assignment_by_id(assignment_id)
            return True
        except RouteAssignmentNotFoundException:
            return False

    async def get_active_assignments_count(
        self,
        route_id: Optional[int] = None,
        user_id: Optional[UUID] = None,
        day: Optional[int] = None,
    ) -> int:
        """
        Get count of active route assignments, optionally filtered.

        Args:
            route_id: Optional filter by route ID
            user_id: Optional filter by user ID
            day: Optional filter by day of week

        Returns:
            Count of active route assignments

        Raises:
            RouteAssignmentOperationException: If counting fails
        """
        try:
            logger.debug(
                "Getting active assignments count",
                route_id=route_id,
                user_id=str(user_id) if user_id else None,
                day=day,
                company_id=str(self.company_id),
            )

            count = await self.repository.count_route_assignments(
                route_id=route_id,
                user_id=user_id,
                day=day,
                is_active=True,
            )

            return count

        except Exception as e:
            logger.error(
                "Failed to get active assignments count in service",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RouteAssignmentOperationException(
                message=f"Failed to get active assignments count: {str(e)}",
                operation="count",
            ) from e

    async def get_assignments_by_day(
        self, day: int, is_active: Optional[bool] = True
    ) -> list[RouteAssignmentListItem]:
        """
        Get all assignments for a specific day of the week.

        Args:
            day: Day of week (0=Monday, 6=Sunday)
            is_active: Filter by active status (defaults to True)

        Returns:
            List of route assignments

        Raises:
            RouteAssignmentOperationException: If retrieval fails or day is invalid
        """
        try:
            # Validate day
            if day < 0 or day > 6:
                raise RouteAssignmentOperationException(
                    message="Day must be between 0 (Monday) and 6 (Sunday)",
                    operation="get_by_day",
                )

            logger.debug(
                "Getting assignments by day",
                day=day,
                is_active=is_active,
                company_id=str(self.company_id),
            )

            assignments = await self.repository.list_route_assignments(
                day=day,
                is_active=is_active,
                limit=1000,  # High limit to get all assignments for a day
                offset=0,
            )

            logger.debug(
                "Assignments retrieved successfully",
                day=day,
                count=len(assignments),
                company_id=str(self.company_id),
            )

            return assignments

        except RouteAssignmentOperationException:
            raise
        except Exception as e:
            logger.error(
                "Failed to get assignments by day in service",
                day=day,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RouteAssignmentOperationException(
                message=f"Failed to get assignments by day: {str(e)}",
                operation="get_by_day",
            ) from e
