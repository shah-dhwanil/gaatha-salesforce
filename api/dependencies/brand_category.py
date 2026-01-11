from typing import Annotated
from fastapi import Depends
from api.service.brand_category import BrandCategoryService
from api.dependencies.common import DatabasePoolDep
from api.dependencies.common import CompanyIDDep


def get_brand_category_service(
    db_pool: DatabasePoolDep,
    company_id: CompanyIDDep,
) -> BrandCategoryService:
    return BrandCategoryService(db_pool, company_id)


BrandCategoryServiceDep = Annotated[
    BrandCategoryService, Depends(get_brand_category_service)
]
