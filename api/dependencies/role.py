from typing import Annotated
from fastapi import Depends
from api.service.role import RoleService
from api.dependencies.common import CompanyIDDep, DatabasePoolDep


async def get_role_service(
    db_pool: DatabasePoolDep, company_id: CompanyIDDep
) -> RoleService:
    """
    Dependency to get RoleService instance.

    Args:
        db_pool: Database pool from dependency
        company_id: Company UUID from path parameter

    Returns:
        RoleService instance configured for the tenant
    """
    return RoleService(db_pool, company_id)


RoleServiceDep = Annotated[RoleService, Depends(get_role_service)]
