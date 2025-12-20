from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class RoleInDB(BaseModel):
    name: str
    description: Optional[str]
    permissions: list[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
