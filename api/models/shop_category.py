"""
Pydantic models for ShopCategory entity.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ShopCategoryCreate(BaseModel):
    """Model for creating a new shop category."""

    name: str = Field(..., min_length=1, max_length=32, description="Shop category name")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate and normalize shop category name."""
        if not v or not v.strip():
            raise ValueError("Shop category name cannot be empty")
        return v.strip()


class ShopCategoryUpdate(BaseModel):
    """Model for updating an existing shop category."""

    name: Optional[str] = Field(None, min_length=1, max_length=32, description="Shop category name")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate and normalize shop category name."""
        if v is None:
            return None
        if not v.strip():
            raise ValueError("Shop category name cannot be empty")
        return v.strip()


class ShopCategoryInDB(BaseModel):
    """Model for ShopCategory as stored in database."""

    id: int = Field(..., description="Shop category ID")
    name: str = Field(..., description="Shop category name")
    is_active: bool = Field(..., description="Whether the shop category is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class ShopCategoryResponse(BaseModel):
    """Model for ShopCategory API response."""

    id: int = Field(..., description="Shop category ID")
    name: str = Field(..., description="Shop category name")
    is_active: bool = Field(..., description="Whether the shop category is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class ShopCategoryListItem(BaseModel):
    """Minimal model for ShopCategory in list views to optimize performance."""

    id: int = Field(..., description="Shop category ID")
    name: str = Field(..., description="Shop category name")
    is_active: bool = Field(..., description="Whether the shop category is active")

    class Config:
        from_attributes = True

