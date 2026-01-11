"""
Brand controller/router for FastAPI endpoints.

This module defines all REST API endpoints for brand management including
visibility and margin configuration in a multi-tenant environment.
"""

from api.models.brand import BrandMarginAddOrUpdate
from typing import Annotated, Optional

from fastapi import APIRouter, HTTPException, Path, Query, status, Body
from fastapi.responses import Response
import structlog

from api.dependencies.brand import BrandServiceDep
from api.exceptions.brand import (
    BrandAlreadyExistsException,
    BrandNotFoundException,
)
from api.models import ListResponseModel, ResponseModel
from api.models.brand import (
    BrandCreate,
    BrandDetailItem,
    BrandListItem,
    BrandMarginInDB,
    BrandUpdate,
)

logger = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/companies/{company_id}/brands",
    tags=["Brands"],
    responses={
        400: {"description": "Bad Request - Invalid input"},
        404: {"description": "Resource Not Found"},
        500: {"description": "Internal Server Error"},
    },
)


@router.post(
    "",
    response_model=ResponseModel[BrandDetailItem],
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Brand created successfully"},
        409: {"description": "Brand already exists (duplicate name or code)"},
    },
    summary="Create a new brand",
    description="Create a new brand with visibility and margin configurations",
)
async def create_brand(
    brand_data: BrandCreate,
    brand_service: BrandServiceDep,
):
    """
    Create a new brand.

    **Request Body:**
    - **name**: Brand name (required, unique when active)
    - **code**: Brand code (required, unique)
    - **for_general**: Visibility for general trade
    - **for_modern**: Visibility for modern trade
    - **for_horeca**: Visibility for HORECA segment
    - **logo**: Logo document information (optional)
    - **area_id**: List of area IDs for visibility (optional, empty/null = global visibility)
    - **margins**: List of margin configurations, each with name, area_id, and margin values (optional)

    The brand is created with:
    - Visibility records for specified areas (or NULL for global)
    - Multiple margin records with user-provided names (if provided)
    """
    try:
        brand = await brand_service.create_brand(brand_data)
        return ResponseModel(status_code=status.HTTP_201_CREATED, data=brand)

    except BrandAlreadyExistsException as e:
        logger.warning(
            "Brand already exists",
            brand_name=brand_data.name,
            brand_code=brand_data.code,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to create brand",
            brand_name=brand_data.name,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create brand",
        )


@router.get(
    "/{brand_id}",
    response_model=ResponseModel[BrandDetailItem],
    responses={
        200: {"description": "Brand retrieved successfully"},
        404: {"description": "Brand not found"},
    },
    summary="Get brand by ID",
    description="Retrieve detailed brand information including all visibility and margin configurations",
)
async def get_brand(
    brand_id: Annotated[int, Path(description="Brand ID", ge=1)],
    brand_service: BrandServiceDep,
):
    """
    Get a brand by ID.

    Returns complete brand information including:
    - All brand fields
    - Associated areas with visibility configurations
    - All margin configurations with area-specific settings
    - Logo document information
    """
    try:
        brand = await brand_service.get_brand_by_id(brand_id)
        return ResponseModel(status_code=status.HTTP_200_OK, data=brand)

    except BrandNotFoundException as e:
        logger.info(
            "Brand not found",
            brand_id=brand_id,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to get brand",
            brand_id=brand_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve brand",
        )


@router.get(
    "/by-code/{code}",
    response_model=ResponseModel[BrandDetailItem],
    responses={
        200: {"description": "Brand retrieved successfully"},
        404: {"description": "Brand not found"},
    },
    summary="Get brand by code",
    description="Retrieve detailed brand information by unique brand code",
)
async def get_brand_by_code(
    code: Annotated[str, Path(description="Brand code")],
    brand_service: BrandServiceDep,
):
    """
    Get a brand by code.

    Returns complete brand information including visibility and margin configurations.
    """
    try:
        brand = await brand_service.get_brand_by_code(code)
        return ResponseModel(status_code=status.HTTP_200_OK, data=brand)

    except BrandNotFoundException as e:
        logger.info(
            "Brand not found",
            brand_code=code,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to get brand by code",
            brand_code=code,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve brand",
        )


@router.get(
    "",
    response_model=ListResponseModel[BrandListItem],
    responses={
        200: {"description": "Brands listed successfully"},
    },
    summary="List brands",
    description="Retrieve a paginated list of brands with category and product counts",
)
async def list_brands(
    brand_service: BrandServiceDep,
    is_active: Annotated[
        Optional[bool],
        Query(description="Filter by active status"),
    ] = None,
    limit: Annotated[
        int,
        Query(description="Maximum number of brands to return", ge=1, le=100),
    ] = 20,
    offset: Annotated[
        int,
        Query(description="Number of brands to skip", ge=0),
    ] = 0,
):
    """
    List brands with pagination.

    Returns:
    - **name**: Brand name
    - **code**: Brand code
    - **no_of_categories**: Count of active categories
    - **no_of_products**: Count of active products
    - **created_at**: Creation timestamp
    - **is_active**: Active status

    Use pagination parameters to navigate through large result sets.
    """
    try:
        brands = await brand_service.list_brands(
            is_active=is_active,
            limit=limit,
            offset=offset,
        )

        return ListResponseModel(
            status_code=status.HTTP_200_OK,
            data=brands,
            records_per_page=limit,
            total_count=len(
                brands
            ),  # Note: In real scenarios, total_count should reflect the total available records
        )

    except Exception as e:
        logger.error(
            "Failed to list brands",
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list brands",
        )


@router.patch(
    "/{brand_id}",
    response_model=ResponseModel[BrandDetailItem],
    responses={
        200: {"description": "Brand updated successfully"},
        404: {"description": "Brand not found"},
        409: {"description": "Brand name/code conflict"},
    },
    summary="Update a brand",
    description="Update brand information (partial update supported)",
)
async def update_brand(
    brand_id: Annotated[int, Path(description="Brand ID", ge=1)],
    brand_data: BrandUpdate,
    brand_service: BrandServiceDep,
):
    """
    Update a brand.

    Only provided fields will be updated. All fields are optional.

    **Note:** Use separate endpoints for managing visibility and margins.
    """
    try:
        brand = await brand_service.update_brand(brand_id, brand_data)
        return ResponseModel(status_code=status.HTTP_200_OK, data=brand)

    except BrandNotFoundException as e:
        logger.info(
            "Brand not found",
            brand_id=brand_id,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except BrandAlreadyExistsException as e:
        logger.warning(
            "Brand conflict",
            brand_id=brand_id,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to update brand",
            brand_id=brand_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update brand",
        )


@router.delete(
    "/{brand_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Brand deleted successfully"},
        404: {"description": "Brand not found"},
    },
    summary="Delete a brand",
    description="Soft delete a brand (sets is_deleted=true, is_active=false)",
)
async def delete_brand(
    brand_id: Annotated[int, Path(description="Brand ID", ge=1)],
    brand_service: BrandServiceDep,
):
    """
    Delete a brand.

    This is a soft delete operation - the brand record is marked as deleted
    but remains in the database for audit purposes.
    """
    try:
        await brand_service.delete_brand(brand_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except BrandNotFoundException as e:
        logger.info(
            "Brand not found",
            brand_id=brand_id,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to delete brand",
            brand_id=brand_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete brand",
        )


# ==================== Visibility Management Endpoints ====================


@router.post(
    "/{brand_id}/visibility",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Visibility added successfully"},
        404: {"description": "Brand or area not found"},
        409: {"description": "Visibility already exists"},
    },
    summary="Add brand visibility",
    description="Add visibility for a brand in a specific area or globally",
)
async def add_brand_visibility(
    brand_id: Annotated[int, Path(description="Brand ID", ge=1)],
    area_id: Annotated[
        Optional[int],
        Body(description="Area ID (null for global visibility)", embed=True),
    ] = None,
    brand_service: BrandServiceDep = None,
) -> None:
    """
    Add visibility for a brand.

    - **area_id**: null or omitted = global visibility
    - **area_id**: specific ID = visibility for that area only

    Multiple visibility records can exist for different areas.
    """
    try:
        await brand_service.add_brand_visibility(brand_id, area_id)

    except BrandNotFoundException as e:
        logger.info(
            "Brand not found",
            brand_id=brand_id,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except BrandAlreadyExistsException as e:
        logger.warning(
            "Visibility already exists",
            brand_id=brand_id,
            area_id=area_id,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to add brand visibility",
            brand_id=brand_id,
            area_id=area_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add brand visibility",
        )


@router.delete(
    "/{brand_id}/visibility",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Visibility removed successfully"},
        404: {"description": "Brand or visibility not found"},
    },
    summary="Remove brand visibility",
    description="Remove visibility for a brand in a specific area or globally",
)
async def remove_brand_visibility(
    brand_id: Annotated[int, Path(description="Brand ID", ge=1)],
    area_id: Annotated[
        Optional[int],
        Query(description="Area ID (null for global visibility)"),
    ] = None,
    brand_service: BrandServiceDep = None,
):
    """
    Remove visibility for a brand.

    - **area_id**: null or omitted = remove global visibility
    - **area_id**: specific ID = remove visibility for that area

    This is a soft delete operation.
    """
    try:
        await brand_service.remove_brand_visibility(brand_id, area_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except BrandNotFoundException as e:
        logger.info(
            "Brand or visibility not found",
            brand_id=brand_id,
            area_id=area_id,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to remove brand visibility",
            brand_id=brand_id,
            area_id=area_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove brand visibility",
        )


# ==================== Margin Management Endpoints ====================


@router.post(
    "/{brand_id}/margins",
    response_model=ResponseModel[BrandMarginInDB],
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Margin added/updated successfully"},
        404: {"description": "Brand or area not found"},
    },
    summary="Add or update brand margin",
    description="Add or update margin configuration for a brand in a specific area or globally",
)
async def add_brand_margin(
    brand_id: Annotated[int, Path(description="Brand ID", ge=1)],
    margins: BrandMarginAddOrUpdate = Body(..., description="Margin configuration"),
    brand_service: BrandServiceDep = None,
):
    """
    Add or update margin configuration for a brand.

    - **area_id**: null or omitted = global margin configuration
    - **area_id**: specific ID = margin for that area only

    **Margins structure:**
    - **super_stockist**: Margin for super stockist level (type: MARKUP/MARKDOWN/FIXED, value: number)
    - **distributor**: Margin for distributor level
    - **retailer**: Margin for retailer level

    If a margin already exists for the brand+area combination, it will be updated.
    """
    try:
        margin = await brand_service.add_brand_margin(
            brand_id, margins.area_id, margins
        )
        return ResponseModel(status_code=status.HTTP_201_CREATED, data=margin)

    except BrandNotFoundException as e:
        logger.info(
            "Brand not found",
            brand_id=brand_id,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to add brand margin",
            brand_id=brand_id,
            area_id=margins.area_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add brand margin",
        )


@router.delete(
    "/{brand_id}/margins",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Margin removed successfully"},
        404: {"description": "Brand or margin not found"},
    },
    summary="Remove brand margin",
    description="Remove margin configuration for a brand in a specific area or globally",
)
async def remove_brand_margin(
    brand_id: Annotated[int, Path(description="Brand ID", ge=1)],
    area_id: Annotated[
        Optional[int],
        Query(description="Area ID (null for global margin)"),
    ] = None,
    brand_service: BrandServiceDep = None,
):
    """
    Remove margin configuration for a brand.

    - **area_id**: null or omitted = remove global margin
    - **area_id**: specific ID = remove margin for that area

    This is a soft delete operation.
    """
    try:
        await brand_service.remove_brand_margin(brand_id, area_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except BrandNotFoundException as e:
        logger.info(
            "Brand or margin not found",
            brand_id=brand_id,
            area_id=area_id,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to remove brand margin",
            brand_id=brand_id,
            area_id=area_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove brand margin",
        )
