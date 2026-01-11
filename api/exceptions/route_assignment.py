"""
Custom exceptions for route assignment operations.
"""

from typing import Optional
from uuid import UUID


class RouteAssignmentException(Exception):
    """Base exception for route assignment operations."""

    def __init__(self, message: str = "Route assignment operation failed") -> None:
        self.message = message
        super().__init__(self.message)


class RouteAssignmentNotFoundException(RouteAssignmentException):
    """Exception raised when a route assignment is not found."""

    def __init__(
        self,
        assignment_id: Optional[int] = None,
        route_id: Optional[int] = None,
        user_id: Optional[UUID] = None,
    ) -> None:
        if assignment_id:
            message = f"Route assignment with id {assignment_id} not found"
        elif route_id and user_id:
            message = (
                f"Route assignment for route {route_id} and user {user_id} not found"
            )
        elif route_id:
            message = f"Route assignment for route {route_id} not found"
        elif user_id:
            message = f"Route assignment for user {user_id} not found"
        else:
            message = "Route assignment not found"
        super().__init__(message)


class RouteAssignmentAlreadyExistsException(RouteAssignmentException):
    """Exception raised when a route assignment already exists."""

    def __init__(
        self,
        route_id: Optional[int] = None,
        user_id: Optional[UUID] = None,
    ) -> None:
        if route_id and user_id:
            message = f"Active route assignment already exists for route {route_id} and user {user_id}"
        else:
            message = "Route assignment already exists"
        super().__init__(message)


class RouteAssignmentOperationException(RouteAssignmentException):
    """Exception raised when a route assignment operation fails."""

    def __init__(
        self,
        message: str = "Route assignment operation failed",
        operation: Optional[str] = None,
    ) -> None:
        if operation:
            message = f"Route assignment {operation} operation failed: {message}"
        super().__init__(message)


class InvalidDateRangeException(RouteAssignmentException):
    """Exception raised when date range is invalid."""

    def __init__(
        self, message: str = "Invalid date range for route assignment"
    ) -> None:
        super().__init__(message)


class RouteAssignmentConflictException(RouteAssignmentException):
    """Exception raised when a route assignment conflicts with an existing assignment."""

    def __init__(
        self,
        message: str = "Route assignment conflicts with existing assignment",
    ) -> None:
        super().__init__(message)
