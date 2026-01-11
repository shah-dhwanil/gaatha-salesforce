"""
Product controller/router for FastAPI endpoints.

This module defines all REST API endpoints for product management including
price and visibility configuration in a multi-tenant environment.
"""

from uuid import UUID
from typing import Annotated, Optional

from fastapi import APIRouter, HTTPException, Path, Query, status
from fastapi.responses import Response
import structlog

from api.dependencies.product import ProductServiceDep
from api.exceptions.product import (
    ProductAlreadyExistsException,
    ProductNotFoundException,
    ProductOperationException,
)
from api.models import ListResponseModel, ResponseModel
from api.models.product import (
    ProductCreate,
    ProductDetailItem,
    ProductListItem,
    ProductUpdate,
)

logger = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/companies/{company_id}/products",
    tags=["Products"],
    responses={
        400: {"description": "Bad Request - Invalid input"},
        404: {"description": "Resource Not Found"},
        500: {"description": "Internal Server Error"},
    },
)


@router.post(
    "",
    response_model=ResponseModel[ProductDetailItem],
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Product created successfully"},
        409: {"description": "Product already exists (duplicate code)"},
    },
    summary="Create a new product",
    description="Create a new product with pricing and visibility configurations",
)
async def create_product(
    product_data: ProductCreate,
    product_service: ProductServiceDep,
):
    """
    Create a new product.

    **Request Body:**
    - **brand_id**: Brand ID (required)
    - **brand_category_id**: Brand category ID (required)
    - **brand_subcategory_id**: Brand subcategory ID (optional)
    - **name**: Product name (required)
    - **code**: Product code (required, unique)
    - **description**: Product description (optional)
    - **barcode**: Product barcode (optional)
    - **hsn_code**: HSN code (optional)
    - **gst_rate**: GST rate percentage (required)
    - **gst_category**: GST category (required)
    - **dimensions**: Dimensions information (optional)
    - **compliance**: Compliance information (optional)
    - **measurement_details**: Measurement details (optional)
    - **packaging_type**: Packaging type (optional)
    - **packaging_details**: List of packaging details (optional)
    - **images**: List of product images (optional)
    - **prices**: List of price configurations per area (optional)
    - **visibility**: List of visibility configurations per area and shop type (optional)

    The product is created with:
    - Price records for specified areas (optional)
    - Visibility records for specified areas and shop types (optional)
    """
    try:
        product = await product_service.create_product(product_data)
        return ResponseModel(status_code=status.HTTP_201_CREATED, data=product)

    except ProductAlreadyExistsException as e:
        logger.warning(
            "Product already exists",
            product_name=product_data.name,
            product_code=product_data.code,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        )

    except ProductOperationException as e:
        logger.error(
            "Failed to create product",
            product_name=product_data.name,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to create product",
            product_name=product_data.name,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create product",
        )


@router.get(
    "/{product_id}",
    response_model=ResponseModel[ProductDetailItem],
    responses={
        200: {"description": "Product retrieved successfully"},
        404: {"description": "Product not found"},
    },
    summary="Get product by ID",
    description="Retrieve detailed product information including all pricing and visibility configurations",
)
async def get_product(
    product_id: Annotated[int, Path(description="Product ID", ge=1)],
    product_service: ProductServiceDep,
):
    """
    Get a product by ID.

    Returns complete product information including:
    - All product fields
    - Brand and category names
    - Dimensions and measurement details
    - Packaging details
    - All images
    - All price configurations with area-specific settings
    - All visibility configurations per area and shop type
    """
    try:
        product = await product_service.get_product_by_id(product_id)
        return ResponseModel(status_code=status.HTTP_200_OK, data=product)

    except ProductNotFoundException as e:
        logger.info(
            "Product not found",
            product_id=product_id,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to get product",
            product_id=product_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve product",
        )


@router.get(
    "/by-code/{code}",
    response_model=ResponseModel[ProductDetailItem],
    responses={
        200: {"description": "Product retrieved successfully"},
        404: {"description": "Product not found"},
    },
    summary="Get product by code",
    description="Retrieve detailed product information by unique product code",
)
async def get_product_by_code(
    code: Annotated[str, Path(description="Product code")],
    product_service: ProductServiceDep,
):
    """
    Get a product by code.

    Returns complete product information including pricing and visibility configurations.
    """
    try:
        product = await product_service.get_product_by_code(code)
        return ResponseModel(status_code=status.HTTP_200_OK, data=product)

    except ProductNotFoundException as e:
        logger.info(
            "Product not found",
            product_code=code,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to get product by code",
            product_code=code,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve product",
        )


@router.get(
    "",
    response_model=ListResponseModel[ProductListItem],
    responses={
        200: {"description": "Products listed successfully"},
    },
    summary="List products",
    description="Retrieve a paginated list of products with images, name, category, price, and status",
)
async def list_products(
    product_service: ProductServiceDep,
    is_active: Annotated[
        Optional[bool],
        Query(description="Filter by active status"),
    ] = None,
    brand_id: Annotated[
        Optional[int],
        Query(description="Filter by brand ID", ge=1),
    ] = None,
    category_id: Annotated[
        Optional[int],
        Query(description="Filter by category ID", ge=1),
    ] = None,
    limit: Annotated[
        int,
        Query(description="Maximum number of products to return", ge=1, le=100),
    ] = 20,
    offset: Annotated[
        int,
        Query(description="Number of products to skip", ge=0),
    ] = 0,
):
    """
    List products with pagination and filtering.

    Returns:
    - **id**: Product ID
    - **name**: Product name
    - **category_name**: Brand category name
    - **images**: List of product images
    - **price**: Base price (MRP from default area)
    - **is_active**: Active status

    Use pagination parameters to navigate through large result sets.
    Use filter parameters to narrow down results by brand, category, or status.
    """
    try:
        products = await product_service.list_products(
            is_active=is_active,
            brand_id=brand_id,
            category_id=category_id,
            limit=limit,
            offset=offset,
        )

        return ListResponseModel(
            status_code=status.HTTP_200_OK,
            data=products,
            records_per_page=limit,
            total_count=len(
                products
            ),  # Note: In real scenarios, total_count should reflect the total available records
        )

    except Exception as e:
        logger.error(
            "Failed to list products",
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list products",
        )


@router.patch(
    "/{product_id}",
    response_model=ResponseModel[ProductDetailItem],
    responses={
        200: {"description": "Product updated successfully"},
        404: {"description": "Product not found"},
        409: {"description": "Product code conflict"},
    },
    summary="Update a product",
    description="Update product information (partial update supported)",
)
async def update_product(
    product_id: Annotated[int, Path(description="Product ID", ge=1)],
    product_data: ProductUpdate,
    product_service: ProductServiceDep,
):
    """
    Update a product.

    Only provided fields will be updated. All fields are optional.

    **Note:** This updates only the main product information. Use separate endpoints
    for managing prices and visibility configurations if needed.
    """
    try:
        product = await product_service.update_product(product_id, product_data)
        return ResponseModel(status_code=status.HTTP_200_OK, data=product)

    except ProductNotFoundException as e:
        logger.info(
            "Product not found",
            product_id=product_id,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except ProductAlreadyExistsException as e:
        logger.warning(
            "Product conflict",
            product_id=product_id,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        )

    except ProductOperationException as e:
        logger.error(
            "Failed to update product",
            product_id=product_id,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to update product",
            product_id=product_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update product",
        )


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Product deleted successfully"},
        404: {"description": "Product not found"},
    },
    summary="Delete a product",
    description="Soft delete a product (sets is_active=false)",
)
async def delete_product(
    product_id: Annotated[int, Path(description="Product ID", ge=1)],
    product_service: ProductServiceDep,
):
    """
    Delete a product.

    This is a soft delete operation - the product record is marked as inactive
    but remains in the database for audit purposes.
    """
    try:
        await product_service.delete_product(product_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except ProductNotFoundException as e:
        logger.info(
            "Product not found",
            product_id=product_id,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to delete product",
            product_id=product_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete product",
        )


@router.get(
    "/shop/{shop_id}",
    response_model=ListResponseModel[ProductListItem],
    responses={
        200: {"description": "Products for shop retrieved successfully"},
    },
    summary="Get products for a specific shop",
    description="Retrieve products available for a specific shop based on route and area assignments",
)
async def get_products_for_shop(
    shop_id: Annotated[UUID, Path(description="Shop/Retailer ID")],
    product_service: ProductServiceDep,
    limit: Annotated[
        int,
        Query(description="Maximum number of products to return", ge=1, le=100),
    ] = 20,
    offset: Annotated[
        int,
        Query(description="Number of products to skip", ge=0),
    ] = 0,
):
    """
    Get products available for a specific shop.

    This endpoint retrieves products that are available for a shop considering:
    - The shop's assigned route
    - The route's area hierarchy (division, area, zone, region, nation)
    - Area-specific pricing with priority: division > area > zone > region > nation > default

    Returns:
    - **id**: Product ID
    - **name**: Product name
    - **category_name**: Brand category name
    - **images**: List of product images
    - **price**: Area-specific MRP (based on shop's area hierarchy)
    - **is_active**: Active status

    Use pagination parameters to navigate through large result sets.
    """
    try:
        products = await product_service.get_products_for_shop_id(
            shop_id=shop_id, limit=limit, offset=offset
        )

        return ListResponseModel(
            status_code=status.HTTP_200_OK,
            data=products,
            records_per_page=limit,
            total_count=len(products),
        )

    except Exception as e:
        logger.error(
            "Failed to get products for shop",
            shop_id=shop_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve products for shop",
        )
