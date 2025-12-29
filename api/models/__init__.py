"""
Models module for Pydantic data models.

This module contains all Pydantic models used for request/response validation,
data serialization, and type safety throughout the application.
"""

from api.models.area import (
    AreaCreate,
    AreaHierarchyResponse,
    AreaInDB,
    AreaListItem,
    AreaResponse,
    AreaUpdate,
)
from api.models.base import ListResponseModel, ResponseModel
from api.models.errors import HTTPDetail, HTTPException
from api.models.role import (
    RoleCreate,
    RoleInDB,
    RoleListItem,
    RoleResponse,
    RoleUpdate,
)
from api.models.route import (
    RouteCreate,
    RouteInDB,
    RouteListItem,
    RouteResponse,
    RouteUpdate,
)
from api.models.route_assignment import (
    RouteAssignmentCreate,
    RouteAssignmentDetailItem,
    RouteAssignmentInDB,
    RouteAssignmentListItem,
    RouteAssignmentResponse,
    RouteAssignmentUpdate,
)
from api.models.route_log import (
    RouteLogCreate,
    RouteLogInDB,
    RouteLogListItem,
    RouteLogResponse,
    RouteLogUpdate,
)
from api.models.shop_category import (
    ShopCategoryCreate,
    ShopCategoryInDB,
    ShopCategoryListItem,
    ShopCategoryResponse,
    ShopCategoryUpdate,
)

__all__ = [
    # Base models
    "ResponseModel",
    "ListResponseModel",
    # Error models
    "HTTPDetail",
    "HTTPException",
    # Area models
    "AreaCreate",
    "AreaUpdate",
    "AreaInDB",
    "AreaResponse",
    "AreaListItem",
    "AreaHierarchyResponse",
    # Role models
    "RoleCreate",
    "RoleUpdate",
    "RoleInDB",
    "RoleResponse",
    "RoleListItem",
    # Route models
    "RouteCreate",
    "RouteUpdate",
    "RouteInDB",
    "RouteResponse",
    "RouteListItem",
    # Route assignment models
    "RouteAssignmentCreate",
    "RouteAssignmentUpdate",
    "RouteAssignmentInDB",
    "RouteAssignmentResponse",
    "RouteAssignmentListItem",
    "RouteAssignmentDetailItem",
    # Route log models
    "RouteLogCreate",
    "RouteLogUpdate",
    "RouteLogInDB",
    "RouteLogResponse",
    "RouteLogListItem",
    # Shop category models
    "ShopCategoryCreate",
    "ShopCategoryUpdate",
    "ShopCategoryInDB",
    "ShopCategoryResponse",
    "ShopCategoryListItem",
]
