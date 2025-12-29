from typing import Optional
from uuid import UUID
from pydantic import BaseModel

class AuthRequest(BaseModel):
    username: str
    otp_code: str

class AuthenticatedUser(BaseModel):
    user_id: UUID
    area_id: Optional[int]
    company_id: Optional[UUID]
    role: str

class AuthResponse(BaseModel):
    user: AuthenticatedUser
    access_token: str