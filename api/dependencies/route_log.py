"""
Route Log dependencies for FastAPI routes.

This module provides FastAPI dependency functions for route log service,
enabling dependency injection of the RouteLogService into endpoints.
"""

from typing import Annotated

from fastapi import Depends

from api.dependencies.common import CompanyIDDep, DatabasePoolDep
from api.service.route_log import RouteLogService


def get_route_log_service(
    db_pool: DatabasePoolDep,
    company_id: CompanyIDDep,
) -> RouteLogService:
    """
    Dependency to get RouteLogService instance.

    Args:
        db_pool: Database pool from dependency
        company_id: Company ID from path parameter

    Returns:
        RouteLogService instance configured for the tenant

    Example:
        ```python
        @router.post("/route-logs")
        async def create_log(
            service: RouteLogService = Depends(get_route_log_service)
        ):
            pass
        ```
    """
    return RouteLogService(db_pool, company_id)


# Type alias for cleaner endpoint signatures
RouteLogServiceDep = Annotated[RouteLogService, Depends(get_route_log_service)]
