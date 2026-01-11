"""
Brand Category controller/router for FastAPI endpoints.

This module defines all REST API endpoints for brand category management including
visibility and margin configuration in a multi-tenant environment.
"""

from api.models.brand_category import BrandCategoryMarginAddOrUpdate
from typing import Annotated, Optional

from fastapi import APIRouter, Body, HTTPException, Path, Query, status
from fastapi.responses import Response
import structlog

from api.dependencies.brand_category import BrandCategoryServiceDep
from api.exceptions.brand_category import (
    BrandCategoryAlreadyExistsException,
    BrandCategoryNotFoundException,
)
from api.models import ListResponseModel, ResponseModel
from api.models.brand_category import (
    BrandCategoryCreate,
    BrandCategoryDetailItem,
    BrandCategoryListItem,
    BrandCategoryMarginInDB,
    BrandCategoryUpdate,
)

logger = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/companies/{company_id}/brand-categories",
    tags=["Brand Categories"],
    responses={
        400: {"description": "Bad Request - Invalid input"},
        404: {"description": "Resource Not Found"},
        500: {"description": "Internal Server Error"},
    },
)


@router.post(
    "",
    response_model=ResponseModel[BrandCategoryDetailItem],
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Brand category created successfully"},
        409: {"description": "Brand category already exists (duplicate name or code)"},
    },
    summary="Create a new brand category",
    description="Create a new brand category with visibility and margin configurations",
)
async def create_brand_category(
    brand_category_data: BrandCategoryCreate,
    brand_category_service: BrandCategoryServiceDep,
):
    """
    Create a new brand category.

    **Request Body:**
    - **name**: Brand category name (required, unique when active)
    - **code**: Brand category code (required, unique)
    - **brand_id**: Brand ID this category belongs to (required)
    - **parent_category_id**: Parent category ID for hierarchical structure (optional)
    - **for_general**: Visibility for general trade
    - **for_modern**: Visibility for modern trade
    - **for_horeca**: Visibility for HORECA segment
    - **logo**: Logo document information (optional)
    - **area_id**: List of area IDs for visibility (optional, empty/null = global visibility)
    - **margins**: List of margin configurations with area_id (optional)

    The brand category is created with:
    - Visibility records for specified areas (or NULL for global)
    - Margin records (with NULL values if not provided)
    """
    try:
        brand_category = await brand_category_service.create_brand_category(
            brand_category_data
        )
        return ResponseModel(status_code=status.HTTP_201_CREATED, data=brand_category)

    except BrandCategoryAlreadyExistsException as e:
        logger.warning(
            "Brand category already exists",
            brand_category_name=brand_category_data.name,
            brand_category_code=brand_category_data.code,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to create brand category",
            brand_category_name=brand_category_data.name,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create brand category",
        )


@router.get(
    "/{brand_category_id}",
    response_model=ResponseModel[BrandCategoryDetailItem],
    responses={
        200: {"description": "Brand category retrieved successfully"},
        404: {"description": "Brand category not found"},
    },
    summary="Get brand category by ID",
    description="Retrieve detailed brand category information including all visibility and margin configurations",
)
async def get_brand_category(
    brand_category_id: Annotated[int, Path(description="Brand category ID", ge=1)],
    brand_category_service: BrandCategoryServiceDep,
):
    """
    Get a brand category by ID.

    Returns complete brand category information including:
    - All brand category fields
    - Parent category name (if exists)
    - Associated areas with visibility configurations
    - All margin configurations with area-specific settings
    - Logo document information
    """
    try:
        brand_category = await brand_category_service.get_brand_category_by_id(
            brand_category_id
        )
        return ResponseModel(status_code=status.HTTP_200_OK, data=brand_category)

    except BrandCategoryNotFoundException as e:
        logger.info(
            "Brand category not found",
            brand_category_id=brand_category_id,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to get brand category",
            brand_category_id=brand_category_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve brand category",
        )


@router.get(
    "/by-code/{code}",
    response_model=ResponseModel[BrandCategoryDetailItem],
    responses={
        200: {"description": "Brand category retrieved successfully"},
        404: {"description": "Brand category not found"},
    },
    summary="Get brand category by code",
    description="Retrieve detailed brand category information by unique brand category code",
)
async def get_brand_category_by_code(
    code: Annotated[str, Path(description="Brand category code")],
    brand_category_service: BrandCategoryServiceDep,
):
    """
    Get a brand category by code.

    Returns complete brand category information including visibility and margin configurations.
    """
    try:
        brand_category = await brand_category_service.get_brand_category_by_code(code)
        return ResponseModel(status_code=status.HTTP_200_OK, data=brand_category)

    except BrandCategoryNotFoundException as e:
        logger.info(
            "Brand category not found",
            brand_category_code=code,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to get brand category by code",
            brand_category_code=code,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve brand category",
        )


@router.get(
    "",
    response_model=ListResponseModel[BrandCategoryListItem],
    responses={
        200: {"description": "Brand categories listed successfully"},
    },
    summary="List brand categories",
    description="Retrieve a paginated list of brand categories with product counts",
)
async def list_brand_categories(
    brand_category_service: BrandCategoryServiceDep,
    brand_id: Annotated[
        Optional[int],
        Query(description="Filter by brand ID"),
    ] = None,
    is_active: Annotated[
        Optional[bool],
        Query(description="Filter by active status"),
    ] = None,
    limit: Annotated[
        int,
        Query(description="Maximum number of brand categories to return", ge=1, le=100),
    ] = 20,
    offset: Annotated[
        int,
        Query(description="Number of brand categories to skip", ge=0),
    ] = 0,
):
    """
    List brand categories with pagination.

    Returns:
    - **name**: Brand category name
    - **code**: Brand category code
    - **no_of_products**: Count of active products
    - **created_at**: Creation timestamp
    - **is_active**: Active status

    Use pagination parameters to navigate through large result sets.
    Filter by brand_id to get categories for a specific brand.
    """
    try:
        brand_categories = await brand_category_service.list_brand_categories(
            brand_id=brand_id,
            is_active=is_active,
            limit=limit,
            offset=offset,
        )

        return ListResponseModel(
            status_code=status.HTTP_200_OK,
            data=brand_categories,
            records_per_page=limit,
            total_count=len(brand_categories),
        )

    except Exception as e:
        logger.error(
            "Failed to list brand categories",
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list brand categories",
        )


@router.patch(
    "/{brand_category_id}",
    response_model=ResponseModel[BrandCategoryDetailItem],
    responses={
        200: {"description": "Brand category updated successfully"},
        404: {"description": "Brand category not found"},
        409: {"description": "Brand category name/code conflict"},
    },
    summary="Update a brand category",
    description="Update brand category information (partial update supported)",
)
async def update_brand_category(
    brand_category_id: Annotated[int, Path(description="Brand category ID", ge=1)],
    brand_category_data: BrandCategoryUpdate,
    brand_category_service: BrandCategoryServiceDep,
):
    """
    Update a brand category.

    Only provided fields will be updated. All fields are optional.

    **Note:** Use separate endpoints for managing visibility and margins if needed.
    """
    try:
        brand_category = await brand_category_service.update_brand_category(
            brand_category_id, brand_category_data
        )
        return ResponseModel(status_code=status.HTTP_200_OK, data=brand_category)

    except BrandCategoryNotFoundException as e:
        logger.info(
            "Brand category not found",
            brand_category_id=brand_category_id,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except BrandCategoryAlreadyExistsException as e:
        logger.warning(
            "Brand category conflict",
            brand_category_id=brand_category_id,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to update brand category",
            brand_category_id=brand_category_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update brand category",
        )


@router.delete(
    "/{brand_category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Brand category deleted successfully"},
        404: {"description": "Brand category not found"},
    },
    summary="Delete a brand category",
    description="Soft delete a brand category (sets is_deleted=true, is_active=false)",
)
async def delete_brand_category(
    brand_category_id: Annotated[int, Path(description="Brand category ID", ge=1)],
    brand_category_service: BrandCategoryServiceDep,
):
    """
    Delete a brand category.

    This is a soft delete operation - the brand category record is marked as deleted
    but remains in the database for audit purposes.
    """
    try:
        await brand_category_service.delete_brand_category(brand_category_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except BrandCategoryNotFoundException as e:
        logger.info(
            "Brand category not found",
            brand_category_id=brand_category_id,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to delete brand category",
            brand_category_id=brand_category_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete brand category",
        )


# ==================== Visibility Management Endpoints ====================


@router.post(
    "/{brand_category_id}/visibility",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Visibility added successfully"},
        404: {"description": "Brand category or area not found"},
        409: {"description": "Visibility already exists"},
    },
    summary="Add brand category visibility",
    description="Add visibility for a brand category in a specific area or globally",
)
async def add_brand_category_visibility(
    brand_category_id: Annotated[int, Path(description="Brand category ID", ge=1)],
    area_id: Annotated[
        Optional[int],
        Body(description="Area ID (null for global visibility)", embed=True),
    ] = None,
    brand_category_service: BrandCategoryServiceDep = None,
) -> None:
    """
    Add visibility for a brand category.

    - **area_id**: null or omitted = global visibility
    - **area_id**: specific ID = visibility for that area only

    Multiple visibility records can exist for different areas.
    """
    try:
        await brand_category_service.add_brand_category_visibility(
            brand_category_id, area_id
        )

    except BrandCategoryNotFoundException as e:
        logger.info(
            "Brand category not found",
            brand_category_id=brand_category_id,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except BrandCategoryAlreadyExistsException as e:
        logger.warning(
            "Visibility already exists",
            brand_category_id=brand_category_id,
            area_id=area_id,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to add brand category visibility",
            brand_category_id=brand_category_id,
            area_id=area_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add brand category visibility",
        )


@router.delete(
    "/{brand_category_id}/visibility",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Visibility removed successfully"},
        404: {"description": "Brand category or visibility not found"},
    },
    summary="Remove brand category visibility",
    description="Remove visibility for a brand category in a specific area or globally",
)
async def remove_brand_category_visibility(
    brand_category_id: Annotated[int, Path(description="Brand category ID", ge=1)],
    area_id: Annotated[
        Optional[int],
        Query(description="Area ID (null for global visibility)"),
    ] = None,
    brand_category_service: BrandCategoryServiceDep = None,
):
    """
    Remove visibility for a brand category.

    - **area_id**: null or omitted = remove global visibility
    - **area_id**: specific ID = remove visibility for that area

    This is a soft delete operation.
    """
    try:
        await brand_category_service.remove_brand_category_visibility(
            brand_category_id, area_id
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except BrandCategoryNotFoundException as e:
        logger.info(
            "Brand category or visibility not found",
            brand_category_id=brand_category_id,
            area_id=area_id,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to remove brand category visibility",
            brand_category_id=brand_category_id,
            area_id=area_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove brand category visibility",
        )


# ==================== Margin Management Endpoints ====================


@router.post(
    "/{brand_category_id}/margins",
    response_model=ResponseModel[BrandCategoryMarginInDB],
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Margin added/updated successfully"},
        404: {"description": "Brand category or area not found"},
    },
    summary="Add or update brand category margin",
    description="Add or update margin configuration for a brand category in a specific area or globally",
)
async def add_brand_category_margin(
    brand_category_id: Annotated[int, Path(description="Brand category ID", ge=1)],
    margins: BrandCategoryMarginAddOrUpdate = Body(
        ..., description="Margin configuration"
    ),
    brand_category_service: BrandCategoryServiceDep = None,
):
    """
    Add or update margin configuration for a brand category.

    - **area_id**: null or omitted = global margin configuration
    - **area_id**: specific ID = margin for that area only

    **Margins structure:**
    - **super_stockist**: Margin for super stockist level (type: MARKUP/MARKDOWN/FIXED, value: number)
    - **distributor**: Margin for distributor level
    - **retailer**: Margin for retailer level

    If a margin already exists for the brand_category+area combination, it will be updated.
    """
    try:
        margin = await brand_category_service.add_brand_category_margin(
            brand_category_id, margins.area_id, margins
        )
        return ResponseModel(status_code=status.HTTP_201_CREATED, data=margin)

    except BrandCategoryNotFoundException as e:
        logger.info(
            "Brand category not found",
            brand_category_id=brand_category_id,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to add brand category margin",
            brand_category_id=brand_category_id,
            area_id=margins.area_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add brand category margin",
        )


@router.delete(
    "/{brand_category_id}/margins",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Margin removed successfully"},
        404: {"description": "Brand category or margin not found"},
    },
    summary="Remove brand category margin",
    description="Remove margin configuration for a brand category in a specific area or globally",
)
async def remove_brand_category_margin(
    brand_category_id: Annotated[int, Path(description="Brand category ID", ge=1)],
    area_id: Annotated[
        Optional[int],
        Query(description="Area ID (null for global margin)"),
    ] = None,
    brand_category_service: BrandCategoryServiceDep = None,
):
    """
    Remove margin configuration for a brand category.

    - **area_id**: null or omitted = remove global margin
    - **area_id**: specific ID = remove margin for that area

    This is a soft delete operation.
    """
    try:
        await brand_category_service.remove_brand_category_margin(
            brand_category_id, area_id
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except BrandCategoryNotFoundException as e:
        logger.info(
            "Brand category or margin not found",
            brand_category_id=brand_category_id,
            area_id=area_id,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to remove brand category margin",
            brand_category_id=brand_category_id,
            area_id=area_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove brand category margin",
        )
