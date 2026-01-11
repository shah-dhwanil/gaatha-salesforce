from typing import Annotated
from fastapi import Depends
from api.service.distributor import DistributorService
from api.dependencies.common import CompanyIDDep, DatabasePoolDep


async def get_distributor_service(
    db_pool: DatabasePoolDep, company_id: CompanyIDDep
) -> DistributorService:
    """
    Dependency to get DistributorService instance.

    Args:
        db_pool: Database pool from dependency
        company_id: Company UUID from path parameter

    Returns:
        DistributorService instance configured for the tenant
    """
    return DistributorService(db_pool, company_id)


DistributorServiceDep = Annotated[DistributorService, Depends(get_distributor_service)]
