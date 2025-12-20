from datetime import datetime
from enum import StrEnum
from typing import Optional
from pydantic import BaseModel

class AreaType(StrEnum):
    DIVISION = "DIVISION"
    AREA = "AREA"
    REGION = "REGION"
    ZONE = "ZONE"
    NATION = "NATION"


class AreaInDB(BaseModel):
    id: int
    name: str
    type: str
    area_id: Optional[int]
    region_id: Optional[int]
    zone_id: Optional[int]
    nation_id: Optional[int]
    is_active: bool
    created_at: datetime
    updated_at: datetime
