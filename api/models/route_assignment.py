"""
Pydantic models for RouteAssignment entity.
"""

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_core import PydanticCustomError


class RouteAssignmentCreate(BaseModel):
    """Model for creating a new route assignment."""

    route_id: int = Field(..., gt=0, description="Route ID")
    user_id: UUID = Field(..., description="User ID")
    from_date: date = Field(..., description="Assignment start date")
    to_date: Optional[date] = Field(None, description="Assignment end date")
    day: int = Field(..., ge=0, le=6, description="Day of week (0=Monday, 6=Sunday)")
    is_active: bool = Field(default=True, description="Whether the assignment is active")

    @field_validator("route_id")
    @classmethod
    def validate_route_id(cls, v: int) -> int:
        """Validate route_id is positive."""
        if v <= 0:
            raise PydanticCustomError(
                "invalid_route_id",
                "Route ID must be a positive integer",
            )
        return v

    @field_validator("day")
    @classmethod
    def validate_day(cls, v: int) -> int:
        """Validate day is between 0 and 6."""
        if v < 0 or v > 6:
            raise PydanticCustomError(
                "invalid_day",
                "Day must be between 0 (Monday) and 6 (Sunday)",
            )
        return v

    @model_validator(mode="after")
    def validate_date_range(self) -> "RouteAssignmentCreate":
        """Validate that to_date is greater than or equal to from_date."""
        if self.to_date is not None and self.to_date < self.from_date:
            raise PydanticCustomError(
                "invalid_date_range",
                "End date must be greater than or equal to start date",
            )
        return self


class RouteAssignmentUpdate(BaseModel):
    """Model for updating an existing route assignment."""

    from_date: Optional[date] = Field(None, description="Assignment start date")
    to_date: Optional[date] = Field(None, description="Assignment end date")
    day: Optional[int] = Field(None, ge=0, le=6, description="Day of week (0=Monday, 6=Sunday)")

    @field_validator("day")
    @classmethod
    def validate_day(cls, v: Optional[int]) -> Optional[int]:
        """Validate day is between 0 and 6 if provided."""
        if v is not None and (v < 0 or v > 6):
            raise PydanticCustomError(
                "invalid_day",
                "Day must be between 0 (Monday) and 6 (Sunday)",
            )
        return v


class RouteAssignmentInDB(BaseModel):
    """Model for RouteAssignment as stored in database."""

    id: int = Field(..., description="Route assignment ID")
    route_id: int = Field(..., description="Route ID")
    user_id: UUID = Field(..., description="User ID")
    from_date: date = Field(..., description="Assignment start date")
    to_date: Optional[date] = Field(None, description="Assignment end date")
    day: int = Field(..., description="Day of week (0=Monday, 6=Sunday)")
    is_active: bool = Field(..., description="Whether the assignment is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class RouteAssignmentResponse(BaseModel):
    """Model for RouteAssignment API response."""

    id: int = Field(..., description="Route assignment ID")
    route_id: int = Field(..., description="Route ID")
    user_id: UUID = Field(..., description="User ID")
    from_date: date = Field(..., description="Assignment start date")
    to_date: Optional[date] = Field(None, description="Assignment end date")
    day: int = Field(..., description="Day of week (0=Monday, 6=Sunday)")
    is_active: bool = Field(..., description="Whether the assignment is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class RouteAssignmentListItem(BaseModel):
    """Minimal model for RouteAssignment in list views to optimize performance."""

    id: int = Field(..., description="Route assignment ID")
    route_id: int = Field(..., description="Route ID")
    route_name: str = Field(..., description="Route name")
    route_code: str = Field(..., description="Route code")
    user_id: UUID = Field(..., description="User ID")
    user_name: str = Field(..., description="User name")
    from_date: date = Field(..., description="Assignment start date")
    to_date: Optional[date] = Field(None, description="Assignment end date")
    day: int = Field(..., description="Day of week (0=Monday, 6=Sunday)")
    is_active: bool = Field(..., description="Whether the assignment is active")

    class Config:
        from_attributes = True


class RouteAssignmentDetailItem(BaseModel):
    """Model for RouteAssignment detail view."""

    id: int = Field(..., description="Route assignment ID")
    route_id: int = Field(..., description="Route ID")
    route_name: str = Field(..., description="Route name")
    route_code: str = Field(..., description="Route code")
    user_id: UUID = Field(..., description="User ID")
    user_name: str = Field(..., description="User name")
    user_username: str = Field(..., description="User username")
    from_date: date = Field(..., description="Assignment start date")
    to_date: Optional[date] = Field(None, description="Assignment end date")
    day: int = Field(..., description="Day of week (0=Monday, 6=Sunday)")
    is_active: bool = Field(..., description="Whether the assignment is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True

