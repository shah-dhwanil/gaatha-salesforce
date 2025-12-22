"""
Role controller for FastAPI routes.

This module defines the API endpoints for role operations including
CRUD operations and role management.
"""

from api.database import DatabasePool
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, status
import structlog

from api.database import get_db_pool
from api.repository.role import RoleRepository
from api.service.role import RoleService
from api.models.base import ResponseModel, ListResponseModel
from api.models.role import (
    CreateRoleRequest,
    UpdateRoleRequest,
    RoleResponse,
)

logger = structlog.get_logger(__name__)

# Create router
router = APIRouter(prefix="/roles", tags=["roles"])


# Dependency to get role service
async def get_role_service(
    db: Annotated[DatabasePool, Depends(get_db_pool, scope="function")],
) -> RoleService:
    """Dependency to create and return RoleService instance."""
    role_repository = RoleRepository(db)
    return RoleService(role_repository)


@router.post(
    "/",
    response_model=ResponseModel[RoleResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new role",
    description="Create a new role with the specified name, description, and permissions for a company.",
)
async def create_role(
    request: CreateRoleRequest,
    role_service: RoleService = Depends(get_role_service),
) -> ResponseModel[RoleResponse]:
    """
    Create a new role.

    Args:
        request: CreateRoleRequest with role details
        role_service: Injected RoleService dependency

    Returns:
        RoleResponse with created role details

    Raises:
        HTTPException: 409 if role already exists
        HTTPException: 400 if validation fails
    """
    logger.info(
        "Creating new role", name=request.name, company_id=str(request.company_id)
    )

    role = await role_service.create_role(
        company_id=request.company_id,
        name=request.name,
        description=request.description,
        permissions=request.permissions,
    )

    return ResponseModel(
        status_code=status.HTTP_201_CREATED,
        data=RoleResponse(
            name=role.name,
            description=role.description,
            permissions=role.permissions,
            is_active=role.is_active,
            created_at=role.created_at,
            updated_at=role.updated_at,
        ),
    )


@router.get(
    "/{company_id}",
    response_model=ListResponseModel[RoleResponse],
    status_code=status.HTTP_200_OK,
    summary="Get all roles for a company",
    description="Retrieve all active roles for the specified company with pagination.",
)
async def get_roles_by_company(
    company_id: UUID,
    limit: int = 10,
    offset: int = 0,
    role_service: RoleService = Depends(get_role_service),
) -> ListResponseModel[RoleResponse]:
    """
    Get all roles for a company with pagination.

    Args:
        company_id: UUID of the company
        limit: Maximum number of records to return (default: 10)
        offset: Number of records to skip (default: 0)
        role_service: Injected RoleService dependency

    Returns:
        ListResponseModel with list of roles, pagination info, and total count
    """
    logger.info(
        "Fetching roles for company",
        company_id=str(company_id),
        limit=limit,
        offset=offset,
    )

    roles, total_count = await role_service.get_roles_by_company(
        company_id, limit, offset
    )

    role_responses = [
        RoleResponse(
            name=role.name,
            description=role.description,
            permissions=role.permissions,
            is_active=role.is_active,
            created_at=role.created_at,
            updated_at=role.updated_at,
        )
        for role in roles
    ]

    return ListResponseModel(
        status_code=status.HTTP_200_OK,
        data=role_responses,
        records_per_page=len(role_responses),
        total_count=total_count,
    )


@router.get(
    "/{company_id}/{name}",
    response_model=ResponseModel[RoleResponse],
    status_code=status.HTTP_200_OK,
    summary="Get role by name",
    description="Retrieve a specific role by name for a company.",
)
async def get_role_by_name(
    company_id: UUID,
    name: str,
    role_service: RoleService = Depends(get_role_service),
) -> ResponseModel[RoleResponse]:
    """
    Get a role by name.

    Args:
        company_id: UUID of the company
        name: Name of the role
        role_service: Injected RoleService dependency

    Returns:
        RoleResponse with role details

    Raises:
        HTTPException: 404 if role not found
    """
    logger.info("Fetching role by name", name=name, company_id=str(company_id))

    role = await role_service.get_role_by_name(company_id, name)

    return ResponseModel(
        status_code=status.HTTP_200_OK,
        data=RoleResponse(
            name=role.name,
            description=role.description,
            permissions=role.permissions,
            is_active=role.is_active,
            created_at=role.created_at,
            updated_at=role.updated_at,
        ),
    )


@router.patch(
    "/{company_id}/{name}",
    response_model=ResponseModel[RoleResponse],
    status_code=status.HTTP_200_OK,
    summary="Update a role",
    description="Update an existing role's description and/or permissions.",
)
async def update_role(
    company_id: UUID,
    name: str,
    request: UpdateRoleRequest,
    role_service: RoleService = Depends(get_role_service),
) -> ResponseModel[RoleResponse]:
    """
    Update a role.

    Args:
        request: UpdateRoleRequest with update details
        role_service: Injected RoleService dependency

    Returns:
        RoleResponse with updated role details

    Raises:
        HTTPException: 404 if role not found
        HTTPException: 400 if no fields provided for update
    """
    logger.info("Updating role", name=name, company_id=str(company_id))

    # Validate at least one field is provided
    if not request.has_updates():
        role = await role_service.get_role_by_name(company_id, name)
    else:
        role = await role_service.update_role(
            company_id=company_id,
            name=name,
            description=request.description,
            permissions=request.permissions,
        )

    return ResponseModel(
        status_code=status.HTTP_200_OK,
        data=RoleResponse(
            name=role.name,
            description=role.description,
            permissions=role.permissions,
            is_active=role.is_active,
            created_at=role.created_at,
            updated_at=role.updated_at,
        ),
    )


@router.delete(
    "/{company_id}/{name}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a role",
    description="Soft delete a role by marking it as inactive.",
)
async def delete_role(
    company_id: UUID,
    name: str,
    role_service: RoleService = Depends(get_role_service),
) -> None:
    """
    Delete a role (soft delete).

    Args:
        request: DeleteRoleRequest with role identifier
        role_service: Injected RoleService dependency

    Returns:
        RoleDeletedResponse with deletion confirmation

    Raises:
        HTTPException: 404 if role not found
    """
    logger.info("Deleting role", name=name, company_id=str(company_id))

    await role_service.delete_role(company_id, name)

    return