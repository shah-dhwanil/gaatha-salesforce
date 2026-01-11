from typing import Annotated
from fastapi import Depends
from api.service.user import UserService
from api.dependencies.common import DatabasePoolDep


async def get_user_service(
    db_pool: DatabasePoolDep,
) -> UserService:
    """
    Dependency to get UserService instance.

    Args:
        db_pool: Database pool from dependency

    Returns:
        UserService instance
    """
    return UserService(db_pool)


UserServiceDep = Annotated[UserService, Depends(get_user_service)]
