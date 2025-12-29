"""
ShopCategory controller/router for FastAPI endpoints.

This module defines all REST API endpoints for shop category management
in a multi-tenant environment.
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, status
from fastapi.responses import Response
import structlog

from api.dependencies.shop_category import ShopCategoryServiceDep
from api.exceptions.shop_category import (
    ShopCategoryAlreadyExistsException,
    ShopCategoryNotFoundException,
    ShopCategoryOperationException,
    ShopCategoryValidationException,
)
from api.models import ListResponseModel, ResponseModel
from api.models.shop_category import (
    ShopCategoryCreate,
    ShopCategoryListItem,
    ShopCategoryResponse,
    ShopCategoryUpdate,
)

logger = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/companies/{company_id}/shop-categories",
    tags=["Shop Categories"],
    responses={
        400: {"description": "Bad Request - Invalid input"},
        404: {"description": "Resource Not Found"},
        500: {"description": "Internal Server Error"},
    },
)


@router.post(
    "",
    response_model=ResponseModel[ShopCategoryResponse],
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Shop category created successfully"},
        400: {"description": "Validation error"},
        409: {"description": "Shop category already exists"},
    },
    summary="Create a new shop category",
    description="Create a new shop category with specified name",
)
async def create_shop_category(
    shop_category_data: ShopCategoryCreate,
    shop_category_service: ShopCategoryServiceDep,
):
    """
    Create a new shop category.

    - **name**: Unique shop category name (1-32 characters)
    """
    try:
        shop_category = await shop_category_service.create_shop_category(
            shop_category_data
        )
        return ResponseModel(status_code=status.HTTP_201_CREATED, data=shop_category)

    except ShopCategoryAlreadyExistsException as e:
        logger.warning(
            "Shop category already exists",
            shop_category_name=shop_category_data.name,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        )

    except ShopCategoryValidationException as e:
        logger.warning(
            "Shop category validation failed",
            shop_category_name=shop_category_data.name,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to create shop category",
            shop_category_name=shop_category_data.name,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create shop category",
        )


@router.get(
    "/{shop_category_id}",
    response_model=ResponseModel[ShopCategoryResponse],
    responses={
        200: {"description": "Shop category retrieved successfully"},
        404: {"description": "Shop category not found"},
    },
    summary="Get shop category by ID",
    description="Retrieve detailed information about a specific shop category",
)
async def get_shop_category(
    shop_category_id: Annotated[
        int, Path(description="ID of the shop category to retrieve", ge=1)
    ],
    shop_category_service: ShopCategoryServiceDep,
):
    """
    Get a shop category by ID.

    Returns complete shop category information including timestamps.
    """
    try:
        shop_category = await shop_category_service.get_shop_category_by_id(
            shop_category_id
        )
        return ResponseModel(status_code=status.HTTP_200_OK, data=shop_category)

    except ShopCategoryNotFoundException as e:
        logger.info(
            "Shop category not found",
            shop_category_id=shop_category_id,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to get shop category",
            shop_category_id=shop_category_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve shop category",
        )


@router.get(
    "",
    response_model=ListResponseModel[ShopCategoryListItem],
    responses={
        200: {"description": "Shop categories retrieved successfully"},
        400: {"description": "Invalid pagination parameters"},
    },
    summary="List all shop categories",
    description="List all shop categories with pagination and optional filtering by active status",
)
async def list_shop_categories(
    shop_category_service: ShopCategoryServiceDep,
    is_active: Annotated[
        bool | None,
        Query(description="Filter by active status (true/false, optional)"),
    ] = None,
    limit: Annotated[
        int,
        Query(ge=1, le=100, description="Number of shop categories to return (1-100)"),
    ] = 20,
    offset: Annotated[
        int,
        Query(ge=0, description="Number of shop categories to skip (pagination)"),
    ] = 0,
):
    """
    List all shop categories with pagination.

    Returns minimal shop category data (id, name, is_active) for performance.
    Use the detail endpoint to get complete shop category information.

    - **is_active**: Optional filter by active status
    - **limit**: Number of results to return (default: 20, max: 100)
    - **offset**: Number of results to skip (default: 0)
    """
    try:
        shop_categories, total_count = await shop_category_service.list_shop_categories(
            is_active=is_active,
            limit=limit,
            offset=offset,
        )

        return ListResponseModel(
            status_code=status.HTTP_200_OK,
            data=shop_categories,
            records_per_page=limit,
            total_count=total_count,
        )

    except ShopCategoryValidationException as e:
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
            "Failed to list shop categories",
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list shop categories",
        )


@router.patch(
    "/{shop_category_id}",
    response_model=ResponseModel[ShopCategoryResponse],
    responses={
        200: {"description": "Shop category updated successfully"},
        400: {"description": "Validation error"},
        404: {"description": "Shop category not found"},
    },
    summary="Update a shop category",
    description="Update shop category name (cannot update is_active)",
)
async def update_shop_category(
    shop_category_id: Annotated[
        int, Path(description="ID of the shop category to update", ge=1)
    ],
    shop_category_data: ShopCategoryUpdate,
    shop_category_service: ShopCategoryServiceDep,
):
    """
    Update an existing shop category.

    Only name can be updated.
    Use delete endpoint to deactivate a shop category.

    - **name**: Optional new name
    """
    try:
        shop_category = await shop_category_service.update_shop_category(
            shop_category_id, shop_category_data
        )
        return ResponseModel(status_code=status.HTTP_200_OK, data=shop_category)

    except ShopCategoryNotFoundException as e:
        logger.info(
            "Shop category not found for update",
            shop_category_id=shop_category_id,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except ShopCategoryValidationException as e:
        logger.warning(
            "Shop category update validation failed",
            shop_category_id=shop_category_id,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to update shop category",
            shop_category_id=shop_category_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update shop category",
        )


@router.delete(
    "/{shop_category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Shop category deactivated successfully"},
        400: {"description": "Validation error"},
        404: {"description": "Shop category not found"},
    },
    summary="Delete a shop category (soft delete)",
    description="Soft delete a shop category by setting is_active to false",
)
async def delete_shop_category(
    shop_category_id: Annotated[
        int, Path(description="ID of the shop category to delete", ge=1)
    ],
    shop_category_service: ShopCategoryServiceDep,
):
    """
    Delete a shop category (soft delete).

    Sets is_active to false instead of permanently deleting the shop category.
    The shop category will still exist in the database but won't be active.
    """
    try:
        await shop_category_service.delete_shop_category(shop_category_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except ShopCategoryNotFoundException as e:
        logger.info(
            "Shop category not found for deletion",
            shop_category_id=shop_category_id,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except ShopCategoryValidationException as e:
        logger.warning(
            "Shop category deletion validation failed",
            shop_category_id=shop_category_id,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to delete shop category",
            shop_category_id=shop_category_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete shop category",
        )


@router.post(
    "/bulk",
    response_model=ResponseModel[list[ShopCategoryResponse]],
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Shop categories created successfully"},
        400: {"description": "Validation error"},
        409: {"description": "One or more shop categories already exist"},
    },
    summary="Bulk create shop categories",
    description="Create multiple shop categories in a single transaction",
)
async def bulk_create_shop_categories(
    shop_categories_data: list[ShopCategoryCreate],
    shop_category_service: ShopCategoryServiceDep,
):
    """
    Bulk create multiple shop categories.

    All shop categories are created in a single transaction.
    If any shop category fails, the entire operation is rolled back.

    - **shop_categories_data**: List of shop category objects to create
    """
    try:
        shop_categories = await shop_category_service.bulk_create_shop_categories(
            shop_categories_data
        )
        return ResponseModel(
            status_code=status.HTTP_201_CREATED, data=shop_categories
        )

    except ShopCategoryAlreadyExistsException as e:
        logger.warning(
            "Bulk create failed - shop categories already exist",
            count=len(shop_categories_data),
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        )

    except ShopCategoryValidationException as e:
        logger.warning(
            "Bulk create validation failed",
            count=len(shop_categories_data),
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )

    except ShopCategoryOperationException as e:
        logger.error(
            "Bulk create operation failed",
            count=len(shop_categories_data),
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to bulk create shop categories",
            count=len(shop_categories_data),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to bulk create shop categories",
        )

