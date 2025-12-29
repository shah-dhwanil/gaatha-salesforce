"""
Route Assignment dependencies for FastAPI routes.

This module provides FastAPI dependency functions for route assignment service,
enabling dependency injection of the RouteAssignmentService into endpoints.
"""

from typing import Annotated

from fastapi import Depends

from api.dependencies.common import CompanyIDDep, DatabasePoolDep
from api.service.route_assignment import RouteAssignmentService


def get_route_assignment_service(
    db_pool: DatabasePoolDep,
    company_id: CompanyIDDep,
) -> RouteAssignmentService:
    """
    Dependency to get RouteAssignmentService instance.

    Args:
        db_pool: Database pool from dependency
        company_id: Company ID from path parameter

    Returns:
        RouteAssignmentService instance configured for the tenant

    Example:
        ```python
        @router.post("/route-assignments")
        async def create_assignment(
            service: RouteAssignmentService = Depends(get_route_assignment_service)
        ):
            pass
        ```
    """
    return RouteAssignmentService(db_pool, company_id)


# Type alias for cleaner endpoint signatures
RouteAssignmentServiceDep = Annotated[
    RouteAssignmentService, Depends(get_route_assignment_service)
]

