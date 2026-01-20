"""
Order controller/router for FastAPI endpoints.

This module defines all REST API endpoints for order management
in a multi-tenant environment.
"""

from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Query, status
from fastapi.responses import Response
import structlog

from api.dependencies.order import OrderServiceDep
from api.exceptions.order import (
    OrderAlreadyExistsException,
    OrderNotFoundException,
    OrderOperationException,
    OrderStatusException,
    OrderValidationException,
)
from api.models import ListResponseModel, ResponseModel
from api.models.orders import (
    OrderCreate,
    OrderDetailResponse,
    OrderListItem,
    OrderResponse,
    OrderStatus,
    OrderType,
    OrderItemUpdate,
)

logger = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/companies/{company_id}/orders",
    tags=["Orders"],
    responses={
        400: {"description": "Bad Request - Invalid input"},
        404: {"description": "Resource Not Found"},
        409: {"description": "Resource Already Exists"},
        500: {"description": "Internal Server Error"},
    },
)


@router.post(
    "",
    response_model=ResponseModel[OrderResponse],
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Order created successfully"},
        400: {"description": "Validation error"},
        404: {"description": "Retailer, member, or product not found"},
    },
    summary="Create a new order",
    description="Create a new order with automatic amount calculation based on items",
)
async def create_order(
    order_data: OrderCreate,
    order_service: OrderServiceDep,
):
    """
    Create a new order in the system.

    **Request Body:**
    - **retailer_id**: Retailer ID (UUID, required)
    - **member_id**: Member/sales person ID (UUID, required)
    - **order_type**: Type of order (TELEPHONE, IN_STORE, OTHERS)
    - **order_status**: Initial status (default: DRAFT)
    - **items**: List of order items with product_id and quantity (at least 1 required)

    **Automatic Calculations:**
    - Base amount (sum of product prices × quantities)
    - Discount amount
    - Net amount (base - discount)
    - GST amounts (IGST, CGST, SGST)
    - Total amount (net + taxes)

    **Validations:**
    - At least one item required
    - No duplicate products in items
    - All products must exist and have pricing
    - Retailer and member must exist
    """
    try:
        order = await order_service.create_order(order_data)
        return ResponseModel(status_code=status.HTTP_201_CREATED, data=order)

    except OrderValidationException as e:
        logger.warning(
            "Order validation failed",
            retailer_id=str(order_data.retailer_id),
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )

    except OrderOperationException as e:
        logger.error(
            "Failed to create order",
            retailer_id=str(order_data.retailer_id),
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Unexpected error creating order",
            retailer_id=str(order_data.retailer_id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create order",
        )


@router.get(
    "/{order_id}",
    response_model=ResponseModel[OrderResponse],
    responses={
        200: {"description": "Order retrieved successfully"},
        404: {"description": "Order not found"},
    },
    summary="Get order by ID",
    description="Retrieve order information with items",
)
async def get_order(
    order_id: Annotated[UUID, Path(description="Order ID (UUID)")],
    order_service: OrderServiceDep,
):
    """
    Get an order by ID.

    Returns complete order information including:
    - All order fields (amounts, status, type)
    - List of order items (product_id and quantity)
    - Timestamps
    """
    try:
        order = await order_service.get_order_by_id(order_id)
        return ResponseModel(status_code=status.HTTP_200_OK, data=order)

    except OrderNotFoundException as e:
        logger.info(
            "Order not found",
            order_id=str(order_id),
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to get order",
            order_id=str(order_id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve order",
        )


@router.get(
    "/{order_id}/detail",
    response_model=ResponseModel[OrderDetailResponse],
    responses={
        200: {"description": "Order detail retrieved successfully"},
        404: {"description": "Order not found"},
    },
    summary="Get order detail by ID",
    description="Retrieve detailed order information with joined retailer, member, and product data",
)
async def get_order_detail(
    order_id: Annotated[UUID, Path(description="Order ID (UUID)")],
    order_service: OrderServiceDep,
):
    """
    Get detailed order information by ID.

    Returns complete order information including:
    - All order fields (amounts, status, type)
    - Retailer details (name, code, mobile)
    - Member details (name, code)
    - Order items with product details (product_id, product_name, product_code, quantity)
    - Timestamps
    """
    try:
        order = await order_service.get_order_detail_by_id(order_id)
        return ResponseModel(status_code=status.HTTP_200_OK, data=order)

    except OrderNotFoundException as e:
        logger.info(
            "Order not found",
            order_id=str(order_id),
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to get order detail",
            order_id=str(order_id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve order detail",
        )


@router.get(
    "",
    response_model=ListResponseModel[OrderListItem],
    responses={
        200: {"description": "Orders retrieved successfully"},
        400: {"description": "Invalid pagination parameters"},
    },
    summary="List all orders",
    description="List orders with pagination and optional filtering",
)
async def list_orders(
    order_service: OrderServiceDep,
    retailer_id: Annotated[
        UUID | None,
        Query(description="Filter by retailer ID"),
    ] = None,
    member_id: Annotated[
        UUID | None,
        Query(description="Filter by member ID"),
    ] = None,
    order_status: Annotated[
        OrderStatus | None,
        Query(description="Filter by order status"),
    ] = None,
    order_type: Annotated[
        OrderType | None,
        Query(description="Filter by order type"),
    ] = None,
    is_active: Annotated[
        bool | None,
        Query(description="Filter by active status (true/false, optional)"),
    ] = None,
    limit: Annotated[
        int,
        Query(ge=1, le=100, description="Number of orders to return (1-100)"),
    ] = 20,
    offset: Annotated[
        int,
        Query(ge=0, description="Number of orders to skip (pagination)"),
    ] = 0,
):
    """
    List all orders with pagination and filtering.

    Returns optimized order data with minimal fields for performance:
    - id, retailer_id, member_id
    - retailer_name, member_name (joined)
    - total_amount
    - order_type, order_status
    - is_active
    - created_at, updated_at

    Use the detail endpoint (GET /{order_id}/detail) to get complete order information.

    **Filters:**
    - **retailer_id**: Filter by specific retailer
    - **member_id**: Filter by specific member/sales person
    - **order_status**: Filter by order status (DRAFT, CONFIRMED, DELIVERED, CANCELLED)
    - **order_type**: Filter by order type (TELEPHONE, IN_STORE, OTHERS)
    - **is_active**: Filter by active status
    - **limit**: Results per page (default: 20, max: 100)
    - **offset**: Skip results for pagination (default: 0)

    **Examples:**
    - List confirmed orders: `?order_status=CONFIRMED`
    - List orders for retailer: `?retailer_id=<uuid>`
    - List active telephone orders: `?order_type=TELEPHONE&is_active=true`

    **Ordering:**
    - Results are ordered by created_at DESC (newest first)
    """
    try:
        orders, total_count = await order_service.list_orders(
            retailer_id=retailer_id,
            member_id=member_id,
            order_status=order_status,
            order_type=order_type,
            is_active=is_active,
            limit=limit,
            offset=offset,
        )

        return ListResponseModel(
            status_code=status.HTTP_200_OK,
            data=orders,
            records_per_page=limit,
            total_count=total_count,
        )

    except OrderValidationException as e:
        logger.warning(
            "Invalid parameters for list orders",
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to list orders",
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list orders",
        )


@router.patch(
    "/{order_id}",
    response_model=ResponseModel[OrderResponse],
    responses={
        200: {"description": "Order updated successfully"},
        400: {"description": "Validation error"},
        404: {"description": "Order not found"},
    },
    summary="Update order items",
    description="Update order by upserting items with automatic amount recalculation",
)
async def update_order(
    order_id: Annotated[UUID, Path(description="Order ID (UUID)")],
    order_data: OrderItemUpdate,
    order_service: OrderServiceDep,
):
    """
    Update an order by upserting items.

    **Upsert Logic:**
    - If a product already exists in the order, its quantity will be updated
    - If a product doesn't exist in the order, it will be added as a new item
    - Other existing items not in the update request remain unchanged

    **Updatable Fields:**
    - **items**: List of order items (required, at least 1 item)
      - Each item has: product_id (UUID) and quantity (int > 0)

    **Automatic Recalculation:**
    After upserting items, all amounts are automatically recalculated based on ALL current items:
    - Base amount, discount, net amount
    - GST amounts (IGST, CGST, SGST)
    - Total amount

    **Validations:**
    - At least one item required
    - No duplicate products in the update request
    - All products must exist

    **Example Request:**
    ```json
    {
      "items": [
        {"product_id": "uuid1", "quantity": 5},
        {"product_id": "uuid2", "quantity": 3}
      ]
    }
    ```

    **Note:** Use the separate `/status` endpoint to update order status with validation.
    """
    try:
        order = await order_service.update_order(order_id, order_data)
        return ResponseModel(status_code=status.HTTP_200_OK, data=order)

    except OrderNotFoundException as e:
        logger.info(
            "Order not found",
            order_id=str(order_id),
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except OrderValidationException as e:
        logger.warning(
            "Order validation failed",
            order_id=str(order_id),
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )

    except OrderOperationException as e:
        logger.error(
            "Failed to update order",
            order_id=str(order_id),
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Unexpected error updating order",
            order_id=str(order_id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update order",
        )


@router.patch(
    "/{order_id}/status",
    response_model=ResponseModel[OrderResponse],
    responses={
        200: {"description": "Order status updated successfully"},
        400: {"description": "Invalid status transition"},
        404: {"description": "Order not found"},
    },
    summary="Update order status",
    description="Update only the order status with transition validation",
)
async def update_order_status(
    order_id: Annotated[UUID, Path(description="Order ID (UUID)")],
    new_status: Annotated[OrderStatus, Query(description="New order status")],
    order_service: OrderServiceDep,
):
    """
    Update only the order status.

    **Status Transitions:**
    Valid transitions only:
    - DRAFT → CONFIRMED, CANCELLED
    - CONFIRMED → DELIVERED, CANCELLED
    - DELIVERED → (no transitions allowed - terminal state)
    - CANCELLED → (no transitions allowed - terminal state)

    **Examples:**
    - Confirm draft order: `PATCH /{order_id}/status?new_status=CONFIRMED`
    - Mark as delivered: `PATCH /{order_id}/status?new_status=DELIVERED`
    - Cancel order: `PATCH /{order_id}/status?new_status=CANCELLED`
    """
    try:
        order = await order_service.update_order_status(order_id, new_status)
        return ResponseModel(status_code=status.HTTP_200_OK, data=order)

    except OrderNotFoundException as e:
        logger.info(
            "Order not found",
            order_id=str(order_id),
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except OrderStatusException as e:
        logger.warning(
            "Invalid status transition",
            order_id=str(order_id),
            new_status=new_status.value,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to update order status",
            order_id=str(order_id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update order status",
        )


@router.delete(
    "/{order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Order deleted successfully"},
        404: {"description": "Order not found"},
    },
    summary="Delete an order",
    description="Soft delete an order (sets is_active to false)",
)
async def delete_order(
    order_id: Annotated[UUID, Path(description="Order ID (UUID)")],
    order_service: OrderServiceDep,
):
    """
    Soft delete an order.

    This sets the order's is_active flag to false rather than permanently deleting it.
    The order will no longer appear in default listings but can be retrieved by ID.

    **Note:** This is a soft delete operation. The order record remains in the database
    but is marked as inactive.
    """
    try:
        await order_service.delete_order(order_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except OrderNotFoundException as e:
        logger.info(
            "Order not found",
            order_id=str(order_id),
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to delete order",
            order_id=str(order_id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete order",
        )
