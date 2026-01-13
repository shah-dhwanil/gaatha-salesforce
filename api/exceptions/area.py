"""
Custom exceptions for Area operations.
"""

from api.exceptions.app import ErrorTypes
from api.exceptions.app import AppException
from typing import Optional


class AreaNotFoundException(AppException):
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

        super().__init__(ErrorTypes.ResourceNotFound,self.message, resource="area", field="id" if area_id else None, value=str(area_id) if area_id else None)


class AreaAlreadyExistsException(AppException):
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

        super().__init__(ErrorTypes.ResourceAlreadyExists,self.message, resource="area", field="name" if area_name else None, value=area_name if area_name else None)


class AreaOperationException(AppException):
    """Exception raised when an area operation fails."""

    def __init__(
        self, message: str = "Area operation failed", operation: str = "unknown"
    ):
        self.operation = operation
        self.message = f"{message} (operation: {operation})"
        super().__init__(ErrorTypes.InternalError, self.message, resource="area", field="operation", value=operation)


class AreaInvalidHierarchyException(AppException):
    """Exception raised when area hierarchy validation fails."""

    def __init__(self, message: str = "Invalid area hierarchy"):
        self.message = message
        super().__init__(ErrorTypes.InvalidOperation, self.message, resource="area", field="hierarchy")
