"""
Service layer for Order entity operations.

This service provides business logic for orders, including order amount calculation,
order item management, and order status transitions, acting as an intermediary
between the API layer and the repository layer.
"""

from api.models.orders import OrderUpdate
from api.models.orders import OrderItemCreate
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

import structlog

from api.database import DatabasePool
from api.exceptions.order import (
    OrderAlreadyExistsException,
    OrderNotFoundException,
    OrderOperationException,
    OrderStatusException,
    OrderValidationException,
)
from api.models.orders import (
    OrderCreate,
    OrderDetailResponse,
    OrderListItem,
    OrderResponse,
    OrderStatus,
    OrderType,
    OrderItemUpdate,
)
from api.repository.order import OrderRepository
from api.repository.product import ProductRepository
from api.repository.retailer import RetailerRepository

logger = structlog.get_logger(__name__)


class OrderService:
    """
    Service for managing Order business logic.

    This service handles business logic, validation, orchestration, and
    amount calculation for order operations in a multi-tenant environment.
    """

    def __init__(self, db_pool: DatabasePool, company_id: UUID) -> None:
        """
        Initialize the OrderService.

        Args:
            db_pool: Database pool instance for connection management
            company_id: UUID of the company (tenant) for schema isolation
        """
        self.db_pool = db_pool
        self.company_id = company_id
        self.repository = OrderRepository(db_pool, company_id)
        self.product_repository = ProductRepository(db_pool, company_id)
        self.retailer_repository = RetailerRepository(db_pool, company_id)
        logger.debug(
            "OrderService initialized",
            company_id=str(company_id),
        )

    async def _calculate_order_amounts(
        self, retailer_id: UUID, items: list[OrderItemCreate]
    ) -> dict:
        """
        Calculate order amounts based on items and product pricing.

        Args:
            retailer_id: ID of the retailer
            items: List of order items with product_id and quantity

        Returns:
            Dictionary containing calculated amounts

        Raises:
            OrderValidationException: If product pricing not found
            OrderOperationException: If calculation fails
        """
        try:
            base_amount = Decimal("0.00")
            discount_amount = Decimal("0.00")
            igst_amount = Decimal("0.00")
            cgst_amount = Decimal("0.00")
            sgst_amount = Decimal("0.00")
            
            
            # Calculate base amount from items
            for item in items:
                # Get product with pricing for retailer's area
                product = await self.product_repository.get_product_prize_for_shop_id(
                    item.product_id,
                    retailer_id,
                )
                
                # TODO: Implement proper pricing logic based on area/route
                # For now, using a simplified calculation
                # You'll need to get the actual price from product_prices table
                # filtered by area_id from the retailer's route
                
                # Placeholder: assuming MRP is available
                # In production, you should fetch from product_prices table
                if product is None or product[0] is None:
                    raise OrderValidationException(
                        message=f"Product {item.product_id} has no pricing information",
                        field="product_id",
                        value=str(item.product_id),
                    )
                
                item_amount = Decimal(str(product[0])) * Decimal(str(item.quantity))
                base_amount += item_amount
                cgst_amount += item_amount * Decimal(str(product[1]/2))/100
                sgst_amount += item_amount * Decimal(str(product[1]/2))/100
                print("Product ID:", item.product_id, "Amount:", item_amount, "CGST:", cgst_amount, "SGST:", sgst_amount)
            
            # Calculate net amount (base - discount)
            net_amount = base_amount - discount_amount
            
            # Calculate total amount
            total_amount = net_amount + igst_amount + cgst_amount + sgst_amount
            
            return {
                "base_amount": base_amount.quantize(Decimal("0.01")),
                "discount_amount": discount_amount.quantize(Decimal("0.01")),
                "net_amount": net_amount.quantize(Decimal("0.01")),
                "igst_amount": igst_amount.quantize(Decimal("0.01")),
                "cgst_amount": cgst_amount.quantize(Decimal("0.01")),
                "sgst_amount": sgst_amount.quantize(Decimal("0.01")),
                "total_amount": total_amount.quantize(Decimal("0.01")),
            }
            
        except OrderValidationException:
            raise
        except Exception as e:
            logger.error(
                "Failed to calculate order amounts",
                retailer_id=str(retailer_id),
                error=str(e),
                company_id=str(self.company_id),
            )
            raise OrderOperationException(
                message=f"Failed to calculate order amounts: {str(e)}",
                operation="calculate_amounts",
            ) from e

    def _validate_status_transition(
        self, current_status: OrderStatus, new_status: OrderStatus
    ) -> bool:
        """
        Validate if the status transition is allowed.

        Valid transitions:
        - DRAFT -> CONFIRMED, CANCELLED
        - CONFIRMED -> DELIVERED, CANCELLED
        - DELIVERED -> (no transitions allowed)
        - CANCELLED -> (no transitions allowed)

        Args:
            current_status: Current order status
            new_status: New order status to transition to

        Returns:
            True if transition is valid

        Raises:
            OrderStatusException: If transition is invalid
        """
        valid_transitions = {
            OrderStatus.DRAFT: [OrderStatus.CONFIRMED, OrderStatus.CANCELLED],
            OrderStatus.CONFIRMED: [OrderStatus.DELIVERED, OrderStatus.CANCELLED],
            OrderStatus.DELIVERED: [],
            OrderStatus.CANCELLED: [],
        }

        if new_status not in valid_transitions.get(current_status, []):
            raise OrderStatusException(
                current_status=current_status.value,
                new_status=new_status.value,
            )

        return True

    async def create_order(self, order_data: OrderCreate) -> OrderResponse:
        """
        Create a new order with automatic amount calculation.

        Args:
            order_data: Order data to create (without amounts)

        Returns:
            Created order with items

        Raises:
            OrderAlreadyExistsException: If order with ID already exists
            OrderValidationException: If validation fails
            OrderOperationException: If creation fails
        """
        try:
            logger.info(
                "Creating order",
                retailer_id=str(order_data.retailer_id),
                member_id=str(order_data.member_id),
                items_count=len(order_data.items),
                company_id=str(self.company_id),
            )

            # Validate items
            if not order_data.items or len(order_data.items) == 0:
                raise OrderValidationException(
                    message="Order must have at least one item",
                    field="items",
                )

            # Check for duplicate products in items
            product_ids = [item.product_id for item in order_data.items]
            if len(product_ids) != len(set(product_ids)):
                raise OrderValidationException(
                    message="Order cannot have duplicate products",
                    field="items",
                )

            # Calculate order amounts
            amounts = await self._calculate_order_amounts(
                order_data.retailer_id, order_data.items
            )

            # Generate order ID
            order_id = uuid4()

            # Create order using repository
            order = await self.repository.create_order(
                order_data, order_id, amounts
            )

            # Get order items
            items = await self.repository.get_order_items(order.id)

            logger.info(
                "Order created successfully",
                order_id=str(order.id),
                retailer_id=str(order_data.retailer_id),
                total_amount=str(amounts["total_amount"]),
                company_id=str(self.company_id),
            )

            return OrderResponse(
                **order.model_dump(),
                items=[
                    {"product_id": item.product_id, "quantity": item.quantity}
                    for item in items
                ],
            )

        except (
            OrderAlreadyExistsException,
            OrderValidationException,
            OrderOperationException,
        ):
            raise
        except Exception as e:
            logger.error(
                "Failed to create order in service",
                retailer_id=str(order_data.retailer_id),
                error=str(e),
                company_id=str(self.company_id),
            )
            raise OrderOperationException(
                message=f"Failed to create order: {str(e)}",
                operation="create_order",
            ) from e

    async def get_order_by_id(self, order_id: UUID) -> OrderResponse:
        """
        Get an order by ID with items.

        Args:
            order_id: ID of the order

        Returns:
            Order with items

        Raises:
            OrderNotFoundException: If order not found
            OrderOperationException: If retrieval fails
        """
        try:
            logger.debug(
                "Getting order by ID",
                order_id=str(order_id),
                company_id=str(self.company_id),
            )

            # Get order
            order = await self.repository.get_order_by_id(order_id)

            # Get order items
            items = await self.repository.get_order_items(order_id)

            return OrderResponse(
                **order.model_dump(),
                items=[
                    {"product_id": item.product_id, "quantity": item.quantity}
                    for item in items
                ],
            )

        except OrderNotFoundException:
            logger.warning(
                "Order not found",
                order_id=str(order_id),
                company_id=str(self.company_id),
            )
            raise
        except Exception as e:
            logger.error(
                "Failed to get order in service",
                order_id=str(order_id),
                error=str(e),
                company_id=str(self.company_id),
            )
            raise OrderOperationException(
                message=f"Failed to get order: {str(e)}",
                operation="get_order",
            ) from e

    async def get_order_detail_by_id(self, order_id: UUID) -> OrderDetailResponse:
        """
        Get order details by ID with full joined information.

        Args:
            order_id: ID of the order

        Returns:
            Order with full details including retailer, member, and product information

        Raises:
            OrderNotFoundException: If order not found
            OrderOperationException: If retrieval fails
        """
        try:
            logger.debug(
                "Getting order detail by ID",
                order_id=str(order_id),
                company_id=str(self.company_id),
            )

            order_detail = await self.repository.get_order_detail_by_id(order_id)

            return order_detail

        except OrderNotFoundException:
            logger.warning(
                "Order not found",
                order_id=str(order_id),
                company_id=str(self.company_id),
            )
            raise
        except Exception as e:
            logger.error(
                "Failed to get order detail in service",
                order_id=str(order_id),
                error=str(e),
                company_id=str(self.company_id),
            )
            raise OrderOperationException(
                message=f"Failed to get order detail: {str(e)}",
                operation="get_order_detail",
            ) from e

    async def list_orders(
        self,
        retailer_id: Optional[UUID] = None,
        member_id: Optional[UUID] = None,
        order_status: Optional[OrderStatus] = None,
        order_type: Optional[OrderType] = None,
        is_active: Optional[bool] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[OrderListItem], int]:
        """
        List all orders with optional filtering and return total count.

        Returns optimized list view with minimal fields for performance.

        Args:
            retailer_id: Filter by retailer ID
            member_id: Filter by member ID
            order_status: Filter by order status
            order_type: Filter by order type
            is_active: Filter by active status
            limit: Maximum number of orders to return (default: 20, max: 100)
            offset: Number of orders to skip (default: 0)

        Returns:
            Tuple of (list of orders with minimal data, total count)

        Raises:
            OrderValidationException: If validation fails
            OrderOperationException: If listing fails
        """
        try:
            logger.debug(
                "Listing orders",
                retailer_id=str(retailer_id) if retailer_id else None,
                member_id=str(member_id) if member_id else None,
                order_status=order_status.value if order_status else None,
                order_type=order_type.value if order_type else None,
                is_active=is_active,
                limit=limit,
                offset=offset,
                company_id=str(self.company_id),
            )

            # Validate pagination parameters
            if limit < 1 or limit > 100:
                raise OrderValidationException(
                    message="Limit must be between 1 and 100",
                    field="limit",
                    value=limit,
                )

            if offset < 0:
                raise OrderValidationException(
                    message="Offset must be non-negative",
                    field="offset",
                    value=offset,
                )

            # Get orders and count in parallel for better performance
            async with self.db_pool.acquire() as conn:
                orders = await self.repository.list_orders(
                    retailer_id=retailer_id,
                    member_id=member_id,
                    order_status=order_status,
                    order_type=order_type,
                    is_active=is_active,
                    limit=limit,
                    offset=offset,
                    connection=conn,
                )
                total_count = await self.repository.count_orders(
                    retailer_id=retailer_id,
                    member_id=member_id,
                    order_status=order_status,
                    order_type=order_type,
                    is_active=is_active,
                    connection=conn,
                )

            logger.debug(
                "Orders listed successfully",
                count=len(orders),
                total_count=total_count,
                company_id=str(self.company_id),
            )

            return orders, total_count

        except OrderValidationException:
            raise
        except Exception as e:
            logger.error(
                "Failed to list orders in service",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise OrderOperationException(
                message=f"Failed to list orders: {str(e)}",
                operation="list_orders",
            ) from e


    async def update_order(
        self, order_id: UUID, order_data: OrderItemUpdate
    ) -> OrderResponse:
        """
        Update an existing order by upserting items.

        For each item in the update:
        - If the product already exists in the order, update its quantity
        - If the product doesn't exist, add it as a new item
        
        Amounts are automatically recalculated based on all current items after upsert.

        Args:
            order_id: ID of the order to update
            order_data: Order data with items to upsert

        Returns:
            Updated order with all items

        Raises:
            OrderNotFoundException: If order not found
            OrderValidationException: If validation fails
            OrderOperationException: If update fails
        """
        # try:
        #     logger.info(
        #         "Updating order items",
        #         order_id=str(order_id),
        #         items_count=len(order_data.items),
        #         company_id=str(self.company_id),
        #     )

        #     # Get current order
        #     current_order = await self.repository.get_order_by_id(order_id)

        #     async with self.db_pool.acquire() as conn:
        #         async with conn.transaction():
        #             # Upsert items using repository (will use ON CONFLICT)
        #             await self.repository._update_order(order_id, order_data, conn)
                    
        #             # Get all current items after upsert
        #             current_items = await self.repository.get_order_items(order_id, conn)
                    
        #             # Recalculate amounts based on all current items
        #             amounts = await self._calculate_order_amounts(
        #                 current_order.retailer_id,
        #                 [OrderItemCreate(product_id=item.product_id, quantity=item.quantity) 
        #                  for item in current_items]
        #             )
                    
        #             # Update order amounts
        #             await conn.execute(
        #                 """
        #                 UPDATE orders
        #                 SET base_amount = $1, discount_amount = $2, net_amount = $3,
        #                     igst_amount = $4, cgst_amount = $5, sgst_amount = $6,
        #                     total_amount = $7
        #                 WHERE id = $8
        #                 """,
        #                 amounts["base_amount"],
        #                 amounts["discount_amount"],
        #                 amounts["net_amount"],
        #                 amounts["igst_amount"],
        #                 amounts["cgst_amount"],
        #                 amounts["sgst_amount"],
        #                 amounts["total_amount"],
        #                 order_id,
        #             )
                    
        #             # Get updated order
        #             order = await self.repository.get_order_by_id(order_id, conn)

        #     logger.info(
        #         "Order updated successfully",
        #         order_id=str(order_id),
        #         total_amount=str(amounts["total_amount"]),
        #         company_id=str(self.company_id),
        #     )

        #     return OrderResponse(
        #         **order.model_dump(),
        #         items=[
        #             {"product_id": item.product_id, "quantity": item.quantity}
        #             for item in current_items
        #         ],
        #     )

        # except (
        #     OrderNotFoundException,
        #     OrderValidationException,
        #     OrderOperationException,
        # ):
        #     raise
        # except Exception as e:
        #     logger.error(
        #         "Failed to update order in service",
        #         order_id=str(order_id),
        #         error=str(e),
        #         company_id=str(self.company_id),
        #     )
        #     raise OrderOperationException(
        #         message=f"Failed to update order: {str(e)}",
        #         operation="update_order",
        #     ) from e

        try:
            async with self.db_pool.transaction() as conn:
                # Update order items
                await self.repository.update_order_items(order_id, order_data.items, conn)

                # Get all current items after upsert
                current_order_detail = await self.repository.get_order_detail_by_id(order_id, conn)

                # Recalculate amounts based on all current items
                amounts = await self._calculate_order_amounts(
                    current_order_detail.retailer_id,
                    current_order_detail.items
                )
                await self.repository.update_order(order_id, OrderUpdate(
                    base_amount=amounts["base_amount"],
                    discount_amount=amounts["discount_amount"],
                    net_amount=amounts["net_amount"],
                    igst_amount=amounts["igst_amount"],
                    cgst_amount=amounts["cgst_amount"],
                    sgst_amount=amounts["sgst_amount"],
                    total_amount=amounts["total_amount"],
                ), conn)
                # Get updated order
                order = await self.repository.get_order_detail_by_id(order_id, conn)
            return order
        except Exception as e:
            logger.error(
                "Failed to update order in service",
                order_id=str(order_id),
                error=str(e),
                company_id=str(self.company_id),
            )
            raise OrderOperationException(
                message=f"Failed to update order: {str(e)}",
                operation="update_order",
            ) from e
        
    async def update_order_status(
        self, order_id: UUID, new_status: OrderStatus
    ) -> OrderResponse:
        """
        Update order status with validation.

        Args:
            order_id: ID of the order
            new_status: New status to set

        Returns:
            Updated order with items

        Raises:
            OrderNotFoundException: If order not found
            OrderStatusException: If invalid status transition
            OrderOperationException: If update fails
        """
        try:
            logger.info(
                "Updating order status",
                order_id=str(order_id),
                new_status=new_status.value,
                company_id=str(self.company_id),
            )

            # Get current order
            current_order = await self.repository.get_order_by_id(order_id)
            current_status = OrderStatus(current_order.order_status)

            # Validate status transition
            self._validate_status_transition(current_status, new_status)

            # Update status
            order_data = OrderUpdate(order_status=new_status)
            order = await self.repository.update_order(order_id, order_data)

            # Get order items
            items = await self.repository.get_order_items(order.id)

            logger.info(
                "Order status updated successfully",
                order_id=str(order_id),
                old_status=current_status.value,
                new_status=new_status.value,
                company_id=str(self.company_id),
            )

            return OrderResponse(
                **order.model_dump(),
                items=[
                    {"product_id": item.product_id, "quantity": item.quantity}
                    for item in items
                ],
            )

        except (OrderNotFoundException, OrderStatusException, OrderOperationException):
            raise
        except Exception as e:
            logger.error(
                "Failed to update order status in service",
                order_id=str(order_id),
                error=str(e),
                company_id=str(self.company_id),
            )
            raise OrderOperationException(
                message=f"Failed to update order status: {str(e)}",
                operation="update_order_status",
            ) from e

    async def delete_order(self, order_id: UUID) -> None:
        """
        Soft delete an order (set is_active to false).

        Args:
            order_id: ID of the order to delete

        Raises:
            OrderNotFoundException: If order not found
            OrderOperationException: If deletion fails
        """
        try:
            logger.info(
                "Deleting order",
                order_id=str(order_id),
                company_id=str(self.company_id),
            )

            await self.repository.delete_order(order_id)

            logger.info(
                "Order deleted successfully",
                order_id=str(order_id),
                company_id=str(self.company_id),
            )

        except (OrderNotFoundException, OrderOperationException):
            raise
        except Exception as e:
            logger.error(
                "Failed to delete order in service",
                order_id=str(order_id),
                error=str(e),
                company_id=str(self.company_id),
            )
            raise OrderOperationException(
                message=f"Failed to delete order: {str(e)}",
                operation="delete_order",
            ) from e
