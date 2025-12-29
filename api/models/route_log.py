"""
Pydantic models for RouteLog entity.
"""

from datetime import date as Date, datetime, time
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_core import PydanticCustomError


class RouteLogCreate(BaseModel):
    """Model for creating a new route log."""

    route_assignment_id: int = Field(..., gt=0, description="Route assignment ID")
    co_worker_id: Optional[UUID] = Field(None, description="Co-worker member ID")
    date: Date = Field(..., description="Date of the route log")
    start_time: time = Field(..., description="Start time of the route")
    end_time: Optional[time] = Field(None, description="End time of the route")

    @field_validator("route_assignment_id")
    @classmethod
    def validate_route_assignment_id(cls, v: int) -> int:
        """Validate route_assignment_id is positive."""
        if v <= 0:
            raise PydanticCustomError(
                "invalid_route_assignment_id",
                "Route assignment ID must be a positive integer",
            )
        return v

    @model_validator(mode="after")
    def validate_time_range(self) -> "RouteLogCreate":
        """Validate that end_time is after start_time."""
        if self.end_time is not None and self.end_time <= self.start_time:
            raise PydanticCustomError(
                "invalid_time_range",
                "End time must be after start time",
            )
        return self


class RouteLogUpdate(BaseModel):
    """Model for updating an existing route log."""

    co_worker_id: Optional[UUID] = Field(None, description="Co-worker member ID")
    date: Optional[Date] = Field(None, description="Date of the route log")
    start_time: Optional[time] = Field(None, description="Start time of the route")
    end_time: Optional[time] = Field(None, description="End time of the route")

    @model_validator(mode="after")
    def validate_time_range(self) -> "RouteLogUpdate":
        """Validate that end_time is after start_time if both are provided."""
        if self.start_time is not None and self.end_time is not None:
            if self.end_time <= self.start_time:
                raise PydanticCustomError(
                    "invalid_time_range",
                    "End time must be after start time",
                )
        return self


class RouteLogInDB(BaseModel):
    """Model for RouteLog as stored in database."""

    id: int = Field(..., description="Route log ID")
    route_assignment_id: int = Field(..., description="Route assignment ID")
    co_worker_id: Optional[UUID] = Field(None, description="Co-worker member ID")
    date: Date = Field(..., description="Date of the route log")
    start_time: time = Field(..., description="Start time of the route")
    end_time: Optional[time] = Field(None, description="End time of the route")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class RouteLogResponse(BaseModel):
    """Model for RouteLog API response."""

    id: int = Field(..., description="Route log ID")
    route_assignment_id: int = Field(..., description="Route assignment ID")
    co_worker_id: Optional[UUID] = Field(None, description="Co-worker member ID")
    date: Date = Field(..., description="Date of the route log")
    start_time: time = Field(..., description="Start time of the route")
    end_time: Optional[time] = Field(None, description="End time of the route")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class RouteLogListItem(BaseModel):
    """Minimal model for RouteLog in list views to optimize performance."""

    id: int = Field(..., description="Route log ID")
    route_assignment_id: int = Field(..., description="Route assignment ID")
    co_worker_id: Optional[UUID] = Field(None, description="Co-worker member ID")
    date: Date = Field(..., description="Date of the route log")
    start_time: time = Field(..., description="Start time of the route")
    end_time: Optional[time] = Field(None, description="End time of the route")

    class Config:
        from_attributes = True

