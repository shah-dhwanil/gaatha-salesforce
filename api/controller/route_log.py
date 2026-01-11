"""
Route Log controller/router for FastAPI endpoints.

This module defines all REST API endpoints for route log management
in a multi-tenant environment. Route logs track daily route execution details.
"""

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Query, status
import structlog

from api.dependencies.route_log import RouteLogServiceDep
from api.exceptions.route_log import (
    RouteLogNotFoundException,
    RouteLogOperationException,
    RouteLogValidationException,
)
from api.models import ListResponseModel, ResponseModel
from api.models.route_log import (
    RouteLogCreate,
    RouteLogListItem,
    RouteLogResponse,
    RouteLogUpdate,
)

logger = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/companies/{company_id}/route-logs",
    tags=["Route Logs"],
    responses={
        400: {"description": "Bad Request - Invalid input"},
        404: {"description": "Resource Not Found"},
        500: {"description": "Internal Server Error"},
    },
)


@router.post(
    "",
    response_model=ResponseModel[RouteLogResponse],
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Route log created successfully"},
        400: {"description": "Validation error or invalid time range"},
        404: {"description": "Route assignment not found"},
    },
    summary="Create a new route log",
    description="Create a route log entry for a specific route assignment",
)
async def create_route_log(
    route_log_data: RouteLogCreate,
    service: RouteLogServiceDep,
):
    """
    Create a new route log entry for tracking route execution.

    **Request Body:**
    - **route_assignment_id**: ID of the route assignment (must exist)
    - **co_worker_id**: UUID of the co-worker (optional)
    - **date**: Date of the route log (YYYY-MM-DD)
    - **start_time**: Start time of the route (HH:MM:SS)
    - **end_time**: End time of the route (optional, HH:MM:SS)

    **Constraints:**
    - end_time must be after start_time (if provided)
    - Route assignment must exist in the same tenant
    """
    try:
        route_log = await service.create_route_log(route_log_data)
        return ResponseModel(status_code=status.HTTP_201_CREATED, data=route_log)

    except RouteLogValidationException as e:
        logger.warning(
            "Route log validation failed",
            route_assignment_id=route_log_data.route_assignment_id,
            date=str(route_log_data.date),
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )

    except RouteLogOperationException as e:
        logger.error(
            "Failed to create route log",
            route_assignment_id=route_log_data.route_assignment_id,
            date=str(route_log_data.date),
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Unexpected error creating route log",
            route_assignment_id=route_log_data.route_assignment_id,
            date=str(route_log_data.date),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create route log",
        )


@router.get(
    "/{route_log_id}",
    response_model=ResponseModel[RouteLogResponse],
    responses={
        200: {"description": "Route log retrieved successfully"},
        404: {"description": "Route log not found"},
    },
    summary="Get route log by ID",
    description="Retrieve detailed information about a specific route log",
)
async def get_route_log(
    route_log_id: Annotated[int, Path(description="Route log ID", ge=1)],
    service: RouteLogServiceDep,
):
    """
    Get a route log by ID.

    Returns complete route log information including:
    - All route log fields (id, route_assignment_id, co_worker_id, date, times)
    - Timestamps (created_at, updated_at)
    """
    try:
        route_log = await service.get_route_log_by_id(route_log_id)
        return ResponseModel(status_code=status.HTTP_200_OK, data=route_log)

    except RouteLogNotFoundException as e:
        logger.info(
            "Route log not found",
            route_log_id=route_log_id,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to get route log",
            route_log_id=route_log_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve route log",
        )


@router.get(
    "",
    response_model=ListResponseModel[RouteLogListItem],
    responses={
        200: {"description": "Route logs retrieved successfully"},
        400: {"description": "Invalid parameters"},
    },
    summary="List all route logs",
    description="List route logs with pagination and optional filtering",
)
async def list_route_logs(
    service: RouteLogServiceDep,
    route_assignment_id: Annotated[
        int | None,
        Query(description="Filter by route assignment ID", ge=1),
    ] = None,
    co_worker_id: Annotated[
        UUID | None,
        Query(description="Filter by co-worker ID (UUID)"),
    ] = None,
    date_from: Annotated[
        date | None,
        Query(description="Filter logs from this date (inclusive)"),
    ] = None,
    date_to: Annotated[
        date | None,
        Query(description="Filter logs until this date (inclusive)"),
    ] = None,
    limit: Annotated[
        int,
        Query(ge=1, le=100, description="Number of logs to return (1-100)"),
    ] = 20,
    offset: Annotated[
        int,
        Query(ge=0, description="Number of logs to skip (pagination)"),
    ] = 0,
):
    """
    List all route logs with pagination and filtering.

    Returns route log data with minimal fields for performance.
    Use the detail endpoint (GET /{route_log_id}) to get complete information.

    **Filters:**
    - **route_assignment_id**: Filter by specific route assignment
    - **co_worker_id**: Filter by specific co-worker
    - **date_from**: Filter logs from this date (inclusive)
    - **date_to**: Filter logs until this date (inclusive)
    - **limit**: Results per page (default: 20, max: 100)
    - **offset**: Skip results for pagination (default: 0)

    **Examples:**
    - List logs for assignment 5: `?route_assignment_id=5`
    - List logs for date range: `?date_from=2025-01-01&date_to=2025-01-31`
    - List co-worker's logs: `?co_worker_id={uuid}`
    """
    try:
        route_logs, total_count = await service.list_route_logs(
            route_assignment_id=route_assignment_id,
            co_worker_id=co_worker_id,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            offset=offset,
        )

        return ListResponseModel(
            status_code=status.HTTP_200_OK,
            data=route_logs,
            records_per_page=limit,
            total_count=total_count,
        )

    except RouteLogValidationException as e:
        logger.warning(
            "Invalid parameters for list route logs",
            route_assignment_id=route_assignment_id,
            co_worker_id=str(co_worker_id) if co_worker_id else None,
            date_from=str(date_from) if date_from else None,
            date_to=str(date_to) if date_to else None,
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
            "Failed to list route logs",
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list route logs",
        )


@router.patch(
    "/{route_log_id}",
    response_model=ResponseModel[RouteLogResponse],
    responses={
        200: {"description": "Route log updated successfully"},
        400: {"description": "Validation error or invalid time range"},
        404: {"description": "Route log not found"},
    },
    summary="Update a route log",
    description="Update route log details (route_assignment_id cannot be changed)",
)
async def update_route_log(
    route_log_id: Annotated[int, Path(description="Route log ID", ge=1)],
    route_log_data: RouteLogUpdate,
    service: RouteLogServiceDep,
):
    """
    Update an existing route log.

    **Updatable Fields:**
    - **co_worker_id**: Change the co-worker (or set to None)
    - **date**: Change the date
    - **start_time**: Change the start time
    - **end_time**: Change the end time (or set to None)

    **Note**:
    - route_assignment_id cannot be updated after creation
    - At least one field must be provided for update
    - end_time must be after start_time (if both are provided)
    """
    try:
        route_log = await service.update_route_log(route_log_id, route_log_data)
        return ResponseModel(status_code=status.HTTP_200_OK, data=route_log)

    except RouteLogNotFoundException as e:
        logger.info(
            "Route log not found for update",
            route_log_id=route_log_id,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except RouteLogValidationException as e:
        logger.warning(
            "Route log update validation failed",
            route_log_id=route_log_id,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )

    except RouteLogOperationException as e:
        logger.warning(
            "Route log update operation failed",
            route_log_id=route_log_id,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to update route log",
            route_log_id=route_log_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update route log",
        )


# @router.delete(
#     "/{route_log_id}",
#     status_code=status.HTTP_204_NO_CONTENT,
#     responses={
#         204: {"description": "Route log deleted successfully"},
#         404: {"description": "Route log not found"},
#     },
#     summary="Delete a route log",
#     description="Permanently delete a route log entry",
# )
# async def delete_route_log(
#     route_log_id: Annotated[int, Path(description="Route log ID", ge=1)],
#     service: RouteLogServiceDep,
# ):
#     """
#     Delete a route log (hard delete).

#     Permanently removes the route log from the database.
#     This action cannot be undone.
#     """
#     try:
#         await service.delete_route_log(route_log_id)
#         return Response(status_code=status.HTTP_204_NO_CONTENT)

#     except RouteLogNotFoundException as e:
#         logger.info(
#             "Route log not found for deletion",
#             route_log_id=route_log_id,
#             error=e.message,
#         )
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=e.message,
#         )

#     except Exception as e:
#         logger.error(
#             "Failed to delete route log",
#             route_log_id=route_log_id,
#             error=str(e),
#         )
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Failed to delete route log",
#         )


@router.get(
    "/route-assignment/{route_assignment_id}/logs",
    response_model=ListResponseModel[RouteLogListItem],
    responses={
        200: {"description": "Route logs retrieved successfully"},
    },
    summary="Get logs by route assignment",
    description="Get all logs for a specific route assignment",
)
async def get_logs_by_route_assignment(
    route_assignment_id: Annotated[int, Path(description="Route assignment ID", ge=1)],
    service: RouteLogServiceDep,
):
    """
    Get all logs for a specific route assignment.

    Returns all route logs for the specified route assignment.
    Useful for viewing the execution history of a specific assignment.

    **Parameters:**
    - **route_assignment_id**: ID of the route assignment
    """
    try:
        route_logs = await service.get_route_logs_by_route_assignment(
            route_assignment_id
        )
        return ListResponseModel(
            status_code=status.HTTP_200_OK,
            data=route_logs,
            records_per_page=len(route_logs),
            total_count=len(route_logs),
        )

    except Exception as e:
        logger.error(
            "Failed to get logs by route assignment",
            route_assignment_id=route_assignment_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get route logs",
        )


@router.get(
    "/co-worker/{co_worker_id}/logs",
    response_model=ListResponseModel[RouteLogListItem],
    responses={
        200: {"description": "Co-worker logs retrieved successfully"},
    },
    summary="Get logs by co-worker",
    description="Get all logs for a specific co-worker with optional date filtering",
)
async def get_logs_by_co_worker(
    co_worker_id: Annotated[UUID, Path(description="Co-worker ID (UUID)")],
    service: RouteLogServiceDep,
    date_from: Annotated[
        date | None,
        Query(description="Filter logs from this date (inclusive)"),
    ] = None,
    date_to: Annotated[
        date | None,
        Query(description="Filter logs until this date (inclusive)"),
    ] = None,
):
    """
    Get all logs for a specific co-worker.

    Returns all route logs for the specified co-worker.
    Optionally filter by date range.

    **Parameters:**
    - **co_worker_id**: UUID of the co-worker
    - **date_from**: Optional start date filter (inclusive)
    - **date_to**: Optional end date filter (inclusive)
    """
    try:
        route_logs = await service.get_route_logs_by_co_worker(
            co_worker_id, date_from, date_to
        )
        return ListResponseModel(
            status_code=status.HTTP_200_OK,
            data=route_logs,
            records_per_page=len(route_logs),
            total_count=len(route_logs),
        )

    except Exception as e:
        logger.error(
            "Failed to get logs by co-worker",
            co_worker_id=str(co_worker_id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get co-worker logs",
        )


@router.get(
    "/date-range/logs",
    response_model=ListResponseModel[RouteLogListItem],
    responses={
        200: {"description": "Route logs retrieved successfully"},
        400: {"description": "Invalid date range"},
    },
    summary="Get logs by date range",
    description="Get all logs within a specific date range",
)
async def get_logs_by_date_range(
    service: RouteLogServiceDep,
    date_from: Annotated[
        date,
        Query(description="Start date (inclusive)"),
    ],
    date_to: Annotated[
        date,
        Query(description="End date (inclusive)"),
    ],
):
    """
    Get all logs within a specific date range.

    Returns all route logs within the specified date range.
    Useful for generating reports or viewing historical data.

    **Parameters:**
    - **date_from**: Start date (inclusive, required)
    - **date_to**: End date (inclusive, required)
    """
    try:
        route_logs = await service.get_route_logs_by_date_range(date_from, date_to)
        return ListResponseModel(
            status_code=status.HTTP_200_OK,
            data=route_logs,
            records_per_page=len(route_logs),
            total_count=len(route_logs),
        )

    except RouteLogValidationException as e:
        logger.warning(
            "Invalid date range for route logs",
            date_from=str(date_from),
            date_to=str(date_to),
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to get logs by date range",
            date_from=str(date_from),
            date_to=str(date_to),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get route logs",
        )


@router.get(
    "/count",
    response_model=ResponseModel[dict],
    responses={
        200: {"description": "Count retrieved successfully"},
    },
    summary="Get route logs count",
    description="Get the total count of route logs with optional filters",
)
async def get_route_logs_count(
    service: RouteLogServiceDep,
    route_assignment_id: Annotated[
        int | None,
        Query(description="Optional filter by route assignment ID", ge=1),
    ] = None,
    co_worker_id: Annotated[
        UUID | None,
        Query(description="Optional filter by co-worker ID"),
    ] = None,
    date_from: Annotated[
        date | None,
        Query(description="Optional filter by start date (inclusive)"),
    ] = None,
    date_to: Annotated[
        date | None,
        Query(description="Optional filter by end date (inclusive)"),
    ] = None,
):
    """
    Get count of route logs.

    Returns the total number of route logs.
    Optionally filter by route assignment, co-worker, and/or date range.

    **Filters:**
    - **route_assignment_id**: Count logs for specific route assignment
    - **co_worker_id**: Count logs for specific co-worker
    - **date_from**: Count logs from this date (inclusive)
    - **date_to**: Count logs until this date (inclusive)
    """
    try:
        count = await service.get_route_logs_count(
            route_assignment_id=route_assignment_id,
            co_worker_id=co_worker_id,
            date_from=date_from,
            date_to=date_to,
        )
        filters = {
            "route_assignment_id": route_assignment_id,
            "co_worker_id": str(co_worker_id) if co_worker_id else None,
            "date_from": str(date_from) if date_from else None,
            "date_to": str(date_to) if date_to else None,
        }
        active_filters = {k: v for k, v in filters.items() if v is not None}

        return ResponseModel(
            status_code=status.HTTP_200_OK,
            data={
                "count": count,
                "filters": active_filters if active_filters else "none",
            },
        )

    except Exception as e:
        logger.error(
            "Failed to get route logs count",
            route_assignment_id=route_assignment_id,
            co_worker_id=str(co_worker_id) if co_worker_id else None,
            date_from=str(date_from) if date_from else None,
            date_to=str(date_to) if date_to else None,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get route logs count",
        )
