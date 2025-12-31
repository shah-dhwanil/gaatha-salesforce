from typing import Annotated
from fastapi import Depends
from api.service.retailer import RetailerService
from api.dependencies.common import CompanyIDDep, DatabasePoolDep


async def get_retailer_service(
    db_pool: DatabasePoolDep,
    company_id: CompanyIDDep
) -> RetailerService:
    """
    Dependency to get RetailerService instance.

    Args:
        db_pool: Database pool from dependency
        company_id: Company UUID from path parameter

    Returns:
        RetailerService instance configured for the tenant
    """
    return RetailerService(db_pool, company_id)

RetailerServiceDep = Annotated[RetailerService, Depends(get_retailer_service)]

