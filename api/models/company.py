from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class CompanyInDB(BaseModel):
    id: UUID
    name: str
    gst_no: str
    cin_no: str
    address: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
