"""
Pydantic models for Route entity.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_core import PydanticCustomError


class RouteCreate(BaseModel):
    """Model for creating a new route."""

    name: str = Field(..., min_length=1, max_length=32, description="Route name")
    code: str = Field(..., min_length=1, max_length=32, description="Route code")
    area_id: int = Field(..., gt=0, description="Area ID")
    is_general: bool = Field(default=False, description="Whether the route is general")
    is_modern: bool = Field(default=False, description="Whether the route is modern")
    is_horeca: bool = Field(default=False, description="Whether the route is horeca")
    is_active: bool = Field(default=True, description="Whether the route is active")

    @field_validator("name", "code")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        """Validate and normalize string fields."""
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()
    @field_validator("area_id")
    @classmethod
    def validate_area_id(cls, v: int) -> int:
        """Validate area_id is positive."""
        if v <= 0:
            raise PydanticCustomError(
                "invalid_area_id",
                "Area ID must be a positive integer",
            )
        return v

    @model_validator(mode="after")
    def validate_trade_types(self) -> "RouteCreate":
        """Validate that any one trade type is selected."""
        if sum([self.is_general, self.is_modern, self.is_horeca]) != 1:
            raise PydanticCustomError(
                "trade_type",
                "Any one trade type (general, modern, or horeca) must be selected",
            )
        return self


class RouteUpdate(BaseModel):
    """Model for updating an existing route."""

    name: Optional[str] = Field(None, min_length=1, max_length=32, description="Route name")
    area_id: Optional[int] = Field(None, gt=0, description="Area ID")
    is_general: Optional[bool] = Field(None, description="Whether the route is general")
    is_modern: Optional[bool] = Field(None, description="Whether the route is modern")
    is_horeca: Optional[bool] = Field(None, description="Whether the route is horeca")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate and normalize name."""
        if v is not None and (not v or not v.strip()):
            raise ValueError("Name cannot be empty")
        return v.strip() if v else None

    @field_validator("area_id")
    @classmethod
    def validate_area_id(cls, v: Optional[int]) -> Optional[int]:
        """Validate area_id is positive if provided."""
        if v is not None and v <= 0:
            raise PydanticCustomError(
                "invalid_area_id",
                "Area ID must be a positive integer",
            )
        return v
    @model_validator(mode="after")
    def validate_trade_types(self) -> "RouteUpdate":
        """Validate that at least one trade type is selected if any are being updated."""
        trade_types_updated = [
            self.is_general,
            self.is_modern,
            self.is_horeca,
        ]

        # If any trade type is being updated
        if any(t is not None for t in trade_types_updated):
            # Check if at least one will be True
            if sum(trade_types_updated) != 1:
                raise PydanticCustomError(
                    "trade_type",
                    "Any one trade type (general, modern, or horeca) must be selected",
                )

        return self



class RouteInDB(BaseModel):
    """Model for Route as stored in database."""

    id: int = Field(..., description="Route ID")
    name: str = Field(..., description="Route name")
    code: str = Field(..., description="Route code")
    area_id: int = Field(..., description="Area ID")
    is_general: bool = Field(..., description="Whether the route is general")
    is_modern: bool = Field(..., description="Whether the route is modern")
    is_horeca: bool = Field(..., description="Whether the route is horeca")
    is_active: bool = Field(..., description="Whether the route is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class RouteResponse(BaseModel):
    """Model for Route API response."""

    id: int = Field(..., description="Route ID")
    name: str = Field(..., description="Route name")
    code: str = Field(..., description="Route code")
    area_id: int = Field(..., description="Area ID")
    is_general: bool = Field(..., description="Whether the route is general")
    is_modern: bool = Field(..., description="Whether the route is modern")
    is_horeca: bool = Field(..., description="Whether the route is horeca")
    is_active: bool = Field(..., description="Whether the route is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class RouteListItem(BaseModel):
    """Minimal model for Route in list views to optimize performance."""

    id: int = Field(..., description="Route ID")
    name: str = Field(..., description="Route name")
    code: str = Field(..., description="Route code")
    area_id: int = Field(..., description="Area ID")
    division_name: str = Field(..., description="Division name")
    area_name: str = Field(..., description="Area name")
    region_name: str = Field(..., description="Region name")
    is_general: bool = Field(..., description="Whether the route is general")
    is_modern: bool = Field(..., description="Whether the route is modern")
    is_horeca: bool = Field(..., description="Whether the route is horeca")
    is_active: bool = Field(..., description="Whether the route is active")


    class Config:
        from_attributes = True


class RouteDetailItem(BaseModel):
    """Model for Route detail view."""

    id: int = Field(..., description="Route ID")
    name: str = Field(..., description="Route name")
    code: str = Field(..., description="Route code")
    area_id: int = Field(..., description="Area ID")
    division_name: str = Field(..., description="Division name")
    area_name: str = Field(..., description="Area name")
    region_name: str = Field(..., description="Region name")
    zone_name: str = Field(..., description="Zone name")
    nation_name: str = Field(..., description="Nation name")
    is_general: bool = Field(..., description="Whether the route is general")
    is_modern: bool = Field(..., description="Whether the route is modern")
    is_horeca: bool = Field(..., description="Whether the route is horeca")
    is_active: bool = Field(..., description="Whether the route is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True