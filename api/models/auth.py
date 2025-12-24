from typing import Optional
from pydantic import BaseModel
from uuid import UUID


class AuthenticatedUser(BaseModel):
    user_id: UUID
    area_id: Optional[int]
    company_id: UUID
    role: str


class LoginRequest(BaseModel):
    username: str
    otp_code: str


class LoginResponse(BaseModel):
    user: AuthenticatedUser
    access_token: str
