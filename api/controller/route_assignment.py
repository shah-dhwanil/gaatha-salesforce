"""
Route Assignment controller/router for FastAPI endpoints.

This module defines all REST API endpoints for route assignment management
in a multi-tenant environment. Route assignments link users to routes for specific days.
"""

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Query, status
from fastapi.responses import Response
import structlog

from api.dependencies.route_assignment import RouteAssignmentServiceDep
from api.exceptions.route_assignment import (
    InvalidDateRangeException,
    RouteAssignmentAlreadyExistsException,
    RouteAssignmentNotFoundException,
    RouteAssignmentOperationException,
)
from api.exceptions.route import RouteNotFoundException
from api.exceptions.user import UserNotFoundException
from api.models import ListResponseModel, ResponseModel
from api.models.route_assignment import (
    RouteAssignmentCreate,
    RouteAssignmentDetailItem,
    RouteAssignmentListItem,
    RouteAssignmentResponse,
    RouteAssignmentUpdate,
)

logger = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/companies/{company_id}/route-assignments",
    tags=["Route Assignments"],
    responses={
        400: {"description": "Bad Request - Invalid input"},
        404: {"description": "Resource Not Found"},
        409: {"description": "Conflict - Resource already exists"},
        500: {"description": "Internal Server Error"},
    },
)


@router.post(
    "",
    response_model=ResponseModel[RouteAssignmentResponse],
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Route assignment created successfully"},
        400: {"description": "Validation error or invalid date range"},
        404: {"description": "Route or user not found"},
        409: {"description": "Assignment already exists for this route-user combination"},
    },
    summary="Create a new route assignment",
    description="Assign a user to a route for a specific day of the week",
)
async def create_route_assignment(
    assignment_data: RouteAssignmentCreate,
    service: RouteAssignmentServiceDep,
):
    """
    Create a new route assignment linking a user to a route for a specific day.

    **Request Body:**
    - **route_id**: ID of the route (must exist)
    - **user_id**: UUID of the user (must exist)
    - **from_date**: Assignment start date (YYYY-MM-DD)
    - **to_date**: Assignment end date (optional, None for open-ended)
    - **day**: Day of week (0=Monday through 6=Sunday)
    - **is_active**: Whether the assignment is active (default: true)

    **Day Mapping:**
    - 0 = Monday
    - 1 = Tuesday
    - 2 = Wednesday
    - 3 = Thursday
    - 4 = Friday
    - 5 = Saturday
    - 6 = Sunday

    **Constraints:**
    - Only one active assignment per route-user combination
    - to_date must be >= from_date (if provided)
    - Route and user must exist in the same tenant
    """
    try:
        assignment = await service.create_route_assignment(assignment_data)
        return ResponseModel(status_code=status.HTTP_201_CREATED, data=assignment)

    except RouteAssignmentAlreadyExistsException as e:
        logger.warning(
            "Route assignment already exists",
            route_id=assignment_data.route_id,
            user_id=str(assignment_data.user_id),
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        )

    except InvalidDateRangeException as e:
        logger.warning(
            "Invalid date range for route assignment",
            route_id=assignment_data.route_id,
            from_date=str(assignment_data.from_date),
            to_date=str(assignment_data.to_date),
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )

    except RouteNotFoundException as e:
        logger.warning(
            "Route not found for assignment",
            route_id=assignment_data.route_id,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except UserNotFoundException as e:
        logger.warning(
            "User not found for assignment",
            user_id=str(assignment_data.user_id),
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except RouteAssignmentOperationException as e:
        logger.error(
            "Failed to create route assignment",
            route_id=assignment_data.route_id,
            user_id=str(assignment_data.user_id),
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create route assignment",
        )

    except Exception as e:
        logger.error(
            "Unexpected error creating route assignment",
            route_id=assignment_data.route_id,
            user_id=str(assignment_data.user_id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create route assignment",
        )


@router.get(
    "/{assignment_id}",
    response_model=ResponseModel[RouteAssignmentDetailItem],
    responses={
        200: {"description": "Route assignment retrieved successfully"},
        404: {"description": "Route assignment not found"},
    },
    summary="Get route assignment by ID",
    description="Retrieve detailed information about a specific route assignment",
)
async def get_route_assignment(
    assignment_id: Annotated[int, Path(description="Route assignment ID", ge=1)],
    service: RouteAssignmentServiceDep,
):
    """
    Get a route assignment by ID.

    Returns complete assignment information including:
    - All assignment fields (id, route_id, user_id, dates, day, is_active)
    - Route details (name, code)
    - User details (name, username)
    - Timestamps (created_at, updated_at)
    """
    try:
        assignment = await service.get_route_assignment_by_id(assignment_id)
        return ResponseModel(status_code=status.HTTP_200_OK, data=assignment)

    except RouteAssignmentNotFoundException as e:
        logger.info(
            "Route assignment not found",
            assignment_id=assignment_id,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to get route assignment",
            assignment_id=assignment_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve route assignment",
        )


@router.get(
    "",
    response_model=ListResponseModel[RouteAssignmentListItem],
    responses={
        200: {"description": "Route assignments retrieved successfully"},
        400: {"description": "Invalid parameters"},
    },
    summary="List all route assignments",
    description="List route assignments with pagination and optional filtering",
)
async def list_route_assignments(
    service: RouteAssignmentServiceDep,
    route_id: Annotated[
        int | None,
        Query(description="Filter by route ID", ge=1),
    ] = None,
    user_id: Annotated[
        UUID | None,
        Query(description="Filter by user ID (UUID)"),
    ] = None,
    day: Annotated[
        int | None,
        Query(description="Filter by day of week (0=Monday, 6=Sunday)", ge=0, le=6),
    ] = None,
    is_active: Annotated[
        bool | None,
        Query(description="Filter by active status (true/false, optional)"),
    ] = None,
    from_date: Annotated[
        date | None,
        Query(description="Filter assignments starting from this date"),
    ] = None,
    to_date: Annotated[
        date | None,
        Query(description="Filter assignments ending before this date"),
    ] = None,
    limit: Annotated[
        int,
        Query(ge=1, le=100, description="Number of assignments to return (1-100)"),
    ] = 20,
    offset: Annotated[
        int,
        Query(ge=0, description="Number of assignments to skip (pagination)"),
    ] = 0,
):
    """
    List all route assignments with pagination and filtering.

    Returns optimized assignment data with route and user names.
    Use the detail endpoint (GET /{assignment_id}) to get complete assignment information.

    **Filters:**
    - **route_id**: Filter by specific route
    - **user_id**: Filter by specific user
    - **day**: Filter by day of week (0=Monday through 6=Sunday)
    - **is_active**: Filter by active status
    - **from_date**: Filter assignments starting from this date
    - **to_date**: Filter assignments ending before this date
    - **limit**: Results per page (default: 20, max: 100)
    - **offset**: Skip results for pagination (default: 0)

    **Examples:**
    - List all active assignments: `?is_active=true`
    - List assignments for route 5: `?route_id=5`
    - List Monday assignments: `?day=0&is_active=true`
    - List user's assignments: `?user_id={uuid}`
    """
    try:
        assignments, total_count = await service.list_route_assignments(
            route_id=route_id,
            user_id=user_id,
            day=day,
            is_active=is_active,
            from_date=from_date,
            to_date=to_date,
            limit=limit,
            offset=offset,
        )

        return ListResponseModel(
            status_code=status.HTTP_200_OK,
            data=assignments,
            records_per_page=limit,
            total_count=total_count,
        )

    except RouteAssignmentOperationException as e:
        logger.warning(
            "Invalid parameters for list route assignments",
            route_id=route_id,
            user_id=str(user_id) if user_id else None,
            day=day,
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
            "Failed to list route assignments",
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list route assignments",
        )


@router.patch(
    "/{assignment_id}",
    response_model=ResponseModel[RouteAssignmentResponse],
    responses={
        200: {"description": "Route assignment updated successfully"},
        400: {"description": "Validation error or invalid date range"},
        404: {"description": "Route assignment not found"},
    },
    summary="Update a route assignment",
    description="Update route assignment details (route_id and user_id cannot be changed)",
)
async def update_route_assignment(
    assignment_id: Annotated[int, Path(description="Route assignment ID", ge=1)],
    assignment_data: RouteAssignmentUpdate,
    service: RouteAssignmentServiceDep,
):
    """
    Update an existing route assignment.

    **Updatable Fields:**
    - **from_date**: Change the start date
    - **to_date**: Change the end date (or set to None for open-ended)
    - **day**: Change the day of week (0-6)

    **Note**: 
    - route_id and user_id cannot be updated after creation
    - At least one field must be provided for update
    - to_date must be >= from_date (if both are provided)
    """
    try:
        assignment = await service.update_route_assignment(
            assignment_id, assignment_data
        )
        return ResponseModel(status_code=status.HTTP_200_OK, data=assignment)

    except RouteAssignmentNotFoundException as e:
        logger.info(
            "Route assignment not found for update",
            assignment_id=assignment_id,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except InvalidDateRangeException as e:
        logger.warning(
            "Invalid date range for route assignment update",
            assignment_id=assignment_id,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )

    except RouteAssignmentOperationException as e:
        logger.warning(
            "Route assignment update validation failed",
            assignment_id=assignment_id,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to update route assignment",
            assignment_id=assignment_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update route assignment",
        )


@router.delete(
    "/{assignment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Route assignment deactivated successfully"},
        404: {"description": "Route assignment not found"},
    },
    summary="Delete a route assignment (soft delete)",
    description="Soft delete a route assignment by setting is_active to false",
)
async def delete_route_assignment(
    assignment_id: Annotated[int, Path(description="Route assignment ID", ge=1)],
    service: RouteAssignmentServiceDep,
):
    """
    Delete a route assignment (soft delete).

    Sets is_active to false instead of permanently deleting the assignment.
    The assignment will still exist in the database but won't be active.
    This maintains historical data for audit trails.
    """
    try:
        await service.delete_route_assignment(assignment_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except RouteAssignmentNotFoundException as e:
        logger.info(
            "Route assignment not found for deletion",
            assignment_id=assignment_id,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to delete route assignment",
            assignment_id=assignment_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete route assignment",
        )


@router.get(
    "/route/{route_id}/assignments",
    response_model=ListResponseModel[RouteAssignmentListItem],
    responses={
        200: {"description": "Route assignments retrieved successfully"},
    },
    summary="Get assignments by route",
    description="Get all assignments for a specific route",
)
async def get_assignments_by_route(
    route_id: Annotated[int, Path(description="Route ID", ge=1)],
    service: RouteAssignmentServiceDep,
    is_active: Annotated[
        bool,
        Query(description="Filter by active status"),
    ] = True,
):
    """
    Get all assignments for a specific route.

    Returns all route assignments (active by default) for the specified route.
    Useful for viewing who is assigned to a route across different days.

    **Parameters:**
    - **route_id**: ID of the route
    - **is_active**: Filter by active status (default: true)
    """
    try:
        assignments = await service.get_assignments_by_route(route_id, is_active)
        return ListResponseModel(
            status_code=status.HTTP_200_OK,
            data=assignments,
            records_per_page=len(assignments),
            total_count=len(assignments),
        )

    except Exception as e:
        logger.error(
            "Failed to get assignments by route",
            route_id=route_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get route assignments",
        )


@router.get(
    "/user/{user_id}/assignments",
    response_model=ListResponseModel[RouteAssignmentListItem],
    responses={
        200: {"description": "User assignments retrieved successfully"},
    },
    summary="Get assignments by user",
    description="Get all assignments for a specific user",
)
async def get_assignments_by_user(
    user_id: Annotated[UUID, Path(description="User ID (UUID)")],
    service: RouteAssignmentServiceDep,
    is_active: Annotated[
        bool,
        Query(description="Filter by active status"),
    ] = True,
):
    """
    Get all assignments for a specific user.

    Returns all route assignments (active by default) for the specified user.
    Useful for viewing a user's weekly route schedule.

    **Parameters:**
    - **user_id**: UUID of the user
    - **is_active**: Filter by active status (default: true)
    """
    try:
        assignments = await service.get_assignments_by_user(user_id, is_active)
        return ListResponseModel(
            status_code=status.HTTP_200_OK,
            data=assignments,
            records_per_page=len(assignments),
            total_count=len(assignments),
        )

    except Exception as e:
        logger.error(
            "Failed to get assignments by user",
            user_id=str(user_id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user assignments",
        )


@router.get(
    "/day/{day}/assignments",
    response_model=ListResponseModel[RouteAssignmentListItem],
    responses={
        200: {"description": "Day assignments retrieved successfully"},
        400: {"description": "Invalid day value"},
    },
    summary="Get assignments by day",
    description="Get all assignments for a specific day of the week",
)
async def get_assignments_by_day(
    day: Annotated[int, Path(description="Day of week (0=Monday, 6=Sunday)", ge=0, le=6)],
    service: RouteAssignmentServiceDep,
    is_active: Annotated[
        bool,
        Query(description="Filter by active status"),
    ] = True,
):
    """
    Get all assignments for a specific day of the week.

    Returns all route assignments (active by default) for the specified day.
    Useful for viewing the daily schedule across all routes and users.

    **Day Mapping:**
    - 0 = Monday
    - 1 = Tuesday
    - 2 = Wednesday
    - 3 = Thursday
    - 4 = Friday
    - 5 = Saturday
    - 6 = Sunday

    **Parameters:**
    - **day**: Day of week (0-6)
    - **is_active**: Filter by active status (default: true)
    """
    try:
        assignments = await service.get_assignments_by_day(day, is_active)
        return ListResponseModel(
            status_code=status.HTTP_200_OK,
            data=assignments,
            records_per_page=len(assignments),
            total_count=len(assignments),
        )

    except RouteAssignmentOperationException as e:
        logger.warning(
            "Invalid day value",
            day=day,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to get assignments by day",
            day=day,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get day assignments",
        )


@router.get(
    "/count/active",
    response_model=ResponseModel[dict],
    responses={
        200: {"description": "Count retrieved successfully"},
    },
    summary="Get active assignments count",
    description="Get the total count of active route assignments with optional filters",
)
async def get_active_assignments_count(
    service: RouteAssignmentServiceDep,
    route_id: Annotated[
        int | None,
        Query(description="Optional filter by route ID", ge=1),
    ] = None,
    user_id: Annotated[
        UUID | None,
        Query(description="Optional filter by user ID"),
    ] = None,
    day: Annotated[
        int | None,
        Query(description="Optional filter by day of week (0-6)", ge=0, le=6),
    ] = None,
):
    """
    Get count of active route assignments.

    Returns the total number of assignments with is_active=true.
    Optionally filter by route, user, and/or day.

    **Filters:**
    - **route_id**: Count assignments for specific route
    - **user_id**: Count assignments for specific user
    - **day**: Count assignments for specific day of week
    """
    try:
        count = await service.get_active_assignments_count(
            route_id=route_id,
            user_id=user_id,
            day=day,
        )
        filters = {
            "route_id": route_id,
            "user_id": str(user_id) if user_id else None,
            "day": day,
        }
        active_filters = {k: v for k, v in filters.items() if v is not None}

        return ResponseModel(
            status_code=status.HTTP_200_OK,
            data={
                "active_count": count,
                "filters": active_filters if active_filters else "none",
            },
        )

    except Exception as e:
        logger.error(
            "Failed to get active assignments count",
            route_id=route_id,
            user_id=str(user_id) if user_id else None,
            day=day,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get active assignments count",
        )

