from typing import Annotated
from fastapi import Depends
from api.service.product import ProductService
from api.dependencies.common import DatabasePoolDep
from api.dependencies.common import CompanyIDDep


def get_product_service(
    db_pool: DatabasePoolDep,
    company_id: CompanyIDDep,
) -> ProductService:
    return ProductService(db_pool, company_id)


ProductServiceDep = Annotated[ProductService, Depends(get_product_service)]
