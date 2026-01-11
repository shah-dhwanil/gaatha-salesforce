from typing import Annotated
from fastapi import Depends
from api.service.area import AreaService
from api.dependencies.common import DatabasePoolDep
from api.dependencies.common import CompanyIDDep


def get_area_service(
    db_pool: DatabasePoolDep,
    company_id: CompanyIDDep,
) -> AreaService:
    return AreaService(db_pool, company_id)


AreaServiceDep = Annotated[AreaService, Depends(get_area_service)]
