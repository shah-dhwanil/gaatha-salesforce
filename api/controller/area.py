"""
Area controller/router for FastAPI endpoints.

This module defines all REST API endpoints for hierarchical area management
(NATION, ZONE, REGION, AREA, DIVISION) in a multi-tenant environment.
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, status
from fastapi.responses import Response
import structlog

from api.dependencies.area import AreaServiceDep
from api.exceptions.area import (
    AreaAlreadyExistsException,
    AreaInvalidHierarchyException,
    AreaNotFoundException,
    AreaOperationException,
)
from api.models import ListResponseModel, ResponseModel
from api.models.area import AreaCreate, AreaListItem, AreaResponse, AreaUpdate

logger = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/companies/{company_id}/areas",
    tags=["Areas"],
    responses={
        400: {"description": "Bad Request - Invalid input or hierarchy"},
        404: {"description": "Resource Not Found"},
        500: {"description": "Internal Server Error"},
    },
)


@router.post(
    "",
    response_model=ResponseModel[AreaResponse],
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Area created successfully"},
        400: {"description": "Validation or hierarchy error"},
        404: {"description": "Parent area not found"},
        409: {"description": "Area already exists (duplicate name+type)"},
    },
    summary="Create a new area",
    description="Create a new area in the hierarchy with automatic parent validation and hierarchy setup",
)
async def create_area(
    area_data: AreaCreate,
    area_service: AreaServiceDep,
):
    """
    Create a new area in the hierarchy.

    The service automatically:
    - Validates parent area exists and is of correct type
    - Populates all ancestor IDs (nation_id, zone_id, region_id, area_id) based on parent
    - Enforces hierarchy rules (NATION > ZONE > REGION > AREA > DIVISION)

    **Hierarchy Rules:**
    - **NATION**: Top level, no parent required
    - **ZONE**: Requires nation_id only
    - **REGION**: Requires zone_id only (nation_id auto-populated)
    - **AREA**: Requires region_id only (zone_id, nation_id auto-populated)
    - **DIVISION**: Requires area_id only (all ancestors auto-populated)

    **Request Body:**
    - **name**: Area name (1-64 characters)
    - **type**: NATION, ZONE, REGION, AREA, or DIVISION
    - **nation_id**: Parent nation ID (required for ZONE)
    - **zone_id**: Parent zone ID (required for REGION)
    - **region_id**: Parent region ID (required for AREA)
    - **area_id**: Parent area ID (required for DIVISION)
    """
    try:
        area = await area_service.create_area(area_data)
        return ResponseModel(status_code=status.HTTP_201_CREATED, data=area)

    except AreaAlreadyExistsException as e:
        logger.warning(
            "Area already exists",
            area_name=area_data.name,
            area_type=area_data.type,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        )

    except AreaNotFoundException as e:
        logger.warning(
            "Parent area not found",
            area_name=area_data.name,
            area_type=area_data.type,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except AreaInvalidHierarchyException as e:
        logger.warning(
            "Invalid area hierarchy",
            area_name=area_data.name,
            area_type=area_data.type,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to create area",
            area_name=area_data.name,
            area_type=area_data.type,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create area",
        )


@router.get(
    "/{area_id}",
    response_model=ResponseModel[AreaResponse],
    responses={
        200: {"description": "Area retrieved successfully"},
        404: {"description": "Area not found"},
    },
    summary="Get area by ID",
    description="Retrieve detailed information about a specific area including all parent references",
)
async def get_area(
    area_id: Annotated[int, Path(description="Area ID", ge=1)],
    area_service: AreaServiceDep,
):
    """
    Get an area by ID.

    Returns complete area information including:
    - All fields (id, name, type, parent IDs)
    - Timestamps (created_at, updated_at)
    - Active status
    """
    try:
        area = await area_service.get_area_by_id(area_id)
        return ResponseModel(status_code=status.HTTP_200_OK, data=area)

    except AreaNotFoundException as e:
        logger.info(
            "Area not found",
            area_id=area_id,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to get area",
            area_id=area_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve area",
        )


@router.get(
    "/by-name/{area_type}/{name}",
    response_model=ResponseModel[AreaResponse],
    responses={
        200: {"description": "Area retrieved successfully"},
        404: {"description": "Area not found"},
    },
    summary="Get area by name and type",
    description="Retrieve an area by its name and type combination",
)
async def get_area_by_name_and_type(
    name: Annotated[str, Path(description="Area name")],
    area_type: Annotated[str, Path(description="Area type: NATION, ZONE, REGION, AREA, or DIVISION")],
    area_service: AreaServiceDep,
):
    """
    Get an area by name and type.

    Since area names must be unique within a type, this combination uniquely identifies an area.
    """
    try:
        area = await area_service.get_area_by_name_and_type(name, area_type)
        return ResponseModel(status_code=status.HTTP_200_OK, data=area)

    except AreaNotFoundException as e:
        logger.info(
            "Area not found",
            area_name=name,
            area_type=area_type,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to get area by name and type",
            area_name=name,
            area_type=area_type,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve area",
        )


@router.get(
    "",
    response_model=ListResponseModel[AreaListItem],
    responses={
        200: {"description": "Areas retrieved successfully"},
        400: {"description": "Invalid parameters or hierarchy"},
    },
    summary="List all areas",
    description="List areas with pagination and optional filtering by type, parent, and active status",
)
async def list_areas(
    area_service: AreaServiceDep,
    area_type: Annotated[
        str | None,
        Query(description="Filter by area type: NATION, ZONE, REGION, AREA, or DIVISION"),
    ] = None,
    is_active: Annotated[
        bool | None,
        Query(description="Filter by active status (true/false, optional)"),
    ] = None,
    parent_id: Annotated[
        int | None,
        Query(description="Filter by parent area ID", ge=1),
    ] = None,
    parent_type: Annotated[
        str | None,
        Query(description="Parent type: nation, zone, region, or area (required if parent_id is provided)"),
    ] = None,
    limit: Annotated[
        int,
        Query(ge=1, le=100, description="Number of areas to return (1-100)"),
    ] = 20,
    offset: Annotated[
        int,
        Query(ge=0, description="Number of areas to skip (pagination)"),
    ] = 0,
):
    """
    List all areas with pagination and filtering.

    Returns minimal area data (id, name, type, is_active) for performance.
    Use the detail endpoint (GET /{area_id}) to get complete area information.

    **Filters:**
    - **area_type**: Filter by specific hierarchy level
    - **is_active**: Filter by active status
    - **parent_id + parent_type**: Get all children of a specific parent
      - Example: parent_id=5, parent_type="nation" returns all zones under nation 5
    - **limit**: Results per page (default: 20, max: 100)
    - **offset**: Skip results for pagination (default: 0)

    **Examples:**
    - List all nations: `?area_type=NATION`
    - List zones under nation 1: `?parent_id=1&parent_type=nation`
    - List active divisions: `?area_type=DIVISION&is_active=true`
    """
    try:
        areas, total_count = await area_service.list_areas(
            area_type=area_type,
            is_active=is_active,
            parent_id=parent_id,
            parent_type=parent_type,
            limit=limit,
            offset=offset,
        )

        return ListResponseModel(
            status_code=status.HTTP_200_OK,
            data=areas,
            records_per_page=limit,
            total_count=total_count,
        )

    except AreaInvalidHierarchyException as e:
        logger.warning(
            "Invalid parameters for list areas",
            area_type=area_type,
            parent_id=parent_id,
            parent_type=parent_type,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to list areas",
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list areas",
        )


@router.patch(
    "/{area_id}",
    response_model=ResponseModel[AreaResponse],
    responses={
        200: {"description": "Area updated successfully"},
        400: {"description": "Validation or hierarchy error"},
        404: {"description": "Area or parent not found"},
    },
    summary="Update an area",
    description="Update area details with automatic parent validation and hierarchy setup",
)
async def update_area(
    area_id: Annotated[int, Path(description="Area ID", ge=1)],
    area_data: AreaUpdate,
    area_service: AreaServiceDep,
):
    """
    Update an existing area.

    The service automatically validates hierarchy when updating type or parent references.

    **Updatable Fields:**
    - **name**: Area name
    - **type**: Area type (triggers hierarchy re-validation)
    - **parent IDs**: Parent references (auto-populates ancestors based on hierarchy)

    **Note**: At least one field must be provided for update.
    """
    try:
        area = await area_service.update_area(area_id, area_data)
        return ResponseModel(status_code=status.HTTP_200_OK, data=area)

    except AreaNotFoundException as e:
        logger.info(
            "Area not found for update",
            area_id=area_id,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except AreaInvalidHierarchyException as e:
        logger.warning(
            "Area update validation failed",
            area_id=area_id,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to update area",
            area_id=area_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update area",
        )


@router.delete(
    "/{area_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Area deactivated successfully"},
        404: {"description": "Area not found"},
    },
    summary="Delete an area (soft delete)",
    description="Soft delete an area by setting is_active to false",
)
async def delete_area(
    area_id: Annotated[int, Path(description="Area ID", ge=1)],
    area_service: AreaServiceDep,
):
    """
    Delete an area (soft delete).

    Sets is_active to false instead of permanently deleting the area.
    The area will still exist in the database but won't be active.
    """
    try:
        await area_service.delete_area(area_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except AreaNotFoundException as e:
        logger.info(
            "Area not found for deletion",
            area_id=area_id,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to delete area",
            area_id=area_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete area",
        )


@router.get(
    "/parent/{parent_id}/children",
    response_model=ResponseModel[list[AreaResponse]],
    responses={
        200: {"description": "Child areas retrieved successfully"},
        400: {"description": "Invalid parent type"},
    },
    summary="Get child areas of a parent",
    description="Get all immediate child areas of a specific parent area",
)
async def get_areas_by_parent(
    parent_id: Annotated[int, Path(description="Parent area ID", ge=1)],
    parent_type: Annotated[str, Query(description="Parent type: nation, zone, region, or area")],
    area_service: AreaServiceDep,
):
    """
    Get all child areas of a parent.

    Returns full area information for all immediate children.

    **Parent Types:**
    - **nation**: Returns all zones under the nation
    - **zone**: Returns all regions under the zone
    - **region**: Returns all areas under the region
    - **area**: Returns all divisions under the area
    """
    try:
        areas = await area_service.get_areas_by_parent(parent_id, parent_type)
        return ListResponseModel[AreaResponse](
            status_code=status.HTTP_200_OK,
            data=areas,
            records_per_page=20,
            total_count=len(areas),
        )

    except AreaInvalidHierarchyException as e:
        logger.warning(
            "Invalid parent type for get children",
            parent_id=parent_id,
            parent_type=parent_type,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to get areas by parent",
            parent_id=parent_id,
            parent_type=parent_type,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get child areas",
        )


@router.get(
    "/hierarchy/nations",
    response_model=ResponseModel[list[AreaListItem]],
    responses={
        200: {"description": "Nations retrieved successfully"},
    },
    summary="Get all nations",
    description="Get all active nations (top-level areas)",
)
async def get_all_nations(
    area_service: AreaServiceDep,
):
    """
    Get all active nations.

    Returns minimal data for all nations. Useful for populating dropdowns.
    """
    try:
        nations = await area_service.get_nations()
        return ResponseModel(status_code=status.HTTP_200_OK, data=nations)

    except Exception as e:
        logger.error(
            "Failed to get nations",
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get nations",
        )

@router.get(
    "/nation/{nation_id}/zones",
    response_model=ResponseModel[list[AreaResponse]],
    responses={
        200: {"description": "Zones retrieved successfully"},
    },
    summary="Get zones by nation",
    description="Get all zones under a specific nation",
)
async def get_zones_by_nation(
    nation_id: Annotated[int, Path(description="Nation ID", ge=1)],
    area_service: AreaServiceDep,
):
    """
    Get all zones under a nation.

    Convenience endpoint for navigating the hierarchy.
    """
    try:
        zones = await area_service.get_zones_by_nation(nation_id)
        return ResponseModel(status_code=status.HTTP_200_OK, data=zones)

    except Exception as e:
        logger.error(
            "Failed to get zones by nation",
            nation_id=nation_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get zones",
        )


@router.get(
    "/zone/{zone_id}/regions",
    response_model=ResponseModel[list[AreaResponse]],
    responses={
        200: {"description": "Regions retrieved successfully"},
    },
    summary="Get regions by zone",
    description="Get all regions under a specific zone",
)
async def get_regions_by_zone(
    zone_id: Annotated[int, Path(description="Zone ID", ge=1)],
    area_service: AreaServiceDep,
):
    """
    Get all regions under a zone.

    Convenience endpoint for navigating the hierarchy.
    """
    try:
        regions = await area_service.get_regions_by_zone(zone_id)
        return ResponseModel(status_code=status.HTTP_200_OK, data=regions)

    except Exception as e:
        logger.error(
            "Failed to get regions by zone",
            zone_id=zone_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get regions",
        )


@router.get(
    "/region/{region_id}/areas",
    response_model=ResponseModel[list[AreaResponse]],
    responses={
        200: {"description": "Areas retrieved successfully"},
    },
    summary="Get areas by region",
    description="Get all areas under a specific region",
)
async def get_areas_by_region(
    region_id: Annotated[int, Path(description="Region ID", ge=1)],
    area_service: AreaServiceDep,
):
    """
    Get all areas under a region.

    Convenience endpoint for navigating the hierarchy.
    """
    try:
        areas = await area_service.get_areas_by_region(region_id)
        return ResponseModel(status_code=status.HTTP_200_OK, data=areas)

    except Exception as e:
        logger.error(
            "Failed to get areas by region",
            region_id=region_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get areas",
        )


@router.get(
    "/area/{area_id}/divisions",
    response_model=ResponseModel[list[AreaResponse]],
    responses={
        200: {"description": "Divisions retrieved successfully"},
    },
    summary="Get divisions by area",
    description="Get all divisions under a specific area",
)
async def get_divisions_by_area(
    area_id: Annotated[int, Path(description="Area ID", ge=1)],
    area_service: AreaServiceDep,
):
    """
    Get all divisions under an area.

    Convenience endpoint for navigating the hierarchy.
    """
    try:
        divisions = await area_service.get_divisions_by_area(area_id)
        return ResponseModel(status_code=status.HTTP_200_OK, data=divisions)

    except Exception as e:
        logger.error(
            "Failed to get divisions by area",
            area_id=area_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get divisions",
        )


@router.get(
    "/exists/{area_id}",
    response_model=ResponseModel[dict],
    responses={
        200: {"description": "Existence check completed"},
    },
    summary="Check if area exists",
    description="Check if an area with the given ID exists",
)
async def check_area_exists(
    area_id: Annotated[int, Path(description="Area ID", ge=1)],
    area_service: AreaServiceDep,
):
    """
    Check if an area exists.

    Returns a boolean indicating whether the area exists.
    """
    try:
        exists = await area_service.check_area_exists(area_id)
        return ResponseModel(
            status_code=status.HTTP_200_OK,
            data={"area_id": area_id, "exists": exists},
        )

    except Exception as e:
        logger.error(
            "Failed to check area existence",
            area_id=area_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check area existence",
        )


@router.get(
    "/count/active",
    response_model=ResponseModel[dict],
    responses={
        200: {"description": "Count retrieved successfully"},
    },
    summary="Get active areas count",
    description="Get the total count of active areas, optionally filtered by type",
)
async def get_active_areas_count(
    area_service: AreaServiceDep,
    area_type: Annotated[
        str | None,
        Query(description="Optional filter by area type"),
    ] = None,
):
    """
    Get count of active areas.

    Returns the total number of areas with is_active=true.
    Optionally filter by area type.
    """
    try:
        count = await area_service.get_active_areas_count(area_type)
        return ResponseModel(
            status_code=status.HTTP_200_OK,
            data={"area_type": area_type or "ALL", "active_count": count},
        )

    except Exception as e:
        logger.error(
            "Failed to get active areas count",
            area_type=area_type,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get active areas count",
        )

