from typing import Annotated
from fastapi import Depends
from api.service.shop_category import ShopCategoryService
from api.dependencies.common import CompanyIDDep, DatabasePoolDep


async def get_shop_category_service(
    db_pool: DatabasePoolDep, company_id: CompanyIDDep
) -> ShopCategoryService:
    """
    Dependency to get ShopCategoryService instance.

    Args:
        db_pool: Database pool from dependency
        company_id: Company UUID from path parameter

    Returns:
        ShopCategoryService instance configured for the tenant
    """
    return ShopCategoryService(db_pool, company_id)


ShopCategoryServiceDep = Annotated[
    ShopCategoryService, Depends(get_shop_category_service)
]
