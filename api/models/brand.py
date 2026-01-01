from pydantic.fields import Field
from api.models.area import AreaListItem
from datetime import datetime
from api.models.docuemnts import DocumentInDB
from typing import Optional
from typing import Literal
from pydantic import BaseModel

class BrandMargins(BaseModel):
    class Margin(BaseModel):
        type:Literal["MARKUP","MARKDOWN","FIXED"]
        value:float
    super_stockist:Optional[Margin] = Field(default=None)
    distributor:Optional[Margin] = Field(default=None)
    retailer:Optional[Margin]   = Field(default=None)

class BrandMarginInDB(BaseModel):
    id:int
    area_id:Optional[int] = Field(default=None)
    name:str
    margins:BrandMargins
    is_active:bool
    created_at:datetime
    updated_at:datetime

class BrandMarginCreate(BaseModel):
    name:str
    area_id:Optional[int] = Field(default=None)
    margins:BrandMargins

class BrandMarginAddOrUpdate(BaseModel):
    name:Optional[str] = Field(default=None)
    area_id: Optional[int] = Field(default=None)
    margins:Optional[BrandMargins] = Field(default=None)

class BrandMarginListItem(BaseModel):
    id:int
    area:Optional[AreaListItem] = Field(default=None)
    margins:BrandMargins
    is_active:bool

class BrandMarginUpdate(BaseModel):
    area_id:Optional[int] = Field(default=None)
    margins:Optional[BrandMargins] = Field(default=None)

class BrandInDB(BaseModel):
    id:int
    name:str
    code:str
    for_general:bool
    for_modern:bool
    for_horeca:bool
    logo:Optional[DocumentInDB] = Field(default=None)
    is_active:bool
    is_deleted:bool
    created_at:datetime
    updated_at:datetime

class BrandCreate(BaseModel):
    name:str
    code:str
    for_general:bool
    for_modern:bool
    for_horeca:bool
    logo:Optional[DocumentInDB] = Field(default=None)
    area_id:Optional[list[int]] = Field(default=None)
    margins:Optional[list[BrandMarginCreate]] = Field(default=None)

class BrandUpdate(BaseModel):
    name:Optional[str] = Field(default=None)
    code:Optional[str] = Field(default=None)
    for_general:Optional[bool] = Field(default=None)
    for_modern:Optional[bool] = Field(default=None)
    for_horeca:Optional[bool] = Field(default=None)
    logo:Optional[DocumentInDB] = Field(default=None)
    is_active:Optional[bool] = Field(default=None)

class BrandListItem(BaseModel):
    id:int 
    name:str
    code:str
    no_of_categories:int
    no_of_products:int
    is_active:bool
    created_at:datetime

# Response model for brand details which is should be returned when brand get by id or code
class BrandDetailItem(BaseModel):
    id:int
    name:str
    code:str
    for_general:bool
    for_modern:bool
    for_horeca:bool
    logo:Optional[DocumentInDB] = Field(default=None)
    area:Optional[list[AreaListItem]] = Field(default=None)
    margins:Optional[list[BrandMarginInDB]] = Field(default=None)
    is_active:bool
    is_deleted:bool
    created_at:datetime
    updated_at:datetime
