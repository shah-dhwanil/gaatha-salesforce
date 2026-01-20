"""
Pydantic models for Order entity.
"""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


class OrderStatus(StrEnum):
    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class OrderType(StrEnum):
    TELEPHONE = "TELEPHONE"
    IN_STORE = "IN_STORE"
    OTHERS = "OTHERS"


# Order Item Models
class OrderItemCreate(BaseModel):
    """Model for creating an order item."""

    product_id: int = Field(..., description="Product ID")
    quantity: int = Field(..., gt=0, description="Quantity of product")

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: int) -> int:
        """Validate quantity is positive."""
        if v <= 0:
            raise ValueError("Quantity must be greater than 0")
        return v


class OrderItemUpdate(BaseModel):
    """Model for updating an order item."""

    quantity: Optional[int] = Field(None, gt=0, description="Quantity of product")

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: Optional[int]) -> Optional[int]:
        """Validate quantity is positive."""
        if v is not None and v <= 0:
            raise ValueError("Quantity must be greater than 0")
        return v


class OrderItemInDB(BaseModel): 
    """Model for Order Item as stored in database."""

    order_id: UUID = Field(..., description="Order ID")
    product_id: int = Field(..., description="Product ID")
    quantity: int = Field(..., description="Quantity of product")

    class Config:
        from_attributes = True


class OrderItemResponse(BaseModel):
    """Model for Order Item API response."""

    product_id: int = Field(..., description="Product ID")
    quantity: int = Field(..., description="Quantity of product")

    class Config:
        from_attributes = True


class OrderItemDetailResponse(BaseModel):
    """Model for Order Item with product details."""

    product_id: int = Field(..., description="Product ID")
    product_name: str = Field(..., description="Product name")
    product_code: str = Field(..., description="Product code")
    quantity: int = Field(..., description="Quantity of product")

    class Config:
        from_attributes = True


# Order Models
class OrderCreate(BaseModel):
    """Model for creating a new order. Amounts are calculated based on items."""

    retailer_id: UUID = Field(..., description="Retailer ID")
    member_id: UUID = Field(..., description="Member ID")
    order_type: OrderType = Field(..., description="Type of order")
    order_status: OrderStatus = Field(
        default=OrderStatus.DRAFT, description="Status of order"
    )
    items: List[OrderItemCreate] = Field(
        ..., min_length=1, description="List of order items"
    )

    @model_validator(mode="after")
    def validate_order_items(self):
        """Validate order has at least one item."""
        if len(self.items) == 0:
            raise ValueError("Order must have at least one item")
        return self


class OrderItemUpdate(BaseModel):
    """Model for updating an existing order.
    
    Only items can be updated. If a product already exists in the order,
    its quantity will be updated. If it doesn't exist, it will be added.
    Amounts are automatically recalculated based on items.
    """

    items: List[OrderItemCreate] = Field(
        ..., min_length=1, description="List of order items to upsert"
    )

    @model_validator(mode="after")
    def validate_items(self):
        """Validate items are provided and not empty."""
        if len(self.items) == 0:
            raise ValueError("Order must have at least one item")
        # Check for duplicate products
        product_ids = [item.product_id for item in self.items]
        if len(product_ids) != len(set(product_ids)):
            raise ValueError("Order cannot have duplicate products in update")
        return self

class OrderUpdate(BaseModel):
    "Model for updating order"
    order_status: Optional[OrderStatus] = Field(
        None, description="Status of order"
    )
    order_type: Optional[OrderType] = Field(
        None, description="Type of order"
    )
    base_amount: Optional[Decimal] = Field(
        None, description="Base amount before discount"
    )
    discount_amount: Optional[Decimal] = Field(
        None, description="Total discount amount"
    )
    net_amount: Optional[Decimal] = Field(
        None, description="Net amount after discount"
    )
    igst_amount: Optional[Decimal] = Field(
        None, description="IGST amount"
    )
    cgst_amount: Optional[Decimal] = Field(
        None, description="CGST amount"
    )
    sgst_amount: Optional[Decimal] = Field(
        None, description="SGST amount"
    )
    total_amount: Optional[Decimal] = Field(
        None, description="Total amount including taxes"
    )

class OrderInDB(BaseModel):
    """Model for Order as stored in database."""

    id: UUID = Field(..., description="Order ID")
    retailer_id: UUID = Field(..., description="Retailer ID")
    member_id: UUID = Field(..., description="Member ID")
    base_amount: Decimal = Field(..., description="Base amount before discount")
    discount_amount: Decimal = Field(..., description="Total discount amount")
    net_amount: Decimal = Field(..., description="Net amount after discount")
    igst_amount: Decimal = Field(..., description="IGST amount")
    cgst_amount: Decimal = Field(..., description="CGST amount")
    sgst_amount: Decimal = Field(..., description="SGST amount")
    total_amount: Decimal = Field(..., description="Total amount including taxes")
    order_type: str = Field(..., description="Type of order")
    order_status: str = Field(..., description="Status of order")
    is_active: bool = Field(..., description="Whether the order is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class OrderResponse(BaseModel):
    """Model for Order API response."""

    id: UUID = Field(..., description="Order ID")
    retailer_id: UUID = Field(..., description="Retailer ID")
    member_id: UUID = Field(..., description="Member ID")
    base_amount: Decimal = Field(..., description="Base amount before discount")
    discount_amount: Decimal = Field(..., description="Total discount amount")
    net_amount: Decimal = Field(..., description="Net amount after discount")
    igst_amount: Decimal = Field(..., description="IGST amount")
    cgst_amount: Decimal = Field(..., description="CGST amount")
    sgst_amount: Decimal = Field(..., description="SGST amount")
    total_amount: Decimal = Field(..., description="Total amount including taxes")
    order_type: OrderType = Field(..., description="Type of order")
    order_status: OrderStatus = Field(..., description="Status of order")
    is_active: bool = Field(..., description="Whether the order is active")
    items: List[OrderItemResponse] = Field(..., description="List of order items")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class OrderListItem(BaseModel):
    """Minimal model for Order in list views to optimize performance."""

    id: UUID = Field(..., description="Order ID")
    retailer_id: UUID = Field(..., description="Retailer ID")
    retailer_name: str = Field(..., description="Retailer name")
    member_id: UUID = Field(..., description="Member ID")
    member_name: str = Field(..., description="Member name")
    total_amount: Decimal = Field(..., description="Total amount including taxes")
    order_type: OrderType = Field(..., description="Type of order")
    order_status: OrderStatus = Field(..., description="Status of order")
    is_active: bool = Field(..., description="Whether the order is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class OrderDetailResponse(BaseModel):
    """Detailed model for Order with joined data."""

    id: UUID = Field(..., description="Order ID")
    retailer_id: UUID = Field(..., description="Retailer ID")
    retailer_name: str = Field(..., description="Retailer name")
    retailer_code: str = Field(..., description="Retailer code")
    retailer_mobile: str = Field(..., description="Retailer mobile number")
    member_id: UUID = Field(..., description="Member ID")
    member_name: str = Field(..., description="Member name")
    base_amount: Decimal = Field(..., description="Base amount before discount")
    discount_amount: Decimal = Field(..., description="Total discount amount")
    net_amount: Decimal = Field(..., description="Net amount after discount")
    igst_amount: Decimal = Field(..., description="IGST amount")
    cgst_amount: Decimal = Field(..., description="CGST amount")
    sgst_amount: Decimal = Field(..., description="SGST amount")
    total_amount: Decimal = Field(..., description="Total amount including taxes")
    order_type: OrderType = Field(..., description="Type of order")
    order_status: OrderStatus = Field(..., description="Status of order")
    is_active: bool = Field(..., description="Whether the order is active")
    items: List[OrderItemDetailResponse] = Field(
        ..., description="List of order items with product details"
    )
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True
        ignore_extra = True

