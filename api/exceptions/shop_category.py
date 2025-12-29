"""
Custom exceptions for ShopCategory operations.
"""

from typing import Any, Optional

from api.exceptions.app import AppException, ErrorTypes


class ShopCategoryNotFoundException(AppException):
    """Exception raised when a shop category is not found."""

    def __init__(
        self,
        shop_category_id: Optional[int] = None,
        shop_category_name: Optional[str] = None,
        message: Optional[str] = None,
        **kwargs,
    ) -> None:
        if message is None:
            if shop_category_id is not None:
                message = f"Shop category with ID '{shop_category_id}' not found"
            elif shop_category_name is not None:
                message = f"Shop category with name '{shop_category_name}' not found"
            else:
                message = "Shop category not found"
        super().__init__(
            type=ErrorTypes.ResourceNotFound,
            message=message,
            resource="shop_category",
            field="id" if shop_category_id else "name",
            value=shop_category_id if shop_category_id else shop_category_name,
            **kwargs,
        )


class ShopCategoryAlreadyExistsException(AppException):
    """Exception raised when trying to create a shop category that already exists."""

    def __init__(
        self,
        shop_category_name: str,
        message: Optional[str] = None,
        **kwargs,
    ) -> None:
        if message is None:
            message = f"Shop category with name '{shop_category_name}' already exists"
        super().__init__(
            type=ErrorTypes.ResourceAlreadyExists,
            message=message,
            resource="shop_category",
            field="name",
            value=shop_category_name,
            **kwargs,
        )


class ShopCategoryValidationException(AppException):
    """Exception raised when shop category validation fails."""

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
            resource="shop_category",
            field=field,
            value=value,
            **kwargs,
        )


class ShopCategoryOperationException(AppException):
    """Exception raised when a shop category operation fails."""

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        **kwargs,
    ) -> None:
        super().__init__(
            type=ErrorTypes.InvalidOperation,
            message=message,
            resource="shop_category",
            **kwargs,
        )
        self.operation = operation

