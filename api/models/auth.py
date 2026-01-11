from pydantic.fields import Field
from h11._abnf import token
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, model_validator

class VerifyOTPRequest(BaseModel):
    username: Optional[str] = Field(None, description="Username of the user")
    contact_no: Optional[str] = Field(None, description="Contact number of the user")
    otp_code: str

    @model_validator(mode="after")
    def check_at_least_one_field(cls, values):
        if not values.username and not values.contact_no:
            raise ValueError("Either 'username' or 'contact_no' must be provided.")
        return values

class VerifyOTPResponse(BaseModel):
    class Company(BaseModel):
        company_id: UUID
        company_name: str
    token: str
    companies: Optional[list[Company]]


class AuthenticatedUser(BaseModel):
    user_id: UUID
    area_id: Optional[int]
    company_id: Optional[UUID]
    role: str

class AuthUserToCompanyRequest(BaseModel):
    company_id: Optional[UUID] = Field(None, description="Company ID to switch to")

class AuthResponse(BaseModel):
    user: AuthenticatedUser
    access_token: str

class GenerateOtpRequest(BaseModel):
    username: Optional[str] = Field(None, description="Username of the user")
    contact_no: Optional[str] = Field(None, description="Contact number of the user")

    @model_validator(mode="after")
    def check_at_least_one_field(cls, values):
        if not values.username and not values.contact_no:
            raise ValueError("Either 'username' or 'contact_no' must be provided.")
        return values