from datetime import datetime
from uuid import UUID
from typing import Optional
from pydantic import BaseModel


class UserInDB(BaseModel):
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
