# Dependency to get area service
from api.repository.area import AreaRepository
from api.service.area import AreaService
from typing import Annotated
from api.database import get_db_pool
from fastapi.params import Depends
from api.database import DatabasePool


async def get_area_service(
    db: Annotated[DatabasePool, Depends(get_db_pool, scope="function")],
) -> AreaService:
    """Dependency to create and return AreaService instance."""
    area_repository = AreaRepository(db)
    return AreaService(area_repository)
