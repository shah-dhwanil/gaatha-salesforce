"""
Custom exceptions for Role operations.
"""

from typing import Any, Optional

from api.exceptions.app import AppException, ErrorTypes


class RoleNotFoundException(AppException):
    """Exception raised when a role is not found."""

    def __init__(
        self,
        role_name: str,
        message: Optional[str] = None,
        **kwargs,
    ) -> None:
        if message is None:
            message = f"Role with name '{role_name}' not found"
        super().__init__(
            type=ErrorTypes.ResourceNotFound,
            message=message,
            resource="role",
            field="name",
            value=role_name,
            **kwargs,
        )


class RoleAlreadyExistsException(AppException):
    """Exception raised when trying to create a role that already exists."""

    def __init__(
        self,
        role_name: str,
        message: Optional[str] = None,
        **kwargs,
    ) -> None:
        if message is None:
            message = f"Role with name '{role_name}' already exists"
        super().__init__(
            type=ErrorTypes.ResourceAlreadyExists,
            message=message,
            resource="role",
            field="name",
            value=role_name,
            **kwargs,
        )


class RoleValidationException(AppException):
    """Exception raised when role validation fails."""

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
            resource="role",
            field=field,
            value=value,
            **kwargs,
        )


class RoleOperationException(AppException):
    """Exception raised when a role operation fails."""

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        **kwargs,
    ) -> None:
        super().__init__(
            type=ErrorTypes.InvalidOperation,
            message=message,
            resource="role",
            **kwargs,
        )
        self.operation = operation

