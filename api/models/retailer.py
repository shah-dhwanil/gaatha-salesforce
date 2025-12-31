"""
Pydantic models for Retailer entity.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from api.models.docuemnts import DocumentInDB
from api.models.user import BankDetails


class RetailerCreate(BaseModel):
    """Model for creating a new retailer."""

    name: str = Field(..., min_length=1, max_length=255, description="Retailer name")
    contact_person_name: str = Field(..., min_length=1, max_length=255, description="Contact person name")
    mobile_number: str = Field(..., min_length=10, max_length=15, description="Mobile number")
    email: Optional[EmailStr] = Field(None, description="Email address")
    gst_no: str = Field(..., min_length=15, max_length=15, description="GST number")
    pan_no: str = Field(..., min_length=10, max_length=10, description="PAN number")
    license_no: Optional[str] = Field(None, max_length=255, description="License number")
    address: str = Field(..., min_length=1, description="Address")
    category_id: int = Field(..., description="Shop category ID")
    pin_code: str = Field(..., min_length=6, max_length=6, description="PIN code")
    map_link: Optional[str] = Field(None, description="Map link")
    documents: Optional[DocumentInDB] = Field(None, description="Documents")
    store_images: Optional[DocumentInDB] = Field(None, description="Store images")
    route_id: int = Field(..., description="Route ID")
    bank_details: BankDetails = Field(..., description="Bank details")
    is_verified: bool = Field(default=False, description="Whether the retailer is verified")

    @field_validator("name", "contact_person_name", "address")
    @classmethod
    def validate_required_strings(cls, v: str) -> str:
        """Validate and normalize required string fields."""
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()

    @field_validator("gst_no", "pan_no", "mobile_number", "pin_code")
    @classmethod
    def validate_codes(cls, v: str) -> str:
        """Validate and normalize code fields."""
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip().upper()

    @field_validator("license_no")
    @classmethod
    def validate_license_no(cls, v: Optional[str]) -> Optional[str]:
        """Validate and normalize license number."""
        if v is None:
            return None
        if not v.strip():
            raise ValueError("License number cannot be empty string")
        return v.strip().upper()


class RetailerUpdate(BaseModel):
    """Model for updating an existing retailer."""

    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Retailer name")
    contact_person_name: Optional[str] = Field(None, min_length=1, max_length=255, description="Contact person name")
    mobile_number: Optional[str] = Field(None, min_length=10, max_length=15, description="Mobile number")
    email: Optional[EmailStr] = Field(None, description="Email address")
    gst_no: Optional[str] = Field(None, min_length=15, max_length=15, description="GST number")
    pan_no: Optional[str] = Field(None, min_length=10, max_length=10, description="PAN number")
    license_no: Optional[str] = Field(None, max_length=255, description="License number")
    address: Optional[str] = Field(None, min_length=1, description="Address")
    category_id: Optional[int] = Field(None, description="Shop category ID")
    pin_code: Optional[str] = Field(None, min_length=6, max_length=6, description="PIN code")
    map_link: Optional[str] = Field(None, description="Map link")
    route_id: Optional[int] = Field(None, description="Route ID")
    is_verified: Optional[bool] = Field(None, description="Whether the retailer is verified")

    @field_validator("name", "contact_person_name", "address")
    @classmethod
    def validate_strings(cls, v: Optional[str]) -> Optional[str]:
        """Validate and normalize string fields."""
        if v is None:
            return None
        if not v.strip():
            raise ValueError("Field cannot be empty string")
        return v.strip()

    @field_validator("gst_no", "pan_no", "mobile_number", "pin_code")
    @classmethod
    def validate_codes(cls, v: Optional[str]) -> Optional[str]:
        """Validate and normalize code fields."""
        if v is None:
            return None
        if not v.strip():
            raise ValueError("Field cannot be empty string")
        return v.strip().upper()

    @field_validator("license_no")
    @classmethod
    def validate_license_no(cls, v: Optional[str]) -> Optional[str]:
        """Validate and normalize license number."""
        if v is None:
            return None
        if not v.strip():
            raise ValueError("License number cannot be empty string")
        return v.strip().upper()


class RetailerInDB(BaseModel):
    """Model for Retailer as stored in database."""

    id: UUID = Field(..., description="Retailer ID")
    name: str = Field(..., description="Retailer name")
    code: str = Field(..., description="Retailer code")
    contact_person_name: str = Field(..., description="Contact person name")
    mobile_number: str = Field(..., description="Mobile number")
    email: Optional[str] = Field(None, description="Email address")
    gst_no: str = Field(..., description="GST number")
    pan_no: str = Field(..., description="PAN number")
    license_no: Optional[str] = Field(None, description="License number")
    address: str = Field(..., description="Address")
    category_id: int = Field(..., description="Shop category ID")
    pin_code: str = Field(..., description="PIN code")
    map_link: Optional[str] = Field(None, description="Map link")
    documents: Optional[dict] = Field(None, description="Documents")
    store_images: Optional[dict] = Field(None, description="Store images")
    route_id: int = Field(..., description="Route ID")
    is_verified: bool = Field(..., description="Whether the retailer is verified")
    is_active: bool = Field(..., description="Whether the retailer is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class RetailerResponse(BaseModel):
    """Model for Retailer API response."""

    id: UUID = Field(..., description="Retailer ID")
    name: str = Field(..., description="Retailer name")
    code: str = Field(..., description="Retailer code")
    contact_person_name: str = Field(..., description="Contact person name")
    mobile_number: str = Field(..., description="Mobile number")
    email: Optional[str] = Field(None, description="Email address")
    gst_no: str = Field(..., description="GST number")
    pan_no: str = Field(..., description="PAN number")
    license_no: Optional[str] = Field(None, description="License number")
    address: str = Field(..., description="Address")
    category_id: int = Field(..., description="Shop category ID")
    pin_code: str = Field(..., description="PIN code")
    map_link: Optional[str] = Field(None, description="Map link")
    documents: Optional[dict] = Field(None, description="Documents")
    store_images: Optional[dict] = Field(None, description="Store images")
    route_id: int = Field(..., description="Route ID")
    is_verified: bool = Field(..., description="Whether the retailer is verified")
    is_active: bool = Field(..., description="Whether the retailer is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class RetailerListItem(BaseModel):
    """Minimal model for Retailer in list views to optimize performance."""

    id: UUID = Field(..., description="Retailer ID")
    name: str = Field(..., description="Retailer name")
    code: str = Field(..., description="Retailer code")
    contact_person_name: str = Field(..., description="Contact person name")
    mobile_number: str = Field(..., description="Mobile number")
    address: str = Field(..., description="Address")
    route_id: int = Field(..., description="Route ID")
    route_name: str = Field(..., description="Route name")
    store_images: Optional[dict] = Field(None, description="Store images")
    is_verified: bool = Field(..., description="Whether the retailer is verified")
    is_active: bool = Field(..., description="Whether the retailer is active")

    class Config:
        from_attributes = True


class RetailerDetailItem(BaseModel):
    """Detailed model for Retailer with joined data."""

    id: UUID = Field(..., description="Retailer ID")
    name: str = Field(..., description="Retailer name")
    code: str = Field(..., description="Retailer code")
    contact_person_name: str = Field(..., description="Contact person name")
    mobile_number: str = Field(..., description="Mobile number")
    email: Optional[str] = Field(None, description="Email address")
    gst_no: str = Field(..., description="GST number")
    pan_no: str = Field(..., description="PAN number")
    license_no: Optional[str] = Field(None, description="License number")
    address: str = Field(..., description="Address")
    category_id: int = Field(..., description="Shop category ID")
    category_name: str = Field(..., description="Shop category name")
    pin_code: str = Field(..., description="PIN code")
    map_link: Optional[str] = Field(None, description="Map link")
    documents: Optional[dict] = Field(None, description="Documents")
    store_images: Optional[dict] = Field(None, description="Store images")
    route_id: int = Field(..., description="Route ID")
    route_name: str = Field(..., description="Route name")
    bank_details: BankDetails = Field(..., description="Bank details")
    is_verified: bool = Field(..., description="Whether the retailer is verified")
    is_active: bool = Field(..., description="Whether the retailer is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True
        ignore_extra = True

