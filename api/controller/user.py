"""
User controller/router for FastAPI endpoints.

This module defines all REST API endpoints for user management
in a multi-tenant environment.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Query, status
from fastapi.responses import Response
import structlog

from api.dependencies.user import UserServiceDep
from api.dependencies.common import CompanyIDDep
from api.exceptions.user import (
    UserAlreadyExistsException,
    UserNotFoundException,
    UserOperationException,
    UserValidationException,
)
from api.models import ListResponseModel, ResponseModel
from api.models.user import (
    UserCreate,
    UserDetailsResponse,
    UserListResponse,
    UserResponse,
    UserUpdate,
)

logger = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/users",
    tags=["Users"],
    responses={
        400: {"description": "Bad Request - Invalid input"},
        404: {"description": "Resource Not Found"},
        500: {"description": "Internal Server Error"},
    },
)


@router.post(
    "",
    response_model=ResponseModel[UserResponse],
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "User created successfully"},
        400: {"description": "Validation error"},
        409: {"description": "User already exists"},
    },
    summary="Create a new user",
    description="Create a new user with specified username, name, contact, company, role, and area",
)
async def create_user(
    user_data: UserCreate,
    user_service: UserServiceDep,
):
    """
    Create a new user.

    - **username**: Unique username (1-100 characters)
    - **name**: Full name of the user (1-255 characters)
    - **contact_no**: Contact phone number (1-20 characters)
    - **company_id**: UUID of the company (optional for super admin)
    - **role**: Role name (optional for super admin)
    - **area_id**: Area ID (optional for super admin)
    - **bank_details**: Bank account details (optional for super admin)
    - **is_super_admin**: Whether the user is a super admin (default: false)
    """
    try:
        user = await user_service.create_user(user_data)
        return ResponseModel(status_code=status.HTTP_201_CREATED, data=user)

    except UserAlreadyExistsException as e:
        logger.warning(
            "User already exists",
            username=user_data.username,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        )

    except UserValidationException as e:
        logger.warning(
            "User validation failed",
            username=user_data.username,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to create user",
            username=user_data.username,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user",
        )


@router.get(
    "/{user_id}",
    response_model=ResponseModel[UserDetailsResponse],
    responses={
        200: {"description": "User retrieved successfully"},
        404: {"description": "User not found"},
    },
    summary="Get user by ID",
    description="Retrieve detailed information about a specific user including company and area details",
)
async def get_user_by_id(
    user_id: Annotated[UUID, Path(description="User UUID")],
    user_service: UserServiceDep,
):
    """
    Get a user by ID.

    Returns complete user information including company name, area details, and timestamps.
    """
    try:
        user = await user_service.get_user_by_id(user_id)
        return ResponseModel(status_code=status.HTTP_200_OK, data=user)

    except UserNotFoundException as e:
        logger.info(
            "User not found",
            user_id=str(user_id),
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to get user",
            user_id=str(user_id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user",
        )


@router.get(
    "/username/{username}",
    response_model=ResponseModel[UserDetailsResponse],
    responses={
        200: {"description": "User retrieved successfully"},
        404: {"description": "User not found"},
    },
    summary="Get user by username",
    description="Retrieve user information by username",
)
async def get_user_by_username(
    username: Annotated[str, Path(description="Username of the user")],
    user_service: UserServiceDep,
):
    """
    Get a user by username.

    Returns complete user information for the user with the specified username.
    """
    try:
        user = await user_service.get_user_by_username(username)
        return ResponseModel(status_code=status.HTTP_200_OK, data=user)

    except UserNotFoundException as e:
        logger.info(
            "User not found by username",
            username=username,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to get user by username",
            username=username,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user",
        )


@router.get(
    "/companies/{company_id}/users",
    response_model=ListResponseModel[UserListResponse],
    responses={
        200: {"description": "Users retrieved successfully"},
        400: {"description": "Invalid pagination parameters"},
    },
    summary="List users by company",
    description="List all users for a specific company with pagination and optional filtering by active status",
)
async def list_users_by_company(
    company_id: CompanyIDDep,
    user_service: UserServiceDep,
    is_active: Annotated[
        bool | None,
        Query(description="Filter by active status (true/false, optional)"),
    ] = None,
    limit: Annotated[
        int,
        Query(ge=1, le=100, description="Number of users to return (1-100)"),
    ] = 20,
    offset: Annotated[
        int,
        Query(ge=0, description="Number of users to skip (pagination)"),
    ] = 0,
):
    """
    List all users for a specific company with pagination.

    Returns minimal user data for performance.
    Use the detail endpoint to get complete user information.

    - **company_id**: Company UUID (from path)
    - **is_active**: Optional filter by active status
    - **limit**: Number of results to return (default: 20, max: 100)
    - **offset**: Number of results to skip (default: 0)
    """
    try:
        users, total_count = await user_service.get_users_by_company_id(
            company_id=company_id,
            is_active=is_active,
            limit=limit,
            offset=offset,
        )

        return ListResponseModel(
            status_code=status.HTTP_200_OK,
            data=users,
            records_per_page=limit,
            total_count=total_count,
        )

    except UserValidationException as e:
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
            "Failed to list users by company",
            company_id=str(company_id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list users",
        )


@router.get(
    "/companies/{company_id}/roles/{role_name}/users",
    response_model=ListResponseModel[UserListResponse],
    responses={
        200: {"description": "Users retrieved successfully"},
        400: {"description": "Invalid pagination parameters"},
    },
    summary="List users by role",
    description="List all users with a specific role with pagination and optional filtering by active status",
)
async def list_users_by_role(
    company_id: CompanyIDDep,
    role_name: Annotated[str, Path(description="Role name")],
    user_service: UserServiceDep,
    is_active: Annotated[
        bool | None,
        Query(description="Filter by active status (true/false, optional)"),
    ] = None,
    limit: Annotated[
        int,
        Query(ge=1, le=100, description="Number of users to return (1-100)"),
    ] = 20,
    offset: Annotated[
        int,
        Query(ge=0, description="Number of users to skip (pagination)"),
    ] = 0,
):
    """
    List all users with a specific role with pagination.

    Returns minimal user data for performance.
    Use the detail endpoint to get complete user information.

    - **role_name**: Role name (from path)
    - **is_active**: Optional filter by active status
    - **limit**: Number of results to return (default: 20, max: 100)
    - **offset**: Number of results to skip (default: 0)
    """
    try:
        users, total_count = await user_service.get_users_by_role(
            company_id=company_id,
            role=role_name,
            is_active=is_active,
            limit=limit,
            offset=offset,
        )

        return ListResponseModel(
            status_code=status.HTTP_200_OK,
            data=users,
            records_per_page=limit,
            total_count=total_count,
        )

    except UserValidationException as e:
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
            "Failed to list users by role",
            role=role_name,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list users",
        )


@router.patch(
    "/companies/{company_id}/users/{user_id}",
    response_model=ResponseModel[UserResponse],
    responses={
        200: {"description": "User updated successfully"},
        400: {"description": "Validation error"},
        404: {"description": "User not found"},
    },
    summary="Update a user",
    description="Update user name, contact, role, area, or bank details",
)
async def update_user(
    company_id: CompanyIDDep,
    user_id: Annotated[UUID, Path(description="User UUID")],
    user_data: UserUpdate,
    user_service: UserServiceDep,
):
    """
    Update an existing user.

    Only specified fields will be updated.
    Username and super admin status cannot be updated.

    - **name**: Optional new name
    - **contact_no**: Optional new contact number
    - **role**: Optional new role
    - **area_id**: Optional new area assignment
    - **bank_details**: Optional new bank details
    """
    try:
        user = await user_service.update_user(user_id, user_data, company_id)
        return ResponseModel(status_code=status.HTTP_200_OK, data=user)

    except UserNotFoundException as e:
        logger.info(
            "User not found for update",
            user_id=str(user_id),
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except UserValidationException as e:
        logger.warning(
            "User update validation failed",
            user_id=str(user_id),
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to update user",
            user_id=str(user_id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user",
        )


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "User deactivated successfully"},
        404: {"description": "User not found"},
    },
    summary="Delete a user (soft delete)",
    description="Soft delete a user by setting is_active to false",
)
async def delete_user(
    user_id: Annotated[UUID, Path(description="User UUID")],
    user_service: UserServiceDep,
):
    """
    Delete a user (soft delete).

    Sets is_active to false instead of permanently deleting the user.
    The user will still exist in the database but won't be active.
    """
    try:
        await user_service.delete_user(user_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except UserNotFoundException as e:
        logger.info(
            "User not found for deletion",
            user_id=str(user_id),
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to delete user",
            user_id=str(user_id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user",
        )


@router.post(
    "/{user_id}/activate",
    response_model=ResponseModel[UserResponse],
    responses={
        200: {"description": "User activated successfully"},
        404: {"description": "User not found"},
    },
    summary="Activate a user",
    description="Activate a user by setting is_active to true",
)
async def activate_user(
    user_id: Annotated[UUID, Path(description="User UUID")],
    user_service: UserServiceDep,
):
    """
    Activate a user.

    Sets is_active to true for a previously deactivated user.
    """
    try:
        user = await user_service.activate_user(user_id)
        return ResponseModel(status_code=status.HTTP_200_OK, data=user)

    except UserNotFoundException as e:
        logger.info(
            "User not found for activation",
            user_id=str(user_id),
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to activate user",
            user_id=str(user_id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to activate user",
        )


@router.get(
    "/{user_id}/exists",
    response_model=ResponseModel[dict],
    responses={
        200: {"description": "Existence check completed"},
    },
    summary="Check if user exists",
    description="Check if a user with the given ID exists",
)
async def check_user_exists(
    user_id: Annotated[UUID, Path(description="User UUID")],
    user_service: UserServiceDep,
):
    """
    Check if a user exists.

    Returns a boolean indicating whether the user exists.
    """
    try:
        exists = await user_service.check_user_exists(user_id)
        return ResponseModel(
            status_code=status.HTTP_200_OK,
            data={"user_id": str(user_id), "exists": exists},
        )

    except Exception as e:
        logger.error(
            "Failed to check user existence",
            user_id=str(user_id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check user existence",
        )


@router.get(
    "/username/{username}/exists",
    response_model=ResponseModel[dict],
    responses={
        200: {"description": "Existence check completed"},
    },
    summary="Check if username exists",
    description="Check if a user with the given username exists",
)
async def check_username_exists(
    username: Annotated[str, Path(description="Username to check")],
    user_service: UserServiceDep,
):
    """
    Check if a username exists.

    Returns a boolean indicating whether the username is already taken.
    """
    try:
        exists = await user_service.check_username_exists(username)
        return ResponseModel(
            status_code=status.HTTP_200_OK,
            data={"username": username, "exists": exists},
        )

    except Exception as e:
        logger.error(
            "Failed to check username existence",
            username=username,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check username existence",
        )

