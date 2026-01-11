from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel
from api.models.docuemnts import DocumentInDB


class MeasurementDetails(BaseModel):
    type: str
    shelf_life: Optional[str] = None
    net: float
    net_unit: str
    gross: float
    gross_unit: str


class PackagingDetails(BaseModel):
    name: str
    qty: int
    parent: Optional[str] = None
    base_qty: int
    base_unit: str
    is_default: bool


class ProductMargins(BaseModel):
    class Margin(BaseModel):
        type: Literal["MARKUP", "MARKDOWN", "FIXED"]
        value: float
        purchase_price: float
        sale_price: float

    super_stockist: Margin
    distributor: Margin
    retailer: Margin


class MinOrderQuantities(BaseModel):
    super_stockist: int
    distributor: int
    retailer: int


class Dimensions(BaseModel):
    length: float
    width: float
    height: float
    weight: float
    unit: str


# Product Price Models
class ProductPriceCreate(BaseModel):
    area_id: Optional[int] = None
    mrp: float
    margins: Optional[ProductMargins] = None
    min_order_quantity: Optional[MinOrderQuantities] = None


class ProductPriceInDB(BaseModel):
    id: int
    product_id: int
    area_id: Optional[int] = None
    mrp: float
    margins: Optional[ProductMargins] = None
    min_order_quantity: Optional[MinOrderQuantities] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ProductPriceUpdate(BaseModel):
    mrp: Optional[float] = None
    margins: Optional[ProductMargins] = None
    min_order_quantity: Optional[MinOrderQuantities] = None
    is_active: Optional[bool] = None


# Product Visibility Models
class ProductVisibilityCreate(BaseModel):
    area_id: Optional[int] = None
    for_general: bool = False
    for_modern: bool = False
    for_horeca: bool = False
    for_type_a: bool = False
    for_type_b: bool = False
    for_type_c: bool = False


class ProductVisibilityInDB(BaseModel):
    id: int
    product_id: int
    area_id: Optional[int] = None
    for_general: bool
    for_modern: bool
    for_horeca: bool
    for_type_a: bool
    for_type_b: bool
    for_type_c: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


# Product Models
class ProductInDB(BaseModel):
    id: int
    brand_id: int
    brand_category_id: int
    brand_subcategory_id: Optional[int] = None
    name: str
    code: str
    description: Optional[str] = None
    barcode: Optional[str] = None
    hsn_code: Optional[str] = None
    gst_rate: float
    gst_category: str
    dimensions: Optional[Dimensions] = None
    compliance: Optional[str] = None
    measurement_details: Optional[MeasurementDetails] = None
    packaging_type: Optional[str] = None
    packaging_details: Optional[list[PackagingDetails]] = None
    images: Optional[list[DocumentInDB]] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ProductCreate(BaseModel):
    brand_id: int
    brand_category_id: int
    brand_subcategory_id: Optional[int] = None
    name: str
    code: str
    description: Optional[str] = None
    barcode: Optional[str] = None
    hsn_code: Optional[str] = None
    gst_rate: float
    gst_category: str
    dimensions: Optional[Dimensions] = None
    compliance: Optional[str] = None
    measurement_details: Optional[MeasurementDetails] = None
    packaging_type: str
    packaging_details: list[PackagingDetails]
    images: Optional[list[DocumentInDB]] = None
    prices: list[ProductPriceCreate]
    visibility: list[ProductVisibilityCreate]


class ProductUpdate(BaseModel):
    brand_id: Optional[int] = None
    brand_category_id: Optional[int] = None
    brand_subcategory_id: Optional[int] = None
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    barcode: Optional[str] = None
    hsn_code: Optional[str] = None
    gst_rate: Optional[float] = None
    gst_category: Optional[str] = None
    dimensions: Optional[Dimensions] = None
    compliance: Optional[str] = None
    measurement_details: MeasurementDetails
    packaging_type: str
    packaging_details: Optional[list[PackagingDetails]] = None
    images: Optional[list[DocumentInDB]] = None
    is_active: Optional[bool] = None


class ProductListItem(BaseModel):
    id: int
    name: str
    brand_name: str
    category_name: str
    packaging_type: Optional[str] = None
    measurement_details: Optional[MeasurementDetails] = None
    images: Optional[list[DocumentInDB]] = None
    price: Optional[float] = None
    is_active: bool


class ProductDetailItem(BaseModel):
    id: int
    brand_id: int
    brand_name: str
    brand_category_id: int
    category_name: str
    brand_subcategory_id: Optional[int] = None
    subcategory_name: Optional[str] = None
    name: str
    code: str
    description: Optional[str] = None
    barcode: Optional[str] = None
    hsn_code: Optional[str] = None
    gst_rate: float
    gst_category: str
    dimensions: Optional[Dimensions] = None
    compliance: Optional[str] = None
    measurement_details: Optional[MeasurementDetails] = None
    packaging_type: Optional[str] = None
    packaging_details: Optional[list[PackagingDetails]] = None
    images: Optional[list[DocumentInDB]] = None
    prices: Optional[list[ProductPriceInDB]] = None
    visibility: Optional[list[ProductVisibilityInDB]] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
