"""
Service layer for RouteLog entity operations.

This service provides business logic for route logs, acting as an intermediary
between the API layer and the repository layer.
"""

from datetime import date
from typing import Optional
from uuid import UUID

import structlog

from api.database import DatabasePool
from api.exceptions.route_log import (
    RouteLogNotFoundException,
    RouteLogOperationException,
    RouteLogValidationException,
)
from api.models.route_log import (
    RouteLogCreate,
    RouteLogListItem,
    RouteLogResponse,
    RouteLogUpdate,
)
from api.repository.route_log import RouteLogRepository

logger = structlog.get_logger(__name__)


class RouteLogService:
    """
    Service for managing RouteLog business logic.

    This service handles business logic, validation, and orchestration
    for route log operations in a multi-tenant environment.
    """

    def __init__(self, db_pool: DatabasePool, company_id: UUID) -> None:
        """
        Initialize the RouteLogService.

        Args:
            db_pool: Database pool instance for connection management
            company_id: UUID of the company (tenant) for schema isolation
        """
        self.db_pool = db_pool
        self.company_id = company_id
        self.repository = RouteLogRepository(db_pool, company_id)
        logger.debug(
            "RouteLogService initialized",
            company_id=str(company_id),
        )

    async def create_route_log(
        self, route_log_data: RouteLogCreate
    ) -> RouteLogResponse:
        """
        Create a new route log.

        Args:
            route_log_data: Route log data to create

        Returns:
            Created route log

        Raises:
            RouteLogValidationException: If validation fails
            RouteLogOperationException: If creation fails
        """
        try:
            logger.info(
                "Creating route log",
                route_assignment_id=route_log_data.route_assignment_id,
                co_worker_id=str(route_log_data.co_worker_id)
                if route_log_data.co_worker_id
                else None,
                date=str(route_log_data.date),
                company_id=str(self.company_id),
            )

            # Additional business logic validation
            if (
                route_log_data.end_time
                and route_log_data.end_time <= route_log_data.start_time
            ):
                raise RouteLogValidationException(
                    message="End time must be after start time",
                    field="end_time",
                    value=str(route_log_data.end_time),
                )

            # Create route log using repository
            route_log = await self.repository.create_route_log(route_log_data)

            logger.info(
                "Route log created successfully",
                route_log_id=route_log.id,
                route_assignment_id=route_log.route_assignment_id,
                date=str(route_log.date),
                company_id=str(self.company_id),
            )

            return RouteLogResponse(**route_log.model_dump())

        except (
            RouteLogValidationException,
            RouteLogOperationException,
        ):
            raise
        except Exception as e:
            logger.error(
                "Failed to create route log in service",
                route_assignment_id=route_log_data.route_assignment_id,
                date=str(route_log_data.date),
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RouteLogOperationException(
                message=f"Failed to create route log: {str(e)}",
                operation="create",
            ) from e

    async def get_route_log_by_id(self, route_log_id: int) -> RouteLogResponse:
        """
        Get a route log by ID.

        Args:
            route_log_id: ID of the route log

        Returns:
            Route log with detailed information

        Raises:
            RouteLogNotFoundException: If route log not found
            RouteLogOperationException: If retrieval fails
        """
        try:
            logger.debug(
                "Getting route log by ID",
                route_log_id=route_log_id,
                company_id=str(self.company_id),
            )

            route_log = await self.repository.get_route_log_by_id(route_log_id)

            return RouteLogResponse(**route_log.model_dump())

        except RouteLogNotFoundException:
            logger.warning(
                "Route log not found",
                route_log_id=route_log_id,
                company_id=str(self.company_id),
            )
            raise
        except Exception as e:
            logger.error(
                "Failed to get route log in service",
                route_log_id=route_log_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RouteLogOperationException(
                message=f"Failed to get route log: {str(e)}",
                operation="get",
            ) from e

    async def list_route_logs(
        self,
        route_assignment_id: Optional[int] = None,
        co_worker_id: Optional[UUID] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[RouteLogListItem], int]:
        """
        List all route logs with optional filtering and return total count.

        Args:
            route_assignment_id: Filter by route assignment ID
            co_worker_id: Filter by co-worker ID
            date_from: Filter by start date (inclusive)
            date_to: Filter by end date (inclusive)
            limit: Maximum number of route logs to return (default: 20, max: 100)
            offset: Number of route logs to skip (default: 0)

        Returns:
            Tuple of (list of route logs with minimal data, total count)

        Raises:
            RouteLogValidationException: If validation fails
            RouteLogOperationException: If listing fails
        """
        try:
            logger.debug(
                "Listing route logs",
                route_assignment_id=route_assignment_id,
                co_worker_id=str(co_worker_id) if co_worker_id else None,
                date_from=str(date_from) if date_from else None,
                date_to=str(date_to) if date_to else None,
                limit=limit,
                offset=offset,
                company_id=str(self.company_id),
            )

            # Validate pagination parameters
            if limit < 1 or limit > 100:
                raise RouteLogValidationException(
                    message="Limit must be between 1 and 100",
                    field="limit",
                    value=limit,
                )

            if offset < 0:
                raise RouteLogValidationException(
                    message="Offset must be non-negative",
                    field="offset",
                    value=offset,
                )

            # Validate date range
            if date_from and date_to and date_to < date_from:
                raise RouteLogValidationException(
                    message="End date must be greater than or equal to start date",
                    field="date_to",
                    value=str(date_to),
                )

            # Get route logs and count in parallel for better performance
            async with self.db_pool.acquire() as conn:
                route_logs = await self.repository.list_route_logs(
                    route_assignment_id=route_assignment_id,
                    co_worker_id=co_worker_id,
                    date_from=date_from,
                    date_to=date_to,
                    limit=limit,
                    offset=offset,
                    connection=conn,
                )
                total_count = await self.repository.count_route_logs(
                    route_assignment_id=route_assignment_id,
                    co_worker_id=co_worker_id,
                    date_from=date_from,
                    date_to=date_to,
                    connection=conn,
                )

            logger.debug(
                "Route logs listed successfully",
                count=len(route_logs),
                total_count=total_count,
                company_id=str(self.company_id),
            )

            return route_logs, total_count

        except RouteLogValidationException:
            raise
        except Exception as e:
            logger.error(
                "Failed to list route logs in service",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RouteLogOperationException(
                message=f"Failed to list route logs: {str(e)}",
                operation="list",
            ) from e

    async def update_route_log(
        self, route_log_id: int, route_log_data: RouteLogUpdate
    ) -> RouteLogResponse:
        """
        Update an existing route log.

        Note: Route assignment ID cannot be updated.

        Args:
            route_log_id: ID of the route log to update
            route_log_data: Route log data to update

        Returns:
            Updated route log

        Raises:
            RouteLogNotFoundException: If route log not found
            RouteLogValidationException: If validation fails
            RouteLogOperationException: If update fails
        """
        try:
            logger.info(
                "Updating route log",
                route_log_id=route_log_id,
                company_id=str(self.company_id),
            )

            # Validate at least one field is provided
            if not any(
                [
                    route_log_data.co_worker_id is not None,
                    route_log_data.date is not None,
                    route_log_data.start_time is not None,
                    route_log_data.end_time is not None,
                ]
            ):
                raise RouteLogValidationException(
                    message="At least one field must be provided for update",
                )

            # Additional business logic validation for time range
            if route_log_data.start_time and route_log_data.end_time:
                if route_log_data.end_time <= route_log_data.start_time:
                    raise RouteLogValidationException(
                        message="End time must be after start time",
                        field="end_time",
                        value=str(route_log_data.end_time),
                    )

            # Update route log using repository
            route_log = await self.repository.update_route_log(
                route_log_id, route_log_data
            )

            logger.info(
                "Route log updated successfully",
                route_log_id=route_log_id,
                company_id=str(self.company_id),
            )

            return RouteLogResponse(**route_log.model_dump())

        except (
            RouteLogNotFoundException,
            RouteLogValidationException,
            RouteLogOperationException,
        ):
            raise
        except Exception as e:
            logger.error(
                "Failed to update route log in service",
                route_log_id=route_log_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RouteLogOperationException(
                message=f"Failed to update route log: {str(e)}",
                operation="update",
            ) from e

    async def delete_route_log(self, route_log_id: int) -> None:
        """
        Delete a route log.

        Args:
            route_log_id: ID of the route log to delete

        Raises:
            RouteLogNotFoundException: If route log not found
            RouteLogOperationException: If deletion fails
        """
        try:
            logger.info(
                "Deleting route log",
                route_log_id=route_log_id,
                company_id=str(self.company_id),
            )

            # Delete route log using repository
            await self.repository.delete_route_log(route_log_id)

            logger.info(
                "Route log deleted successfully",
                route_log_id=route_log_id,
                company_id=str(self.company_id),
            )

        except RouteLogNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to delete route log in service",
                route_log_id=route_log_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RouteLogOperationException(
                message=f"Failed to delete route log: {str(e)}",
                operation="delete",
            ) from e

    async def get_route_logs_by_route_assignment(
        self, route_assignment_id: int
    ) -> list[RouteLogListItem]:
        """
        Get all route logs for a specific route assignment.

        Args:
            route_assignment_id: ID of the route assignment

        Returns:
            List of route logs

        Raises:
            RouteLogOperationException: If retrieval fails
        """
        try:
            logger.debug(
                "Getting route logs by route assignment",
                route_assignment_id=route_assignment_id,
                company_id=str(self.company_id),
            )

            route_logs = await self.repository.get_route_logs_by_route_assignment(
                route_assignment_id=route_assignment_id,
            )

            logger.debug(
                "Route logs retrieved successfully",
                route_assignment_id=route_assignment_id,
                count=len(route_logs),
                company_id=str(self.company_id),
            )

            return route_logs

        except Exception as e:
            logger.error(
                "Failed to get route logs by route assignment in service",
                route_assignment_id=route_assignment_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RouteLogOperationException(
                message=f"Failed to get route logs by route assignment: {str(e)}",
                operation="get_by_route_assignment",
            ) from e

    async def check_route_log_exists(self, route_log_id: int) -> bool:
        """
        Check if a route log exists.

        Args:
            route_log_id: ID of the route log to check

        Returns:
            True if route log exists, False otherwise
        """
        try:
            await self.repository.get_route_log_by_id(route_log_id)
            return True
        except RouteLogNotFoundException:
            return False

    async def get_route_logs_count(
        self,
        route_assignment_id: Optional[int] = None,
        co_worker_id: Optional[UUID] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> int:
        """
        Get count of route logs, optionally filtered.

        Args:
            route_assignment_id: Optional filter by route assignment ID
            co_worker_id: Optional filter by co-worker ID
            date_from: Optional filter by start date (inclusive)
            date_to: Optional filter by end date (inclusive)

        Returns:
            Count of route logs

        Raises:
            RouteLogOperationException: If counting fails
        """
        try:
            logger.debug(
                "Getting route logs count",
                route_assignment_id=route_assignment_id,
                co_worker_id=str(co_worker_id) if co_worker_id else None,
                date_from=str(date_from) if date_from else None,
                date_to=str(date_to) if date_to else None,
                company_id=str(self.company_id),
            )

            count = await self.repository.count_route_logs(
                route_assignment_id=route_assignment_id,
                co_worker_id=co_worker_id,
                date_from=date_from,
                date_to=date_to,
            )

            return count

        except Exception as e:
            logger.error(
                "Failed to get route logs count in service",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RouteLogOperationException(
                message=f"Failed to get route logs count: {str(e)}",
                operation="count",
            ) from e

    async def get_route_logs_by_co_worker(
        self,
        co_worker_id: UUID,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> list[RouteLogListItem]:
        """
        Get all route logs for a specific co-worker, optionally filtered by date range.

        Args:
            co_worker_id: ID of the co-worker
            date_from: Optional filter by start date (inclusive)
            date_to: Optional filter by end date (inclusive)

        Returns:
            List of route logs

        Raises:
            RouteLogOperationException: If retrieval fails
        """
        try:
            logger.debug(
                "Getting route logs by co-worker",
                co_worker_id=str(co_worker_id),
                date_from=str(date_from) if date_from else None,
                date_to=str(date_to) if date_to else None,
                company_id=str(self.company_id),
            )

            route_logs = await self.repository.list_route_logs(
                co_worker_id=co_worker_id,
                date_from=date_from,
                date_to=date_to,
                limit=1000,  # High limit to get all logs for a co-worker
                offset=0,
            )

            logger.debug(
                "Route logs retrieved successfully",
                co_worker_id=str(co_worker_id),
                count=len(route_logs),
                company_id=str(self.company_id),
            )

            return route_logs

        except Exception as e:
            logger.error(
                "Failed to get route logs by co-worker in service",
                co_worker_id=str(co_worker_id),
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RouteLogOperationException(
                message=f"Failed to get route logs by co-worker: {str(e)}",
                operation="get_by_co_worker",
            ) from e

    async def get_route_logs_by_date_range(
        self, date_from: date, date_to: date
    ) -> list[RouteLogListItem]:
        """
        Get all route logs within a specific date range.

        Args:
            date_from: Start date (inclusive)
            date_to: End date (inclusive)

        Returns:
            List of route logs

        Raises:
            RouteLogValidationException: If date range is invalid
            RouteLogOperationException: If retrieval fails
        """
        try:
            # Validate date range
            if date_to < date_from:
                raise RouteLogValidationException(
                    message="End date must be greater than or equal to start date",
                    field="date_to",
                    value=str(date_to),
                )

            logger.debug(
                "Getting route logs by date range",
                date_from=str(date_from),
                date_to=str(date_to),
                company_id=str(self.company_id),
            )

            route_logs = await self.repository.list_route_logs(
                date_from=date_from,
                date_to=date_to,
                limit=1000,  # High limit to get all logs in the date range
                offset=0,
            )

            logger.debug(
                "Route logs retrieved successfully",
                date_from=str(date_from),
                date_to=str(date_to),
                count=len(route_logs),
                company_id=str(self.company_id),
            )

            return route_logs

        except RouteLogValidationException:
            raise
        except Exception as e:
            logger.error(
                "Failed to get route logs by date range in service",
                date_from=str(date_from),
                date_to=str(date_to),
                error=str(e),
                company_id=str(self.company_id),
            )
            raise RouteLogOperationException(
                message=f"Failed to get route logs by date range: {str(e)}",
                operation="get_by_date_range",
            ) from e
