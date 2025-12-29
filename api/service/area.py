"""
Service layer for Area entity operations.

This service provides business logic for hierarchical areas (NATION, ZONE, REGION, AREA, DIVISION),
acting as an intermediary between the API layer and the repository layer.
"""

from typing import Optional
from uuid import UUID

import structlog

from api.database import DatabasePool
from api.exceptions.area import (
    AreaAlreadyExistsException,
    AreaInvalidHierarchyException,
    AreaNotFoundException,
    AreaOperationException,
)
from api.models.area import (
    AreaCreate,
    AreaInDB,
    AreaListItem,
    AreaResponse,
    AreaType,
    AreaUpdate,
)
from api.repository.area import AreaRepository

logger = structlog.get_logger(__name__)


class AreaService:
    """
    Service for managing Area business logic.

    This service handles business logic, validation, and orchestration
    for hierarchical area operations in a multi-tenant environment.
    """

    def __init__(self, db_pool: DatabasePool, company_id: UUID) -> None:
        """
        Initialize the AreaService.

        Args:
            db_pool: Database pool instance for connection management
            company_id: UUID of the company (tenant) for schema isolation
        """
        self.db_pool = db_pool
        self.company_id = company_id
        self.repository = AreaRepository(db_pool, company_id)
        logger.debug(
            "AreaService initialized",
            company_id=str(company_id),
        )

    async def create_area(self, area_data: AreaCreate) -> AreaResponse:
        """
        Create a new area.

        Args:
            area_data: Area data to create

        Returns:
            Created area

        Raises:
            AreaAlreadyExistsException: If area with the same name and type already exists
            AreaNotFoundException: If parent area doesn't exist
            AreaInvalidHierarchyException: If hierarchy validation fails
            AreaOperationException: If creation fails
        """
        try:
            logger.info(
                "Creating area",
                area_name=area_data.name,
                area_type=area_data.type,
                company_id=str(self.company_id),
            )
            # Fetch data of it parent and set to the model
            if area_data.type == AreaType.DIVISION.value:
                parent_area = await self.repository.get_area_by_id(area_data.area_id)
                if parent_area.type != AreaType.AREA.value:
                    raise AreaInvalidHierarchyException(
                        message="Division's parent area must be of type AREA",
                    )
                area_data.region_id = parent_area.region_id
                area_data.zone_id = parent_area.zone_id
                area_data.nation_id = parent_area.nation_id
            elif area_data.type == AreaType.AREA.value:
                parent_area = await self.repository.get_area_by_id(area_data.region_id)
                if parent_area.type != AreaType.REGION.value:
                    raise AreaInvalidHierarchyException(
                        message="Area's parent region must be of type REGION",
                    )
                area_data.area_id = None
                area_data.zone_id = parent_area.zone_id
                area_data.nation_id = parent_area.nation_id
            elif area_data.type == AreaType.REGION.value:
                parent_area = await self.repository.get_area_by_id(area_data.zone_id)
                if parent_area.type != AreaType.ZONE.value:
                    raise AreaInvalidHierarchyException(
                        message="Region's parent zone must be of type ZONE",
                    )
                area_data.area_id = None
                area_data.region_id = None
                area_data.nation_id = parent_area.nation_id
            elif area_data.type == AreaType.ZONE.value:
                parent_area = await self.repository.get_area_by_id(area_data.nation_id)
                if parent_area.type != AreaType.NATION.value:
                    raise AreaInvalidHierarchyException(
                        message="Zone's parent nation must be of type NATION",
                    )
                area_data.area_id = None
                area_data.region_id = None
                area_data.zone_id = None
            elif area_data.type == AreaType.NATION.value:
                area_data.area_id = None
                area_data.region_id = None
                area_data.zone_id = None
                area_data.nation_id = None
            else:
                raise AreaInvalidHierarchyException(
                    message="Invalid area type",
                )

            # Create area using repository
            area = await self.repository.create_area(area_data)

            logger.info(
                "Area created successfully",
                area_id=area.id,
                area_name=area.name,
                area_type=area.type,
                company_id=str(self.company_id),
            )

            return AreaResponse(**area.model_dump())

        except (
            AreaAlreadyExistsException,
            AreaNotFoundException,
            AreaInvalidHierarchyException,
        ):
            raise
        except Exception as e:
            logger.error(
                "Failed to create area in service",
                area_name=area_data.name,
                area_type=area_data.type,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def get_area_by_id(self, area_id: int) -> AreaResponse:
        """
        Get an area by ID.

        Args:
            area_id: ID of the area

        Returns:
            Area

        Raises:
            AreaNotFoundException: If area not found
            AreaOperationException: If retrieval fails
        """
        try:
            logger.debug(
                "Getting area by ID",
                area_id=area_id,
                company_id=str(self.company_id),
            )

            area = await self.repository.get_area_by_id(area_id)

            return AreaResponse(**area.model_dump())

        except AreaNotFoundException:
            logger.warning(
                "Area not found",
                area_id=area_id,
                company_id=str(self.company_id),
            )
            raise
        except Exception as e:
            logger.error(
                "Failed to get area in service",
                area_id=area_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def get_area_by_name_and_type(
        self, name: str, area_type: str
    ) -> AreaResponse:
        """
        Get an area by name and type.

        Args:
            name: Name of the area
            area_type: Type of the area (NATION, ZONE, REGION, AREA, DIVISION)

        Returns:
            Area

        Raises:
            AreaNotFoundException: If area not found
            AreaOperationException: If retrieval fails
        """
        try:
            logger.debug(
                "Getting area by name and type",
                area_name=name,
                area_type=area_type,
                company_id=str(self.company_id),
            )

            area = await self.repository.get_area_by_name_and_type(name, area_type)

            return AreaResponse(**area.model_dump())

        except AreaNotFoundException:
            logger.warning(
                "Area not found",
                area_name=name,
                area_type=area_type,
                company_id=str(self.company_id),
            )
            raise
        except Exception as e:
            logger.error(
                "Failed to get area in service",
                area_name=name,
                area_type=area_type,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def list_areas(
        self,
        area_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        parent_id: Optional[int] = None,
        parent_type: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[AreaListItem], int]:
        """
        List all areas with optional filtering and return total count.

        Args:
            area_type: Filter by area type (NATION, ZONE, REGION, AREA, DIVISION)
            is_active: Filter by active status
            parent_id: Filter by parent area ID
            parent_type: Filter by parent type (nation, zone, region, area)
            limit: Maximum number of areas to return (default: 20, max: 100)
            offset: Number of areas to skip (default: 0)

        Returns:
            Tuple of (list of areas with minimal data, total count)

        Raises:
            AreaInvalidHierarchyException: If validation fails
            AreaOperationException: If listing fails
        """
        try:
            logger.debug(
                "Listing areas",
                area_type=area_type,
                is_active=is_active,
                parent_id=parent_id,
                parent_type=parent_type,
                limit=limit,
                offset=offset,
                company_id=str(self.company_id),
            )

            # Validate pagination parameters
            if limit < 1 or limit > 100:
                raise AreaInvalidHierarchyException(
                    message="Limit must be between 1 and 100"
                )

            if offset < 0:
                raise AreaInvalidHierarchyException(
                    message="Offset must be non-negative"
                )

            # Validate area type if provided
            if area_type is not None:
                try:
                    AreaType(area_type.upper())
                except ValueError:
                    raise AreaInvalidHierarchyException(
                        message=f"Invalid area type: {area_type}. Must be one of: NATION, ZONE, REGION, AREA, DIVISION"
                    )

            # Validate parent_type if provided
            if parent_type is not None and parent_type.lower() not in [
                "nation",
                "zone",
                "region",
                "area",
            ]:
                raise AreaInvalidHierarchyException(
                    message=f"Invalid parent type: {parent_type}. Must be one of: nation, zone, region, area"
                )

            # Get areas and count in parallel for better performance
            async with self.db_pool.acquire() as conn:
                areas = await self.repository.list_areas(
                    area_type=area_type,
                    is_active=is_active,
                    parent_id=parent_id,
                    parent_type=parent_type,
                    limit=limit,
                    offset=offset,
                    connection=conn,
                )
                total_count = await self.repository.count_areas(
                    area_type=area_type,
                    is_active=is_active,
                    parent_id=parent_id,
                    parent_type=parent_type,
                    connection=conn,
                )

            logger.debug(
                "Areas listed successfully",
                count=len(areas),
                total_count=total_count,
                company_id=str(self.company_id),
            )

            return areas, total_count

        except AreaInvalidHierarchyException:
            raise
        except Exception as e:
            logger.error(
                "Failed to list areas in service",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def update_area(self, area_id: int, area_data: AreaUpdate) -> AreaResponse:
        """
        Update an existing area.

        Args:
            area_id: ID of the area to update
            area_data: Area data to update

        Returns:
            Updated area

        Raises:
            AreaNotFoundException: If area not found
            AreaInvalidHierarchyException: If validation fails
            AreaOperationException: If update fails
        """
        try:
            logger.info(
                "Updating area",
                area_id=area_id,
                company_id=str(self.company_id),
            )

            # Validate at least one field is provided
            if not any(
                [
                    area_data.name,
                    area_data.type,
                    area_data.area_id is not None,
                    area_data.region_id is not None,
                    area_data.zone_id is not None,
                    area_data.nation_id is not None,
                ]
            ):
                raise AreaInvalidHierarchyException(
                    message="At least one field must be provided for update"
                )

            # Validate parent exists if being updated
            if any(
                [
                    area_data.type is not None,
                    area_data.area_id is not None,
                    area_data.region_id is not None,
                    area_data.zone_id is not None,
                    area_data.nation_id is not None,
                ]
            ):
                if area_data.type == AreaType.DIVISION.value:
                    parent_area = await self.repository.get_area_by_id(area_data.area_id)
                    if parent_area.type != AreaType.AREA.value:
                        raise AreaInvalidHierarchyException(
                            message="Division's parent area must be of type AREA",
                        )
                    area_data.region_id = parent_area.region_id
                    area_data.zone_id = parent_area.zone_id
                    area_data.nation_id = parent_area.nation_id
                elif area_data.type == AreaType.AREA.value:
                    parent_area = await self.repository.get_area_by_id(area_data.region_id)
                    if parent_area.type != AreaType.REGION.value:
                        raise AreaInvalidHierarchyException(
                            message="Area's parent region must be of type REGION",
                        )
                    area_data.area_id = None
                    area_data.zone_id = parent_area.zone_id
                    area_data.nation_id = parent_area.nation_id
                elif area_data.type == AreaType.REGION.value:
                    parent_area = await self.repository.get_area_by_id(area_data.zone_id)
                    if parent_area.type != AreaType.ZONE.value:
                        raise AreaInvalidHierarchyException(
                            message="Region's parent zone must be of type ZONE",
                        )
                    area_data.area_id = None
                    area_data.region_id = None
                    area_data.nation_id = parent_area.nation_id
                elif area_data.type == AreaType.ZONE.value:
                    parent_area = await self.repository.get_area_by_id(area_data.nation_id)
                    if parent_area.type != AreaType.NATION.value:
                        raise AreaInvalidHierarchyException(
                            message="Zone's parent nation must be of type NATION",
                        )
                    area_data.area_id = None
                    area_data.region_id = None
                    area_data.zone_id = None
                elif area_data.type == AreaType.NATION.value:
                    area_data.area_id = None
                    area_data.region_id = None
                    area_data.zone_id = None
                    area_data.nation_id = None
                else:
                    raise AreaInvalidHierarchyException(
                        message="Invalid area type",
                    )

            # Update area using repository
            area = await self.repository.update_area(area_id, area_data)

            logger.info(
                "Area updated successfully",
                area_id=area_id,
                company_id=str(self.company_id),
            )

            return AreaResponse(**area.model_dump())

        except (AreaNotFoundException, AreaInvalidHierarchyException):
            raise
        except Exception as e:
            logger.error(
                "Failed to update area in service",
                area_id=area_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def delete_area(self, area_id: int) -> None:
        """
        Soft delete an area by setting is_active to False.

        Args:
            area_id: ID of the area to delete

        Raises:
            AreaNotFoundException: If area not found
            AreaOperationException: If deletion fails
        """
        try:
            logger.info(
                "Deleting area",
                area_id=area_id,
                company_id=str(self.company_id),
            )

            # Soft delete area using repository
            await self.repository.delete_area(area_id)

            logger.info(
                "Area deleted successfully",
                area_id=area_id,
                company_id=str(self.company_id),
            )

        except AreaNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to delete area in service",
                area_id=area_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def get_areas_by_parent(
        self, parent_id: int, parent_type: str
    ) -> list[AreaResponse]:
        """
        Get all child areas of a parent area.

        Args:
            parent_id: ID of the parent area
            parent_type: Type of parent (nation, zone, region, area)

        Returns:
            List of child areas

        Raises:
            AreaInvalidHierarchyException: If parent_type is invalid
            AreaOperationException: If retrieval fails
        """
        try:
            logger.debug(
                "Getting areas by parent",
                parent_id=parent_id,
                parent_type=parent_type,
                company_id=str(self.company_id),
            )

            # Validate parent_type
            if parent_type.lower() not in ["nation", "zone", "region", "area"]:
                raise AreaInvalidHierarchyException(
                    message=f"Invalid parent type: {parent_type}. Must be one of: nation, zone, region, area"
                )

            areas = await self.repository.get_areas_by_parent(parent_id, parent_type)

            return [AreaResponse(**area.model_dump()) for area in areas]

        except AreaInvalidHierarchyException:
            raise
        except Exception as e:
            logger.error(
                "Failed to get areas by parent in service",
                parent_id=parent_id,
                parent_type=parent_type,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def check_area_exists(self, area_id: int) -> bool:
        """
        Check if an area exists.

        Args:
            area_id: ID of the area to check

        Returns:
            True if area exists, False otherwise
        """
        try:
            await self.repository.get_area_by_id(area_id)
            return True
        except AreaNotFoundException:
            return False

    async def check_area_exists_by_name_and_type(
        self, name: str, area_type: str
    ) -> bool:
        """
        Check if an area exists by name and type.

        Args:
            name: Name of the area
            area_type: Type of the area

        Returns:
            True if area exists, False otherwise
        """
        try:
            await self.repository.get_area_by_name_and_type(name, area_type)
            return True
        except AreaNotFoundException:
            return False

    async def get_active_areas_count(self, area_type: Optional[str] = None) -> int:
        """
        Get count of active areas, optionally filtered by type.

        Args:
            area_type: Optional filter by area type

        Returns:
            Count of active areas

        Raises:
            AreaOperationException: If counting fails
        """
        try:
            logger.debug(
                "Getting active areas count",
                area_type=area_type,
                company_id=str(self.company_id),
            )

            count = await self.repository.count_areas(
                area_type=area_type, is_active=True
            )

            return count

        except Exception as e:
            logger.error(
                "Failed to get active areas count in service",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def get_nations(self) -> list[AreaListItem]:
        """
        Get all active nations (top-level areas).

        Returns:
            List of active nations

        Raises:
            AreaOperationException: If retrieval fails
        """
        try:
            logger.debug(
                "Getting all nations",
                company_id=str(self.company_id),
            )

            nations = await self.repository.list_areas(
                area_type=AreaType.NATION.value, is_active=True, limit=100
            )

            return nations

        except Exception as e:
            logger.error(
                "Failed to get nations in service",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def get_zones_by_nation(self, nation_id: int) -> list[AreaResponse]:
        """
        Get all zones under a specific nation.

        Args:
            nation_id: ID of the nation

        Returns:
            List of zones

        Raises:
            AreaOperationException: If retrieval fails
        """
        try:
            logger.debug(
                "Getting zones by nation",
                nation_id=nation_id,
                company_id=str(self.company_id),
            )

            zones = await self.repository.get_areas_by_parent(nation_id, "nation")

            return [AreaResponse(**zone.model_dump()) for zone in zones]

        except Exception as e:
            logger.error(
                "Failed to get zones by nation in service",
                nation_id=nation_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def get_regions_by_zone(self, zone_id: int) -> list[AreaResponse]:
        """
        Get all regions under a specific zone.

        Args:
            zone_id: ID of the zone

        Returns:
            List of regions

        Raises:
            AreaOperationException: If retrieval fails
        """
        try:
            logger.debug(
                "Getting regions by zone",
                zone_id=zone_id,
                company_id=str(self.company_id),
            )

            regions = await self.repository.get_areas_by_parent(zone_id, "zone")

            return [AreaResponse(**region.model_dump()) for region in regions]

        except Exception as e:
            logger.error(
                "Failed to get regions by zone in service",
                zone_id=zone_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def get_areas_by_region(self, region_id: int) -> list[AreaResponse]:
        """
        Get all areas under a specific region.

        Args:
            region_id: ID of the region

        Returns:
            List of areas

        Raises:
            AreaOperationException: If retrieval fails
        """
        try:
            logger.debug(
                "Getting areas by region",
                region_id=region_id,
                company_id=str(self.company_id),
            )

            areas = await self.repository.get_areas_by_parent(region_id, "region")

            return [AreaResponse(**area.model_dump()) for area in areas]

        except Exception as e:
            logger.error(
                "Failed to get areas by region in service",
                region_id=region_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def get_divisions_by_area(self, area_id: int) -> list[AreaResponse]:
        """
        Get all divisions under a specific area.

        Args:
            area_id: ID of the area

        Returns:
            List of divisions

        Raises:
            AreaOperationException: If retrieval fails
        """
        try:
            logger.debug(
                "Getting divisions by area",
                area_id=area_id,
                company_id=str(self.company_id),
            )

            divisions = await self.repository.get_areas_by_parent(area_id, "area")

            return [AreaResponse(**division.model_dump()) for division in divisions]

        except Exception as e:
            logger.error(
                "Failed to get divisions by area in service",
                area_id=area_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise