from typing import Annotated
from fastapi import Depends
from api.service.brand import BrandService
from api.dependencies.common import DatabasePoolDep
from api.dependencies.common import CompanyIDDep

def get_brand_service(
    db_pool: DatabasePoolDep,
    company_id: CompanyIDDep,
) -> BrandService:
    return BrandService(db_pool, company_id) 

BrandServiceDep = Annotated[BrandService, Depends(get_brand_service)]
