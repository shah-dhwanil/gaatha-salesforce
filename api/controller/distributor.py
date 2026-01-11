"""
Distributor controller/router for FastAPI endpoints.

This module defines all REST API endpoints for distributor management
in a multi-tenant environment.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Query, status
from fastapi.responses import Response
import structlog

from api.dependencies.distributor import DistributorServiceDep
from api.exceptions.distributor import (
    DistributorAlreadyExistsException,
    DistributorNotFoundException,
    DistributorOperationException,
    DistributorValidationException,
)
from api.models import ListResponseModel, ResponseModel
from api.models.distributor import (
    DistributorCreate,
    DistributorDetailItem,
    DistributorListItem,
    DistributorResponse,
    DistributorUpdate,
)

logger = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/companies/{company_id}/distributors",
    tags=["Distributors"],
    responses={
        400: {"description": "Bad Request - Invalid input"},
        404: {"description": "Resource Not Found"},
        409: {"description": "Resource Already Exists"},
        500: {"description": "Internal Server Error"},
    },
)


@router.post(
    "",
    response_model=ResponseModel[DistributorResponse],
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Distributor created successfully"},
        400: {"description": "Validation error"},
        404: {"description": "Area not found"},
        409: {
            "description": "Distributor already exists (duplicate code, GST, PAN, etc.)"
        },
    },
    summary="Create a new distributor",
    description="Create a new distributor with all required details including vehicles and trade types",
)
async def create_distributor(
    distributor_data: DistributorCreate,
    distributor_service: DistributorServiceDep,
):
    """
    Create a new distributor in the system.

    **Request Body:**
    - **name**: Distributor name (1-255 characters)
    - **contact_person_name**: Name of the contact person (1-255 characters)
    - **mobile_number**: Mobile number (10-15 characters) - will be uppercased
    - **email**: Email address (optional)
    - **gst_no**: GST number (15 characters) - will be uppercased
    - **pan_no**: PAN number (10 characters) - will be uppercased
    - **license_no**: License number (optional, max 255 characters) - will be uppercased
    - **address**: Full address (required)
    - **pin_code**: PIN code (6 characters) - will be uppercased
    - **map_link**: Google Maps link (optional)
    - **documents**: Documents metadata in DocumentInDB format (optional)
    - **store_images**: Store images metadata in DocumentInDB format (optional)
    - **vehicle_3**: Number of 3-wheeler vehicles (integer, >= 0)
    - **vehicle_4**: Number of 4-wheeler vehicles (integer, >= 0)
    - **salesman_count**: Number of salesmen (integer, >= 0)
    - **area_id**: Area ID (foreign key)
    - **for_general**: Serves general trade (boolean, default: false)
    - **for_modern**: Serves modern trade (boolean, default: false)
    - **for_horeca**: Serves HORECA (boolean, default: false)
    - **bank_details**: Bank account details (required)
    - **route_ids**: List of route IDs to associate with distributor (optional)

    **Unique Constraints:**
    - code (auto-generated), gst_no, pan_no, license_no, mobile_number, email must be unique

    **Default Values:**
    - is_active: true
    - Code is auto-generated as: {COMPANY_PREFIX}_DIST_{SERIAL_NUMBER}

    **Note:**
    - A user account is automatically created for the distributor
    - Bank details are stored in the members table
    - Routes can be added/removed after creation
    """
    try:
        distributor = await distributor_service.create_distributor(distributor_data)
        return ResponseModel(status_code=status.HTTP_201_CREATED, data=distributor)

    except DistributorAlreadyExistsException as e:
        logger.warning(
            "Distributor already exists",
            distributor_name=distributor_data.name,
            error=e.message,
        )
        raise e

    except DistributorValidationException as e:
        logger.warning(
            "Distributor validation failed",
            distributor_name=distributor_data.name,
            error=e.message,
        )
        raise e

    except DistributorOperationException as e:
        if "area" in e.message.lower():
            logger.warning(
                "Foreign key constraint failed",
                distributor_name=distributor_data.name,
                area_id=distributor_data.area_id,
                error=e.message,
            )
            raise e
        logger.error(
            "Failed to create distributor",
            distributor_name=distributor_data.name,
            error=str(e),
        )
        raise e

    except Exception as e:
        logger.error(
            "Unexpected error creating distributor",
            distributor_name=distributor_data.name,
        )
        raise e


@router.get(
    "/{distributor_id}",
    response_model=ResponseModel[DistributorDetailItem],
    responses={
        200: {"description": "Distributor retrieved successfully"},
        404: {"description": "Distributor not found"},
    },
    summary="Get distributor by ID",
    description="Retrieve detailed information about a specific distributor including area name and route details",
)
async def get_distributor(
    distributor_id: Annotated[UUID, Path(description="Distributor ID (UUID)")],
    distributor_service: DistributorServiceDep,
):
    """
    Get a distributor by ID.

    Returns complete distributor information including:
    - All distributor fields
    - Area name (joined from areas)
    - Route details (id, name, and type for each active route)
    - Bank details (joined from members)
    - Documents and store images
    - Vehicle counts and salesman count
    - Trade type flags (for_general, for_modern, for_horeca)
    - Active status
    - Timestamps
    """
    try:
        distributor = await distributor_service.get_distributor_by_id(distributor_id)
        return ResponseModel(status_code=status.HTTP_200_OK, data=distributor)

    except DistributorNotFoundException as e:
        logger.info(
            "Distributor not found",
            distributor_id=str(distributor_id),
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to get distributor",
            distributor_id=str(distributor_id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve distributor",
        )


@router.get(
    "/by-code/{code}",
    response_model=ResponseModel[DistributorDetailItem],
    responses={
        200: {"description": "Distributor retrieved successfully"},
        404: {"description": "Distributor not found"},
    },
    summary="Get distributor by code",
    description="Retrieve a distributor by its unique code",
)
async def get_distributor_by_code(
    code: Annotated[str, Path(description="Distributor code")],
    distributor_service: DistributorServiceDep,
):
    """
    Get a distributor by its unique code.

    Returns complete distributor information including area name and route details.
    Only returns active distributors.
    """
    try:
        distributor = await distributor_service.get_distributor_by_code(code)
        return ResponseModel(status_code=status.HTTP_200_OK, data=distributor)

    except DistributorNotFoundException as e:
        logger.info(
            "Distributor not found by code",
            distributor_code=code,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to get distributor by code",
            distributor_code=code,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve distributor",
        )


@router.get(
    "",
    response_model=ListResponseModel[DistributorListItem],
    responses={
        200: {"description": "Distributors retrieved successfully"},
        400: {"description": "Invalid pagination parameters"},
    },
    summary="List all distributors",
    description="List distributors with pagination and optional filtering by area and status",
)
async def list_distributors(
    distributor_service: DistributorServiceDep,
    area_id: Annotated[
        int | None,
        Query(description="Filter by area ID", ge=1),
    ] = None,
    is_active: Annotated[
        bool | None,
        Query(description="Filter by active status (true/false, optional)"),
    ] = None,
    limit: Annotated[
        int,
        Query(ge=1, le=100, description="Number of distributors to return (1-100)"),
    ] = 20,
    offset: Annotated[
        int,
        Query(ge=0, description="Number of distributors to skip (pagination)"),
    ] = 0,
):
    """
    List all distributors with pagination and filtering.

    Returns optimized distributor data with minimal fields for performance:
    - id, name, code
    - contact_person_name, mobile_number
    - address
    - area_id, area_name (joined)
    - route_count (number of associated active routes)
    - is_active

    Use the detail endpoint (GET /{distributor_id}) to get complete distributor information.

    **Filters:**
    - **area_id**: Filter by specific area
    - **is_active**: Filter by active status
    - **limit**: Results per page (default: 20, max: 100)
    - **offset**: Skip results for pagination (default: 0)

    **Examples:**
    - List active distributors in area 1: `?area_id=1&is_active=true`
    - List all distributors with pagination: `?limit=50&offset=0`
    """
    try:
        distributors, total_count = await distributor_service.list_distributors(
            area_id=area_id,
            is_active=is_active,
            limit=limit,
            offset=offset,
        )

        return ListResponseModel(
            status_code=status.HTTP_200_OK,
            data=distributors,
            records_per_page=limit,
            total_count=total_count,
        )

    except DistributorValidationException as e:
        logger.warning(
            "Invalid parameters for list distributors",
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
            "Failed to list distributors",
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list distributors",
        )


@router.patch(
    "/{distributor_id}",
    response_model=ResponseModel[DistributorResponse],
    responses={
        200: {"description": "Distributor updated successfully"},
        400: {"description": "Validation error"},
        404: {"description": "Distributor not found"},
        409: {"description": "Duplicate value (GST, PAN, etc.)"},
    },
    summary="Update a distributor",
    description="Update distributor details (code cannot be changed)",
)
async def update_distributor(
    distributor_id: Annotated[UUID, Path(description="Distributor ID (UUID)")],
    distributor_data: DistributorUpdate,
    distributor_service: DistributorServiceDep,
):
    """
    Update an existing distributor.

    **Updatable Fields:**
    - name, contact_person_name, mobile_number, email
    - gst_no, pan_no, license_no
    - address, pin_code, map_link
    - vehicle_3, vehicle_4, salesman_count
    - area_id
    - for_general, for_modern, for_horeca
    - documents, store_images

    **Note**:
    - Distributor code cannot be updated after creation
    - At least one field must be provided for update
    - Unique constraints are enforced (GST, PAN, license, mobile, email)
    - Routes are managed via separate endpoints
    - User data (name, contact_no) is automatically synced
    """
    try:
        distributor = await distributor_service.update_distributor(
            distributor_id, distributor_data
        )
        return ResponseModel(status_code=status.HTTP_200_OK, data=distributor)

    except DistributorNotFoundException as e:
        logger.info(
            "Distributor not found for update",
            distributor_id=str(distributor_id),
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except DistributorAlreadyExistsException as e:
        logger.warning(
            "Distributor update failed - duplicate value",
            distributor_id=str(distributor_id),
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        )

    except DistributorValidationException as e:
        logger.warning(
            "Distributor update validation failed",
            distributor_id=str(distributor_id),
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to update distributor",
            distributor_id=str(distributor_id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update distributor",
        )


@router.delete(
    "/{distributor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Distributor deactivated successfully"},
        404: {"description": "Distributor not found"},
    },
    summary="Delete a distributor (soft delete)",
    description="Soft delete a distributor by setting is_active to false",
)
async def delete_distributor(
    distributor_id: Annotated[UUID, Path(description="Distributor ID (UUID)")],
    distributor_service: DistributorServiceDep,
):
    """
    Delete a distributor (soft delete).

    Sets is_active to false instead of permanently deleting the distributor.
    The distributor will still exist in the database but won't be active.
    """
    try:
        await distributor_service.delete_distributor(distributor_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except DistributorNotFoundException as e:
        logger.info(
            "Distributor not found for deletion",
            distributor_id=str(distributor_id),
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to delete distributor",
            distributor_id=str(distributor_id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete distributor",
        )


@router.post(
    "/{distributor_id}/routes/{route_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Route added to distributor successfully"},
        404: {"description": "Distributor or route not found"},
    },
    summary="Add a route to distributor",
    description="Associate a route with a distributor (distributor can have multiple routes)",
)
async def add_route_to_distributor(
    distributor_id: Annotated[UUID, Path(description="Distributor ID (UUID)")],
    route_id: Annotated[int, Path(description="Route ID", ge=1)],
    distributor_service: DistributorServiceDep,
):
    """
    Add a route to a distributor.

    Distributors can be associated with multiple routes. This endpoint adds
    a new route to the distributor's list of routes.

    **Note:**
    - If the route is already associated, this operation is idempotent
    - The route must exist in the routes table
    """
    try:
        await distributor_service.add_distributor_route(distributor_id, route_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except DistributorNotFoundException as e:
        logger.info(
            "Distributor not found for adding route",
            distributor_id=str(distributor_id),
            route_id=route_id,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except DistributorOperationException as e:
        logger.error(
            "Failed to add route to distributor",
            distributor_id=str(distributor_id),
            route_id=route_id,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Unexpected error adding route to distributor",
            distributor_id=str(distributor_id),
            route_id=route_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add route to distributor",
        )


@router.delete(
    "/{distributor_id}/routes/{route_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Route removed from distributor successfully"},
        404: {"description": "Distributor not found"},
    },
    summary="Remove a route from distributor",
    description="Disassociate a route from a distributor (soft delete)",
)
async def remove_route_from_distributor(
    distributor_id: Annotated[UUID, Path(description="Distributor ID (UUID)")],
    route_id: Annotated[int, Path(description="Route ID", ge=1)],
    distributor_service: DistributorServiceDep,
):
    """
    Remove a route from a distributor (soft delete).

    Sets is_active to false for the distributor_routes association.
    The route is not deleted from the routes table.

    **Note:**
    - This is a soft delete operation
    - The association still exists in the database but is marked inactive
    """
    try:
        await distributor_service.remove_distributor_route(distributor_id, route_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except DistributorNotFoundException as e:
        logger.info(
            "Distributor not found for removing route",
            distributor_id=str(distributor_id),
            route_id=route_id,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except DistributorOperationException as e:
        logger.error(
            "Failed to remove route from distributor",
            distributor_id=str(distributor_id),
            route_id=route_id,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Unexpected error removing route from distributor",
            distributor_id=str(distributor_id),
            route_id=route_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove route from distributor",
        )


@router.get(
    "/area/{area_id}/distributors",
    response_model=ListResponseModel[DistributorListItem],
    responses={
        200: {"description": "Distributors retrieved successfully"},
    },
    summary="Get distributors by area",
    description="Get all active distributors for a specific area",
)
async def get_distributors_by_area(
    area_id: Annotated[int, Path(description="Area ID", ge=1)],
    distributor_service: DistributorServiceDep,
):
    """
    Get all active distributors for a specific area.

    Returns optimized distributor list for all active distributors in the area.
    Useful for area planning and management.
    """
    try:
        distributors = await distributor_service.get_all_active_distributors_by_area(
            area_id
        )
        return ListResponseModel(
            status_code=status.HTTP_200_OK,
            data=distributors,
            records_per_page=len(distributors),
            total_count=len(distributors),
        )

    except Exception as e:
        logger.error(
            "Failed to get distributors by area",
            area_id=area_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get distributors",
        )


@router.get(
    "/by-trade/filter",
    response_model=ListResponseModel[DistributorListItem],
    responses={
        200: {"description": "Distributors retrieved successfully"},
        400: {"description": "Invalid pagination parameters"},
    },
    summary="Get distributors by trade type",
    description="Filter distributors by trade types (general, modern, HORECA)",
)
async def get_distributors_by_trade_type(
    distributor_service: DistributorServiceDep,
    for_general: Annotated[
        bool | None,
        Query(description="Filter by general trade flag"),
    ] = None,
    for_modern: Annotated[
        bool | None,
        Query(description="Filter by modern trade flag"),
    ] = None,
    for_horeca: Annotated[
        bool | None,
        Query(description="Filter by HORECA trade flag"),
    ] = None,
    limit: Annotated[
        int,
        Query(ge=1, le=100, description="Number of distributors to return (1-100)"),
    ] = 20,
    offset: Annotated[
        int,
        Query(ge=0, description="Number of distributors to skip (pagination)"),
    ] = 0,
):
    """
    Get distributors filtered by trade types.

    **Trade Types:**
    - **for_general**: General trade (traditional retailers)
    - **for_modern**: Modern trade (supermarkets, malls)
    - **for_horeca**: Hotels, Restaurants, Cafés

    **Examples:**
    - Get distributors serving general trade: `?for_general=true`
    - Get distributors serving both modern and HORECA: `?for_modern=true&for_horeca=true`
    - Get distributors NOT serving general trade: `?for_general=false`

    **Note:**
    - Multiple filters create an AND condition
    - Omitting a filter means "don't care" about that trade type
    """
    try:
        # Validate at least one filter is provided
        if all(x is None for x in [for_general, for_modern, for_horeca]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one trade type filter must be provided",
            )

        (
            distributors,
            total_count,
        ) = await distributor_service.get_distributors_by_trade_type(
            for_general=for_general,
            for_modern=for_modern,
            for_horeca=for_horeca,
            limit=limit,
            offset=offset,
        )

        return ListResponseModel(
            status_code=status.HTTP_200_OK,
            data=distributors,
            records_per_page=limit,
            total_count=total_count,
        )

    except DistributorValidationException as e:
        logger.warning(
            "Invalid parameters for trade type filter",
            for_general=for_general,
            for_modern=for_modern,
            for_horeca=for_horeca,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to get distributors by trade type",
            for_general=for_general,
            for_modern=for_modern,
            for_horeca=for_horeca,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get distributors by trade type",
        )


@router.get(
    "/stats/counts",
    response_model=ResponseModel[dict],
    responses={
        200: {"description": "Counts retrieved successfully"},
    },
    summary="Get distributor statistics",
    description="Get counts of active distributors with optional filters",
)
async def get_distributor_stats(
    distributor_service: DistributorServiceDep,
    area_id: Annotated[
        int | None,
        Query(description="Optional filter by area ID", ge=1),
    ] = None,
):
    """
    Get distributor statistics.

    Returns:
    - Total active distributors count
    - Optionally filtered by area

    **Examples:**
    - Get total active distributors: `/stats/counts`
    - Get active distributors in area 1: `/stats/counts?area_id=1`
    """
    try:
        active_count = await distributor_service.get_active_distributors_count(
            area_id=area_id,
        )

        filters = {
            "area_id": area_id,
        }
        active_filters = {k: v for k, v in filters.items() if v is not None}

        return ResponseModel(
            status_code=status.HTTP_200_OK,
            data={
                "active_count": active_count,
                "filters": active_filters if active_filters else None,
            },
        )

    except Exception as e:
        logger.error(
            "Failed to get distributor stats",
            area_id=area_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get distributor statistics",
        )
