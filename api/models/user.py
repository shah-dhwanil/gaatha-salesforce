from datetime import datetime
from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator, ConfigDict
from pydantic.functional_validators import model_validator


class BankDetails(BaseModel):
    """Bank details model representing database record."""

    account_number: str
    account_name: str
    bank_name: str
    bank_branch: str
    account_type: Literal["SAVINGS", "CURRENT"]
    ifsc_code: str


class UserInDB(BaseModel):
    """User model representing database record."""

    id: UUID
    username: Optional[str]
    name: str
    contact_no: str
    company_id: Optional[UUID]
    role: Optional[str]
    area_id: Optional[int]
    bank_details: Optional[BankDetails]
    salary: Optional[int] = Field(default=0, description="Salary of the user")
    is_active: bool
    is_super_admin: bool = Field(
        default=False, description="Indicates if the user is a super admin"
    )
    created_at: datetime
    updated_at: datetime


class UserCreate(BaseModel):
    """Request model for creating a new user."""

    username: Optional[str] = Field(
        None, min_length=1, max_length=100, description="Unique username for the user"
    )
    name: str = Field(
        ..., min_length=1, max_length=255, description="Full name of the user"
    )
    contact_no: str = Field(
        ..., min_length=1, max_length=20, description="Contact phone number"
    )
    company_id: Optional[UUID] = Field(
        None, description="UUID of the company the user belongs to"
    )
    role: Optional[str] = Field(None, description="Role of the user")
    area_id: Optional[int] = Field(None, description="Area of the user")
    bank_details: Optional[BankDetails] = Field(
        None, description="Bank details of the user"
    )
    salary: Optional[int] = Field(default=None, description="Salary of the user")
    is_super_admin: bool = Field(
        default=False, description="Indicates if the user is a super admin"
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: Optional[str]) -> Optional[str]:
        """Validate and clean username."""
        if v is not None and not v.strip():
            raise ValueError("Username cannot be empty or whitespace")
        return v.strip() if v is not None else None

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

    @model_validator(mode="after")
    def validate_user_request(self) -> "UserCreate":
        """Validate the user request."""
        if self.role and self.role.lower() == "admin":
            return self
        if not self.is_super_admin :
            if not self.company_id:
                raise ValueError("Company ID is required")
            if not self.role:
                raise ValueError("Role is required")
            if not self.area_id:
                raise ValueError("Area ID is required")
            if not self.bank_details:
                raise ValueError("Bank details are required")
            if self.role.lower() not in ["retailer","distributor","super_stockist"]:
                if self.salary is None:
                    raise ValueError("Salary is required")
        return self


class UserUpdate(BaseModel):
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
    bank_details: Optional[BankDetails] = Field(
        None, description="Bank details of the user"
    )
    salary: Optional[int] = Field(None, description="Salary of the user")
    company_id: Optional[UUID] = Field(
        None, description="UUID of the company (for schema context)"
    )

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
                self.bank_details is not None,
                self.salary is not None,
            ]
        )


class UserListResponse(BaseModel):
    """User list response model."""

    model_config = ConfigDict(
        extra="allow",
    )

    id: UUID
    username: Optional[str] = Field(..., description="Username of the user")
    name: str = Field(..., description="Name of the user")
    contact_no: str = Field(..., description="Contact number of the user")
    company_id: Optional[UUID] = Field(..., description="Company ID of the user")
    role: Optional[str] = Field(..., description="Role of the user")
    area_id: Optional[int] = Field(..., description="Area ID of the user")
    area_name: Optional[str] = Field(
        ..., description="Name of area asscociated with the user"
    )
    is_active: bool = Field(..., description="Whether the user is active")


class UserResponse(BaseModel):
    """User response model."""

    id: UUID = Field(..., description="ID of the user")
    username: Optional[str] = Field(None, description="Username of the user")
    name: str = Field(..., description="Name of the user")
    contact_no: str = Field(..., description="Contact number of the user")
    company_id: Optional[UUID] = Field(..., description="Company ID of the user")
    role: Optional[str] = Field(..., description="Role of the user")
    area_id: Optional[int] = Field(..., description="Area ID of the user")
    bank_details: Optional[BankDetails] = Field(
        ..., description="Bank details of the user"
    )
    salary: Optional[int] = Field(default=0, description="Salary of the user")
    is_super_admin: bool = Field(..., description="Whether the user is a super admin")
    is_active: bool = Field(..., description="Whether the user is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class UserDetailsResponse(BaseModel):
    """User details response model."""

    id: UUID = Field(..., description="ID of the user")
    username: Optional[str] = Field(None, description="Username of the user")
    name: str = Field(..., description="Name of the user")
    contact_no: str = Field(..., description="Contact number of the user")
    company_id: Optional[UUID] = Field(..., description="Company ID of the user")
    company_name: Optional[str] = Field(..., description="Name of the company")
    role: Optional[str] = Field(..., description="Role of the user")
    area_id: Optional[int] = Field(..., description="Area ID of the user")
    area_name: Optional[str] = Field(
        ..., description="Name of the area asscociated with the user"
    )
    area_type: Optional[str] = Field(
        ..., description="Type of the area asscociated with the user"
    )
    bank_details: Optional[BankDetails] = Field(
        ..., description="Bank details of the user"
    )
    salary: Optional[int] = Field(default=0, description="Salary of the user")
    is_super_admin: bool = Field(..., description="Whether the user is a super admin")
    is_active: bool = Field(..., description="Whether the user is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
