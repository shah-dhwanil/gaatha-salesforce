from typing import Annotated
from fastapi import Depends

from api.dependencies.common import DatabasePoolDep
from api.service.company import CompanyService
from api.settings import get_settings
from api.settings.database import DatabaseConfig


def get_database_config() -> DatabaseConfig:
    """
    Dependency to get DatabaseConfig instance.

    Returns:
        DatabaseConfig from application settings
    """
    settings = get_settings()
    return settings.POSTGRES


async def get_company_service(
    db_pool: DatabasePoolDep,
    db_config: Annotated[DatabaseConfig, Depends(get_database_config)],
) -> CompanyService:
    """
    Dependency to get CompanyService instance.

    Args:
        db_pool: Database pool from dependency
        db_config: Database configuration from settings

    Returns:
        CompanyService instance
    """
    return CompanyService(db_pool, db_config)


CompanyServiceDep = Annotated[CompanyService, Depends(get_company_service)]
