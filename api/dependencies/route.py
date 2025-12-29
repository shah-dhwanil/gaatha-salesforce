from typing import Annotated
from fastapi import Depends
from api.service.route import RouteService
from api.dependencies.common import DatabasePoolDep
from api.dependencies.common import CompanyIDDep


def get_route_service(
    db_pool: DatabasePoolDep,
    company_id: CompanyIDDep,
) -> RouteService:
    """
    Dependency to get RouteService instance.

    Args:
        db_pool: Database pool from dependency
        company_id: Company ID from path parameter

    Returns:
        RouteService instance
    """
    return RouteService(db_pool, company_id)


RouteServiceDep = Annotated[RouteService, Depends(get_route_service)]

