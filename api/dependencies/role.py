from api.repository.role import RoleRepository
from api.service.role import RoleService
from api.database import get_db_pool
from fastapi.param_functions import Depends
from api.database import DatabasePool
from typing import Annotated


# Dependency to get role service
async def get_role_service(
    db: Annotated[DatabasePool, Depends(get_db_pool, scope="function")],
) -> RoleService:
    """Dependency to create and return RoleService instance."""
    role_repository = RoleRepository(db)
    return RoleService(role_repository)
