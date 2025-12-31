"""
Custom exceptions for Retailer operations.
"""

from typing import Any, Optional
from uuid import UUID

from api.exceptions.app import AppException, ErrorTypes


class RetailerNotFoundException(AppException):
    """Exception raised when a retailer is not found."""

    def __init__(
        self,
        retailer_id: Optional[UUID] = None,
        retailer_code: Optional[str] = None,
        message: Optional[str] = None,
        **kwargs,
    ) -> None:
        if message is None:
            if retailer_id is not None:
                message = f"Retailer with ID '{retailer_id}' not found"
            elif retailer_code is not None:
                message = f"Retailer with code '{retailer_code}' not found"
            else:
                message = "Retailer not found"
        super().__init__(
            type=ErrorTypes.ResourceNotFound,
            message=message,
            resource="retailer",
            field="id" if retailer_id else "code",
            value=str(retailer_id) if retailer_id else retailer_code,
            **kwargs,
        )


class RetailerAlreadyExistsException(AppException):
    """Exception raised when trying to create a retailer that already exists."""

    def __init__(
        self,
        retailer_code: Optional[str] = None,
        field: Optional[str] = None,
        value: Optional[str] = None,
        message: Optional[str] = None,
        **kwargs,
    ) -> None:
        if message is None:
            if retailer_code:
                message = f"Retailer with code '{retailer_code}' already exists"
            elif field and value:
                message = f"Retailer with {field} '{value}' already exists"
            else:
                message = "Retailer already exists"
        super().__init__(
            type=ErrorTypes.ResourceAlreadyExists,
            message=message,
            resource="retailer",
            field=field or "code",
            value=value or retailer_code,
            **kwargs,
        )


class RetailerValidationException(AppException):
    """Exception raised when retailer validation fails."""

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
            resource="retailer",
            field=field,
            value=value,
            **kwargs,
        )


class RetailerOperationException(AppException):
    """Exception raised when a retailer operation fails."""

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        **kwargs,
    ) -> None:
        super().__init__(
            type=ErrorTypes.InvalidOperation,
            message=message,
            resource="retailer",
            **kwargs,
        )
        self.operation = operation

