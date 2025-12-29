"""
Service layer for Route entity operations.

This service provides business logic for routes, acting as an intermediary
between the API layer and the repository layer.
"""

from typing import Optional
from uuid import UUID

import structlog

from api.database import DatabasePool
from api.exceptions.route import (
    RouteAlreadyExistsException,
    RouteNotFoundException,
    RouteOperationException,
    RouteValidationException,
)
from api.models.route import (
    RouteCreate,
    RouteDetailItem,
    RouteListItem,
    RouteResponse,
    RouteUpdate,
)
from api.repository.route import RouteRepository

logger = structlog.get_logger(__name__)


class RouteService:
    """
    Service for managing Route business logic.

    This service handles business logic, validation, and orchestration
    for route operations in a multi-tenant environment.
    """

    def __init__(self, db_pool: DatabasePool, company_id: UUID) -> None:
        """
        Initialize the RouteService.

        Args:
            db_pool: Database pool instance for connection management
            company_id: UUID of the company (tenant) for schema isolation
        """
        self.db_pool = db_pool
        self.company_id = company_id
        self.repository = RouteRepository(db_pool, company_id)
        logger.debug(
            "RouteService initialized",
            company_id=str(company_id),
        )

    async def create_route(self, route_data: RouteCreate) -> RouteResponse:
        """
        Create a new route.

        Args:
            route_data: Route data to create

        Returns:
            Created route

        Raises:
            RouteAlreadyExistsException: If route with the same code already exists
            RouteOperationException: If creation fails
        """
        try:
            logger.info(
                "Creating route",
                route_name=route_data.name,
                route_code=route_data.code,
                area_id=route_data.area_id,
                company_id=str(self.company_id),
            )

            # Create route using repository
            route = await self.repository.create_route(route_data)

            logger.info(
                "Route created successfully",
                route_id=route.id,
                route_name=route.name,
                route_code=route.code,
                company_id=str(self.company_id),
            )

            return RouteResponse(**route.model_dump())

        except (RouteAlreadyExistsException, RouteOperationException):
            raise
        except Exception as e:
            logger.error(
                "Failed to create route in service",
                route_name=route_data.name,
                route_code=route_data.code,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def get_route_by_id(self, route_id: int) -> RouteDetailItem:
        """
        Get a route by ID with full hierarchical details.

        Args:
            route_id: ID of the route

        Returns:
            Route with detailed information

        Raises:
            RouteNotFoundException: If route not found
            RouteOperationException: If retrieval fails
        """
        try:
            logger.debug(
                "Getting route by ID",
                route_id=route_id,
                company_id=str(self.company_id),
            )

            route = await self.repository.get_route_by_id(route_id)

            return route

        except RouteNotFoundException:
            logger.warning(
                "Route not found",
                route_id=route_id,
                company_id=str(self.company_id),
            )
            raise
        except Exception as e:
            logger.error(
                "Failed to get route in service",
                route_id=route_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def get_route_by_code(self, code: str) -> RouteDetailItem:
        """
        Get a route by code with full hierarchical details.

        Args:
            code: Code of the route

        Returns:
            Route with detailed information

        Raises:
            RouteNotFoundException: If route not found
            RouteOperationException: If retrieval fails
        """
        try:
            logger.debug(
                "Getting route by code",
                route_code=code,
                company_id=str(self.company_id),
            )

            route = await self.repository.get_route_by_code(code)

            return route

        except RouteNotFoundException:
            logger.warning(
                "Route not found",
                route_code=code,
                company_id=str(self.company_id),
            )
            raise
        except Exception as e:
            logger.error(
                "Failed to get route by code in service",
                route_code=code,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def list_routes(
        self,
        area_id: Optional[int] = None,
        is_active: Optional[bool] = None,
        is_general: Optional[bool] = None,
        is_modern: Optional[bool] = None,
        is_horeca: Optional[bool] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[RouteListItem], int]:
        """
        List all routes with optional filtering and return total count.

        Args:
            area_id: Filter by area ID
            is_active: Filter by active status
            is_general: Filter by general status
            is_modern: Filter by modern status
            is_horeca: Filter by horeca status
            limit: Maximum number of routes to return (default: 20, max: 100)
            offset: Number of routes to skip (default: 0)

        Returns:
            Tuple of (list of routes with minimal data, total count)

        Raises:
            RouteValidationException: If validation fails
            RouteOperationException: If listing fails
        """
        try:
            logger.debug(
                "Listing routes",
                area_id=area_id,
                is_active=is_active,
                is_general=is_general,
                is_modern=is_modern,
                is_horeca=is_horeca,
                limit=limit,
                offset=offset,
                company_id=str(self.company_id),
            )

            # Validate pagination parameters
            if limit < 1 or limit > 100:
                raise RouteValidationException(
                    message="Limit must be between 1 and 100",
                    field="limit",
                    value=limit,
                )

            if offset < 0:
                raise RouteValidationException(
                    message="Offset must be non-negative",
                    field="offset",
                    value=offset,
                )

            # Get routes and count in parallel for better performance
            async with self.db_pool.acquire() as conn:
                routes = await self.repository.list_routes(
                    area_id=area_id,
                    is_active=is_active,
                    is_general=is_general,
                    is_modern=is_modern,
                    is_horeca=is_horeca,
                    limit=limit,
                    offset=offset,
                    connection=conn,
                )
                total_count = await self.repository.count_routes(
                    area_id=area_id,
                    is_active=is_active,
                    is_general=is_general,
                    is_modern=is_modern,
                    is_horeca=is_horeca,
                    connection=conn,
                )

            logger.debug(
                "Routes listed successfully",
                count=len(routes),
                total_count=total_count,
                company_id=str(self.company_id),
            )

            return routes, total_count

        except RouteValidationException:
            raise
        except Exception as e:
            logger.error(
                "Failed to list routes in service",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def update_route(
        self, route_id: int, route_data: RouteUpdate
    ) -> RouteResponse:
        """
        Update an existing route.

        Note: Route code cannot be updated.

        Args:
            route_id: ID of the route to update
            route_data: Route data to update

        Returns:
            Updated route

        Raises:
            RouteNotFoundException: If route not found
            RouteValidationException: If validation fails
            RouteOperationException: If update fails
        """
        try:
            logger.info(
                "Updating route",
                route_id=route_id,
                company_id=str(self.company_id),
            )

            # Validate at least one field is provided
            if not any(
                [
                    route_data.name,
                    route_data.is_general is not None,
                    route_data.is_modern is not None,
                    route_data.is_horeca is not None,
                ]
            ):
                raise RouteValidationException(
                    message="At least one field must be provided for update",
                )

            # Update route using repository
            route = await self.repository.update_route(route_id, route_data)

            logger.info(
                "Route updated successfully",
                route_id=route_id,
                company_id=str(self.company_id),
            )

            return RouteResponse(**route.model_dump())

        except (RouteNotFoundException, RouteValidationException):
            raise
        except Exception as e:
            logger.error(
                "Failed to update route in service",
                route_id=route_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def delete_route(self, route_id: int) -> None:
        """
        Soft delete a route by setting is_active to False.

        Args:
            route_id: ID of the route to delete

        Raises:
            RouteNotFoundException: If route not found
            RouteOperationException: If deletion fails
        """
        try:
            logger.info(
                "Deleting route",
                route_id=route_id,
                company_id=str(self.company_id),
            )

            # Soft delete route using repository
            await self.repository.delete_route(route_id)

            logger.info(
                "Route deleted successfully",
                route_id=route_id,
                company_id=str(self.company_id),
            )

        except RouteNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to delete route in service",
                route_id=route_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def get_routes_by_area(self, area_id: int) -> list[RouteListItem]:
        """
        Get all active routes for a specific area.

        Args:
            area_id: ID of the area

        Returns:
            List of routes

        Raises:
            RouteOperationException: If retrieval fails
        """
        try:
            logger.debug(
                "Getting routes by area",
                area_id=area_id,
                company_id=str(self.company_id),
            )

            routes = await self.repository.get_routes_by_area(area_id)

            return routes

        except Exception as e:
            logger.error(
                "Failed to get routes by area in service",
                area_id=area_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def check_route_exists(self, route_id: int) -> bool:
        """
        Check if a route exists.

        Args:
            route_id: ID of the route to check

        Returns:
            True if route exists, False otherwise
        """
        try:
            await self.repository.get_route_by_id(route_id)
            return True
        except RouteNotFoundException:
            return False

    async def check_route_exists_by_code(self, code: str) -> bool:
        """
        Check if a route exists by code.

        Args:
            code: Code of the route to check

        Returns:
            True if route exists, False otherwise
        """
        try:
            await self.repository.get_route_by_code(code)
            return True
        except RouteNotFoundException:
            return False

    async def get_active_routes_count(
        self,
        area_id: Optional[int] = None,
        is_general: Optional[bool] = None,
        is_modern: Optional[bool] = None,
        is_horeca: Optional[bool] = None,
    ) -> int:
        """
        Get count of active routes, optionally filtered by area and route types.

        Args:
            area_id: Optional filter by area ID
            is_general: Optional filter by general status
            is_modern: Optional filter by modern status
            is_horeca: Optional filter by horeca status

        Returns:
            Count of active routes

        Raises:
            RouteOperationException: If counting fails
        """
        try:
            logger.debug(
                "Getting active routes count",
                area_id=area_id,
                is_general=is_general,
                is_modern=is_modern,
                is_horeca=is_horeca,
                company_id=str(self.company_id),
            )

            count = await self.repository.count_routes(
                area_id=area_id,
                is_active=True,
                is_general=is_general,
                is_modern=is_modern,
                is_horeca=is_horeca,
            )

            return count

        except Exception as e:
            logger.error(
                "Failed to get active routes count in service",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def get_general_routes(
        self, area_id: Optional[int] = None, limit: int = 100
    ) -> list[RouteListItem]:
        """
        Get all active general routes, optionally filtered by area.

        Args:
            area_id: Optional filter by area ID
            limit: Maximum number of routes to return (default: 100)

        Returns:
            List of general routes

        Raises:
            RouteOperationException: If retrieval fails
        """
        try:
            logger.debug(
                "Getting general routes",
                area_id=area_id,
                company_id=str(self.company_id),
            )

            routes = await self.repository.list_routes(
                area_id=area_id,
                is_active=True,
                is_general=True,
                limit=limit,
            )

            return routes

        except Exception as e:
            logger.error(
                "Failed to get general routes in service",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def get_modern_routes(
        self, area_id: Optional[int] = None, limit: int = 100
    ) -> list[RouteListItem]:
        """
        Get all active modern routes, optionally filtered by area.

        Args:
            area_id: Optional filter by area ID
            limit: Maximum number of routes to return (default: 100)

        Returns:
            List of modern routes

        Raises:
            RouteOperationException: If retrieval fails
        """
        try:
            logger.debug(
                "Getting modern routes",
                area_id=area_id,
                company_id=str(self.company_id),
            )

            routes = await self.repository.list_routes(
                area_id=area_id,
                is_active=True,
                is_modern=True,
                limit=limit,
            )

            return routes

        except Exception as e:
            logger.error(
                "Failed to get modern routes in service",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def get_horeca_routes(
        self, area_id: Optional[int] = None, limit: int = 100
    ) -> list[RouteListItem]:
        """
        Get all active horeca routes, optionally filtered by area.

        Args:
            area_id: Optional filter by area ID
            limit: Maximum number of routes to return (default: 100)

        Returns:
            List of horeca routes

        Raises:
            RouteOperationException: If retrieval fails
        """
        try:
            logger.debug(
                "Getting horeca routes",
                area_id=area_id,
                company_id=str(self.company_id),
            )

            routes = await self.repository.list_routes(
                area_id=area_id,
                is_active=True,
                is_horeca=True,
                limit=limit,
            )

            return routes

        except Exception as e:
            logger.error(
                "Failed to get horeca routes in service",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

