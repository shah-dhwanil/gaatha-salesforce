"""
Repository for Order entity operations.

This repository handles all database operations for orders in a multi-tenant
architecture using schema-per-tenant approach with asyncpg.
"""

from decimal import Decimal
from typing import Optional
from uuid import UUID

import asyncpg
import structlog

from api.database import DatabasePool
from api.exceptions.order import (
    OrderAlreadyExistsException,
    OrderItemAlreadyExistsException,
    OrderItemNotFoundException,
    OrderNotFoundException,
    OrderOperationException,
)
from api.models.orders import (
    OrderCreate,
    OrderDetailResponse,
    OrderInDB,
    OrderItemCreate,
    OrderItemInDB,
    OrderListItem,
    OrderStatus,
    OrderType,
    OrderUpdate,
)
from api.repository.utils import get_schema_name, set_search_path

logger = structlog.get_logger(__name__)


class OrderRepository:
    """
    Repository for managing Order entities in a multi-tenant database.

    This repository provides methods for CRUD operations on orders and order items,
    handling schema-per-tenant isolation using asyncpg.
    All methods raise exceptions when records are not found.
    """

    def __init__(self, db_pool: DatabasePool, company_id: UUID) -> None:
        """
        Initialize the OrderRepository.

        Args:
            db_pool: Database pool instance for connection management
            company_id: UUID of the company (tenant) for schema isolation
        """
        self.db_pool = db_pool
        self.company_id = company_id
        self.schema_name = get_schema_name(company_id)

    async def _create_order(
        self,
        order_data: OrderCreate,
        order_id: UUID,
        amounts: dict,
        connection: asyncpg.Connection,
    ) -> OrderInDB:
        """
        Private method to create an order with a provided connection.

        Args:
            order_data: Order data to create
            order_id: Order ID
            amounts: Dictionary containing calculated amounts
            connection: Database connection

        Returns:
            Created order

        Raises:
            OrderAlreadyExistsException: If order with the same ID already exists
            OrderOperationException: If creation fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Insert the order
            row = await connection.fetchrow(
                """
                INSERT INTO orders (
                    id, retailer_id, member_id, base_amount, discount_amount,
                    net_amount, igst_amount, cgst_amount, sgst_amount,
                    total_amount, order_type, order_status
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                RETURNING id, retailer_id, member_id, base_amount, discount_amount,
                          net_amount, igst_amount, cgst_amount, sgst_amount,
                          total_amount, order_type, order_status, is_active,
                          created_at, updated_at
                """,
                order_id,
                order_data.retailer_id,
                order_data.member_id,
                amounts["base_amount"],
                amounts["discount_amount"],
                amounts["net_amount"],
                amounts["igst_amount"],
                amounts["cgst_amount"],
                amounts["sgst_amount"],
                amounts["total_amount"],
                order_data.order_type.value,
                order_data.order_status.value,
            )

            # Insert order items
            for item in order_data.items:
                await connection.execute(
                    """
                    INSERT INTO order_items (order_id, product_id, quantity)
                    VALUES ($1, $2, $3)
                    """,
                    order_id,
                    item.product_id,
                    item.quantity,
                )

            logger.info(
                "Order created successfully",
                order_id=order_id,
                retailer_id=str(order_data.retailer_id),
                member_id=str(order_data.member_id),
                total_amount=str(amounts["total_amount"]),
                company_id=str(self.company_id),
            )

            return OrderInDB(**dict(row))

        except asyncpg.UniqueViolationError as e:
            error_msg = str(e)
            if "pk_orders" in error_msg:
                raise OrderAlreadyExistsException(order_id=order_id)
            elif "pk_order_items" in error_msg:
                raise OrderItemAlreadyExistsException(
                    order_id=order_id,
                    message="Duplicate product in order items",
                )
            else:
                raise OrderOperationException(
                    message=f"Failed to create order: {error_msg}",
                    operation="create",
                ) from e
        except asyncpg.ForeignKeyViolationError as e:
            error_msg = str(e)
            if "fk_orders_retailer" in error_msg:
                raise OrderOperationException(
                    message=f"Retailer with id {order_data.retailer_id} not found",
                    operation="create",
                ) from e
            elif "fk_orders_member" in error_msg:
                raise OrderOperationException(
                    message=f"Member with id {order_data.member_id} not found",
                    operation="create",
                ) from e
            elif "fk_order_items_product" in error_msg:
                raise OrderOperationException(
                    message="One or more products not found",
                    operation="create",
                ) from e
            else:
                raise OrderOperationException(
                    message=f"Failed to create order: {error_msg}",
                    operation="create",
                ) from e
        except Exception as e:
            logger.error(
                "Failed to create order",
                retailer_id=str(order_data.retailer_id),
                member_id=str(order_data.member_id),
                error=str(e),
                company_id=str(self.company_id),
            )
            raise OrderOperationException(
                message=f"Failed to create order: {str(e)}",
                operation="create",
            ) from e

    async def create_order(
        self,
        order_data: OrderCreate,
        order_id: UUID,
        amounts: dict,
        connection: Optional[asyncpg.Connection] = None,
    ) -> OrderInDB:
        """
        Create a new order with items.

        Args:
            order_data: Order data to create
            order_id: Order ID
            amounts: Dictionary containing calculated amounts
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Created order

        Raises:
            OrderAlreadyExistsException: If order with the same ID already exists
            OrderOperationException: If creation fails
        """
        if connection:
            return await self._create_order(order_data, order_id, amounts, connection)

        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                return await self._create_order(order_data, order_id, amounts, conn)

    async def _get_order_by_id(
        self, order_id: UUID, connection: asyncpg.Connection
    ) -> OrderInDB:
        """
        Private method to get an order by ID with a provided connection.

        Args:
            order_id: ID of the order
            connection: Database connection

        Returns:
            Order

        Raises:
            OrderNotFoundException: If order not found
            OrderOperationException: If retrieval fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            row = await connection.fetchrow(
                """
                SELECT 
                    id, retailer_id, member_id, base_amount, discount_amount,
                    net_amount, igst_amount, cgst_amount, sgst_amount,
                    total_amount, order_type, order_status, is_active,
                    created_at, updated_at
                FROM orders
                WHERE id = $1
                """,
                order_id,
            )

            if not row:
                raise OrderNotFoundException(order_id=order_id)

            return OrderInDB(**dict(row))

        except OrderNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to get order by id",
                order_id=str(order_id),
                error=str(e),
                company_id=str(self.company_id),
            )
            raise OrderOperationException(
                message=f"Failed to get order: {str(e)}",
                operation="get",
            ) from e

    async def get_order_by_id(
        self, order_id: UUID, connection: Optional[asyncpg.Connection] = None
    ) -> OrderInDB:
        """
        Get an order by ID.

        Args:
            order_id: ID of the order
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Order

        Raises:
            OrderNotFoundException: If order not found
            OrderOperationException: If retrieval fails
        """
        if connection:
            return await self._get_order_by_id(order_id, connection)

        async with self.db_pool.acquire() as conn:
            return await self._get_order_by_id(order_id, conn)

    async def _get_order_detail_by_id(
        self, order_id: UUID, connection: asyncpg.Connection
    ) -> OrderDetailResponse:
        """
        Private method to get order details by ID with joined data.

        Args:
            order_id: ID of the order
            connection: Database connection

        Returns:
            Order with detailed information

        Raises:
            OrderNotFoundException: If order not found
            OrderOperationException: If retrieval fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Get order with retailer and member details
            order_row = await connection.fetchrow(
                """
                SELECT 
                    o.id, o.retailer_id, o.member_id, o.base_amount, o.discount_amount,
                    o.net_amount, o.igst_amount, o.cgst_amount, o.sgst_amount,
                    o.total_amount, o.order_type, o.order_status, o.is_active,
                    o.created_at, o.updated_at,
                    r.name as retailer_name, r.code as retailer_code,
                    r.mobile_number as retailer_mobile,
                    u.name as member_name
                FROM orders o
                INNER JOIN retailer r ON o.retailer_id = r.id
                INNER JOIN salesforce.users u ON u.id = o.member_id
                WHERE o.id = $1
                """,
                order_id,
            )

            if not order_row:
                raise OrderNotFoundException(order_id=order_id)

            # Get order items with product details
            item_rows = await connection.fetch(
                """
                SELECT 
                    oi.product_id, oi.quantity,
                    p.name as product_name, p.code as product_code
                FROM order_items oi
                INNER JOIN products p ON oi.product_id = p.id
                WHERE oi.order_id = $1
                """,
                order_id,
            )

            # Build response
            order_detail = OrderDetailResponse(
                id=order_row["id"],
                retailer_id=order_row["retailer_id"],
                retailer_name=order_row["retailer_name"],
                retailer_code=order_row["retailer_code"],
                retailer_mobile=order_row["retailer_mobile"],
                member_id=order_row["member_id"],
                member_name=order_row["member_name"],
                base_amount=order_row["base_amount"],
                discount_amount=order_row["discount_amount"],
                net_amount=order_row["net_amount"],
                igst_amount=order_row["igst_amount"],
                cgst_amount=order_row["cgst_amount"],
                sgst_amount=order_row["sgst_amount"],
                total_amount=order_row["total_amount"],
                order_type=OrderType(order_row["order_type"]),
                order_status=OrderStatus(order_row["order_status"]),
                is_active=order_row["is_active"],
                created_at=order_row["created_at"],
                updated_at=order_row["updated_at"],
                items=[
                    {
                        "product_id": item["product_id"],
                        "product_name": item["product_name"],
                        "product_code": item["product_code"],
                        "quantity": item["quantity"],
                    }
                    for item in item_rows
                ],
            )

            return order_detail

        except OrderNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to get order detail by id",
                order_id=str(order_id),
                error=str(e),
                company_id=str(self.company_id),
            )
            raise OrderOperationException(
                message=f"Failed to get order detail: {str(e)}",
                operation="get",
            ) from e

    async def get_order_detail_by_id(
        self, order_id: UUID, connection: Optional[asyncpg.Connection] = None
    ) -> OrderDetailResponse:
        """
        Get order details by ID with joined data.

        Args:
            order_id: ID of the order
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Order with detailed information

        Raises:
            OrderNotFoundException: If order not found
            OrderOperationException: If retrieval fails
        """
        if connection:
            return await self._get_order_detail_by_id(order_id, connection)

        async with self.db_pool.acquire() as conn:
            return await self._get_order_detail_by_id(order_id, conn)

    async def _list_orders(
        self,
        connection: asyncpg.Connection,
        retailer_id: Optional[UUID] = None,
        member_id: Optional[UUID] = None,
        order_status: Optional[OrderStatus] = None,
        order_type: Optional[OrderType] = None,
        is_active: Optional[bool] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[OrderListItem]:
        """
        Private method to list orders with a provided connection.
        Returns minimal data to optimize performance.

        Args:
            connection: Database connection
            retailer_id: Filter by retailer ID
            member_id: Filter by member ID
            order_status: Filter by order status
            order_type: Filter by order type
            is_active: Filter by active status
            limit: Maximum number of orders to return
            offset: Number of orders to skip

        Returns:
            List of orders with minimal data

        Raises:
            OrderOperationException: If listing fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Build dynamic query
            query = """
                SELECT 
                    o.id, o.retailer_id, o.member_id, o.total_amount,
                    o.order_type, o.order_status, o.is_active,
                    o.created_at, o.updated_at,
                    r.name as retailer_name,
                    u.name as member_name
                FROM orders o
                INNER JOIN retailer r ON o.retailer_id = r.id
                INNER JOIN members m ON o.member_id = m.id
                INNER JOIN salesforce.users u ON u.id = m.id
            """
            params = []
            param_count = 0
            conditions = []

            # Add WHERE conditions
            if retailer_id is not None:
                param_count += 1
                conditions.append(f"o.retailer_id = ${param_count}")
                params.append(retailer_id)

            if member_id is not None:
                param_count += 1
                conditions.append(f"o.member_id = ${param_count}")
                params.append(member_id)

            if order_status is not None:
                param_count += 1
                conditions.append(f"o.order_status = ${param_count}")
                params.append(order_status.value)

            if order_type is not None:
                param_count += 1
                conditions.append(f"o.order_type = ${param_count}")
                params.append(order_type.value)

            if is_active is not None:
                param_count += 1
                conditions.append(f"o.is_active = ${param_count}")
                params.append(is_active)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            # Add ordering
            query += " ORDER BY o.created_at DESC"

            # Add limit and offset
            if limit is not None:
                param_count += 1
                query += f" LIMIT ${param_count}"
                params.append(limit)

            if offset is not None:
                param_count += 1
                query += f" OFFSET ${param_count}"
                params.append(offset)

            rows = await connection.fetch(query, *params)

            return [OrderListItem(**dict(row)) for row in rows]

        except Exception as e:
            logger.error(
                "Failed to list orders",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise OrderOperationException(
                message=f"Failed to list orders: {str(e)}",
                operation="list",
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
        connection: Optional[asyncpg.Connection] = None,
    ) -> list[OrderListItem]:
        """
        List all orders with optional filtering.
        Returns minimal data to optimize performance.

        Args:
            retailer_id: Filter by retailer ID
            member_id: Filter by member ID
            order_status: Filter by order status
            order_type: Filter by order type
            is_active: Filter by active status
            limit: Maximum number of orders to return
            offset: Number of orders to skip
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            List of orders with minimal data

        Raises:
            OrderOperationException: If listing fails
        """
        if connection:
            return await self._list_orders(
                connection,
                retailer_id,
                member_id,
                order_status,
                order_type,
                is_active,
                limit,
                offset,
            )

        async with self.db_pool.acquire() as conn:
            return await self._list_orders(
                conn, retailer_id, member_id, order_status, order_type, is_active, limit, offset
            )

    async def _count_orders(
        self,
        connection: asyncpg.Connection,
        retailer_id: Optional[UUID] = None,
        member_id: Optional[UUID] = None,
        order_status: Optional[OrderStatus] = None,
        order_type: Optional[OrderType] = None,
        is_active: Optional[bool] = None,
    ) -> int:
        """
        Private method to count orders with a provided connection.

        Args:
            connection: Database connection
            retailer_id: Filter by retailer ID
            member_id: Filter by member ID
            order_status: Filter by order status
            order_type: Filter by order type
            is_active: Filter by active status

        Returns:
            Count of orders

        Raises:
            OrderOperationException: If counting fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Build dynamic query
            query = "SELECT COUNT(*) FROM orders o"
            params = []
            param_count = 0
            conditions = []

            # Add WHERE conditions
            if retailer_id is not None:
                param_count += 1
                conditions.append(f"o.retailer_id = ${param_count}")
                params.append(retailer_id)

            if member_id is not None:
                param_count += 1
                conditions.append(f"o.member_id = ${param_count}")
                params.append(member_id)

            if order_status is not None:
                param_count += 1
                conditions.append(f"o.order_status = ${param_count}")
                params.append(order_status.value)

            if order_type is not None:
                param_count += 1
                conditions.append(f"o.order_type = ${param_count}")
                params.append(order_type.value)

            if is_active is not None:
                param_count += 1
                conditions.append(f"o.is_active = ${param_count}")
                params.append(is_active)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            count = await connection.fetchval(query, *params)
            return count

        except Exception as e:
            logger.error(
                "Failed to count orders",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise OrderOperationException(
                message=f"Failed to count orders: {str(e)}",
                operation="count",
            ) from e

    async def count_orders(
        self,
        retailer_id: Optional[UUID] = None,
        member_id: Optional[UUID] = None,
        order_status: Optional[OrderStatus] = None,
        order_type: Optional[OrderType] = None,
        is_active: Optional[bool] = None,
        connection: Optional[asyncpg.Connection] = None,
    ) -> int:
        """
        Count orders with optional filtering.

        Args:
            retailer_id: Filter by retailer ID
            member_id: Filter by member ID
            order_status: Filter by order status
            order_type: Filter by order type
            is_active: Filter by active status
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Count of orders

        Raises:
            OrderOperationException: If counting fails
        """
        if connection:
            return await self._count_orders(
                connection, retailer_id, member_id, order_status, order_type, is_active
            )

        async with self.db_pool.acquire() as conn:
            return await self._count_orders(
                conn, retailer_id, member_id, order_status, order_type, is_active
            )

    async def _update_order(
        self,
        order_id: UUID,
        order_data: OrderUpdate,
        connection: asyncpg.Connection,
    ) -> OrderInDB:
        """
        Private method to update an order with a provided connection.

        Args:
            order_id: ID of the order to update
            order_data: Order data to update
            connection: Database connection

        Returns:
            Updated order

        Raises:
            OrderNotFoundException: If order not found
            OrderOperationException: If update fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Build dynamic update query
            update_fields = []
            params = []
            param_count = 1

            if order_data.base_amount is not None:
                update_fields.append(f"base_amount = ${param_count}")
                params.append(order_data.base_amount)
                param_count += 1

            if order_data.discount_amount is not None:
                update_fields.append(f"discount_amount = ${param_count}")
                params.append(order_data.discount_amount)
                param_count += 1

            if order_data.net_amount is not None:
                update_fields.append(f"net_amount = ${param_count}")
                params.append(order_data.net_amount)
                param_count += 1

            if order_data.igst_amount is not None:
                update_fields.append(f"igst_amount = ${param_count}")
                params.append(order_data.igst_amount)
                param_count += 1

            if order_data.cgst_amount is not None:
                update_fields.append(f"cgst_amount = ${param_count}")
                params.append(order_data.cgst_amount)
                param_count += 1

            if order_data.sgst_amount is not None:
                update_fields.append(f"sgst_amount = ${param_count}")
                params.append(order_data.sgst_amount)
                param_count += 1

            if order_data.total_amount is not None:
                update_fields.append(f"total_amount = ${param_count}")
                params.append(order_data.total_amount)
                param_count += 1

            if order_data.order_type is not None:
                update_fields.append(f"order_type = ${param_count}")
                params.append(order_data.order_type.value)
                param_count += 1

            if order_data.order_status is not None:
                update_fields.append(f"order_status = ${param_count}")
                params.append(order_data.order_status.value)
                param_count += 1

            query = f"""
                UPDATE orders
                SET {', '.join(update_fields)}
                WHERE id = ${param_count}
                RETURNING id, retailer_id, member_id, base_amount, discount_amount,
                          net_amount, igst_amount, cgst_amount, sgst_amount,
                          total_amount, order_type, order_status, is_active,
                          created_at, updated_at
            """
            print("Update Query:", query, params + [order_id])  # Debug print
            row = await connection.fetchrow(query, *params, order_id)

            if not row:
                raise OrderNotFoundException(order_id=order_id)

            logger.info(
                "Order updated successfully",
                order_id=order_id,
                company_id=str(self.company_id),
            )

            return OrderInDB(**dict(row))

        except OrderNotFoundException:
            raise
        except asyncpg.ForeignKeyViolationError as e:
            error_msg = str(e)
            if "fk_order_items_product" in error_msg:
                raise OrderOperationException(
                    message="One or more products not found",
                    operation="update",
                ) from e
            else:
                raise OrderOperationException(
                    message=f"Failed to update order: {error_msg}",
                    operation="update",
                ) from e
        except Exception as e:
            logger.error(
                "Failed to update order",
                order_id=str(order_id),
                error=str(e),
                company_id=str(self.company_id),
            )
            raise OrderOperationException(
                message=f"Failed to update order: {str(e)}",
                operation="update",
            ) from e

    async def update_order(
        self,
        order_id: UUID,
        order_data: OrderUpdate,
        connection: Optional[asyncpg.Connection] = None,
    ) -> OrderInDB:
        """
        Update an existing order.

        Args:
            order_id: ID of the order to update
            order_data: Order data to update
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Updated order

        Raises:
            OrderNotFoundException: If order not found
            OrderOperationException: If update fails
        """
        if connection:
            return await self._update_order(order_id, order_data, connection)

        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                return await self._update_order(order_id, order_data, conn)

    async def _delete_order(
        self, order_id: UUID, connection: asyncpg.Connection
    ) -> bool:
        """
        Private method to soft delete an order with a provided connection.

        Args:
            order_id: ID of the order to delete
            connection: Database connection

        Returns:
            True if order was deleted

        Raises:
            OrderNotFoundException: If order not found
            OrderOperationException: If deletion fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            result = await connection.execute(
                """
                UPDATE orders
                SET is_active = false
                WHERE id = $1 AND is_active = true
                """,
                order_id,
            )

            if result == "UPDATE 0":
                raise OrderNotFoundException(order_id=order_id)

            logger.info(
                "Order deleted successfully",
                order_id=order_id,
                company_id=str(self.company_id),
            )

            return True

        except OrderNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to delete order",
                order_id=str(order_id),
                error=str(e),
                company_id=str(self.company_id),
            )
            raise OrderOperationException(
                message=f"Failed to delete order: {str(e)}",
                operation="delete",
            ) from e

    async def delete_order(
        self, order_id: UUID, connection: Optional[asyncpg.Connection] = None
    ) -> bool:
        """
        Soft delete an order (set is_active to false).

        Args:
            order_id: ID of the order to delete
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            True if order was deleted

        Raises:
            OrderNotFoundException: If order not found
            OrderOperationException: If deletion fails
        """
        if connection:
            return await self._delete_order(order_id, connection)

        async with self.db_pool.acquire() as conn:
            return await self._delete_order(order_id, conn)

    async def _get_order_items(
        self, order_id: UUID, connection: asyncpg.Connection
    ) -> list[OrderItemInDB]:
        """
        Private method to get order items for an order with a provided connection.

        Args:
            order_id: ID of the order
            connection: Database connection

        Returns:
            List of order items

        Raises:
            OrderOperationException: If retrieval fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            rows = await connection.fetch(
                """
                SELECT order_id, product_id, quantity
                FROM order_items
                WHERE order_id = $1
                """,
                order_id,
            )

            return [OrderItemInDB(**dict(row)) for row in rows]

        except Exception as e:
            logger.error(
                "Failed to get order items",
                order_id=str(order_id),
                error=str(e),
                company_id=str(self.company_id),
            )
            raise OrderOperationException(
                message=f"Failed to get order items: {str(e)}",
                operation="get",
            ) from e

    async def get_order_items(
        self, order_id: UUID, connection: Optional[asyncpg.Connection] = None
    ) -> list[OrderItemInDB]:
        """
        Get order items for an order.

        Args:
            order_id: ID of the order
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            List of order items

        Raises:
            OrderOperationException: If retrieval fails
        """
        if connection:
            return await self._get_order_items(order_id, connection)

        async with self.db_pool.acquire() as conn:
            return await self._get_order_items(order_id, conn)

    async def _update_order_items(
        self,
        order_id: UUID,
        items: list[OrderItemCreate],
        connection: Optional[asyncpg.Connection] = None,
    ) -> bool:
        """
        Update order items for an order.

        Args:
            order_id: ID of the order
            items: List of order items to update
            connection: Optional database connection. If not provided, a new one is acquired.
            """
        await set_search_path(connection, self.schema_name)
        try:
            # Upsert order items (update if exists, insert if not)
            for item in items:
                await connection.execute(
                    """
                    INSERT INTO order_items (order_id, product_id, quantity)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (order_id, product_id)
                    DO UPDATE SET quantity = EXCLUDED.quantity
                    """,
                    order_id,
                    item.product_id,
                    item.quantity,
                )

            logger.info(
                "Order items updated successfully",
                order_id=order_id,
                company_id=str(self.company_id),
            )

            return True

        except Exception as e:
            logger.error(
                "Failed to update order items",
                order_id=str(order_id),
                error=str(e),
                company_id=str(self.company_id),
            )
            raise OrderOperationException(
                message=f"Failed to update order items: {str(e)}",
                operation="update_items",
            ) from e
    async def update_order_items(
        self,
        order_id: UUID,
        items: list[OrderItemCreate],
        connection: Optional[asyncpg.Connection] = None,
    ) -> bool:
        """
        Update order items for an order.

        Args:
            order_id: ID of the order
            items: List of order items to update
            connection: Optional database connection. If not provided, a new one is acquired.
            """
        if connection:
            return await self._update_order_items(order_id, items, connection)

        async with self.db_pool.acquire() as conn:
            return await self._update_order_items(order_id, items, conn)