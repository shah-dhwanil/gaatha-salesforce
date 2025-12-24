"""
User controller for FastAPI routes.

This module defines the API endpoints for user operations including
CRUD operations and user management.
"""

from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
import structlog

from api.service.user import UserService
from api.dependencies.user import get_user_service
from api.models.base import ResponseModel, ListResponseModel
from api.models.users import (
    CreateUserRequest,
    UpdateUserRequest,
    UserResponse,
)

logger = structlog.get_logger(__name__)

# Create router
router = APIRouter(prefix="/users", tags=["users"])


@router.post(
    "/",
    response_model=ResponseModel[UserResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user",
    description="Create a new user with the specified username, name, contact number, company, role, and optional area.",
)
async def create_user(
    request: CreateUserRequest,
    user_service: UserService = Depends(get_user_service),
) -> ResponseModel[UserResponse]:
    """
    Create a new user.

    Args:
        request: CreateUserRequest with user details
        user_service: Injected UserService dependency

    Returns:
        UserResponse with created user details

    Raises:
        HTTPException: 409 if user already exists
        HTTPException: 404 if company, role, or area not found
        HTTPException: 400 if validation fails
    """
    logger.info(
        "Creating new user",
        username=request.username,
        company_id=str(request.company_id),
        role=request.role,
    )

    user = await user_service.create_user(
        username=request.username,
        name=request.name,
        contact_no=request.contact_no,
        company_id=request.company_id,
        role=request.role,
        area_id=request.area_id,
    )

    return ResponseModel(
        status_code=status.HTTP_201_CREATED,
        data=UserResponse(
            id=user.id,
            username=user.username,
            name=user.name,
            contact_no=user.contact_no,
            company_id=user.company_id,
            role=user.role,
            area_id=user.area_id,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
        ),
    )


@router.get(
    "/username/{username}",
    response_model=ResponseModel[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="Get user by username",
    description="Retrieve a specific user by their username.",
)
async def get_user_by_username(
    username: str,
    user_service: UserService = Depends(get_user_service),
) -> ResponseModel[UserResponse]:
    """
    Get a user by username.

    Args:
        username: Username of the user
        user_service: Injected UserService dependency

    Returns:
        UserResponse with user details

    Raises:
        HTTPException: 404 if user not found
    """
    logger.info("Fetching user by username", username=username)

    user = await user_service.get_user_by_username(username)

    return ResponseModel(
        status_code=status.HTTP_200_OK,
        data=UserResponse(
            id=user.id,
            username=user.username,
            name=user.name,
            contact_no=user.contact_no,
            company_id=user.company_id,
            role=user.role,
            area_id=user.area_id,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
        ),
    )


@router.get(
    "/{company_id}",
    response_model=ListResponseModel[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="Get users by company",
    description="Retrieve all users in a company, optionally filtered by role or active status.",
)
async def get_users(
    company_id: UUID,
    role: str | None = Query(None, description="Filter by role"),
    user_service: UserService = Depends(get_user_service),
) -> ListResponseModel[UserResponse]:
    """
    Get users by company, optionally filtered by role and active status.

    Args:
        company_id: UUID of the company
        role: Optional role filter
        active_only: Whether to return only active users (default: True)
        user_service: Injected UserService dependency

    Returns:
        ListResponseModel with list of users
    """
    logger.info(
        "Fetching users",
        company_id=str(company_id),
        role=role,
        active_only=True,
    )

    # Get users based on filters
    if role:
        users = await user_service.get_users_by_role(role, company_id)
    else:
        users = await user_service.get_users_by_company(company_id)

    user_responses = [
        UserResponse(
            id=user.id,
            username=user.username,
            name=user.name,
            contact_no=user.contact_no,
            company_id=user.company_id,
            role=user.role,
            area_id=user.area_id,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
        for user in users
    ]

    return ListResponseModel(
        status_code=status.HTTP_200_OK,
        data=user_responses,
        records_per_page=len(user_responses),
        total_count=len(user_responses),
    )


@router.get(
    "/{company_id}/{user_id}",
    response_model=ResponseModel[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="Get user by ID",
    description="Retrieve a specific user by their UUID.",
)
async def get_user_by_id(
    user_id: UUID,
    company_id: UUID,
    user_service: UserService = Depends(get_user_service),
) -> ResponseModel[UserResponse]:
    """
    Get a user by ID.

    Args:
        user_id: UUID of the user
        company_id: UUID of the company
        user_service: Injected UserService dependency

    Returns:
        UserResponse with user details

    Raises:
        HTTPException: 404 if user not found
    """
    logger.info(
        "Fetching user by ID",
        user_id=str(user_id),
        company_id=str(company_id),
    )

    user = await user_service.get_user_by_id(user_id, company_id)

    return ResponseModel(
        status_code=status.HTTP_200_OK,
        data=UserResponse(
            id=user.id,
            username=user.username,
            name=user.name,
            contact_no=user.contact_no,
            company_id=user.company_id,
            role=user.role,
            area_id=user.area_id,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
        ),
    )


@router.patch(
    "/{company_id}/{user_id}",
    response_model=ResponseModel[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="Update a user",
    description="Update an existing user's details (name, contact number, role, or area).",
)
async def update_user(
    company_id: UUID,
    user_id: UUID,
    request: UpdateUserRequest,
    user_service: UserService = Depends(get_user_service),
) -> ResponseModel[UserResponse]:
    """
    Update a user.

    Args:
        user_id: UUID of the user to update
        request: UpdateUserRequest with update details
        company_id: UUID of the company
        user_service: Injected UserService dependency

    Returns:
        UserResponse with updated user details

    Raises:
        HTTPException: 404 if user not found
        HTTPException: 400 if no fields provided for update or validation fails
    """
    logger.info(
        "Updating user",
        user_id=str(user_id),
        company_id=str(company_id),
    )

    # Validate at least one field is provided
    if not request.has_updates():
        user = await user_service.get_user_by_id(user_id, company_id)
    else:
        user = await user_service.update_user(
            user_id=user_id,
            company_id=company_id,
            name=request.name,
            contact_no=request.contact_no,
            role=request.role,
            area_id=request.area_id,
        )

    return ResponseModel(
        status_code=status.HTTP_200_OK,
        data=UserResponse(
            id=user.id,
            username=user.username,
            name=user.name,
            contact_no=user.contact_no,
            company_id=user.company_id,
            role=user.role,
            area_id=user.area_id,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
        ),
    )


@router.delete(
    "/{company_id}/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a user",
    description="Soft delete a user by marking them as inactive.",
)
async def delete_user(
    company_id: UUID,
    user_id: UUID,
    user_service: UserService = Depends(get_user_service),
) -> None:
    """
    Delete a user (soft delete).

    Args:
        user_id: UUID of the user to delete
        company_id: UUID of the company
        user_service: Injected UserService dependency

    Returns:
        None (204 No Content)

    Raises:
        HTTPException: 404 if user not found
    """
    logger.info(
        "Deleting user",
        user_id=str(user_id),
        company_id=str(company_id),
    )

    await user_service.delete_user(user_id, company_id)

    return
