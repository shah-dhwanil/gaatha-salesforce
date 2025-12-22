"""
Role models for database and API operations.

This module contains Pydantic models for role data validation,
including database representations, API requests, and responses.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


class RoleInDB(BaseModel):
    """Role model representing database record."""

    name: str
    description: Optional[str]
    permissions: list[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime


# Request Models


class CreateRoleRequest(BaseModel):
    """Request model for creating a new role."""

    company_id: UUID = Field(..., description="UUID of the company")
    name: str = Field(..., min_length=1, max_length=100, description="Name of the role")
    description: Optional[str] = Field(
        None, max_length=500, description="Description of the role"
    )
    permissions: Optional[list[str]] = Field(
        default=None, description="List of permissions"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate and clean role name."""
        if not v or not v.strip():
            raise ValueError("Role name cannot be empty or whitespace")
        return v.strip()

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        """Validate and clean description."""
        if v is not None:
            if v.strip() == "":
                raise ValueError("Description cannot be empty string")
            return v.strip()
        return v

    @field_validator("permissions")
    @classmethod
    def validate_permissions(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        """Validate and clean permissions list."""
        if v is not None:
            if not isinstance(v, list):
                raise ValueError("Permissions must be a list")
            # Remove duplicates and empty strings
            cleaned = list(set([p.strip() for p in v if p and p.strip()]))
            if not cleaned and v:
                raise ValueError("Permissions list cannot contain only empty values")
            return cleaned if cleaned else None
        return v


class UpdateRoleRequest(BaseModel):
    """Request model for updating a role."""
    
    description: Optional[str] = Field(
        None, max_length=500, description="New description"
    )
    permissions: Optional[list[str]] = Field(None, description="New permissions list")

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        """Validate and clean description."""
        if v is not None:
            if v.strip() == "":
                raise ValueError("Description cannot be empty string")
            return v.strip()
        return v

    @field_validator("permissions")
    @classmethod
    def validate_permissions(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        """Validate and clean permissions list."""
        if v is not None:
            if not isinstance(v, list):
                raise ValueError("Permissions must be a list")
            # Remove duplicates and empty strings
            cleaned = list(set([p.strip() for p in v if p and p.strip()]))
            if not cleaned and v:
                raise ValueError("Permissions list cannot contain only empty values")
            return cleaned if cleaned else None
        return v

    def has_updates(self) -> bool:
        """Check if at least one field is provided for update."""
        return self.description is not None or self.permissions is not None


# Response Models


class RoleResponse(BaseModel):
    """Response model for a single role."""

    name: str = Field(..., description="Name of the role")
    description: Optional[str] = Field(None, description="Description of the role")
    permissions: list[str] = Field(..., description="List of permissions")
    is_active: bool = Field(..., description="Whether the role is active")
    created_at: datetime = Field(..., description="Timestamp when role was created")
    updated_at: datetime = Field(
        ..., description="Timestamp when role was last updated"
    )
