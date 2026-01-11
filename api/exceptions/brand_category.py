"""
Custom exceptions for Brand Category operations.
"""

from typing import Any, Optional

from api.exceptions.app import AppException, ErrorTypes


class BrandCategoryNotFoundException(AppException):
    """Exception raised when a brand category is not found."""

    def __init__(
        self,
        brand_category_id: Optional[int] = None,
        brand_category_code: Optional[str] = None,
        brand_category_name: Optional[str] = None,
        message: Optional[str] = None,
        **kwargs,
    ) -> None:
        if message is None:
            if brand_category_id:
                message = f"Brand category with ID '{brand_category_id}' not found"
            elif brand_category_code:
                message = f"Brand category with code '{brand_category_code}' not found"
            elif brand_category_name:
                message = f"Brand category with name '{brand_category_name}' not found"
            else:
                message = "Brand category not found"

        value = brand_category_id or brand_category_code or brand_category_name
        field = (
            "id"
            if brand_category_id
            else "code"
            if brand_category_code
            else "name"
            if brand_category_name
            else None
        )

        super().__init__(
            type=ErrorTypes.ResourceNotFound,
            message=message,
            resource="brand_category",
            field=field,
            value=str(value) if value else None,
            **kwargs,
        )


class BrandCategoryAlreadyExistsException(AppException):
    """Exception raised when trying to create a brand category that already exists."""

    def __init__(
        self,
        brand_category_code: Optional[str] = None,
        brand_category_name: Optional[str] = None,
        message: Optional[str] = None,
        **kwargs,
    ) -> None:
        if message is None:
            if brand_category_code and brand_category_name:
                message = f"Brand category with code '{brand_category_code}' or name '{brand_category_name}' already exists"
            elif brand_category_code:
                message = (
                    f"Brand category with code '{brand_category_code}' already exists"
                )
            elif brand_category_name:
                message = (
                    f"Brand category with name '{brand_category_name}' already exists"
                )
            else:
                message = "Brand category already exists"

        super().__init__(
            type=ErrorTypes.ResourceAlreadyExists,
            message=message,
            resource="brand_category",
            field="code" if brand_category_code else "name",
            value=brand_category_code or brand_category_name,
            **kwargs,
        )


class BrandCategoryValidationException(AppException):
    """Exception raised when brand category validation fails."""

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
            resource="brand_category",
            field=field,
            value=value,
            **kwargs,
        )


class BrandCategoryOperationException(AppException):
    """Exception raised when a brand category operation fails."""

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        **kwargs,
    ) -> None:
        super().__init__(
            type=ErrorTypes.InvalidOperation,
            message=message,
            resource="brand_category",
            **kwargs,
        )
        self.operation = operation
