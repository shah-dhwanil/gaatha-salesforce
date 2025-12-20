from typing import Optional
from uuid import UUID

import structlog
from asyncpg import Connection, UniqueViolationError

from api.database import DatabasePool
from api.exceptions.areas import AreaAlreadyExistsException, AreaNotFoundException
from api.models.areas import AreaInDB, AreaType

logger = structlog.get_logger(__name__)


class AreaRepository:
    """Repository for managing area data in company-specific schemas.
    
    This repository handles area operations in a multi-tenant architecture where:
    - Area information is stored in company-specific schemas (named by company_id)
    
    Attributes:
        db_pool: Database connection pool for executing queries
    """
    
    def __init__(self, db_pool: DatabasePool):
        """Initialize the AreaRepository with a database pool.
        
        Args:
            db_pool: DatabasePool instance for managing database connections
        """
        self.db_pool = db_pool
        logger.debug("AreaRepository initialized")

    async def __set_search_path(
        self, conn: Connection, schema: str
    ) -> None:
        """Set the search path for the database connection.
        
        Args:
            conn: Database connection
            schema: Schema name to set in search path
        """
        logger.debug("Setting search path", schema=schema)
        await conn.execute(f"SET search_path TO {schema}, public;")
    
    def __get_schema_name(self, company_id: UUID) -> str:
        """Get the schema name for a given company ID.
        
        Args:
            company_id: UUID of the company
        Returns:
            str: Schema name derived from company ID
        """
        return f"_{str(company_id).replace("-", "")}_"

    async def __create_area(
        self,
        connection: Connection,
        company_id: UUID,
        name: str,
        type: AreaType,
        area_id: Optional[int] = None,
        region_id: Optional[int] = None,
        zone_id: Optional[int] = None,
        nation_id: Optional[int] = None,
    ) -> AreaInDB:
        """Create a new area in the database.
        
        Creates area record in company-specific areas table.
        
        Args:
            connection: Database connection
            company_id: UUID of the company the area belongs to
            name: Name of the area
            type: Type of the area
            area_id: Optional parent area ID
            region_id: Optional parent region ID
            zone_id: Optional parent zone ID
            nation_id: Optional parent nation ID
            
        Returns:
            AreaInDB: Created area object with all details
            
        Raises:
            AreaAlreadyExistsException: If area name already exists
        """
        logger.debug(
            "Creating new area",
            name=name,
            type=type,
            company_id=str(company_id),
            has_area_id=area_id is not None,
            has_region_id=region_id is not None,
            has_zone_id=zone_id is not None,
            has_nation_id=nation_id is not None,
        )
        
        query = """
        INSERT INTO areas (name, type, area_id, region_id, zone_id, nation_id) 
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING *;
        """
        
        try:
            await self.__set_search_path(connection, self.__get_schema_name(company_id))
            rs = await connection.fetchrow(
                query, name, type.value, area_id, region_id, zone_id, nation_id
            )
        except UniqueViolationError as e:
            logger.error(
                "Area creation failed - unique violation",
                name=name,
                company_id=str(company_id),
                error=str(e),
            )
            raise AreaAlreadyExistsException(field="name")
        
        logger.info("Area created successfully", area_id=rs["id"], name=name)
        return AreaInDB(
            id=rs["id"],
            name=rs["name"],
            type=rs["type"],
            area_id=rs["area_id"],
            region_id=rs["region_id"],
            zone_id=rs["zone_id"],
            nation_id=rs["nation_id"],
            is_active=rs["is_active"],
            created_at=rs["created_at"],
            updated_at=rs["updated_at"],
        )

    async def __get_area_by_id(
        self, connection: Connection, company_id: UUID, area_id: int
    ) -> AreaInDB:
        """Retrieve an area by ID.
        
        Queries company-specific areas table.
        
        Args:
            connection: Database connection
            company_id: UUID of the company
            area_id: Area ID to search for
            
        Returns:
            AreaInDB: Complete area object
            
        Raises:
            AreaNotFoundException: If area not found
        """
        logger.debug("Fetching area by ID", area_id=area_id, company_id=str(company_id))
        
        find_area_query = """
        SELECT id, name, type, area_id, region_id, zone_id, nation_id, is_active, created_at, updated_at
        FROM areas
        WHERE id = $1;
        """
        
        await self.__set_search_path(connection, self.__get_schema_name(company_id))
        rs = await connection.fetchrow(find_area_query, area_id)
        
        if rs:
            logger.debug(
                "Area found",
                area_id=area_id,
                name=rs["name"],
                company_id=str(company_id),
            )
            return AreaInDB(
                id=rs["id"],
                name=rs["name"],
                type=rs["type"],
                area_id=rs["area_id"],
                region_id=rs["region_id"],
                zone_id=rs["zone_id"],
                nation_id=rs["nation_id"],
                is_active=rs["is_active"],
                created_at=rs["created_at"],
                updated_at=rs["updated_at"],
            )
        
        logger.warning("Area not found", area_id=area_id, company_id=str(company_id))
        raise AreaNotFoundException(field="id")

    async def __get_area_by_name(
        self, connection: Connection, company_id: UUID, name: str
    ) -> AreaInDB:
        """Retrieve an area by name.
        
        Queries company-specific areas table.
        
        Args:
            connection: Database connection
            company_id: UUID of the company
            name: Area name to search for
            
        Returns:
            AreaInDB: Complete area object
            
        Raises:
            AreaNotFoundException: If area not found
        """
        logger.debug("Fetching area by name", name=name, company_id=str(company_id))
        
        find_area_query = """
        SELECT id, name, type, area_id, region_id, zone_id, nation_id, is_active, created_at, updated_at
        FROM areas
        WHERE name = $1 AND is_active = TRUE;
        """
        
        await self.__set_search_path(connection, self.__get_schema_name(company_id))
        rs = await connection.fetchrow(find_area_query, name)
        
        if rs:
            logger.debug(
                "Area found",
                area_id=rs["id"],
                name=name,
                company_id=str(company_id),
            )
            return AreaInDB(
                id=rs["id"],
                name=rs["name"],
                type=rs["type"],
                area_id=rs["area_id"],
                region_id=rs["region_id"],
                zone_id=rs["zone_id"],
                nation_id=rs["nation_id"],
                is_active=rs["is_active"],
                created_at=rs["created_at"],
                updated_at=rs["updated_at"],
            )
        
        logger.warning("Area not found", name=name, company_id=str(company_id))
        raise AreaNotFoundException(field="name")

    async def __get_areas_by_company_id(
        self, connection: Connection, company_id: UUID
    ) -> list[AreaInDB]:
        """Retrieve all areas by company ID.
        
        Fetches all areas from company-specific areas table.
        
        Args:
            connection: Database connection
            company_id: UUID of the company
            
        Returns:
            list[AreaInDB]: List of all areas in the company
        """
        logger.debug("Fetching all areas for company", company_id=str(company_id))
        
        find_areas_query = """
        SELECT id, name, type, area_id, region_id, zone_id, nation_id, is_active, created_at, updated_at
        FROM areas
        WHERE is_active = TRUE;
        """
        
        await self.__set_search_path(connection, self.__get_schema_name(company_id))
        rs = await connection.fetch(find_areas_query)
        
        areas = []
        for record in rs:
            areas.append(
                AreaInDB(
                    id=record["id"],
                    name=record["name"],
                    type=record["type"],
                    area_id=record["area_id"],
                    region_id=record["region_id"],
                    zone_id=record["zone_id"],
                    nation_id=record["nation_id"],
                    is_active=record["is_active"],
                    created_at=record["created_at"],
                    updated_at=record["updated_at"],
                )
            )
        
        logger.debug(
            "Areas fetched for company",
            company_id=str(company_id),
            area_count=len(areas),
        )
        return areas

    async def __get_areas_by_type(
        self, connection: Connection, company_id: UUID, type: AreaType
    ) -> list[AreaInDB]:
        """Retrieve all areas by type within a company.
        
        Args:
            connection: Database connection
            company_id: UUID of the company
            type: Area type to filter by
            
        Returns:
            list[AreaInDB]: List of areas with the specified type
        """
        logger.debug(
            "Fetching areas by type",
            type=type,
            company_id=str(company_id),
        )
        
        find_areas_query = """
        SELECT id, name, type, area_id, region_id, zone_id, nation_id, is_active, created_at, updated_at
        FROM areas
        WHERE type = $1 AND is_active = TRUE;
        """
        
        await self.__set_search_path(connection, self.__get_schema_name(company_id))
        rs = await connection.fetch(find_areas_query, type.value)
        
        areas = []
        for record in rs:
            areas.append(
                AreaInDB(
                    id=record["id"],
                    name=record["name"],
                    type=record["type"],
                    area_id=record["area_id"],
                    region_id=record["region_id"],
                    zone_id=record["zone_id"],
                    nation_id=record["nation_id"],
                    is_active=record["is_active"],
                    created_at=record["created_at"],
                    updated_at=record["updated_at"],
                )
            )
        
        logger.debug(
            "Areas fetched by type",
            type=type,
            company_id=str(company_id),
            area_count=len(areas),
        )
        return areas

    async def __get_areas_related_to(connection:Connection, area_id:int, area_type: AreaType, required_type:Optional[AreaType]=None) -> list[AreaInDB]:
        """
        Retrieve areas related to a given area based on hierarchy.
        Args:
            connection: Database connection
            area_id: ID of the reference area
            area_type: Type of the reference area
            required_type: Optional type to filter related areas
        Returns:
            list[AreaInDB]: List of related areas
        """
        logger.debug(
            "Fetching areas related to given area",
            area_id=area_id,
            area_type=area_type,
            required_type=required_type,
        )

        query = """
        SELECT id, name, type, area_id, region_id, zone_id, nation_id, is_active, created_at, updated_at
        FROM areas
        WHERE 
        """
        if area_type == AreaType.Area:
            query += "area_id = $1"
        elif area_type == AreaType.Region:
            query += "region_id = $1"
        elif area_type == AreaType.Zone:
            query += "zone_id = $1"
        elif area_type == AreaType.Nation:
            query += "nation_id = $1"
        else:
            return []

        if required_type:
            query += " AND type = $2"

        query += " AND is_active = TRUE;"

        if required_type:
            rs = await connection.fetch(query, area_id, required_type.value)
        else:
            rs = await connection.fetch(query, area_id)

        areas = []
        for record in rs:
            areas.append(
                AreaInDB(
                    id=record["id"],
                    name=record["name"],
                    type=record["type"],
                    area_id=record["area_id"],
                    region_id=record["region_id"],
                    zone_id=record["zone_id"],
                    nation_id=record["nation_id"],
                    is_active=record["is_active"],
                    created_at=record["created_at"],
                    updated_at=record["updated_at"],
                )
            )

        logger.debug(
            "Related areas fetched",
            area_id=area_id,
            area_type=area_type,
            required_type=required_type,
            area_count=len(areas),
        )
        return areas
    async def __update_area(
        self,
        connection: Connection,
        company_id: UUID,
        area_id: int,
        name: Optional[str] = None,
        type: Optional[AreaType] = None,
        area_id_parent: Optional[int] = None,
        region_id: Optional[int] = None,
        zone_id: Optional[int] = None,
        nation_id: Optional[int] = None,
    ) -> AreaInDB:
        """Update area details.
        
        Updates area in company-specific areas table.
        
        Args:
            connection: Database connection
            company_id: UUID of the company for schema context
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
            ValueError: If no fields provided for update
            AreaNotFoundException: If area not found
            AreaAlreadyExistsException: If name already exists
        """
        logger.debug(
            "Updating area",
            area_id=area_id,
            company_id=str(company_id),
            has_name=name is not None,
            has_type=type is not None,
            has_area_id=area_id_parent is not None,
            has_region_id=region_id is not None,
            has_zone_id=zone_id is not None,
            has_nation_id=nation_id is not None,
        )
        
        update_fields = []
        update_values = []
        
        if name is not None:
            update_fields.append(f"name = ${len(update_values) + 2}")
            update_values.append(name)
        if type is not None:
            update_fields.append(f"type = ${len(update_values) + 2}")
            update_values.append(type.value)
        if area_id_parent is not None:
            update_fields.append(f"area_id = ${len(update_values) + 2}")
            update_values.append(area_id_parent)
        if region_id is not None:
            update_fields.append(f"region_id = ${len(update_values) + 2}")
            update_values.append(region_id)
        if zone_id is not None:
            update_fields.append(f"zone_id = ${len(update_values) + 2}")
            update_values.append(zone_id)
        if nation_id is not None:
            update_fields.append(f"nation_id = ${len(update_values) + 2}")
            update_values.append(nation_id)
        
        if not update_fields:
            logger.warning("No fields to update", area_id=area_id)
            raise ValueError("At least one field must be provided for update")
        
        await self.__set_search_path(connection, self.__get_schema_name(company_id))
        
        update_query = f"""
        UPDATE areas
        SET {', '.join(update_fields)}
        WHERE id = $1
        RETURNING *;
        """
        
        try:
            rs = await connection.fetchrow(update_query, area_id, *update_values)
        except UniqueViolationError as e:
            logger.error(
                "Area update failed - unique violation",
                area_id=area_id,
                company_id=str(company_id),
                error=str(e),
            )
            raise AreaAlreadyExistsException(field="name")
        
        if not rs:
            logger.warning("Area not found for update", area_id=area_id)
            raise AreaNotFoundException(field="id")
        
        logger.info("Area updated successfully", area_id=area_id)
        return AreaInDB(
            id=rs["id"],
            name=rs["name"],
            type=rs["type"],
            area_id=rs["area_id"],
            region_id=rs["region_id"],
            zone_id=rs["zone_id"],
            nation_id=rs["nation_id"],
            is_active=rs["is_active"],
            created_at=rs["created_at"],
            updated_at=rs["updated_at"],
        )

    async def __delete_area(
        self, connection: Connection, company_id: UUID, area_id: int
    ) -> None:
        """Delete an area from the database (soft delete).
        
        Marks area as inactive in company-specific areas table.
        
        Args:
            connection: Database connection
            company_id: UUID of the company for schema context
            area_id: ID of the area to delete
            
        Raises:
            AreaNotFoundException: If area not found
        """
        logger.debug(
            "Soft deleting area",
            area_id=area_id,
            company_id=str(company_id),
        )
        
        delete_area_query = """
        UPDATE areas
        SET is_active = FALSE
        WHERE id = $1;
        """
        
        await self.__set_search_path(connection, self.__get_schema_name(company_id))
        result = await connection.execute(delete_area_query, area_id)
        
        if result == "UPDATE 0":
            logger.warning("Area not found for deletion", area_id=area_id)
            raise AreaNotFoundException(field="id")
        
        logger.info("Area soft deleted successfully", area_id=area_id)

    async def create_area(
        self,
        company_id: UUID,
        name: str,
        type: AreaType,
        area_id: Optional[int] = None,
        region_id: Optional[int] = None,
        zone_id: Optional[int] = None,
        nation_id: Optional[int] = None,
        *,
        connection: Optional[Connection] = None,
    ) -> AreaInDB:
        """Create a new area in the database.
        
        Public interface for area creation. Manages connection pooling if needed.
        
        Args:
            company_id: Company UUID
            name: Area name
            type: Area type
            area_id: Optional parent area ID
            region_id: Optional parent region ID
            zone_id: Optional parent zone ID
            nation_id: Optional parent nation ID
            connection: Optional existing connection (for transactions)
            
        Returns:
            AreaInDB: Created area object
        """
        logger.info("create_area called", name=name, type=type, company_id=str(company_id))
        if connection is None:
            async with self.db_pool.acquire() as connection:
                return await self.__create_area(connection, company_id, name, type, area_id, region_id, zone_id, nation_id)
        return await self.__create_area(connection, company_id, name, type, area_id, region_id, zone_id, nation_id)

    async def get_area_by_id(
        self, company_id: UUID, area_id: int, *, connection: Optional[Connection] = None
    ) -> AreaInDB:
        """Retrieve an area by ID.
        
        Public interface for fetching area by ID.
        
        Args:
            company_id: Company UUID
            area_id: Area ID to search for
            connection: Optional existing connection
            
        Returns:
            AreaInDB: Area object with complete details
        """
        logger.info("get_area_by_id called", area_id=area_id, company_id=str(company_id))
        if connection is None:
            async with self.db_pool.acquire() as connection:
                return await self.__get_area_by_id(connection, company_id, area_id)
        return await self.__get_area_by_id(connection, company_id, area_id)

    async def get_area_by_name(
        self, company_id: UUID, name: str, *, connection: Optional[Connection] = None
    ) -> AreaInDB:
        """Retrieve an area by name.
        
        Public interface for fetching area by name.
        
        Args:
            company_id: Company UUID
            name: Area name to search for
            connection: Optional existing connection
            
        Returns:
            AreaInDB: Area object with complete details
        """
        logger.info("get_area_by_name called", name=name, company_id=str(company_id))
        if connection is None:
            async with self.db_pool.acquire() as connection:
                return await self.__get_area_by_name(connection, company_id, name)
        return await self.__get_area_by_name(connection, company_id, name)

    async def get_areas_by_company_id(
        self, company_id: UUID, *, connection: Optional[Connection] = None
    ) -> list[AreaInDB]:
        """Retrieve all areas by company ID.
        
        Public interface for fetching all company areas.
        
        Args:
            company_id: Company UUID
            connection: Optional existing connection
            
        Returns:
            list[AreaInDB]: List of all areas in the company
        """
        logger.info("get_areas_by_company_id called", company_id=str(company_id))
        if connection is None:
            async with self.db_pool.acquire() as connection:
                return await self.__get_areas_by_company_id(connection, company_id)
        return await self.__get_areas_by_company_id(connection, company_id)

    async def get_areas_by_type(
        self, company_id: UUID, type: AreaType, *, connection: Optional[Connection] = None
    ) -> list[AreaInDB]:
        """Retrieve all areas by type within a company.
        
        Public interface for fetching areas by type.
        
        Args:
            company_id: Company UUID
            type: Area type to filter by
            connection: Optional existing connection
            
        Returns:
            list[AreaInDB]: List of areas with the specified type
        """
        logger.info("get_areas_by_type called", type=type, company_id=str(company_id))
        if connection is None:
            async with self.db_pool.acquire() as connection:
                return await self.__get_areas_by_type(connection, company_id, type)
        return await self.__get_areas_by_type(connection, company_id, type)

    async def get_areas_related_to(
        self, company_id: UUID,
        area_id: int,
        area_type: AreaType,
        required_type: Optional[AreaType] = None,
        *, connection: Optional[Connection] = None
    ) -> list[AreaInDB]:
        """Retrieve areas related to a given area based on hierarchy.
        
        Public interface for fetching related areas.
        
        Args:
            company_id: Company UUID
            area_id: ID of the reference area
            area_type: Type of the reference area
            required_type: Optional type to filter related areas
            connection: Optional existing connection
        Returns:
            list[AreaInDB]: List of related areas
        """        
        logger.info(
            "get_areas_related_to called",
            area_id=area_id,
            area_type=area_type,
            required_type=required_type,
            company_id=str(company_id)
        )
        if connection is None:
            async with self.db_pool.acquire() as connection:
                return await self.__get_areas_related_to(connection, area_id, area_type, required_type)
        return await self.__get_areas_related_to(connection, area_id, area_type, required_type)

    async def update_area(
        self,
        company_id: UUID,
        area_id: int,
        name: Optional[str] = None,
        type: Optional[AreaType] = None,
        area_id_parent: Optional[int] = None,
        region_id: Optional[int] = None,
        zone_id: Optional[int] = None,
        nation_id: Optional[int] = None,
        *,
        connection: Optional[Connection] = None,
    ) -> AreaInDB:
        """Update area details.
        
        Public interface for updating area information.
        
        Args:
            company_id: Company UUID
            area_id: ID of the area to update
            name: New name (optional)
            type: New type (optional)
            area_id_parent: New parent area ID (optional)
            region_id: New parent region ID (optional)
            zone_id: New parent zone ID (optional)
            nation_id: New parent nation ID (optional)
            connection: Optional existing connection
            
        Returns:
            AreaInDB: Updated area object
        """
        logger.info("update_area called", area_id=area_id, company_id=str(company_id))
        if connection is None:
            async with self.db_pool.acquire() as connection:
                return await self.__update_area(connection, company_id, area_id, name, type, area_id_parent, region_id, zone_id, nation_id)
        return await self.__update_area(connection, company_id, area_id, name, type, area_id_parent, region_id, zone_id, nation_id)

    async def delete_area(
        self,
        company_id: UUID,
        area_id: int,
        *,
        connection: Optional[Connection] = None,
    ) -> None:
        """Delete an area from the database (soft delete).
        
        Public interface for soft-deleting areas.
        
        Args:
            company_id: Company UUID
            area_id: ID of the area to delete
            connection: Optional existing connection
        """
        logger.info("delete_area called", area_id=area_id, company_id=str(company_id))
        if connection is None:
            async with self.db_pool.acquire() as connection:
                return await self.__delete_area(connection, company_id, area_id)
        return await self.__delete_area(connection, company_id, area_id)
