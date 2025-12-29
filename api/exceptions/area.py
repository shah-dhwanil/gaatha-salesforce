"""
Custom exceptions for Area operations.
"""

from typing import Optional


class AreaException(Exception):
    """Base exception for area operations."""

    def __init__(self, message: str = "Area operation failed"):
        self.message = message
        super().__init__(self.message)


class AreaNotFoundException(AreaException):
    """Exception raised when an area is not found."""

    def __init__(
        self,
        area_id: Optional[int] = None,
        area_name: Optional[str] = None,
        area_type: Optional[str] = None,
        message: Optional[str] = None,
    ):
        self.area_id = area_id
        self.area_name = area_name
        self.area_type = area_type

        if message:
            self.message = message
        elif area_id:
            self.message = f"Area with ID {area_id} not found"
        elif area_name and area_type:
            self.message = f"Area '{area_name}' of type '{area_type}' not found"
        else:
            self.message = "Area not found"

        super().__init__(self.message)


class AreaAlreadyExistsException(AreaException):
    """Exception raised when trying to create an area that already exists."""

    def __init__(
        self,
        area_name: Optional[str] = None,
        area_type: Optional[str] = None,
        message: Optional[str] = None,
    ):
        self.area_name = area_name
        self.area_type = area_type

        if message:
            self.message = message
        elif area_name and area_type:
            self.message = f"Area '{area_name}' of type '{area_type}' already exists"
        else:
            self.message = "Area already exists"

        super().__init__(self.message)


class AreaOperationException(AreaException):
    """Exception raised when an area operation fails."""

    def __init__(self, message: str = "Area operation failed", operation: str = "unknown"):
        self.operation = operation
        self.message = f"{message} (operation: {operation})"
        super().__init__(self.message)


class AreaInvalidHierarchyException(AreaException):
    """Exception raised when area hierarchy validation fails."""

    def __init__(self, message: str = "Invalid area hierarchy"):
        self.message = message
        super().__init__(self.message)

