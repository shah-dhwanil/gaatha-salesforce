"""
Area controller for FastAPI routes.

This module defines the API endpoints for area operations including
CRUD operations and area hierarchy management.
"""

from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, status, Query
import structlog

from api.database import DatabasePool, get_db_pool
from api.repository.area import AreaRepository
from api.service.area import AreaService
from api.models.base import ResponseModel, ListResponseModel
from api.models.area import (
    CreateAreaRequest,
    UpdateAreaRequest,
    AreaResponse,
    AreaType,
)

logger = structlog.get_logger(__name__)

# Create router
router = APIRouter(prefix="/areas", tags=["areas"])


# Dependency to get area service
async def get_area_service(
    db: Annotated[DatabasePool, Depends(get_db_pool, scope="function")],
) -> AreaService:
    """Dependency to create and return AreaService instance."""
    area_repository = AreaRepository(db)
    return AreaService(area_repository)


@router.post(
    "/",
    response_model=ResponseModel[AreaResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new area",
    description="Create a new area with the specified name, type, and parent hierarchy for a company.",
)
async def create_area(
    request: CreateAreaRequest,
    area_service: AreaService = Depends(get_area_service),
) -> ResponseModel[AreaResponse]:
    """
    Create a new area.

    Args:
        request: CreateAreaRequest with area details
        area_service: Injected AreaService dependency

    Returns:
        AreaResponse with created area details

    Raises:
        HTTPException: 409 if area already exists
        HTTPException: 400 if validation fails
    """
    logger.info(
        "Creating new area",
        name=request.name,
        type=request.type,
        company_id=str(request.company_id),
    )

    area = await area_service.create_area(
        company_id=request.company_id,
        name=request.name,
        type=request.type,
        area_id=request.area_id,
        region_id=request.region_id,
        zone_id=request.zone_id,
        nation_id=request.nation_id,
    )

    return ResponseModel(
        status_code=status.HTTP_201_CREATED,
        data=AreaResponse(
            id=area.id,
            name=area.name,
            type=area.type,
            area_id=area.area_id,
            region_id=area.region_id,
            zone_id=area.zone_id,
            nation_id=area.nation_id,
            is_active=area.is_active,
            created_at=area.created_at,
            updated_at=area.updated_at,
        ),
    )


@router.get(
    "/{company_id}",
    response_model=ListResponseModel[AreaResponse],
    status_code=status.HTTP_200_OK,
    summary="Get all areas for a company",
    description="Retrieve all active areas for the specified company with pagination.",
)
async def get_areas_by_company(
    company_id: UUID,
    limit: int = Query(
        10, ge=1, le=100, description="Maximum number of records to return"
    ),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    area_service: AreaService = Depends(get_area_service),
) -> ListResponseModel[AreaResponse]:
    """
    Get all areas for a company with pagination.

    Args:
        company_id: UUID of the company
        limit: Maximum number of records to return (default: 10)
        offset: Number of records to skip (default: 0)
        area_service: Injected AreaService dependency

    Returns:
        ListResponseModel with list of areas, pagination info, and total count
    """
    logger.info(
        "Fetching areas for company",
        company_id=str(company_id),
        limit=limit,
        offset=offset,
    )

    areas, total_count = await area_service.get_areas_by_company_id(
        company_id, limit, offset
    )

    area_responses = [
        AreaResponse(
            id=area.id,
            name=area.name,
            type=area.type,
            area_id=area.area_id,
            region_id=area.region_id,
            zone_id=area.zone_id,
            nation_id=area.nation_id,
            is_active=area.is_active,
            created_at=area.created_at,
            updated_at=area.updated_at,
        )
        for area in areas
    ]

    return ListResponseModel(
        status_code=status.HTTP_200_OK,
        data=area_responses,
        records_per_page=len(area_responses),
        total_count=total_count,
    )


@router.get(
    "/{company_id}/id/{area_id}",
    response_model=ResponseModel[AreaResponse],
    status_code=status.HTTP_200_OK,
    summary="Get area by ID",
    description="Retrieve a specific area by ID for a company.",
)
async def get_area_by_id(
    company_id: UUID,
    area_id: int,
    area_service: AreaService = Depends(get_area_service),
) -> ResponseModel[AreaResponse]:
    """
    Get an area by ID.

    Args:
        company_id: UUID of the company
        area_id: ID of the area
        area_service: Injected AreaService dependency

    Returns:
        AreaResponse with area details

    Raises:
        HTTPException: 404 if area not found
    """
    logger.info("Fetching area by ID", area_id=area_id, company_id=str(company_id))

    area = await area_service.get_area_by_id(company_id, area_id)

    return ResponseModel(
        status_code=status.HTTP_200_OK,
        data=AreaResponse(
            id=area.id,
            name=area.name,
            type=area.type,
            area_id=area.area_id,
            region_id=area.region_id,
            zone_id=area.zone_id,
            nation_id=area.nation_id,
            is_active=area.is_active,
            created_at=area.created_at,
            updated_at=area.updated_at,
        ),
    )


@router.get(
    "/{company_id}/name/{name}",
    response_model=ResponseModel[AreaResponse],
    status_code=status.HTTP_200_OK,
    summary="Get area by name",
    description="Retrieve a specific area by name for a company.",
)
async def get_area_by_name(
    company_id: UUID,
    name: str,
    area_service: AreaService = Depends(get_area_service),
) -> ResponseModel[AreaResponse]:
    """
    Get an area by name.

    Args:
        company_id: UUID of the company
        name: Name of the area
        area_service: Injected AreaService dependency

    Returns:
        AreaResponse with area details

    Raises:
        HTTPException: 404 if area not found
    """
    logger.info("Fetching area by name", name=name, company_id=str(company_id))

    area = await area_service.get_area_by_name(company_id, name)

    return ResponseModel(
        status_code=status.HTTP_200_OK,
        data=AreaResponse(
            id=area.id,
            name=area.name,
            type=area.type,
            area_id=area.area_id,
            region_id=area.region_id,
            zone_id=area.zone_id,
            nation_id=area.nation_id,
            is_active=area.is_active,
            created_at=area.created_at,
            updated_at=area.updated_at,
        ),
    )


@router.get(
    "/{company_id}/type/{area_type}",
    response_model=ListResponseModel[AreaResponse],
    status_code=status.HTTP_200_OK,
    summary="Get areas by type",
    description="Retrieve all areas of a specific type for a company with pagination.",
)
async def get_areas_by_type(
    company_id: UUID,
    area_type: AreaType,
    limit: int = Query(
        10, ge=1, le=100, description="Maximum number of records to return"
    ),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    area_service: AreaService = Depends(get_area_service),
) -> ListResponseModel[AreaResponse]:
    """
    Get all areas of a specific type for a company with pagination.

    Args:
        company_id: UUID of the company
        area_type: Type of areas to retrieve
        limit: Maximum number of records to return (default: 10)
        offset: Number of records to skip (default: 0)
        area_service: Injected AreaService dependency

    Returns:
        ListResponseModel with list of areas, pagination info, and total count
    """
    logger.info(
        "Fetching areas by type",
        company_id=str(company_id),
        area_type=area_type,
        limit=limit,
        offset=offset,
    )

    areas, total_count = await area_service.get_areas_by_type(
        company_id, area_type, limit, offset
    )

    area_responses = [
        AreaResponse(
            id=area.id,
            name=area.name,
            type=area.type,
            area_id=area.area_id,
            region_id=area.region_id,
            zone_id=area.zone_id,
            nation_id=area.nation_id,
            is_active=area.is_active,
            created_at=area.created_at,
            updated_at=area.updated_at,
        )
        for area in areas
    ]

    return ListResponseModel(
        status_code=status.HTTP_200_OK,
        data=area_responses,
        records_per_page=len(area_responses),
        total_count=total_count,
    )


@router.get(
    "/{company_id}/related/{area_id}",
    response_model=ListResponseModel[AreaResponse],
    status_code=status.HTTP_200_OK,
    summary="Get areas related to a specific area",
    description="Retrieve areas related to a given area based on hierarchy with optional type filtering.",
)
async def get_areas_related_to(
    company_id: UUID,
    area_id: int,
    area_type: AreaType = Query(..., description="Type of the reference area"),
    required_type: AreaType | None = Query(
        None, description="Type to filter related areas"
    ),
    limit: int = Query(
        10, ge=1, le=100, description="Maximum number of records to return"
    ),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    area_service: AreaService = Depends(get_area_service),
) -> ListResponseModel[AreaResponse]:
    """
    Get areas related to a specific area based on hierarchy.

    Args:
        company_id: UUID of the company
        area_id: ID of the reference area
        area_type: Type of the reference area
        required_type: Optional type to filter related areas
        limit: Maximum number of records to return (default: 10)
        offset: Number of records to skip (default: 0)
        area_service: Injected AreaService dependency

    Returns:
        ListResponseModel with list of related areas, pagination info, and total count
    """
    logger.info(
        "Fetching areas related to area",
        company_id=str(company_id),
        area_id=area_id,
        area_type=area_type,
        required_type=required_type,
        limit=limit,
        offset=offset,
    )

    areas, total_count = await area_service.get_areas_related_to(
        company_id, area_id, area_type, required_type, limit, offset
    )

    area_responses = [
        AreaResponse(
            id=area.id,
            name=area.name,
            type=area.type,
            area_id=area.area_id,
            region_id=area.region_id,
            zone_id=area.zone_id,
            nation_id=area.nation_id,
            is_active=area.is_active,
            created_at=area.created_at,
            updated_at=area.updated_at,
        )
        for area in areas
    ]

    return ListResponseModel(
        status_code=status.HTTP_200_OK,
        data=area_responses,
        records_per_page=len(area_responses),
        total_count=total_count,
    )


@router.patch(
    "/",
    response_model=ResponseModel[AreaResponse],
    status_code=status.HTTP_200_OK,
    summary="Update an area",
    description="Update an existing area's details.",
)
async def update_area(
    request: UpdateAreaRequest,
    area_service: AreaService = Depends(get_area_service),
) -> ResponseModel[AreaResponse]:
    """
    Update an area.

    Args:
        request: UpdateAreaRequest with update details
        area_service: Injected AreaService dependency

    Returns:
        AreaResponse with updated area details

    Raises:
        HTTPException: 404 if area not found
        HTTPException: 400 if no fields provided for update
    """
    logger.info("Updating area", area_id=request.id, company_id=str(request.company_id))

    # Validate at least one field is provided
    if not request.has_updates():
        area = await area_service.get_area_by_id(request.company_id, request.id)
    else:
        area = await area_service.update_area(
            company_id=request.company_id,
            id=request.id,
            name=request.name,
            type=request.type,
            area_id=request.area_id,
            region_id=request.region_id,
            zone_id=request.zone_id,
            nation_id=request.nation_id,
        )

    return ResponseModel(
        status_code=status.HTTP_200_OK,
        data=AreaResponse(
            id=area.id,
            name=area.name,
            type=area.type,
            area_id=area.area_id,
            region_id=area.region_id,
            zone_id=area.zone_id,
            nation_id=area.nation_id,
            is_active=area.is_active,
            created_at=area.created_at,
            updated_at=area.updated_at,
        ),
    )


@router.delete(
    "/{company_id}/{area_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an area",
    description="Soft delete an area by marking it as inactive.",
)
async def delete_area(
    company_id: UUID,
    area_id: int,
    area_service: AreaService = Depends(get_area_service),
) -> None:
    """
    Delete an area (soft delete).

    Args:
        request: DeleteAreaRequest with area identifier
        area_service: Injected AreaService dependency

    Returns:
        None

    Raises:
        HTTPException: 404 if area not found
    """
    logger.info(
        "Deleting area", area_id=area_id, company_id=str(company_id)
    )

    await area_service.delete_area(company_id, area_id)

    return
