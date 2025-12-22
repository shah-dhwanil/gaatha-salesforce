"""
Company models for database and API operations.

This module contains Pydantic models for company data validation,
including database representations, API requests, and responses.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


class CompanyInDB(BaseModel):
    """Company model representing database record."""

    id: UUID
    name: str
    gst_no: str
    cin_no: str
    address: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


# Request Models


class CreateCompanyRequest(BaseModel):
    """Request model for creating a new company."""

    name: str = Field(
        ..., min_length=1, max_length=255, description="Name of the company"
    )
    gst_no: str = Field(
        ..., min_length=15, max_length=15, description="GST number (15 characters)"
    )
    cin_no: str = Field(
        ..., min_length=21, max_length=21, description="CIN number (21 characters)"
    )
    address: str = Field(
        ..., min_length=1, max_length=500, description="Company address"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate and clean company name."""
        if not v or not v.strip():
            raise ValueError("Company name cannot be empty or whitespace")
        return v.strip()

    @field_validator("gst_no")
    @classmethod
    def validate_gst_no(cls, v: str) -> str:
        """Validate and clean GST number."""
        if not v or not v.strip():
            raise ValueError("GST number cannot be empty or whitespace")
        v_stripped = v.strip()
        if len(v_stripped) != 15:
            raise ValueError("GST number must be exactly 15 characters")
        return v_stripped

    @field_validator("cin_no")
    @classmethod
    def validate_cin_no(cls, v: str) -> str:
        """Validate and clean CIN number."""
        if not v or not v.strip():
            raise ValueError("CIN number cannot be empty or whitespace")
        v_stripped = v.strip()
        if len(v_stripped) != 21:
            raise ValueError("CIN number must be exactly 21 characters")
        return v_stripped

    @field_validator("address")
    @classmethod
    def validate_address(cls, v: str) -> str:
        """Validate and clean address."""
        if not v or not v.strip():
            raise ValueError("Address cannot be empty or whitespace")
        return v.strip()


class UpdateCompanyRequest(BaseModel):
    """Request model for updating a company."""

    name: Optional[str] = Field(
        None, min_length=1, max_length=255, description="Name of the company"
    )
    gst_no: Optional[str] = Field(
        None, min_length=15, max_length=15, description="GST number (15 characters)"
    )
    cin_no: Optional[str] = Field(
        None, min_length=21, max_length=21, description="CIN number (21 characters)"
    )
    address: Optional[str] = Field(
        None, min_length=1, max_length=500, description="Company address"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate and clean company name."""
        if v is not None:
            if not v.strip():
                raise ValueError("Company name cannot be empty or whitespace")
            return v.strip()
        return v

    @field_validator("gst_no")
    @classmethod
    def validate_gst_no(cls, v: Optional[str]) -> Optional[str]:
        """Validate and clean GST number."""
        if v is not None:
            if not v.strip():
                raise ValueError("GST number cannot be empty or whitespace")
            v_stripped = v.strip()
            if len(v_stripped) != 15:
                raise ValueError("GST number must be exactly 15 characters")
            return v_stripped.upper()
        return v

    @field_validator("cin_no")
    @classmethod
    def validate_cin_no(cls, v: Optional[str]) -> Optional[str]:
        """Validate and clean CIN number."""
        if v is not None:
            if not v.strip():
                raise ValueError("CIN number cannot be empty or whitespace")
            v_stripped = v.strip()
            if len(v_stripped) != 21:
                raise ValueError("CIN number must be exactly 21 characters")
            return v_stripped.upper()
        return v

    @field_validator("address")
    @classmethod
    def validate_address(cls, v: Optional[str]) -> Optional[str]:
        """Validate and clean address."""
        if v is not None:
            if not v.strip():
                raise ValueError("Address cannot be empty or whitespace")
            return v.strip()
        return v

    def has_updates(self) -> bool:
        """Check if any field has a value to update."""
        return any([self.name, self.gst_no, self.cin_no, self.address])


# Response Models


class CompanyResponse(BaseModel):
    """Response model for company operations."""

    id: UUID = Field(..., description="Unique identifier of the company")
    name: str = Field(..., description="Name of the company")
    gst_no: str = Field(..., description="GST number")
    cin_no: str = Field(..., description="CIN number")
    address: str = Field(..., description="Company address")
    is_active: bool = Field(..., description="Whether the company is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
