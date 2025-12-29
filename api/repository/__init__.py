"""
Repository module for data access layer.

This module contains all repository classes that handle database operations
in a multi-tenant architecture using schema-per-tenant approach.
"""

from api.repository.area import AreaRepository
from api.repository.role import RoleRepository
from api.repository.route import RouteRepository
from api.repository.route_assignment import RouteAssignmentRepository
from api.repository.user import UserRepository

__all__ = [
    "AreaRepository",
    "RoleRepository",
    "RouteRepository",
    "RouteAssignmentRepository",
    "UserRepository",
]

