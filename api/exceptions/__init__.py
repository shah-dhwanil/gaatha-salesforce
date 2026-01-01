"""
Exceptions module for custom application exceptions.

This module contains all custom exception classes that extend from AppException
and are used throughout the application for error handling.
"""

from api.exceptions.app import AppException, ErrorTypes, UnkownAppException
from api.exceptions.area import (
    AreaAlreadyExistsException,
    AreaInvalidHierarchyException,
    AreaNotFoundException,
    AreaOperationException,
)
from api.exceptions.brand import (
    BrandAlreadyExistsException,
    BrandNotFoundException,
    BrandOperationException,
    BrandValidationException,
)
from api.exceptions.role import (
    RoleAlreadyExistsException,
    RoleNotFoundException,
    RoleOperationException,
    RoleValidationException,
)
from api.exceptions.route import (
    RouteAlreadyExistsException,
    RouteNotFoundException,
    RouteOperationException,
    RouteValidationException,
)
from api.exceptions.route_assignment import (
    InvalidDateRangeException,
    RouteAssignmentAlreadyExistsException,
    RouteAssignmentConflictException,
    RouteAssignmentException,
    RouteAssignmentNotFoundException,
    RouteAssignmentOperationException,
)
from api.exceptions.route_log import (
    RouteLogNotFoundException,
    RouteLogOperationException,
    RouteLogValidationException,
)
from api.exceptions.shop_category import (
    ShopCategoryAlreadyExistsException,
    ShopCategoryNotFoundException,
    ShopCategoryOperationException,
    ShopCategoryValidationException,
)
from api.exceptions.retailer import (
    RetailerAlreadyExistsException,
    RetailerNotFoundException,
    RetailerOperationException,
    RetailerValidationException,
)
from api.exceptions.user import (
    UserAlreadyExistsException,
    UserException,
    UserNotFoundException,
    UserOperationException,
    UserValidationException,
)

__all__ = [
    # Base exceptions
    "AppException",
    "ErrorTypes",
    "UnkownAppException",
    # Area exceptions
    "AreaNotFoundException",
    "AreaAlreadyExistsException",
    "AreaOperationException",
    "AreaInvalidHierarchyException",
    # Brand exceptions
    "BrandNotFoundException",
    "BrandAlreadyExistsException",
    "BrandValidationException",
    "BrandOperationException",
    # Role exceptions
    "RoleNotFoundException",
    "RoleAlreadyExistsException",
    "RoleValidationException",
    "RoleOperationException",
    # Route exceptions
    "RouteNotFoundException",
    "RouteAlreadyExistsException",
    "RouteValidationException",
    "RouteOperationException",
    # Route assignment exceptions
    "RouteAssignmentException",
    "RouteAssignmentNotFoundException",
    "RouteAssignmentAlreadyExistsException",
    "RouteAssignmentOperationException",
    "InvalidDateRangeException",
    "RouteAssignmentConflictException",
    # Route log exceptions
    "RouteLogNotFoundException",
    "RouteLogValidationException",
    "RouteLogOperationException",
    # Shop category exceptions
    "ShopCategoryNotFoundException",
    "ShopCategoryAlreadyExistsException",
    "ShopCategoryValidationException",
    "ShopCategoryOperationException",
    # Retailer exceptions
    "RetailerNotFoundException",
    "RetailerAlreadyExistsException",
    "RetailerValidationException",
    "RetailerOperationException",
    # User exceptions
    "UserNotFoundException",
    "UserAlreadyExistsException",
    "UserException",
    "UserValidationException",
    "UserOperationException",
]
