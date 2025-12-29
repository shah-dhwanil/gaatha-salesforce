"""
Pydantic models for Company entity.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class CompanyCreate(BaseModel):
    """Model for creating a new company."""

    name: str = Field(..., min_length=1, max_length=255, description="Company name")
    gst_no: str = Field(..., min_length=15, max_length=15, description="GST number")
    cin_no: str = Field(..., min_length=21, max_length=21, description="CIN number")
    address: str = Field(..., min_length=1, description="Company address")

    @field_validator("name", "address")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        """Validate and normalize string fields."""
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()

    @field_validator("gst_no")
    @classmethod
    def validate_gst(cls, v: str) -> str:
        """Validate GST number format."""
        v = v.strip().upper()
        if len(v) != 15:
            raise ValueError("GST number must be exactly 15 characters")
        return v

    @field_validator("cin_no")
    @classmethod
    def validate_cin(cls, v: str) -> str:
        """Validate CIN number format."""
        v = v.strip().upper()
        if len(v) != 21:
            raise ValueError("CIN number must be exactly 21 characters")
        return v


class CompanyUpdate(BaseModel):
    """Model for updating an existing company."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    address: Optional[str] = Field(None, min_length=1)
    gst_no: Optional[str] = Field(None, min_length=15, max_length=15)
    cin_no: Optional[str] = Field(None, min_length=21, max_length=21)

    @field_validator("name", "address")
    @classmethod
    def validate_non_empty(cls, v: Optional[str]) -> Optional[str]:
        """Validate and normalize string fields."""
        if v is not None:
            if not v.strip():
                raise ValueError("Field cannot be empty")
            return v.strip()
        return v
    
    @field_validator("gst_no")
    @classmethod
    def validate_gst(cls, v: Optional[str]) -> Optional[str]:
        """Validate GST number format."""
        if v is not None:
            v = v.strip().upper()
            if len(v) != 15:
                raise ValueError("GST number must be exactly 15 characters")
            return v
        return v.upper()
    
    @field_validator("cin_no")
    @classmethod
    def validate_cin(cls, v: Optional[str]) -> Optional[str]:
        """Validate CIN number format."""
        if v is not None:
            v = v.strip().upper()
            if len(v) != 21:
                raise ValueError("CIN number must be exactly 21 characters")
            return v
        return v.upper()    

class CompanyInDB(BaseModel):
    """Model for Company as stored in database."""

    id: UUID = Field(..., description="Company unique identifier")
    name: str = Field(..., description="Company name")
    gst_no: str = Field(..., description="GST number")
    cin_no: str = Field(..., description="CIN number")
    address: str = Field(..., description="Company address")
    is_active: bool = Field(..., description="Whether the company is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class CompanyResponse(BaseModel):
    """Model for Company API response."""

    id: UUID = Field(..., description="Company unique identifier")
    name: str = Field(..., description="Company name")
    gst_no: str = Field(..., description="GST number")
    cin_no: str = Field(..., description="CIN number")
    address: str = Field(..., description="Company address")
    is_active: bool = Field(..., description="Whether the company is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class CompanyListItem(BaseModel):
    """Minimal model for Company in list views to optimize performance."""

    id: UUID = Field(..., description="Company unique identifier")
    name: str = Field(..., description="Company name")
    is_active: bool = Field(..., description="Whether the company is active")

    class Config:
        from_attributes = True

