"""
Custom exceptions for Order operations.
"""

from typing import Any, Optional
from uuid import UUID

from api.exceptions.app import AppException, ErrorTypes


class OrderNotFoundException(AppException):
    """Exception raised when an order is not found."""

    def __init__(
        self,
        order_id: Optional[UUID] = None,
        message: Optional[str] = None,
        **kwargs,
    ) -> None:
        if message is None:
            if order_id is not None:
                message = f"Order with ID '{order_id}' not found"
            else:
                message = "Order not found"
        super().__init__(
            type=ErrorTypes.ResourceNotFound,
            message=message,
            resource="order",
            field="id",
            value=str(order_id) if order_id else None,
            **kwargs,
        )


class OrderItemNotFoundException(AppException):
    """Exception raised when an order item is not found."""

    def __init__(
        self,
        order_id: Optional[UUID] = None,
        product_id: Optional[UUID] = None,
        message: Optional[str] = None,
        **kwargs,
    ) -> None:
        if message is None:
            if order_id and product_id:
                message = f"Order item with order ID '{order_id}' and product ID '{product_id}' not found"
            else:
                message = "Order item not found"
        super().__init__(
            type=ErrorTypes.ResourceNotFound,
            message=message,
            resource="order_item",
            field="order_id, product_id",
            value=f"{order_id}, {product_id}" if order_id and product_id else None,
            **kwargs,
        )


class OrderAlreadyExistsException(AppException):
    """Exception raised when trying to create an order that already exists."""

    def __init__(
        self,
        order_id: Optional[UUID] = None,
        message: Optional[str] = None,
        **kwargs,
    ) -> None:
        if message is None:
            if order_id:
                message = f"Order with ID '{order_id}' already exists"
            else:
                message = "Order already exists"
        super().__init__(
            type=ErrorTypes.ResourceAlreadyExists,
            message=message,
            resource="order",
            field="id",
            value=str(order_id) if order_id else None,
            **kwargs,
        )


class OrderItemAlreadyExistsException(AppException):
    """Exception raised when trying to add an order item that already exists."""

    def __init__(
        self,
        order_id: Optional[UUID] = None,
        product_id: Optional[UUID] = None,
        message: Optional[str] = None,
        **kwargs,
    ) -> None:
        if message is None:
            if order_id and product_id:
                message = f"Order item with order ID '{order_id}' and product ID '{product_id}' already exists"
            else:
                message = "Order item already exists"
        super().__init__(
            type=ErrorTypes.ResourceAlreadyExists,
            message=message,
            resource="order_item",
            field="order_id, product_id",
            value=f"{order_id}, {product_id}" if order_id and product_id else None,
            **kwargs,
        )


class OrderValidationException(AppException):
    """Exception raised when order validation fails."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        **kwargs,
    ) -> None:
        super().__init__(
            type=ErrorTypes.InputValidationError,
            message=message,
            resource="order",
            field=field,
            value=value,
            **kwargs,
        )


class OrderOperationException(AppException):
    """Exception raised when an order operation fails."""

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        **kwargs,
    ) -> None:
        super().__init__(
            type=ErrorTypes.InvalidOperation,
            message=message,
            resource="order",
            **kwargs,
        )


class OrderStatusException(AppException):
    """Exception raised when an invalid order status transition is attempted."""

    def __init__(
        self,
        current_status: str,
        new_status: str,
        message: Optional[str] = None,
        **kwargs,
    ) -> None:
        if message is None:
            message = f"Invalid status transition from '{current_status}' to '{new_status}'"
        super().__init__(
            type=ErrorTypes.InvalidOperation,
            message=message,
            resource="order",
            field="order_status",
            value=f"{current_status} -> {new_status}",
            **kwargs,
        )
