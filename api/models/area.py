"""
Area models for database and API operations.

This module contains Pydantic models for area data validation,
including database representations, API requests, and responses.
"""

from datetime import datetime
from enum import StrEnum
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_core import PydanticCustomError


class AreaType(StrEnum):
    """Enum for area types in the hierarchy."""

    DIVISION = "DIVISION"
    AREA = "AREA"
    REGION = "REGION"
    ZONE = "ZONE"
    NATION = "NATION"


class AreaInDB(BaseModel):
    """Area model representing database record."""

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


# Request Models


class CreateAreaRequest(BaseModel):
    """Request model for creating a new area."""

    company_id: UUID = Field(..., description="UUID of the company")
    name: str = Field(..., min_length=1, max_length=100, description="Name of the area")
    type: AreaType = Field(
        ..., description="Type of the area (DIVISION, AREA, REGION, ZONE, NATION)"
    )
    area_id: Optional[int] = Field(None, description="Parent area ID (for DIVISION)")
    region_id: Optional[int] = Field(None, description="Parent region ID (for AREA)")
    zone_id: Optional[int] = Field(None, description="Parent zone ID (for REGION)")
    nation_id: Optional[int] = Field(None, description="Parent nation ID (for ZONE)")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate and clean area name."""
        if not v or not v.strip():
            raise PydanticCustomError(
                "invalid_name",
                "Area name cannot be empty or whitespace",
            )
        return v.strip()

    @field_validator("area_id", "region_id", "zone_id", "nation_id")
    @classmethod
    def validate_parent_ids(cls, v: Optional[int]) -> Optional[int]:
        """Validate parent IDs are positive if provided."""
        if v is not None and v <= 0:
            raise PydanticCustomError(
                "invalid_parent_id",
                "Parent ID must be a positive integer",
            )
        return v

    @model_validator(mode="after")
    def validate_hierarchy(self) -> "CreateAreaRequest":
        """Validate hierarchy constraints based on area type."""
        area_type = self.type

        if area_type == AreaType.DIVISION:
            # Division must have an area_id
            if self.area_id is None:
                raise PydanticCustomError(
                    "missing_parent",
                    "Division must have a parent area",
                )
            if (
                self.region_id is not None
                or self.zone_id is not None
                or self.nation_id is not None
            ):
                raise PydanticCustomError(
                    "invalid_hierarchy",
                    "Division can only have area_id as parent",
                )

        elif area_type == AreaType.AREA:
            # Area must have a region_id
            if self.region_id is None:
                raise PydanticCustomError(
                    "missing_parent",
                    "Area must have a parent region",
                )
            if (
                self.area_id is not None
                or self.zone_id is not None
                or self.nation_id is not None
            ):
                raise PydanticCustomError(
                    "invalid_hierarchy",
                    "Area can only have region_id as parent",
                )

        elif area_type == AreaType.REGION:
            # Region must have a zone_id
            if self.zone_id is None:
                raise PydanticCustomError(
                    "missing_parent",
                    "Region must have a parent zone",
                )
            if (
                self.area_id is not None
                or self.region_id is not None
                or self.nation_id is not None
            ):
                raise PydanticCustomError(
                    "invalid_hierarchy",
                    "Region can only have zone_id as parent",
                )

        elif area_type == AreaType.ZONE:
            # Zone must have a nation_id
            if self.nation_id is None:
                raise PydanticCustomError(
                    "missing_parent",
                    "Zone must have a parent nation",
                )
            if (
                self.area_id is not None
                or self.region_id is not None
                or self.zone_id is not None
            ):
                raise PydanticCustomError(
                    "invalid_hierarchy",
                    "Zone can only have nation_id as parent",
                )

        elif area_type == AreaType.NATION:
            # Nation is top level, should not have any parents
            if (
                self.area_id is not None
                or self.region_id is not None
                or self.zone_id is not None
                or self.nation_id is not None
            ):
                raise PydanticCustomError(
                    "invalid_hierarchy",
                    "Nation cannot have any parent",
                )

        return self


class UpdateAreaRequest(BaseModel):
    """Request model for updating an area."""

    name: Optional[str] = Field(
        None, min_length=1, max_length=100, description="New name"
    )
    type: Optional[AreaType] = Field(None, description="New type")
    area_id: Optional[int] = Field(None, description="New parent area ID")
    region_id: Optional[int] = Field(None, description="New parent region ID")
    zone_id: Optional[int] = Field(None, description="New parent zone ID")
    nation_id: Optional[int] = Field(None, description="New parent nation ID")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate and clean area name."""
        if v is not None:
            if not v.strip():
                raise PydanticCustomError(
                    "invalid_name",
                    "Area name cannot be empty or whitespace",
                )
            return v.strip()
        return v

    @field_validator("area_id", "region_id", "zone_id", "nation_id")
    @classmethod
    def validate_parent_ids(cls, v: Optional[int]) -> Optional[int]:
        """Validate parent IDs are positive if provided."""
        if v is not None and v <= 0:
            raise PydanticCustomError(
                "invalid_parent_id",
                "Parent ID must be a positive integer",
            )
        return v

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
    def validate_has_updates(self) -> "UpdateAreaRequest":
        """Validate that at least one field is provided for update."""
        if not self.has_updates():
            raise PydanticCustomError(
                "no_updates",
                "At least one field must be provided for update",
            )
        return self

    def has_updates(self) -> bool:
        """Check if at least one field is provided for update."""
        return any(
            [
                self.name is not None,
                self.type is not None,
                self.area_id is not None,
                self.region_id is not None,
                self.zone_id is not None,
                self.nation_id is not None,
            ]
        )

    @model_validator(mode="after")
    def validate_hierarchy(self) -> "UpdateAreaRequest":
        area_type = self.type
        if area_type is None:
            if (
                self.area_id is not None
                or self.region_id is not None
                or self.zone_id is not None
                or self.nation_id is not None
            ):
                raise PydanticCustomError(
                    "missing_type",
                    "Area type must be provided when updating parent IDs",
                )
            return self

        if area_type == AreaType.DIVISION:
            # Division must have an area_id
            if self.area_id is None:
                raise PydanticCustomError(
                    "missing_parent",
                    "Division must have a parent area",
                )
            if (
                self.region_id is not None
                or self.zone_id is not None
                or self.nation_id is not None
            ):
                raise PydanticCustomError(
                    "invalid_hierarchy",
                    "Division can only have area_id as parent",
                )

        elif area_type == AreaType.AREA:
            # Area must have a region_id
            if self.region_id is None:
                raise PydanticCustomError(
                    "missing_parent",
                    "Area must have a parent region",
                )
            if (
                self.area_id is not None
                or self.zone_id is not None
                or self.nation_id is not None
            ):
                raise PydanticCustomError(
                    "invalid_hierarchy",
                    "Area can only have region_id as parent",
                )

        elif area_type == AreaType.REGION:
            # Region must have a zone_id
            if self.zone_id is None:
                raise PydanticCustomError(
                    "missing_parent",
                    "Region must have a parent zone",
                )
            if (
                self.area_id is not None
                or self.region_id is not None
                or self.nation_id is not None
            ):
                raise PydanticCustomError(
                    "invalid_hierarchy",
                    "Region can only have zone_id as parent",
                )

        elif area_type == AreaType.ZONE:
            # Zone must have a nation_id
            if self.nation_id is None:
                raise PydanticCustomError(
                    "missing_parent",
                    "Zone must have a parent nation",
                )
            if (
                self.area_id is not None
                or self.region_id is not None
                or self.zone_id is not None
            ):
                raise PydanticCustomError(
                    "invalid_hierarchy",
                    "Zone can only have nation_id as parent",
                )

        elif area_type == AreaType.NATION:
            # Nation is top level, should not have any parents
            if (
                self.area_id is not None
                or self.region_id is not None
                or self.zone_id is not None
                or self.nation_id is not None
            ):
                raise PydanticCustomError(
                    "invalid_hierarchy",
                    "Nation cannot have any parent",
                )

        return self


class GetAreasRelatedRequest(BaseModel):
    """Request model for getting areas related to another area."""

    company_id: UUID = Field(..., description="UUID of the company")
    area_id: int = Field(..., gt=0, description="ID of the reference area")
    area_type: AreaType = Field(..., description="Type of the reference area")
    required_type: Optional[AreaType] = Field(
        None, description="Type to filter related areas"
    )

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


# Response Models


class AreaResponse(BaseModel):
    """Response model for a single area."""

    id: int = Field(..., description="Area ID")
    name: str = Field(..., description="Name of the area")
    type: str = Field(..., description="Type of the area")
    area_id: Optional[int] = Field(None, description="Parent area ID")
    region_id: Optional[int] = Field(None, description="Parent region ID")
    zone_id: Optional[int] = Field(None, description="Parent zone ID")
    nation_id: Optional[int] = Field(None, description="Parent nation ID")
    is_active: bool = Field(..., description="Whether the area is active")
    created_at: datetime = Field(..., description="Timestamp when area was created")
    updated_at: datetime = Field(
        ..., description="Timestamp when area was last updated"
    )