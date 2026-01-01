"""
Custom exceptions for Brand operations.
"""

from typing import Any, Optional

from api.exceptions.app import AppException, ErrorTypes


class BrandNotFoundException(AppException):
    """Exception raised when a brand is not found."""

    def __init__(
        self,
        brand_id: Optional[int] = None,
        brand_code: Optional[str] = None,
        brand_name: Optional[str] = None,
        message: Optional[str] = None,
        **kwargs,
    ) -> None:
        if message is None:
            if brand_id:
                message = f"Brand with ID '{brand_id}' not found"
            elif brand_code:
                message = f"Brand with code '{brand_code}' not found"
            elif brand_name:
                message = f"Brand with name '{brand_name}' not found"
            else:
                message = "Brand not found"

        value = brand_id or brand_code or brand_name
        field = (
            "id"
            if brand_id
            else "code"
            if brand_code
            else "name"
            if brand_name
            else None
        )

        super().__init__(
            type=ErrorTypes.ResourceNotFound,
            message=message,
            resource="brand",
            field=field,
            value=str(value) if value else None,
            **kwargs,
        )


class BrandAlreadyExistsException(AppException):
    """Exception raised when trying to create a brand that already exists."""

    def __init__(
        self,
        brand_code: Optional[str] = None,
        brand_name: Optional[str] = None,
        message: Optional[str] = None,
        **kwargs,
    ) -> None:
        if message is None:
            if brand_code and brand_name:
                message = (
                    f"Brand with code '{brand_code}' or name '{brand_name}' already exists"
                )
            elif brand_code:
                message = f"Brand with code '{brand_code}' already exists"
            elif brand_name:
                message = f"Brand with name '{brand_name}' already exists"
            else:
                message = "Brand already exists"

        super().__init__(
            type=ErrorTypes.ResourceAlreadyExists,
            message=message,
            resource="brand",
            field="code" if brand_code else "name",
            value=brand_code or brand_name,
            **kwargs,
        )


class BrandValidationException(AppException):
    """Exception raised when brand validation fails."""

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
            resource="brand",
            field=field,
            value=value,
            **kwargs,
        )


class BrandOperationException(AppException):
    """Exception raised when a brand operation fails."""

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        **kwargs,
    ) -> None:
        super().__init__(
            type=ErrorTypes.InvalidOperation,
            message=message,
            resource="brand",
            **kwargs,
        )
        self.operation = operation
