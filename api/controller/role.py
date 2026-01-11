"""
Role controller/router for FastAPI endpoints.

This module defines all REST API endpoints for role management
in a multi-tenant environment.
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, status
from fastapi.responses import Response
import structlog

from api.dependencies.role import RoleServiceDep
from api.exceptions.role import (
    RoleAlreadyExistsException,
    RoleNotFoundException,
    RoleOperationException,
    RoleValidationException,
)
from api.models import ListResponseModel, ResponseModel
from api.models.role import RoleCreate, RoleListItem, RoleResponse, RoleUpdate

logger = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/companies/{company_id}/roles",
    tags=["Roles"],
    responses={
        400: {"description": "Bad Request - Invalid input"},
        404: {"description": "Resource Not Found"},
        500: {"description": "Internal Server Error"},
    },
)


@router.post(
    "",
    response_model=ResponseModel[RoleResponse],
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Role created successfully"},
        400: {"description": "Validation error"},
        409: {"description": "Role already exists"},
    },
    summary="Create a new role",
    description="Create a new role with specified name, description, and permissions",
)
async def create_role(
    role_data: RoleCreate,
    role_service: RoleServiceDep,
):
    """
    Create a new role.

    - **name**: Unique role name (1-32 characters)
    - **description**: Optional role description
    - **permissions**: List of permission strings (max 64 chars each)
    - **is_active**: Whether the role is active (default: true)
    """
    try:
        role = await role_service.create_role(role_data)
        return ResponseModel(status_code=status.HTTP_201_CREATED, data=role)

    except RoleAlreadyExistsException as e:
        logger.warning(
            "Role already exists",
            role_name=role_data.name,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        )

    except RoleValidationException as e:
        logger.warning(
            "Role validation failed",
            role_name=role_data.name,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to create role",
            role_name=role_data.name,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create role",
        )


@router.get(
    "/{role_name}",
    response_model=ResponseModel[RoleResponse],
    responses={
        200: {"description": "Role retrieved successfully"},
        404: {"description": "Role not found"},
    },
    summary="Get role by name",
    description="Retrieve detailed information about a specific role",
)
async def get_role(
    role_name: Annotated[str, Path(description="Name of the role to retrieve")],
    role_service: RoleServiceDep,
):
    """
    Get a role by name.

    Returns complete role information including permissions and timestamps.
    """
    try:
        role = await role_service.get_role_by_name(role_name)
        return ResponseModel(status_code=status.HTTP_200_OK, data=role)

    except RoleNotFoundException as e:
        logger.info(
            "Role not found",
            role_name=role_name,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to get role",
            role_name=role_name,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve role",
        )


@router.get(
    "",
    response_model=ListResponseModel[RoleListItem],
    responses={
        200: {"description": "Roles retrieved successfully"},
        400: {"description": "Invalid pagination parameters"},
    },
    summary="List all roles",
    description="List all roles with pagination and optional filtering by active status",
)
async def list_roles(
    role_service: RoleServiceDep,
    is_active: Annotated[
        bool | None,
        Query(description="Filter by active status (true/false, optional)"),
    ] = None,
    limit: Annotated[
        int,
        Query(ge=1, le=100, description="Number of roles to return (1-100)"),
    ] = 20,
    offset: Annotated[
        int,
        Query(ge=0, description="Number of roles to skip (pagination)"),
    ] = 0,
):
    """
    List all roles with pagination.

    Returns minimal role data (name, description, is_active) for performance.
    Use the detail endpoint to get complete role information.

    - **is_active**: Optional filter by active status
    - **limit**: Number of results to return (default: 20, max: 100)
    - **offset**: Number of results to skip (default: 0)
    """
    try:
        roles, total_count = await role_service.list_roles(
            is_active=is_active,
            limit=limit,
            offset=offset,
        )

        return ListResponseModel(
            status_code=status.HTTP_200_OK,
            data=roles,
            records_per_page=limit,
            total_count=total_count,
        )

    except RoleValidationException as e:
        logger.warning(
            "Invalid pagination parameters",
            limit=limit,
            offset=offset,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to list roles",
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list roles",
        )


@router.patch(
    "/{role_name}",
    response_model=ResponseModel[RoleResponse],
    responses={
        200: {"description": "Role updated successfully"},
        400: {"description": "Validation error"},
        404: {"description": "Role not found"},
    },
    summary="Update a role",
    description="Update role description and/or permissions (cannot update is_active)",
)
async def update_role(
    role_name: Annotated[str, Path(description="Name of the role to update")],
    role_data: RoleUpdate,
    role_service: RoleServiceDep,
):
    """
    Update an existing role.

    Only description and permissions can be updated.
    Use delete endpoint to deactivate a role.

    - **description**: Optional new description
    - **permissions**: Optional new permissions list
    """
    try:
        role = await role_service.update_role(role_name, role_data)
        return ResponseModel(status_code=status.HTTP_200_OK, data=role)

    except RoleNotFoundException as e:
        logger.info(
            "Role not found for update",
            role_name=role_name,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except RoleValidationException as e:
        logger.warning(
            "Role update validation failed",
            role_name=role_name,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to update role",
            role_name=role_name,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update role",
        )


@router.delete(
    "/{role_name}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Role deactivated successfully"},
        400: {"description": "Validation error"},
        404: {"description": "Role not found"},
    },
    summary="Delete a role (soft delete)",
    description="Soft delete a role by setting is_active to false",
)
async def delete_role(
    role_name: Annotated[str, Path(description="Name of the role to delete")],
    role_service: RoleServiceDep,
):
    """
    Delete a role (soft delete).

    Sets is_active to false instead of permanently deleting the role.
    The role will still exist in the database but won't be active.
    """
    try:
        await role_service.delete_role(role_name)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except RoleNotFoundException as e:
        logger.info(
            "Role not found for deletion",
            role_name=role_name,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except RoleValidationException as e:
        logger.warning(
            "Role deletion validation failed",
            role_name=role_name,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to delete role",
            role_name=role_name,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete role",
        )


@router.post(
    "/bulk",
    response_model=ResponseModel[list[RoleResponse]],
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Roles created successfully"},
        400: {"description": "Validation error"},
        409: {"description": "One or more roles already exist"},
    },
    summary="Bulk create roles",
    description="Create multiple roles in a single transaction",
)
async def bulk_create_roles(
    roles_data: list[RoleCreate],
    role_service: RoleServiceDep,
):
    """
    Bulk create multiple roles.

    All roles are created in a single transaction.
    If any role fails, the entire operation is rolled back.

    - **roles_data**: List of role objects to create
    """
    try:
        roles = await role_service.bulk_create_roles(roles_data)
        return ResponseModel(status_code=status.HTTP_201_CREATED, data=roles)

    except RoleAlreadyExistsException as e:
        logger.warning(
            "Bulk create failed - roles already exist",
            count=len(roles_data),
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        )

    except RoleValidationException as e:
        logger.warning(
            "Bulk create validation failed",
            count=len(roles_data),
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )

    except RoleOperationException as e:
        logger.error(
            "Bulk create operation failed",
            count=len(roles_data),
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to bulk create roles",
            count=len(roles_data),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to bulk create roles",
        )


# @router.get(
#     "/count/active",
#     response_model=ResponseModel[int],
#     responses={
#         200: {"description": "Active roles count retrieved successfully"},
#     },
#     summary="Get active roles count",
#     description="Get the total count of active roles",
# )
# async def get_active_roles_count(
#     role_service: RoleServiceDep,
# ):
#     """
#     Get count of active roles.

#     Returns the total number of roles where is_active=true.
#     """
#     try:
#         count = await role_service.get_active_roles_count()
#         return ResponseModel(status_code=status.HTTP_200_OK, data=count)

#     except Exception as e:
#         logger.error(
#             "Failed to get active roles count",
#             error=str(e),
#         )
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Failed to get active roles count",
#         )


# @router.get(
#     "/{role_name}/permissions",
#     response_model=ResponseModel[list[str]],
#     responses={
#         200: {"description": "Permissions retrieved successfully"},
#         404: {"description": "Role not found"},
#     },
#     summary="Get role permissions",
#     description="Get list of permissions for a specific role",
# )
# async def get_role_permissions(
#     role_name: Annotated[str, Path(description="Name of the role")],
#     role_service: RoleServiceDep,
# ):
#     """
#     Get permissions for a specific role.

#     Returns only the permissions array for the specified role.
#     """
#     try:
#         permissions = await role_service.get_role_permissions(role_name)
#         return ResponseModel(status_code=status.HTTP_200_OK, data=permissions)

#     except RoleNotFoundException as e:
#         logger.info(
#             "Role not found for permissions",
#             role_name=role_name,
#             error=e.message,
#         )
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=e.message,
#         )

#     except Exception as e:
#         logger.error(
#             "Failed to get role permissions",
#             role_name=role_name,
#             error=str(e),
#         )
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Failed to get role permissions",
#         )


# @router.head(
#     "/{role_name}",
#     status_code=status.HTTP_200_OK,
#     responses={
#         200: {"description": "Role exists"},
#         404: {"description": "Role not found"},
#     },
#     summary="Check if role exists",
#     description="Check if a role exists without retrieving its data",
# )
# async def check_role_exists(
#     role_name: Annotated[str, Path(description="Name of the role to check")],
#     role_service: RoleServiceDep,
# ):
#     """
#     Check if a role exists.

#     Returns 200 if role exists, 404 if not found.
#     No response body is returned (HEAD request).
#     """
#     try:
#         exists = await role_service.check_role_exists(role_name)
#         if exists:
#             return Response(status_code=status.HTTP_200_OK)
#         else:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail=f"Role '{role_name}' not found",
#             )

#     except HTTPException:
#         raise

#     except Exception as e:
#         logger.error(
#             "Failed to check role existence",
#             role_name=role_name,
#             error=str(e),
#         )
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Failed to check role existence",
#         )
