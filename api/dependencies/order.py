from typing import Annotated
from fastapi import Depends
from api.service.order import OrderService
from api.dependencies.common import CompanyIDDep, DatabasePoolDep


async def get_order_service(
    db_pool: DatabasePoolDep, company_id: CompanyIDDep
) -> OrderService:
    """
    Dependency to get OrderService instance.

    Args:
        db_pool: Database pool from dependency
        company_id: Company UUID from path parameter

    Returns:
        OrderService instance configured for the tenant
    """
    return OrderService(db_pool, company_id)


OrderServiceDep = Annotated[OrderService, Depends(get_order_service)]
