"""
Repository module for data access layer.

This module contains all repository classes that handle database operations
in a multi-tenant architecture using schema-per-tenant approach.
"""

from api.repository.area import AreaRepository
from api.repository.brand import BrandRepository
from api.repository.brand_category import BrandCategoryRepository
from api.repository.role import RoleRepository
from api.repository.route import RouteRepository
from api.repository.route_assignment import RouteAssignmentRepository
from api.repository.route_log import RouteLogRepository
from api.repository.shop_category import ShopCategoryRepository
from api.repository.user import UserRepository
from api.repository.retailer import RetailerRepository

__all__ = [
    "AreaRepository",
    "BrandRepository",
    "BrandCategoryRepository",
    "RoleRepository",
    "RouteRepository",
    "RouteAssignmentRepository",
    "RouteLogRepository",
    "ShopCategoryRepository",
    "UserRepository",
    "RetailerRepository",
]

