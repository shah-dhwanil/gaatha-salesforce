from api.repository.company import CompanyRepository
from api.service.company import CompanyService
from api.database import get_db_pool
from fastapi.param_functions import Depends
from api.database import DatabasePool
from typing import Annotated


# Dependency to get company service
async def get_company_service(
    db: Annotated[DatabasePool, Depends(get_db_pool, scope="function")],
) -> CompanyService:
    """Dependency to create and return CompanyService instance."""
    company_repository = CompanyRepository(db)
    return CompanyService(company_repository)
