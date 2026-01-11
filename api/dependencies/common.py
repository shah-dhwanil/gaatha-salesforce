"""
FastAPI dependencies for dependency injection.

This module contains reusable dependencies for FastAPI endpoints
including authentication, database access, and service initialization.
"""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Path

from api.database import DatabasePool, get_db_pool


async def get_company_id_from_path(
    company_id: Annotated[UUID, Path(description="Company UUID")],
) -> UUID:
    """
    Extract and validate company_id from path parameter.

    Args:
        company_id: Company UUID from path parameter

    Returns:
        Company UUID

    Raises:
        HTTPException: If company_id format is invalid
    """
    return company_id


# Type aliases for cleaner endpoint signatures
DatabasePoolDep = Annotated[DatabasePool, Depends(get_db_pool)]
CompanyIDDep = Annotated[UUID, Depends(get_company_id_from_path)]
