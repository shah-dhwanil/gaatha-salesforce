"""
Area service module for business logic.

This service provides business logic layer for area operations,
acting as an intermediary between API handlers and the area repository.
It handles validation, business rules, and coordinates repository operations.
"""

from uuid import UUID
import structlog

from api.repository.area import AreaRepository
from api.models.area import AreaInDB, AreaType
from api.exceptions.area import InvalidAreaInputException

logger = structlog.get_logger(__name__)


class AreaService:
    """Service class for area business logic.

    This service handles business logic and validation for area operations,
    coordinating between the API layer and the AreaRepository.

    Attributes:
        area_repository: Repository for area data operations
    """

    def __init__(self, area_repository: AreaRepository):
        """Initialize the AreaService with a repository.

        Args:
            area_repository: AreaRepository instance for data operations
        """
        self.area_repository = area_repository
        logger.debug("AreaService initialized")

    async def create_area(
        self,
        company_id: UUID,
        name: str,
        type: AreaType,
        area_id: int | None = None,
        region_id: int | None = None,
        zone_id: int | None = None,
        nation_id: int | None = None,
    ) -> AreaInDB:
        """Create a new area with validation.

        Validates input data and creates a new area through the repository.

        Args:
            company_id: UUID of the company the area belongs to
            name: Name of the area
            type: Type of the area (DIVISION, AREA, REGION, ZONE, NATION)
            area_id: Optional parent area ID
            region_id: Optional parent region ID
            zone_id: Optional parent zone ID
            nation_id: Optional parent nation ID

        Returns:
            AreaInDB: Created area object with all details

        Raises:
            AreaAlreadyExistsException: If area name already exists
            ValueError: If validation fails
        """
        logger.info(
            "Creating area",
            name=name,
            type=type,
            company_id=str(company_id),
        )

        # Validate parent area types (requires database lookup)
        if type == AreaType.DIVISION:
            # At this point, model validation ensures area_id is not None
            assert area_id is not None, (
                "Model validation should ensure area_id is set for DIVISION"
            )
            parent_area = await self.area_repository.get_area_by_id(
                company_id=company_id,
                area_id=area_id,
            )
            if parent_area.type != AreaType.AREA:
                raise InvalidAreaInputException(
                    field="area_id",
                    message="Division's parent area must be of type AREA",
                )
            region_id = parent_area.region_id
            zone_id = parent_area.zone_id
            nation_id = parent_area.nation_id

        elif type == AreaType.AREA:
            # At this point, model validation ensures region_id is not None
            assert region_id is not None, (
                "Model validation should ensure region_id is set for AREA"
            )
            parent_area = await self.area_repository.get_area_by_id(
                company_id=company_id,
                area_id=region_id,
            )
            if parent_area.type != AreaType.REGION:
                raise InvalidAreaInputException(
                    field="region_id",
                    message="Area's parent region must be of type REGION",
                )
            zone_id = parent_area.zone_id
            nation_id = parent_area.nation_id

        elif type == AreaType.REGION:
            # At this point, model validation ensures zone_id is not None
            assert zone_id is not None, (
                "Model validation should ensure zone_id is set for REGION"
            )
            parent_area = await self.area_repository.get_area_by_id(
                company_id=company_id,
                area_id=zone_id,
            )
            if parent_area.type != AreaType.ZONE:
                raise InvalidAreaInputException(
                    field="zone_id", message="Region's parent zone must be of type ZONE"
                )
            nation_id = parent_area.nation_id

        elif type == AreaType.ZONE:
            # At this point, model validation ensures nation_id is not None
            assert nation_id is not None, (
                "Model validation should ensure nation_id is set for ZONE"
            )
            parent_area = await self.area_repository.get_area_by_id(
                company_id=company_id,
                area_id=nation_id,
            )
            if parent_area.type != AreaType.NATION:
                raise InvalidAreaInputException(
                    field="nation_id",
                    message="Zone's parent nation must be of type NATION",
                )

        # Create area through repository
        area = await self.area_repository.create_area(
            company_id=company_id,
            name=name.strip(),
            type=type,
            area_id=area_id,
            region_id=region_id,
            zone_id=zone_id,
            nation_id=nation_id,
        )

        logger.info(
            "Area created successfully",
            name=name,
            area_id=area.id,
            company_id=str(company_id),
        )
        return area

    async def get_area_by_id(self, company_id: UUID, area_id: int) -> AreaInDB:
        """Retrieve an area by ID.

        Args:
            company_id: UUID of the company
            area_id: Area ID to search for

        Returns:
            AreaInDB: Complete area object

        Raises:
            AreaNotFoundException: If area not found
            ValueError: If validation fails
        """
        logger.info("Fetching area by ID", area_id=area_id, company_id=str(company_id))

        area = await self.area_repository.get_area_by_id(
            company_id=company_id,
            area_id=area_id,
        )

        logger.info(
            "Area fetched successfully", area_id=area_id, company_id=str(company_id)
        )
        return area

    async def get_area_by_name(self, company_id: UUID, name: str) -> AreaInDB:
        """Retrieve an area by name.

        Args:
            company_id: UUID of the company
            name: Area name to search for

        Returns:
            AreaInDB: Complete area object

        Raises:
            AreaNotFoundException: If area not found
            ValueError: If validation fails
        """
        logger.info("Fetching area by name", name=name, company_id=str(company_id))

        area = await self.area_repository.get_area_by_name(
            company_id=company_id,
            name=name.strip(),
        )

        logger.info("Area fetched successfully", name=name, company_id=str(company_id))
        return area

    async def get_areas_by_company_id(
        self, company_id: UUID, limit: int = 10, offset: int = 0
    ) -> tuple[list[AreaInDB], int]:
        """Retrieve all areas by company ID with pagination.

        Args:
            company_id: UUID of the company
            limit: Maximum number of records to return (default: 10)
            offset: Number of records to skip (default: 0)

        Returns:
            tuple: (list of AreaInDB objects, total count of areas)
        """
        logger.info(
            "Fetching areas for company with pagination",
            company_id=str(company_id),
            limit=limit,
            offset=offset,
        )

        areas, total_count = await self.area_repository.get_areas_by_company_id(
            company_id=company_id,
            limit=limit,
            offset=offset,
        )

        logger.info(
            "Areas fetched successfully",
            company_id=str(company_id),
            area_count=len(areas),
            total_count=total_count,
        )
        return areas, total_count

    async def get_areas_by_type(
        self, company_id: UUID, type: AreaType, limit: int = 10, offset: int = 0
    ) -> tuple[list[AreaInDB], int]:
        """Retrieve all areas by type within a company with pagination.

        Args:
            company_id: UUID of the company
            type: Area type to filter by
            limit: Maximum number of records to return (default: 10)
            offset: Number of records to skip (default: 0)

        Returns:
            tuple: (list of AreaInDB objects, total count of areas)

        Raises:
            ValueError: If validation fails
        """
        logger.info(
            "Fetching areas by type with pagination",
            type=type,
            company_id=str(company_id),
            limit=limit,
            offset=offset,
        )

        areas, total_count = await self.area_repository.get_areas_by_type(
            company_id=company_id,
            type=type,
            limit=limit,
            offset=offset,
        )

        logger.info(
            "Areas fetched by type successfully",
            type=type,
            company_id=str(company_id),
            area_count=len(areas),
            total_count=total_count,
        )
        return areas, total_count

    async def get_areas_related_to(
        self,
        company_id: UUID,
        area_id: int,
        area_type: AreaType,
        required_type: AreaType | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> tuple[list[AreaInDB], int]:
        """Retrieve areas related to a given area based on hierarchy with pagination.

        Args:
            company_id: UUID of the company
            area_id: ID of the reference area
            area_type: Type of the reference area
            required_type: Optional type to filter related areas
            limit: Maximum number of records to return (default: 10)
            offset: Number of records to skip (default: 0)

        Returns:
            tuple: (list of AreaInDB objects, total count of related areas)

        Raises:
            ValueError: If validation fails
        """
        logger.info(
            "Fetching areas related to given area with pagination",
            area_id=area_id,
            area_type=area_type,
            required_type=required_type,
            company_id=str(company_id),
            limit=limit,
            offset=offset,
        )

        areas, total_count = await self.area_repository.get_areas_related_to(
            company_id=company_id,
            area_id=area_id,
            area_type=area_type,
            required_type=required_type,
            limit=limit,
            offset=offset,
        )

        logger.info(
            "Related areas fetched successfully",
            area_id=area_id,
            area_type=area_type,
            required_type=required_type,
            company_id=str(company_id),
            area_count=len(areas),
            total_count=total_count,
        )
        return areas, total_count

    async def update_area(
        self,
        company_id: UUID,
        id: int,
        name: str | None = None,
        type: AreaType | None = None,
        area_id: int | None = None,
        region_id: int | None = None,
        zone_id: int | None = None,
        nation_id: int | None = None,
    ) -> AreaInDB:
        """Update area details with validation.

        Args:
            company_id: UUID of the company
            area_id: ID of the area to update
            name: New name (optional)
            type: New type (optional)
            area_id_parent: New parent area ID (optional)
            region_id: New parent region ID (optional)
            zone_id: New parent zone ID (optional)
            nation_id: New parent nation ID (optional)

        Returns:
            AreaInDB: Updated area object

        Raises:
            ValueError: If validation fails
            AreaNotFoundException: If area not found
            AreaAlreadyExistsException: If name already exists
        """
        logger.info("Updating area", area_id=id, company_id=str(company_id))

        if type == AreaType.DIVISION:
            # At this point, model validation ensures area_id is not None
            assert area_id is not None, (
                "Model validation should ensure area_id is set for DIVISION"
            )
            parent_area = await self.area_repository.get_area_by_id(
                company_id=company_id,
                area_id=area_id,
            )
            if parent_area.type != AreaType.AREA:
                raise InvalidAreaInputException(
                    field="area_id",
                    message="Division's parent area must be of type AREA",
                )
            region_id = parent_area.region_id
            zone_id = parent_area.zone_id
            nation_id = parent_area.nation_id

        elif type == AreaType.AREA:
            # At this point, model validation ensures region_id is not None
            assert region_id is not None, (
                "Model validation should ensure region_id is set for AREA"
            )
            parent_area = await self.area_repository.get_area_by_id(
                company_id=company_id,
                area_id=region_id,
            )
            if parent_area.type != AreaType.REGION:
                raise InvalidAreaInputException(
                    field="region_id",
                    message="Area's parent region must be of type REGION",
                )
            zone_id = parent_area.zone_id
            nation_id = parent_area.nation_id

        elif type == AreaType.REGION:
            # At this point, model validation ensures zone_id is not None
            assert zone_id is not None, (
                "Model validation should ensure zone_id is set for REGION"
            )
            parent_area = await self.area_repository.get_area_by_id(
                company_id=company_id,
                area_id=zone_id,
            )
            if parent_area.type != AreaType.ZONE:
                raise InvalidAreaInputException(
                    field="zone_id", message="Region's parent zone must be of type ZONE"
                )
            nation_id = parent_area.nation_id

        elif type == AreaType.ZONE:
            # At this point, model validation ensures nation_id is not None
            assert nation_id is not None, (
                "Model validation should ensure nation_id is set for ZONE"
            )
            parent_area = await self.area_repository.get_area_by_id(
                company_id=company_id,
                area_id=nation_id,
            )
            if parent_area.type != AreaType.NATION:
                raise InvalidAreaInputException(
                    field="nation_id",
                    message="Zone's parent nation must be of type NATION",
                )
        # Update area through repository
        area = await self.area_repository.update_area(
            company_id=company_id,
            area_id=id,
            name=name,
            type=type,
            area_id_parent=area_id,
            region_id=region_id,
            zone_id=zone_id,
            nation_id=nation_id,
        )

        logger.info("Area updated successfully", area_id=id, company_id=str(company_id))
        return area

    async def delete_area(self, company_id: UUID, area_id: int) -> None:
        """Delete an area from the database (soft delete).

        Args:
            company_id: UUID of the company
            area_id: ID of the area to delete

        Raises:
            ValueError: If validation fails
            AreaNotFoundException: If area not found
        """
        logger.info("Deleting area", area_id=area_id, company_id=str(company_id))

        # Delete area through repository
        await self.area_repository.delete_area(
            company_id=company_id,
            area_id=area_id,
        )

        logger.info(
            "Area deleted successfully", area_id=area_id, company_id=str(company_id)
        )
