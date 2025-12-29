"""
Custom exceptions for Route operations.
"""

from typing import Any, Optional

from api.exceptions.app import AppException, ErrorTypes


class RouteNotFoundException(AppException):
    """Exception raised when a route is not found."""

    def __init__(
        self,
        route_id: Optional[int] = None,
        route_code: Optional[str] = None,
        message: Optional[str] = None,
        **kwargs,
    ) -> None:
        if message is None:
            if route_id is not None:
                message = f"Route with id '{route_id}' not found"
            elif route_code is not None:
                message = f"Route with code '{route_code}' not found"
            else:
                message = "Route not found"
        
        field = "id" if route_id is not None else "code" if route_code is not None else None
        value = route_id if route_id is not None else route_code if route_code is not None else None
        
        super().__init__(
            type=ErrorTypes.ResourceNotFound,
            message=message,
            resource="route",
            field=field,
            value=value,
            **kwargs,
        )


class RouteAlreadyExistsException(AppException):
    """Exception raised when trying to create a route that already exists."""

    def __init__(
        self,
        route_code: str,
        message: Optional[str] = None,
        **kwargs,
    ) -> None:
        if message is None:
            message = f"Route with code '{route_code}' already exists"
        super().__init__(
            type=ErrorTypes.ResourceAlreadyExists,
            message=message,
            resource="route",
            field="code",
            value=route_code,
            **kwargs,
        )


class RouteValidationException(AppException):
    """Exception raised when route validation fails."""

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
            resource="route",
            field=field,
            value=value,
            **kwargs,
        )


class RouteOperationException(AppException):
    """Exception raised when a route operation fails."""

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        **kwargs,
    ) -> None:
        super().__init__(
            type=ErrorTypes.InvalidOperation,
            message=message,
            resource="route",
            **kwargs,
        )
        self.operation = operation

