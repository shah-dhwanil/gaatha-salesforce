"""
Custom exceptions for RouteLog operations.
"""

from typing import Any, Optional

from api.exceptions.app import AppException, ErrorTypes


class RouteLogNotFoundException(AppException):
    """Exception raised when a route log is not found."""

    def __init__(
        self,
        route_log_id: Optional[int] = None,
        message: Optional[str] = None,
        **kwargs,
    ) -> None:
        if message is None:
            if route_log_id is not None:
                message = f"Route log with id '{route_log_id}' not found"
            else:
                message = "Route log not found"
        
        field = "id" if route_log_id is not None else None
        value = route_log_id if route_log_id is not None else None
        
        super().__init__(
            type=ErrorTypes.ResourceNotFound,
            message=message,
            resource="route_log",
            field=field,
            value=value,
            **kwargs,
        )


class RouteLogValidationException(AppException):
    """Exception raised when route log validation fails."""

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
            resource="route_log",
            field=field,
            value=value,
            **kwargs,
        )


class RouteLogOperationException(AppException):
    """Exception raised when a route log operation fails."""

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        **kwargs,
    ) -> None:
        super().__init__(
            type=ErrorTypes.InvalidOperation,
            message=message,
            resource="route_log",
            **kwargs,
        )
        self.operation = operation

