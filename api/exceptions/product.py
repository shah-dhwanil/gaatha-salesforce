"""
Custom exceptions for Product operations.
"""

from typing import Any, Optional

from api.exceptions.app import AppException, ErrorTypes


class ProductNotFoundException(AppException):
    """Exception raised when a product is not found."""

    def __init__(
        self,
        product_id: Optional[int] = None,
        product_code: Optional[str] = None,
        product_name: Optional[str] = None,
        message: Optional[str] = None,
        **kwargs,
    ) -> None:
        if message is None:
            if product_id:
                message = f"Product with ID '{product_id}' not found"
            elif product_code:
                message = f"Product with code '{product_code}' not found"
            elif product_name:
                message = f"Product with name '{product_name}' not found"
            else:
                message = "Product not found"

        value = product_id or product_code or product_name
        field = (
            "id"
            if product_id
            else "code"
            if product_code
            else "name"
            if product_name
            else None
        )

        super().__init__(
            type=ErrorTypes.ResourceNotFound,
            message=message,
            resource="product",
            field=field,
            value=str(value) if value else None,
            **kwargs,
        )


class ProductAlreadyExistsException(AppException):
    """Exception raised when trying to create a product that already exists."""

    def __init__(
        self,
        product_code: Optional[str] = None,
        product_name: Optional[str] = None,
        message: Optional[str] = None,
        **kwargs,
    ) -> None:
        if message is None:
            if product_code and product_name:
                message = (
                    f"Product with code '{product_code}' or name '{product_name}' already exists"
                )
            elif product_code:
                message = f"Product with code '{product_code}' already exists"
            elif product_name:
                message = f"Product with name '{product_name}' already exists"
            else:
                message = "Product already exists"

        super().__init__(
            type=ErrorTypes.ResourceAlreadyExists,
            message=message,
            resource="product",
            field="code" if product_code else "name",
            value=product_code or product_name,
            **kwargs,
        )


class ProductValidationException(AppException):
    """Exception raised when product validation fails."""

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
            resource="product",
            field=field,
            value=value,
            **kwargs,
        )


class ProductOperationException(AppException):
    """Exception raised when a product operation fails."""

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        **kwargs,
    ) -> None:
        super().__init__(
            type=ErrorTypes.InvalidOperation,
            message=message,
            resource="product",
            **kwargs,
        )
        self.operation = operation
