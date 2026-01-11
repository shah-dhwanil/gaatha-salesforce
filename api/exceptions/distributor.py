"""
Custom exceptions for Distributor operations.
"""

from typing import Any, Optional
from uuid import UUID

from api.exceptions.app import AppException, ErrorTypes


class DistributorNotFoundException(AppException):
    """Exception raised when a distributor is not found."""

    def __init__(
        self,
        distributor_id: Optional[UUID] = None,
        distributor_code: Optional[str] = None,
        message: Optional[str] = None,
        **kwargs,
    ) -> None:
        if message is None:
            if distributor_id is not None:
                message = f"Distributor with ID '{distributor_id}' not found"
            elif distributor_code is not None:
                message = f"Distributor with code '{distributor_code}' not found"
            else:
                message = "Distributor not found"
        super().__init__(
            type=ErrorTypes.ResourceNotFound,
            message=message,
            resource="distributor",
            field="id" if distributor_id else "code",
            value=str(distributor_id) if distributor_id else distributor_code,
            **kwargs,
        )


class DistributorAlreadyExistsException(AppException):
    """Exception raised when trying to create a distributor that already exists."""

    def __init__(
        self,
        distributor_code: Optional[str] = None,
        field: Optional[str] = None,
        value: Optional[str] = None,
        message: Optional[str] = None,
        **kwargs,
    ) -> None:
        if message is None:
            if distributor_code:
                message = f"Distributor with code '{distributor_code}' already exists"
            elif field and value:
                message = f"Distributor with {field} '{value}' already exists"
            else:
                message = "Distributor already exists"
        super().__init__(
            type=ErrorTypes.ResourceAlreadyExists,
            message=message,
            resource="distributor",
            field=field or "code",
            value=value or distributor_code,
            **kwargs,
        )


class DistributorValidationException(AppException):
    """Exception raised when distributor validation fails."""

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
            resource="distributor",
            field=field,
            value=value,
            **kwargs,
        )


class DistributorOperationException(AppException):
    """Exception raised when a distributor operation fails."""

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        **kwargs,
    ) -> None:
        super().__init__(
            type=ErrorTypes.InvalidOperation,
            message=message,
            resource="distributor",
            **kwargs,
        )
        self.operation = operation
