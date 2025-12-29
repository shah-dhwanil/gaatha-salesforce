"""
Pydantic models for Role entity.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class RoleCreate(BaseModel):
    """Model for creating a new role."""

    name: str = Field(..., min_length=1, max_length=32, description="Role name")
    description: Optional[str] = Field(None, description="Role description")
    permissions: list[str] = Field(
        default_factory=list, description="List of permissions"
    )
    is_active: bool = Field(default=True, description="Whether the role is active")

    @field_validator("permissions", mode="before")
    @classmethod
    def validate_permissions(cls, v):
        """Validate permissions field."""
        if v is None:
            return []
        if isinstance(v, list):
            # Ensure all permissions are valid strings and at most 64 chars
            for perm in v:
                if not isinstance(perm, str):
                    raise ValueError("All permissions must be strings")
                if len(perm) > 64:
                    raise ValueError("Permission length cannot exceed 64 characters")
            return v
        raise ValueError("Permissions must be a list")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate and normalize role name."""
        if not v or not v.strip():
            raise ValueError("Role name cannot be empty")
        return v.strip()


class RoleUpdate(BaseModel):
    """Model for updating an existing role."""

    description: Optional[str] = None
    permissions: Optional[list[str]] = None

    @field_validator("permissions", mode="before")
    @classmethod
    def validate_permissions(cls, v):
        """Validate permissions field."""
        if v is None:
            return None
        if isinstance(v, list):
            # Ensure all permissions are valid strings and at most 64 chars
            for perm in v:
                if not isinstance(perm, str):
                    raise ValueError("All permissions must be strings")
                if len(perm) > 64:
                    raise ValueError("Permission length cannot exceed 64 characters")
            return v
        raise ValueError("Permissions must be a list")


class RoleInDB(BaseModel):
    """Model for Role as stored in database."""

    name: str = Field(..., description="Role name")
    description: Optional[str] = Field(None, description="Role description")
    permissions: list[str] = Field(
        default_factory=list, description="List of permissions"
    )
    is_active: bool = Field(..., description="Whether the role is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class RoleResponse(BaseModel):
    """Model for Role API response."""

    name: str = Field(..., description="Role name")
    description: Optional[str] = Field(None, description="Role description")
    permissions: list[str] = Field(
        default_factory=list, description="List of permissions"
    )
    is_active: bool = Field(..., description="Whether the role is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class RoleListItem(BaseModel):
    """Minimal model for Role in list views to optimize performance."""

    name: str = Field(..., description="Role name")
    description: Optional[str] = Field(None, description="Role description")
    is_active: bool = Field(..., description="Whether the role is active")

    class Config:
        from_attributes = True
