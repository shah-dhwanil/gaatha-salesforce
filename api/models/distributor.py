"""
Pydantic models for Distributor entity.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from api.models.docuemnts import DocumentInDB
from api.models.user import BankDetails


class DistributorRouteDetail(BaseModel):
    """Model for route details in distributor response."""

    id: int = Field(..., description="Route ID")
    name: str = Field(..., description="Route name")
    type: str = Field(..., description="Route type (general, modern, or horeca)")

    class Config:
        from_attributes = True


class DistributorCreate(BaseModel):
    """Model for creating a new distributor."""

    name: str = Field(..., min_length=1, max_length=255, description="Distributor name")
    contact_person_name: str = Field(
        ..., min_length=1, max_length=255, description="Contact person name"
    )
    mobile_number: str = Field(
        ..., min_length=10, max_length=15, description="Mobile number"
    )
    email: Optional[EmailStr] = Field(None, description="Email address")
    gst_no: str = Field(..., min_length=15, max_length=15, description="GST number")
    pan_no: str = Field(..., min_length=10, max_length=10, description="PAN number")
    license_no: Optional[str] = Field(
        None, max_length=255, description="License number"
    )
    address: str = Field(..., min_length=1, description="Address")
    pin_code: str = Field(..., min_length=6, max_length=6, description="PIN code")
    map_link: Optional[str] = Field(None, description="Map link")
    documents: Optional[DocumentInDB] = Field(None, description="Documents")
    store_images: Optional[DocumentInDB] = Field(None, description="Store images")
    vehicle_3: int = Field(..., ge=0, description="Number of 3-wheeler vehicles")
    vehicle_4: int = Field(..., ge=0, description="Number of 4-wheeler vehicles")
    salesman_count: int = Field(..., ge=0, description="Number of salesmen")
    area_id: int = Field(..., description="Area ID")
    for_general: bool = Field(
        default=False, description="Whether distributor serves general trade"
    )
    for_modern: bool = Field(
        default=False, description="Whether distributor serves modern trade"
    )
    for_horeca: bool = Field(
        default=False, description="Whether distributor serves HORECA"
    )
    bank_details: BankDetails = Field(..., description="Bank details")
    route_ids: list[int] = Field(
        default=[], description="List of route IDs to associate with distributor"
    )

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


class DistributorUpdate(BaseModel):
    """Model for updating an existing distributor."""

    name: Optional[str] = Field(
        None, min_length=1, max_length=255, description="Distributor name"
    )
    contact_person_name: Optional[str] = Field(
        None, min_length=1, max_length=255, description="Contact person name"
    )
    mobile_number: Optional[str] = Field(
        None, min_length=10, max_length=15, description="Mobile number"
    )
    email: Optional[EmailStr] = Field(None, description="Email address")
    gst_no: Optional[str] = Field(
        None, min_length=15, max_length=15, description="GST number"
    )
    pan_no: Optional[str] = Field(
        None, min_length=10, max_length=10, description="PAN number"
    )
    license_no: Optional[str] = Field(
        None, max_length=255, description="License number"
    )
    address: Optional[str] = Field(None, min_length=1, description="Address")
    pin_code: Optional[str] = Field(
        None, min_length=6, max_length=6, description="PIN code"
    )
    map_link: Optional[str] = Field(None, description="Map link")
    vehicle_3: Optional[int] = Field(
        None, ge=0, description="Number of 3-wheeler vehicles"
    )
    vehicle_4: Optional[int] = Field(
        None, ge=0, description="Number of 4-wheeler vehicles"
    )
    salesman_count: Optional[int] = Field(None, ge=0, description="Number of salesmen")
    area_id: Optional[int] = Field(None, description="Area ID")
    for_general: Optional[bool] = Field(
        None, description="Whether distributor serves general trade"
    )
    for_modern: Optional[bool] = Field(
        None, description="Whether distributor serves modern trade"
    )
    for_horeca: Optional[bool] = Field(
        None, description="Whether distributor serves HORECA"
    )

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


class DistributorInDB(BaseModel):
    """Model for Distributor as stored in database."""

    id: UUID = Field(..., description="Distributor ID")
    name: str = Field(..., description="Distributor name")
    code: str = Field(..., description="Distributor code")
    contact_person_name: str = Field(..., description="Contact person name")
    mobile_number: str = Field(..., description="Mobile number")
    email: Optional[str] = Field(None, description="Email address")
    gst_no: str = Field(..., description="GST number")
    pan_no: str = Field(..., description="PAN number")
    license_no: Optional[str] = Field(None, description="License number")
    address: str = Field(..., description="Address")
    pin_code: str = Field(..., description="PIN code")
    map_link: Optional[str] = Field(None, description="Map link")
    documents: Optional[dict] = Field(None, description="Documents")
    store_images: Optional[dict] = Field(None, description="Store images")
    vehicle_3: int = Field(..., description="Number of 3-wheeler vehicles")
    vehicle_4: int = Field(..., description="Number of 4-wheeler vehicles")
    salesman_count: int = Field(..., description="Number of salesmen")
    area_id: int = Field(..., description="Area ID")
    for_general: bool = Field(
        ..., description="Whether distributor serves general trade"
    )
    for_modern: bool = Field(..., description="Whether distributor serves modern trade")
    for_horeca: bool = Field(..., description="Whether distributor serves HORECA")
    is_active: bool = Field(..., description="Whether the distributor is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class DistributorResponse(BaseModel):
    """Model for Distributor API response."""

    id: UUID = Field(..., description="Distributor ID")
    name: str = Field(..., description="Distributor name")
    code: str = Field(..., description="Distributor code")
    contact_person_name: str = Field(..., description="Contact person name")
    mobile_number: str = Field(..., description="Mobile number")
    email: Optional[str] = Field(None, description="Email address")
    gst_no: str = Field(..., description="GST number")
    pan_no: str = Field(..., description="PAN number")
    license_no: Optional[str] = Field(None, description="License number")
    address: str = Field(..., description="Address")
    pin_code: str = Field(..., description="PIN code")
    map_link: Optional[str] = Field(None, description="Map link")
    documents: Optional[dict] = Field(None, description="Documents")
    store_images: Optional[dict] = Field(None, description="Store images")
    vehicle_3: int = Field(..., description="Number of 3-wheeler vehicles")
    vehicle_4: int = Field(..., description="Number of 4-wheeler vehicles")
    salesman_count: int = Field(..., description="Number of salesmen")
    area_id: int = Field(..., description="Area ID")
    for_general: bool = Field(
        ..., description="Whether distributor serves general trade"
    )
    for_modern: bool = Field(..., description="Whether distributor serves modern trade")
    for_horeca: bool = Field(..., description="Whether distributor serves HORECA")
    is_active: bool = Field(..., description="Whether the distributor is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class DistributorListItem(BaseModel):
    """Minimal model for Distributor in list views to optimize performance."""

    id: UUID = Field(..., description="Distributor ID")
    name: str = Field(..., description="Distributor name")
    code: str = Field(..., description="Distributor code")
    contact_person_name: str = Field(..., description="Contact person name")
    mobile_number: str = Field(..., description="Mobile number")
    address: str = Field(..., description="Address")
    area_id: int = Field(..., description="Area ID")
    area_name: str = Field(..., description="Area name")
    route_count: int = Field(
        ..., description="Number of routes associated with distributor"
    )
    is_active: bool = Field(..., description="Whether the distributor is active")

    class Config:
        from_attributes = True


class DistributorDetailItem(BaseModel):
    """Detailed model for Distributor with joined data."""

    id: UUID = Field(..., description="Distributor ID")
    name: str = Field(..., description="Distributor name")
    code: str = Field(..., description="Distributor code")
    contact_person_name: str = Field(..., description="Contact person name")
    mobile_number: str = Field(..., description="Mobile number")
    email: Optional[str] = Field(None, description="Email address")
    gst_no: str = Field(..., description="GST number")
    pan_no: str = Field(..., description="PAN number")
    license_no: Optional[str] = Field(None, description="License number")
    address: str = Field(..., description="Address")
    pin_code: str = Field(..., description="PIN code")
    map_link: Optional[str] = Field(None, description="Map link")
    documents: Optional[dict] = Field(None, description="Documents")
    store_images: Optional[dict] = Field(None, description="Store images")
    vehicle_3: int = Field(..., description="Number of 3-wheeler vehicles")
    vehicle_4: int = Field(..., description="Number of 4-wheeler vehicles")
    salesman_count: int = Field(..., description="Number of salesmen")
    area_id: int = Field(..., description="Area ID")
    area_name: str = Field(..., description="Area name")
    for_general: bool = Field(
        ..., description="Whether distributor serves general trade"
    )
    for_modern: bool = Field(..., description="Whether distributor serves modern trade")
    for_horeca: bool = Field(..., description="Whether distributor serves HORECA")
    bank_details: BankDetails = Field(..., description="Bank details")
    routes: list[DistributorRouteDetail] = Field(
        default=[], description="Routes associated with distributor"
    )
    is_active: bool = Field(..., description="Whether the distributor is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True
        ignore_extra = True
