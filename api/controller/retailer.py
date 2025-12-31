"""
Retailer controller/router for FastAPI endpoints.

This module defines all REST API endpoints for retailer management
in a multi-tenant environment.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Query, status
from fastapi.responses import Response
import structlog

from api.dependencies.retailer import RetailerServiceDep
from api.exceptions.retailer import (
    RetailerAlreadyExistsException,
    RetailerNotFoundException,
    RetailerOperationException,
    RetailerValidationException,
)
from api.models import ListResponseModel, ResponseModel
from api.models.retailer import (
    RetailerCreate,
    RetailerDetailItem,
    RetailerListItem,
    RetailerResponse,
    RetailerUpdate,
)

logger = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/companies/{company_id}/retailers",
    tags=["Retailers"],
    responses={
        400: {"description": "Bad Request - Invalid input"},
        404: {"description": "Resource Not Found"},
        409: {"description": "Resource Already Exists"},
        500: {"description": "Internal Server Error"},
    },
)


@router.post(
    "",
    response_model=ResponseModel[RetailerResponse],
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Retailer created successfully"},
        400: {"description": "Validation error"},
        404: {"description": "Route or category not found"},
        409: {"description": "Retailer already exists (duplicate code, GST, PAN, etc.)"},
    },
    summary="Create a new retailer",
    description="Create a new retailer with all required details including documents and images",
)
async def create_retailer(
    retailer_data: RetailerCreate,
    retailer_service: RetailerServiceDep,
):
    """
    Create a new retailer in the system.

    **Request Body:**
    - **name**: Retailer name (1-255 characters)
    - **code**: Unique retailer code (1-255 characters) - will be uppercased
    - **contact_person_name**: Name of the contact person (1-255 characters)
    - **mobile_number**: Mobile number (10-15 characters) - will be uppercased
    - **email**: Email address (optional)
    - **gst_no**: GST number (15 characters) - will be uppercased
    - **pan_no**: PAN number (10 characters) - will be uppercased
    - **license_no**: License number (optional, max 255 characters) - will be uppercased
    - **address**: Full address (required)
    - **category_id**: Shop category ID (foreign key)
    - **pin_code**: PIN code (6 characters) - will be uppercased
    - **map_link**: Google Maps link (optional)
    - **documents**: Documents metadata in DocumentInDB format (optional)
    - **store_images**: Store images metadata in DocumentInDB format (optional)
    - **route_id**: Route ID (foreign key)
    - **is_verified**: Verification status (default: false)

    **Unique Constraints:**
    - code, gst_no, pan_no, license_no, mobile_number, email must be unique

    **Default Values:**
    - is_verified: false
    - is_active: true
    """
    try:
        retailer = await retailer_service.create_retailer(retailer_data)
        return ResponseModel(status_code=status.HTTP_201_CREATED, data=retailer)

    except RetailerAlreadyExistsException as e:
        logger.warning(
            "Retailer already exists",
            retailer_name=retailer_data.name,
            error=e.message,
        )
        raise e

    except RetailerValidationException as e:
        logger.warning(
            "Retailer validation failed",
            retailer_name=retailer_data.name,
            error=e.message,
        )
        raise e

    except RetailerOperationException as e:
        if "category" in e.message.lower() or "route" in e.message.lower():
            logger.warning(
                "Foreign key constraint failed",
                retailer_name=retailer_data.name,
                category_id=retailer_data.category_id,
                route_id=retailer_data.route_id,
                error=e.message,
            )
            raise e
        logger.error(
            "Failed to create retailer",
            retailer_name=retailer_data.name,
            error=str(e),
        )
        raise e

    except Exception as e:
        logger.error(
            "Unexpected error creating retailer",
            retailer_name=retailer_data.name,
        )
        raise e


@router.get(
    "/{retailer_id}",
    response_model=ResponseModel[RetailerDetailItem],
    responses={
        200: {"description": "Retailer retrieved successfully"},
        404: {"description": "Retailer not found"},
    },
    summary="Get retailer by ID",
    description="Retrieve detailed information about a specific retailer including category and route names",
)
async def get_retailer(
    retailer_id: Annotated[UUID, Path(description="Retailer ID (UUID)")],
    retailer_service: RetailerServiceDep,
):
    """
    Get a retailer by ID.

    Returns complete retailer information including:
    - All retailer fields
    - Category name (joined from shop_categories)
    - Route name (joined from routes)
    - Documents and store images
    - Verification status
    - Active status
    - Timestamps
    """
    try:
        retailer = await retailer_service.get_retailer_by_id(retailer_id)
        return ResponseModel(status_code=status.HTTP_200_OK, data=retailer)

    except RetailerNotFoundException as e:
        logger.info(
            "Retailer not found",
            retailer_id=str(retailer_id),
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to get retailer",
            retailer_id=str(retailer_id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve retailer",
        )


@router.get(
    "/by-code/{code}",
    response_model=ResponseModel[RetailerDetailItem],
    responses={
        200: {"description": "Retailer retrieved successfully"},
        404: {"description": "Retailer not found"},
    },
    summary="Get retailer by code",
    description="Retrieve a retailer by its unique code",
)
async def get_retailer_by_code(
    code: Annotated[str, Path(description="Retailer code")],
    retailer_service: RetailerServiceDep,
):
    """
    Get a retailer by its unique code.

    Returns complete retailer information including category and route names.
    Only returns active retailers.
    """
    try:
        retailer = await retailer_service.get_retailer_by_code(code)
        return ResponseModel(status_code=status.HTTP_200_OK, data=retailer)

    except RetailerNotFoundException as e:
        logger.info(
            "Retailer not found by code",
            retailer_code=code,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to get retailer by code",
            retailer_code=code,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve retailer",
        )


@router.get(
    "",
    response_model=ListResponseModel[RetailerListItem],
    responses={
        200: {"description": "Retailers retrieved successfully"},
        400: {"description": "Invalid pagination parameters"},
    },
    summary="List all retailers",
    description="List retailers with pagination and optional filtering by route, category, and status",
)
async def list_retailers(
    retailer_service: RetailerServiceDep,
    route_id: Annotated[
        int | None,
        Query(description="Filter by route ID", ge=1),
    ] = None,
    category_id: Annotated[
        int | None,
        Query(description="Filter by shop category ID", ge=1),
    ] = None,
    is_active: Annotated[
        bool | None,
        Query(description="Filter by active status (true/false, optional)"),
    ] = None,
    limit: Annotated[
        int,
        Query(ge=1, le=100, description="Number of retailers to return (1-100)"),
    ] = 20,
    offset: Annotated[
        int,
        Query(ge=0, description="Number of retailers to skip (pagination)"),
    ] = 0,
):
    """
    List all retailers with pagination and filtering.

    Returns optimized retailer data with minimal fields for performance:
    - id, name, code
    - contact_person_name, mobile_number
    - address
    - route_id, route_name (joined)
    - store_images (JSONB)
    - is_verified, is_active

    Use the detail endpoint (GET /{retailer_id}) to get complete retailer information including documents.

    **Filters:**
    - **route_id**: Filter by specific route
    - **category_id**: Filter by specific shop category
    - **is_active**: Filter by active status
    - **limit**: Results per page (default: 20, max: 100)
    - **offset**: Skip results for pagination (default: 0)

    **Examples:**
    - List active retailers for route 1: `?route_id=1&is_active=true`
    - List retailers in category 2: `?category_id=2`
    - List verified retailers: Filter in application after fetching
    """
    try:
        retailers, total_count = await retailer_service.list_retailers(
            route_id=route_id,
            category_id=category_id,
            is_active=is_active,
            limit=limit,
            offset=offset,
        )

        return ListResponseModel(
            status_code=status.HTTP_200_OK,
            data=retailers,
            records_per_page=limit,
            total_count=total_count,
        )

    except RetailerValidationException as e:
        logger.warning(
            "Invalid parameters for list retailers",
            route_id=route_id,
            category_id=category_id,
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
            "Failed to list retailers",
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list retailers",
        )


@router.patch(
    "/{retailer_id}",
    response_model=ResponseModel[RetailerResponse],
    responses={
        200: {"description": "Retailer updated successfully"},
        400: {"description": "Validation error"},
        404: {"description": "Retailer not found"},
        409: {"description": "Duplicate value (GST, PAN, etc.)"},
    },
    summary="Update a retailer",
    description="Update retailer details (code cannot be changed)",
)
async def update_retailer(
    retailer_id: Annotated[UUID, Path(description="Retailer ID (UUID)")],
    retailer_data: RetailerUpdate,
    retailer_service: RetailerServiceDep,
):
    """
    Update an existing retailer.

    **Updatable Fields:**
    - name, contact_person_name, mobile_number, email
    - gst_no, pan_no, license_no
    - address, pin_code, map_link
    - category_id, route_id
    - documents, store_images
    - is_verified

    **Note**:
    - Retailer code cannot be updated after creation
    - At least one field must be provided for update
    - Unique constraints are enforced (GST, PAN, license, mobile, email)
    """
    try:
        retailer = await retailer_service.update_retailer(retailer_id, retailer_data)
        return ResponseModel(status_code=status.HTTP_200_OK, data=retailer)

    except RetailerNotFoundException as e:
        logger.info(
            "Retailer not found for update",
            retailer_id=str(retailer_id),
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except RetailerAlreadyExistsException as e:
        logger.warning(
            "Retailer update failed - duplicate value",
            retailer_id=str(retailer_id),
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        )

    except RetailerValidationException as e:
        logger.warning(
            "Retailer update validation failed",
            retailer_id=str(retailer_id),
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to update retailer",
            retailer_id=str(retailer_id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update retailer",
        )


@router.delete(
    "/{retailer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Retailer deactivated successfully"},
        404: {"description": "Retailer not found"},
    },
    summary="Delete a retailer (soft delete)",
    description="Soft delete a retailer by setting is_active to false",
)
async def delete_retailer(
    retailer_id: Annotated[UUID, Path(description="Retailer ID (UUID)")],
    retailer_service: RetailerServiceDep,
):
    """
    Delete a retailer (soft delete).

    Sets is_active to false instead of permanently deleting the retailer.
    The retailer will still exist in the database but won't be active.
    """
    try:
        await retailer_service.delete_retailer(retailer_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except RetailerNotFoundException as e:
        logger.info(
            "Retailer not found for deletion",
            retailer_id=str(retailer_id),
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to delete retailer",
            retailer_id=str(retailer_id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete retailer",
        )


@router.get(
    "/route/{route_id}/retailers",
    response_model=ListResponseModel[RetailerListItem],
    responses={
        200: {"description": "Retailers retrieved successfully"},
    },
    summary="Get retailers by route",
    description="Get all active retailers for a specific route",
)
async def get_retailers_by_route(
    route_id: Annotated[int, Path(description="Route ID", ge=1)],
    retailer_service: RetailerServiceDep,
):
    """
    Get all active retailers for a specific route.

    Returns optimized retailer list for all active retailers in the route.
    Useful for route planning and assignments.
    """
    try:
        retailers = await retailer_service.get_retailers_by_route(route_id)
        return ListResponseModel(
            status_code=status.HTTP_200_OK,
            data=retailers,
            records_per_page=len(retailers),
            total_count=len(retailers),
        )

    except Exception as e:
        logger.error(
            "Failed to get retailers by route",
            route_id=route_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get retailers",
        )


@router.post(
    "/{retailer_id}/verify",
    response_model=ResponseModel[RetailerResponse],
    responses={
        200: {"description": "Retailer verified successfully"},
        404: {"description": "Retailer not found"},
    },
    summary="Verify a retailer",
    description="Set is_verified to true for a retailer",
)
async def verify_retailer(
    retailer_id: Annotated[UUID, Path(description="Retailer ID (UUID)")],
    retailer_service: RetailerServiceDep,
):
    """
    Verify a retailer.

    Sets is_verified to true. This typically indicates that the retailer's
    documents and information have been reviewed and approved.
    """
    try:
        retailer = await retailer_service.verify_retailer(retailer_id)
        return ResponseModel(status_code=status.HTTP_200_OK, data=retailer)

    except RetailerNotFoundException as e:
        logger.info(
            "Retailer not found for verification",
            retailer_id=str(retailer_id),
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to verify retailer",
            retailer_id=str(retailer_id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify retailer",
        )


@router.post(
    "/{retailer_id}/unverify",
    response_model=ResponseModel[RetailerResponse],
    responses={
        200: {"description": "Retailer unverified successfully"},
        404: {"description": "Retailer not found"},
    },
    summary="Unverify a retailer",
    description="Set is_verified to false for a retailer",
)
async def unverify_retailer(
    retailer_id: Annotated[UUID, Path(description="Retailer ID (UUID)")],
    retailer_service: RetailerServiceDep,
):
    """
    Unverify a retailer.

    Sets is_verified to false. This can be used if verification needs to be revoked
    or if the retailer's information needs to be re-reviewed.
    """
    try:
        retailer = await retailer_service.unverify_retailer(retailer_id)
        return ResponseModel(status_code=status.HTTP_200_OK, data=retailer)

    except RetailerNotFoundException as e:
        logger.info(
            "Retailer not found for unverification",
            retailer_id=str(retailer_id),
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to unverify retailer",
            retailer_id=str(retailer_id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unverify retailer",
        )


@router.get(
    "/stats/counts",
    response_model=ResponseModel[dict],
    responses={
        200: {"description": "Counts retrieved successfully"},
    },
    summary="Get retailer statistics",
    description="Get counts of active and verified retailers with optional filters",
)
async def get_retailer_stats(
    retailer_service: RetailerServiceDep,
    route_id: Annotated[
        int | None,
        Query(description="Optional filter by route ID", ge=1),
    ] = None,
    category_id: Annotated[
        int | None,
        Query(description="Optional filter by category ID", ge=1),
    ] = None,
):
    """
    Get retailer statistics.

    Returns:
    - Total active retailers count
    - Total verified retailers count
    - Verification rate (percentage)

    Optionally filter by route and/or category.
    """
    try:
        active_count = await retailer_service.get_active_retailers_count(
            route_id=route_id,
            category_id=category_id,
        )
        verified_count = await retailer_service.get_verified_retailers_count(
            route_id=route_id,
            category_id=category_id,
        )

        verification_rate = (verified_count / active_count * 100) if active_count > 0 else 0

        filters = {
            "route_id": route_id,
            "category_id": category_id,
        }
        active_filters = {k: v for k, v in filters.items() if v is not None}

        return ResponseModel(
            status_code=status.HTTP_200_OK,
            data={
                "active_count": active_count,
                "verified_count": verified_count,
                "verification_rate": round(verification_rate, 2),
                "filters": active_filters if active_filters else None,
            },
        )

    except Exception as e:
        logger.error(
            "Failed to get retailer stats",
            route_id=route_id,
            category_id=category_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get retailer statistics",
        )

