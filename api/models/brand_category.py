from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
from api.models.area import AreaListItem
from api.models.docuemnts import DocumentInDB


# Brand Category Models
class BrandCategoryMargins(BaseModel):
    class Margin(BaseModel):
        type: Literal["MARKUP", "MARKDOWN", "FIXED"]
        value: float

    super_stockist: Optional[Margin] = Field(default=None)
    distributor: Optional[Margin] = Field(default=None)
    retailer: Optional[Margin] = Field(default=None)


class BrandCategoryMarginInDB(BaseModel):
    id: int
    area_id: Optional[int] = Field(default=None)
    name: Optional[str] = Field(default=None)
    margins: Optional[BrandCategoryMargins] = Field(default=None)
    is_active: bool
    created_at: datetime
    updated_at: datetime


class BrandCategoryMarginCreate(BaseModel):
    area_id: Optional[int] = Field(default=None)
    margins: BrandCategoryMargins


class BrandCategoryMarginListItem(BaseModel):
    id: int
    area: Optional[AreaListItem] = Field(default=None)
    margins: BrandCategoryMargins
    is_active: bool


class BrandCategoryMarginUpdate(BaseModel):
    area_id: Optional[int] = Field(default=None)
    margins: Optional[BrandCategoryMargins] = Field(default=None)


class BrandCategoryInDB(BaseModel):
    id: int
    name: str
    code: str
    brand_id: int
    parent_category_id: Optional[int] = Field(default=None)
    for_general: bool
    for_modern: bool
    for_horeca: bool
    logo: Optional[DocumentInDB] = Field(default=None)
    is_active: bool
    is_deleted: bool
    created_at: datetime
    updated_at: datetime


class BrandCategoryCreate(BaseModel):
    name: str
    code: str
    brand_id: int
    parent_category_id: Optional[int] = Field(default=None)
    for_general: bool
    for_modern: bool
    for_horeca: bool
    logo: Optional[DocumentInDB] = Field(default=None)
    area_id: Optional[list[int]] = Field(default=None)
    margins: Optional[list[BrandCategoryMarginCreate]] = Field(default=None)


class BrandCategoryUpdate(BaseModel):
    name: Optional[str] = Field(default=None)
    code: Optional[str] = Field(default=None)
    brand_id: Optional[int] = Field(default=None)
    parent_category_id: Optional[int] = Field(default=None)
    for_general: Optional[bool] = Field(default=None)
    for_modern: Optional[bool] = Field(default=None)
    for_horeca: Optional[bool] = Field(default=None)
    logo: Optional[DocumentInDB] = Field(default=None)
    is_active: Optional[bool] = Field(default=None)


class BrandCategoryListItem(BaseModel):
    id: int
    name: str
    code: str
    no_of_products: int
    is_active: bool
    created_at: datetime


# Response model for brand category details which is should be returned when brand category get by id or code
class BrandCategoryDetailItem(BaseModel):
    id: int
    name: str
    code: str
    brand_id: int
    parent_category_id: Optional[int] = Field(default=None)
    parent_category_name: Optional[str] = Field(default=None)
    for_general: bool
    for_modern: bool
    for_horeca: bool
    logo: Optional[DocumentInDB] = Field(default=None)
    area: Optional[list[AreaListItem]] = Field(default=None)
    margins: Optional[list[BrandCategoryMarginInDB]] = Field(default=None)
    is_active: bool
    is_deleted: bool
    created_at: datetime
    updated_at: datetime


class BrandCategoryMarginAddOrUpdate(BaseModel):
    name: Optional[str] = Field(default=None)
    area_id: Optional[int] = Field(default=None)
    margins: Optional[BrandCategoryMargins] = Field(default=None)
