"""
User models for database and API operations.

This module contains Pydantic models for user data validation,
including database representations, API requests, and responses.
"""

from datetime import datetime
from uuid import UUID
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class UserInDB(BaseModel):
    """User model representing database record."""

    id: UUID
    username: str
    name: str
    contact_no: str
    company_id: UUID
    role: str
    area_id: Optional[int]
    is_active: bool
    created_at: datetime
    updated_at: datetime


# Request Models


class CreateUserRequest(BaseModel):
    """Request model for creating a new user."""

    username: str = Field(
        ..., min_length=1, max_length=100, description="Unique username for the user"
    )
    name: str = Field(
        ..., min_length=1, max_length=255, description="Full name of the user"
    )
    contact_no: str = Field(
        ..., min_length=1, max_length=20, description="Contact phone number"
    )
    company_id: UUID = Field(..., description="UUID of the company the user belongs to")
    role: str = Field(..., min_length=1, max_length=100, description="Role of the user")
    area_id: Optional[int] = Field(None, description="Optional area assignment")

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate and clean username."""
        if not v or not v.strip():
            raise ValueError("Username cannot be empty or whitespace")
        return v.strip()

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate and clean name."""
        if not v or not v.strip():
            raise ValueError("Name cannot be empty or whitespace")
        return v.strip()

    @field_validator("contact_no")
    @classmethod
    def validate_contact_no(cls, v: str) -> str:
        """Validate and clean contact number."""
        if not v or not v.strip():
            raise ValueError("Contact number cannot be empty or whitespace")
        return v.strip()

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Validate and clean role."""
        if not v or not v.strip():
            raise ValueError("Role cannot be empty or whitespace")
        return v.strip()


class UpdateUserRequest(BaseModel):
    """Request model for updating a user."""

    name: Optional[str] = Field(
        None, min_length=1, max_length=255, description="Full name of the user"
    )
    contact_no: Optional[str] = Field(
        None, min_length=1, max_length=20, description="Contact phone number"
    )
    role: Optional[str] = Field(
        None, min_length=1, max_length=100, description="Role of the user"
    )
    area_id: Optional[int] = Field(None, description="Area assignment")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate and clean name."""
        if v is not None and not v.strip():
            raise ValueError("Name cannot be empty or whitespace")
        return v.strip() if v is not None else None

    @field_validator("contact_no")
    @classmethod
    def validate_contact_no(cls, v: Optional[str]) -> Optional[str]:
        """Validate and clean contact number."""
        if v is not None and not v.strip():
            raise ValueError("Contact number cannot be empty or whitespace")
        return v.strip() if v is not None else None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: Optional[str]) -> Optional[str]:
        """Validate and clean role."""
        if v is not None and not v.strip():
            raise ValueError("Role cannot be empty or whitespace")
        return v.strip() if v is not None else None

    def has_updates(self) -> bool:
        """Check if at least one field is provided for update."""
        return any(
            [
                self.name is not None,
                self.contact_no is not None,
                self.role is not None,
                self.area_id is not None,
            ]
        )


# Response Models


class UserResponse(BaseModel):
    """Response model for user data."""

    id: UUID
    username: str
    name: str
    contact_no: str
    company_id: UUID
    role: str
    area_id: Optional[int]
    is_active: bool
    created_at: datetime
    updated_at: datetime
