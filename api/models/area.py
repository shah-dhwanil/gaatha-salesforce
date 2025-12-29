"""
Pydantic models for Area entity.

Area represents the hierarchical structure: NATION > ZONE > REGION > AREA > DIVISION
"""

from datetime import datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_core import PydanticCustomError

class AreaType(str, Enum):
    """Enum for area types in the hierarchy."""

    DIVISION = "DIVISION"
    AREA = "AREA"
    REGION = "REGION"
    ZONE = "ZONE"
    NATION = "NATION"


class AreaCreate(BaseModel):
    """Model for creating a new area."""

    name: str = Field(..., min_length=1, max_length=64, description="Area name")
    type: Literal["NATION", "ZONE", "REGION", "AREA", "DIVISION"] = Field(
        ..., description="Area type in hierarchy"
    )
    area_id: Optional[int] = Field(
        None, description="Parent area ID (for DIVISION level)"
    )
    region_id: Optional[int] = Field(
        None, description="Parent region ID (for AREA level)"
    )
    zone_id: Optional[int] = Field(None, description="Parent zone ID (for REGION level)")
    nation_id: Optional[int] = Field(
        None, description="Parent nation ID (for ZONE level)"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate and normalize area name."""
        if not v or not v.strip():
            raise ValueError("Area name cannot be empty")
        return v.strip()

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate and normalize area type."""
        return v.upper()

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
    def validate_hierarchy(self) -> "AreaCreate":
        """Validate hierarchy constraints based on area type."""
        area_type = self.type

        if area_type == AreaType.DIVISION.value:
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

        elif area_type == AreaType.AREA.value:
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

        elif area_type == AreaType.REGION.value:
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

        elif area_type == AreaType.ZONE.value:
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

        elif area_type == AreaType.NATION.value:
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

class AreaUpdate(BaseModel):
    """Model for updating an existing area."""

    name: Optional[str] = Field(None, min_length=1, max_length=64)
    type: Optional[Literal["NATION", "ZONE", "REGION", "AREA", "DIVISION"]] = None
    area_id: Optional[int] = None
    region_id: Optional[int] = None
    zone_id: Optional[int] = None
    nation_id: Optional[int] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate and normalize area name."""
        if v is not None:
            if not v.strip():
                raise ValueError("Area name cannot be empty")
            return v.strip()
        return v

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: Optional[str]) -> Optional[str]:
        """Validate and normalize area type."""
        if v is not None:
            return v.upper()
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
    @model_validator(mode="after")
    def validate_hierarchy(self) -> "AreaUpdate":
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

        if area_type == AreaType.DIVISION.value:
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

        elif area_type == AreaType.AREA.value:
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

        elif area_type == AreaType.REGION.value:
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

        elif area_type == AreaType.ZONE.value:
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

        elif area_type == AreaType.NATION.value :
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



class AreaInDB(BaseModel):
    """Model for Area as stored in database."""

    id: int = Field(..., description="Area unique identifier")
    name: str = Field(..., description="Area name")
    type: str = Field(..., description="Area type (NATION, ZONE, REGION, AREA, DIVISION)")
    area_id: Optional[int] = Field(None, description="Parent area ID")
    region_id: Optional[int] = Field(None, description="Parent region ID")
    zone_id: Optional[int] = Field(None, description="Parent zone ID")
    nation_id: Optional[int] = Field(None, description="Parent nation ID")
    is_active: bool = Field(..., description="Whether the area is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class AreaResponse(BaseModel):
    """Model for Area API response."""

    id: int = Field(..., description="Area unique identifier")
    name: str = Field(..., description="Area name")
    type: str = Field(..., description="Area type (NATION, ZONE, REGION, AREA, DIVISION)")
    area_id: Optional[int] = Field(None, description="Parent area ID")
    region_id: Optional[int] = Field(None, description="Parent region ID")
    zone_id: Optional[int] = Field(None, description="Parent zone ID")
    nation_id: Optional[int] = Field(None, description="Parent nation ID")
    is_active: bool = Field(..., description="Whether the area is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class AreaListItem(BaseModel):
    """Minimal model for Area in list views to optimize performance."""

    id: int = Field(..., description="Area unique identifier")
    name: str = Field(..., description="Area name")
    type: str = Field(..., description="Area type")
    is_active: bool = Field(..., description="Whether the area is active")

    class Config:
        from_attributes = True


class AreaHierarchyResponse(BaseModel):
    """Model for Area with hierarchy information."""

    id: int = Field(..., description="Area unique identifier")
    name: str = Field(..., description="Area name")
    type: str = Field(..., description="Area type")
    area_id: Optional[int] = Field(None, description="Parent area ID")
    region_id: Optional[int] = Field(None, description="Parent region ID")
    zone_id: Optional[int] = Field(None, description="Parent zone ID")
    nation_id: Optional[int] = Field(None, description="Parent nation ID")
    is_active: bool = Field(..., description="Whether the area is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    children: list["AreaHierarchyResponse"] = Field(
        default_factory=list, description="Child areas"
    )

    class Config:
        from_attributes = True

