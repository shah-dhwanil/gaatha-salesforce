"""
Route controller/router for FastAPI endpoints.

This module defines all REST API endpoints for route management
in a multi-tenant environment. Routes belong to areas within the hierarchy.
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, status
from fastapi.responses import Response
import structlog

from api.dependencies.route import RouteServiceDep
from api.exceptions.route import (
    RouteAlreadyExistsException,
    RouteNotFoundException,
    RouteOperationException,
    RouteValidationException,
)
from api.models import ListResponseModel, ResponseModel
from api.models.route import (
    RouteCreate,
    RouteDetailItem,
    RouteListItem,
    RouteResponse,
    RouteUpdate,
)

logger = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/companies/{company_id}/routes",
    tags=["Routes"],
    responses={
        400: {"description": "Bad Request - Invalid input"},
        404: {"description": "Resource Not Found"},
        500: {"description": "Internal Server Error"},
    },
)


@router.post(
    "",
    response_model=ResponseModel[RouteResponse],
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Route created successfully"},
        400: {"description": "Validation error"},
        404: {"description": "Area not found"},
        409: {"description": "Route already exists (duplicate code)"},
    },
    summary="Create a new route",
    description="Create a new route associated with an area",
)
async def create_route(
    route_data: RouteCreate,
    route_service: RouteServiceDep,
):
    """
    Create a new route in the system.

    Routes are associated with a division (area) and can have multiple type flags:
    - **is_general**: General trade route
    - **is_modern**: Modern trade route
    - **is_horeca**: Hotel/Restaurant/Café route

    **Request Body:**
    - **name**: Route name (1-32 characters)
    - **code**: Unique route code (1-32 characters)
    - **area_id**: ID of the area (division) this route belongs to
    - **is_general**: Whether this is a general trade route (default: false)
    - **is_modern**: Whether this is a modern trade route (default: false)
    - **is_horeca**: Whether this is a horeca route (default: false)
    - **is_active**: Whether the route is active (default: true)

    **Note**: Multiple type flags can be true simultaneously.
    """
    try:
        route = await route_service.create_route(route_data)
        return ResponseModel(status_code=status.HTTP_201_CREATED, data=route)

    except RouteAlreadyExistsException as e:
        logger.warning(
            "Route already exists",
            route_code=route_data.code,
            route_name=route_data.name,
            error=e.message,
        )
        raise e

    except RouteOperationException as e:
        if "Area with id" in e.message:
            logger.warning(
                "Area not found for route",
                route_name=route_data.name,
                area_id=route_data.area_id,
                error=e.message,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=e.message,
            )
        logger.error(
            "Failed to create route",
            route_name=route_data.name,
            route_code=route_data.code,
            error=e.message,
        )
        raise e

    except Exception as e:
        logger.error(
            "Unexpected error creating route",
            route_name=route_data.name,
            route_code=route_data.code,
            error=str(e),
        )
        raise e


@router.get(
    "/{route_id}",
    response_model=ResponseModel[RouteDetailItem],
    responses={
        200: {"description": "Route retrieved successfully"},
        404: {"description": "Route not found"},
    },
    summary="Get route by ID",
    description="Retrieve detailed information about a specific route including full hierarchy",
)
async def get_route(
    route_id: Annotated[int, Path(description="Route ID", ge=1)],
    route_service: RouteServiceDep,
):
    """
    Get a route by ID.

    Returns complete route information including:
    - All route fields (id, name, code, area_id, type flags)
    - Full hierarchical context (division, area, region, zone, nation names)
    - Timestamps (created_at, updated_at)
    - Active status
    """
    try:
        route = await route_service.get_route_by_id(route_id)
        return ResponseModel(status_code=status.HTTP_200_OK, data=route)

    except RouteNotFoundException as e:
        logger.info(
            "Route not found",
            route_id=route_id,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to get route",
            route_id=route_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve route",
        )


@router.get(
    "/by-code/{code}",
    response_model=ResponseModel[RouteDetailItem],
    responses={
        200: {"description": "Route retrieved successfully"},
        404: {"description": "Route not found"},
    },
    summary="Get route by code",
    description="Retrieve a route by its unique code",
)
async def get_route_by_code(
    code: Annotated[str, Path(description="Route code")],
    route_service: RouteServiceDep,
):
    """
    Get a route by its unique code.

    Returns complete route information including full hierarchical context.
    Only returns active routes.
    """
    try:
        route = await route_service.get_route_by_code(code)
        return ResponseModel(status_code=status.HTTP_200_OK, data=route)

    except RouteNotFoundException as e:
        logger.info(
            "Route not found by code",
            route_code=code,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to get route by code",
            route_code=code,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve route",
        )


@router.get(
    "",
    response_model=ListResponseModel[RouteListItem],
    responses={
        200: {"description": "Routes retrieved successfully"},
        400: {"description": "Invalid parameters"},
    },
    summary="List all routes",
    description="List routes with pagination and optional filtering by area, status, and route types",
)
async def list_routes(
    route_service: RouteServiceDep,
    area_id: Annotated[
        int | None,
        Query(description="Filter by area (division) ID", ge=1),
    ] = None,
    is_active: Annotated[
        bool | None,
        Query(description="Filter by active status (true/false, optional)"),
    ] = None,
    is_general: Annotated[
        bool | None,
        Query(description="Filter by general trade route status"),
    ] = None,
    is_modern: Annotated[
        bool | None,
        Query(description="Filter by modern trade route status"),
    ] = None,
    is_horeca: Annotated[
        bool | None,
        Query(description="Filter by horeca route status"),
    ] = None,
    limit: Annotated[
        int,
        Query(ge=1, le=100, description="Number of routes to return (1-100)"),
    ] = 20,
    offset: Annotated[
        int,
        Query(ge=0, description="Number of routes to skip (pagination)"),
    ] = 0,
):
    """
    List all routes with pagination and filtering.

    Returns optimized route data with minimal hierarchical information (division, area, region)
    and retailer count for each route.
    Use the detail endpoint (GET /{route_id}) to get complete route information.

    **Filters:**
    - **area_id**: Filter by specific area (division)
    - **is_active**: Filter by active status
    - **is_general**: Filter by general trade routes
    - **is_modern**: Filter by modern trade routes
    - **is_horeca**: Filter by horeca routes
    - **limit**: Results per page (default: 20, max: 100)
    - **offset**: Skip results for pagination (default: 0)

    **Examples:**
    - List all active general routes: `?is_active=true&is_general=true`
    - List routes in area 5: `?area_id=5`
    - List modern and horeca routes: `?is_modern=true&is_horeca=true`
    """
    try:
        routes, total_count = await route_service.list_routes(
            area_id=area_id,
            is_active=is_active,
            is_general=is_general,
            is_modern=is_modern,
            is_horeca=is_horeca,
            limit=limit,
            offset=offset,
        )

        return ListResponseModel(
            status_code=status.HTTP_200_OK,
            data=routes,
            records_per_page=limit,
            total_count=total_count,
        )

    except RouteValidationException as e:
        logger.warning(
            "Invalid parameters for list routes",
            area_id=area_id,
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
            "Failed to list routes",
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list routes",
        )


@router.patch(
    "/{route_id}",
    response_model=ResponseModel[RouteResponse],
    responses={
        200: {"description": "Route updated successfully"},
        400: {"description": "Validation error"},
        404: {"description": "Route not found"},
    },
    summary="Update a route",
    description="Update route details (code cannot be changed)",
)
async def update_route(
    route_id: Annotated[int, Path(description="Route ID", ge=1)],
    route_data: RouteUpdate,
    route_service: RouteServiceDep,
):
    """
    Update an existing route.

    **Updatable Fields:**
    - **name**: Route name
    - **is_general**: General trade route flag
    - **is_modern**: Modern trade route flag
    - **is_horeca**: Horeca route flag

    **Note**:
    - Route code cannot be updated after creation
    - At least one field must be provided for update
    - Multiple type flags can be set simultaneously
    """
    try:
        route = await route_service.update_route(route_id, route_data)
        return ResponseModel(status_code=status.HTTP_200_OK, data=route)

    except RouteNotFoundException as e:
        logger.info(
            "Route not found for update",
            route_id=route_id,
            error=e.message,
        )
        raise e

    except RouteValidationException as e:
        logger.warning(
            "Route update validation failed",
            route_id=route_id,
            error=e.message,
        )
        raise e
    except Exception as e:
        logger.error(
            "Failed to update route",
            route_id=route_id,
            error=str(e),
        )
        raise e


@router.delete(
    "/{route_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Route deactivated successfully"},
        404: {"description": "Route not found"},
    },
    summary="Delete a route (soft delete)",
    description="Soft delete a route by setting is_active to false",
)
async def delete_route(
    route_id: Annotated[int, Path(description="Route ID", ge=1)],
    route_service: RouteServiceDep,
):
    """
    Delete a route (soft delete).

    Sets is_active to false instead of permanently deleting the route.
    The route will still exist in the database but won't be active.
    """
    try:
        await route_service.delete_route(route_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except RouteNotFoundException as e:
        logger.info(
            "Route not found for deletion",
            route_id=route_id,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to delete route",
            route_id=route_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete route",
        )


@router.get(
    "/area/{area_id}/routes",
    response_model=ListResponseModel[RouteListItem],
    responses={
        200: {"description": "Routes retrieved successfully"},
    },
    summary="Get routes by area",
    description="Get all active routes for a specific area",
)
async def get_routes_by_area(
    area_id: Annotated[int, Path(description="Area ID", ge=1)],
    route_service: RouteServiceDep,
):
    """
    Get all active routes for a specific area.

    Returns full route information for all active routes in the area.
    Useful for populating dropdowns or viewing area assignments.
    """
    try:
        routes = await route_service.get_routes_by_area(area_id)
        return ListResponseModel(
            status_code=status.HTTP_200_OK,
            data=routes,
            records_per_page=len(routes),
            total_count=len(routes),
        )

    except Exception as e:
        logger.error(
            "Failed to get routes by area",
            area_id=area_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get routes",
        )


@router.get(
    "/types/general",
    response_model=ResponseModel[list[RouteListItem]],
    responses={
        200: {"description": "General routes retrieved successfully"},
    },
    summary="Get general trade routes",
    description="Get all active general trade routes",
)
async def get_general_routes(
    route_service: RouteServiceDep,
    area_id: Annotated[
        int | None,
        Query(description="Optional filter by area ID", ge=1),
    ] = None,
    limit: Annotated[
        int,
        Query(ge=1, le=100, description="Number of routes to return (1-100)"),
    ] = 100,
):
    """
    Get all active general trade routes.

    Optionally filter by area. Returns routes where is_general=true.
    """
    try:
        routes = await route_service.get_general_routes(area_id=area_id, limit=limit)
        return ResponseModel(status_code=status.HTTP_200_OK, data=routes)

    except Exception as e:
        logger.error(
            "Failed to get general routes",
            area_id=area_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get general routes",
        )


@router.get(
    "/types/modern",
    response_model=ResponseModel[list[RouteListItem]],
    responses={
        200: {"description": "Modern routes retrieved successfully"},
    },
    summary="Get modern trade routes",
    description="Get all active modern trade routes",
)
async def get_modern_routes(
    route_service: RouteServiceDep,
    area_id: Annotated[
        int | None,
        Query(description="Optional filter by area ID", ge=1),
    ] = None,
    limit: Annotated[
        int,
        Query(ge=1, le=100, description="Number of routes to return (1-100)"),
    ] = 100,
):
    """
    Get all active modern trade routes.

    Optionally filter by area. Returns routes where is_modern=true.
    """
    try:
        routes = await route_service.get_modern_routes(area_id=area_id, limit=limit)
        return ResponseModel(status_code=status.HTTP_200_OK, data=routes)

    except Exception as e:
        logger.error(
            "Failed to get modern routes",
            area_id=area_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get modern routes",
        )


@router.get(
    "/types/horeca",
    response_model=ResponseModel[list[RouteListItem]],
    responses={
        200: {"description": "Horeca routes retrieved successfully"},
    },
    summary="Get horeca routes",
    description="Get all active horeca (Hotel/Restaurant/Café) routes",
)
async def get_horeca_routes(
    route_service: RouteServiceDep,
    area_id: Annotated[
        int | None,
        Query(description="Optional filter by area ID", ge=1),
    ] = None,
    limit: Annotated[
        int,
        Query(ge=1, le=100, description="Number of routes to return (1-100)"),
    ] = 100,
):
    """
    Get all active horeca routes.

    Horeca stands for Hotel/Restaurant/Café routes.
    Optionally filter by area. Returns routes where is_horeca=true.
    """
    try:
        routes = await route_service.get_horeca_routes(area_id=area_id, limit=limit)
        return ResponseModel(status_code=status.HTTP_200_OK, data=routes)

    except Exception as e:
        logger.error(
            "Failed to get horeca routes",
            area_id=area_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get horeca routes",
        )


# @router.get(
#     "/exists/{route_id}",
#     response_model=ResponseModel[dict],
#     responses={
#         200: {"description": "Existence check completed"},
#     },
#     summary="Check if route exists",
#     description="Check if a route with the given ID exists",
# )
# async def check_route_exists(
#     route_id: Annotated[int, Path(description="Route ID", ge=1)],
#     route_service: RouteServiceDep,
# ):
#     """
#     Check if a route exists.

#     Returns a boolean indicating whether the route exists.
#     """
#     try:
#         exists = await route_service.check_route_exists(route_id)
#         return ResponseModel(
#             status_code=status.HTTP_200_OK,
#             data={"route_id": route_id, "exists": exists},
#         )

#     except Exception as e:
#         logger.error(
#             "Failed to check route existence",
#             route_id=route_id,
#             error=str(e),
#         )
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Failed to check route existence",
#         )


# @router.get(
#     "/exists/code/{code}",
#     response_model=ResponseModel[dict],
#     responses={
#         200: {"description": "Existence check completed"},
#     },
#     summary="Check if route exists by code",
#     description="Check if a route with the given code exists",
# )
# async def check_route_exists_by_code(
#     code: Annotated[str, Path(description="Route code")],
#     route_service: RouteServiceDep,
# ):
#     """
#     Check if a route exists by code.

#     Returns a boolean indicating whether a route with the given code exists.
#     """
#     try:
#         exists = await route_service.check_route_exists_by_code(code)
#         return ResponseModel(
#             status_code=status.HTTP_200_OK,
#             data={"route_code": code, "exists": exists},
#         )

#     except Exception as e:
#         logger.error(
#             "Failed to check route existence by code",
#             route_code=code,
#             error=str(e),
#         )
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Failed to check route existence",
#         )


# @router.get(
#     "/count/active",
#     response_model=ResponseModel[dict],
#     responses={
#         200: {"description": "Count retrieved successfully"},
#     },
#     summary="Get active routes count",
#     description="Get the total count of active routes with optional filters",
# )
# async def get_active_routes_count(
#     route_service: RouteServiceDep,
#     area_id: Annotated[
#         int | None,
#         Query(description="Optional filter by area ID", ge=1),
#     ] = None,
#     is_general: Annotated[
#         bool | None,
#         Query(description="Optional filter by general route status"),
#     ] = None,
#     is_modern: Annotated[
#         bool | None,
#         Query(description="Optional filter by modern route status"),
#     ] = None,
#     is_horeca: Annotated[
#         bool | None,
#         Query(description="Optional filter by horeca route status"),
#     ] = None,
# ):
#     """
#     Get count of active routes.

#     Returns the total number of routes with is_active=true.
#     Optionally filter by area and route types.
#     """
#     try:
#         count = await route_service.get_active_routes_count(
#             area_id=area_id,
#             is_general=is_general,
#             is_modern=is_modern,
#             is_horeca=is_horeca,
#         )
#         filters = {
#             "area_id": area_id,
#             "is_general": is_general,
#             "is_modern": is_modern,
#             "is_horeca": is_horeca,
#         }
#         active_filters = {k: v for k, v in filters.items() if v is not None}

#         return ResponseModel(
#             status_code=status.HTTP_200_OK,
#             data={
#                 "active_count": count,
#                 "filters": active_filters if active_filters else "none",
#             },
#         )

#     except Exception as e:
#         logger.error(
#             "Failed to get active routes count",
#             area_id=area_id,
#             error=str(e),
#         )
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Failed to get active routes count",
#         )
