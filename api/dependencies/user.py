# Dependency to get user service
from api.repository.user import UserRepository
from api.service.user import UserService
from api.database import get_db_pool
from fastapi.param_functions import Depends
from api.database import DatabasePool
from typing import Annotated


async def get_user_service(
    db: Annotated[DatabasePool, Depends(get_db_pool, scope="function")],
) -> UserService:
    """Dependency to create and return UserService instance."""
    user_repository = UserRepository(db)
    return UserService(user_repository)
