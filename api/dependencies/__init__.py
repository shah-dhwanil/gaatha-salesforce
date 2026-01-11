"""
Dependencies module for FastAPI dependency injection.

This module contains reusable dependencies for database access,
authentication, and service initialization.
"""

from api.dependencies.common import (
    CompanyIDDep,
    DatabasePoolDep,
)

__all__ = [
    "DatabasePoolDep",
    "CompanyIDDep",
]
