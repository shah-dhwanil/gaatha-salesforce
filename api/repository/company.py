from uuid import UUID
from api.database import DatabasePool
from typing import Optional
from asyncpg import Connection, UniqueViolationError
from uuid_utils.compat import uuid7
import structlog
from api.exceptions.company import CompanyAlreadyExistsException, CompanyNotFoundException
from api.models.company import CompanyInDB

logger = structlog.get_logger(__name__)


class CompanyRepository:
    """Repository for managing company data in the salesforce schema.
    
    This repository handles company operations where:
    - Company information is stored in the 'salesforce.company' table
    
    Attributes:
        db_pool: Database connection pool for executing queries
    """
    
    def __init__(self, db_pool: DatabasePool):
        """Initialize the CompanyRepository with a database pool.
        
        Args:
            db_pool: DatabasePool instance for managing database connections
        """
        self.db_pool = db_pool
        logger.debug("CompanyRepository initialized")

    async def __set_search_path(
        self, conn: Connection, schema: str = "salesforce"
    ) -> None:
        """Set the search path for the database connection.
        
        Args:
            conn: Database connection
            schema: Schema name to set in search path (default: 'salesforce')
        """
        logger.debug("Setting search path", schema=schema)
        await conn.execute(f"SET search_path TO {schema}, public;")

    async def __create_company(
        self,
        connection: Connection,
        name: str,
        gst_no: str,
        cin_no: str,
        address: str,
    ) -> CompanyInDB:
        """Create a new company in the database.
        
        Creates company record in salesforce.company table.
        
        Args:
            connection: Database connection
            name: Name of the company
            gst_no: GST number (required)
            cin_no: CIN number (required)
            address: Company address (required)
            
        Returns:
            CompanyInDB: Created company object with all details
            
        Raises:
            CompanyAlreadyExistsException: If GST or CIN number already exists
        """
        company_id = uuid7()
        logger.debug(
            "Creating new company",
            company_id=str(company_id),
            name=name,
            gst_no=gst_no,
            cin_no=cin_no,
        )
        
        query = """
        INSERT INTO company (id, name, gst_no, cin_no, address) 
        VALUES ($1, $2, $3, $4, $5)
        RETURNING *;
        """
        
        try:
            await self.__set_search_path(connection, "salesforce")
            rs = await connection.fetchrow(
                query, company_id, name, gst_no, cin_no, address
            )
            logger.debug(
                "Company record created in salesforce schema",
                company_id=str(company_id),
                name=name,
            )
        except UniqueViolationError as e:
            error_msg = str(e)
            field = "gst_no" if "gst_no" in error_msg else "cin_no"
            logger.error(
                "Company creation failed - duplicate value",
                name=name,
                field=field,
                error=error_msg,
            )
            raise CompanyAlreadyExistsException(
                field=field,
                message=f"Company with this {field} already exists."
            ) from e
        
        logger.info("Company created successfully", company_id=str(company_id), name=name)
        return CompanyInDB(
            id=rs["id"],
            name=rs["name"],
            gst_no=rs["gst_no"],
            cin_no=rs["cin_no"],
            address=rs["address"],
            is_active=rs["is_active"],
            created_at=rs["created_at"],
            updated_at=rs["updated_at"],
        )

    async def __get_company_by_id(
        self, connection: Connection, company_id: UUID
    ) -> CompanyInDB:
        """Retrieve a company by ID.
        
        Queries salesforce.company table.
        
        Args:
            connection: Database connection
            company_id: UUID of the company
            
        Returns:
            CompanyInDB: Complete company object
            
        Raises:
            CompanyNotFoundException: If company not found
        """
        logger.debug("Fetching company by ID", company_id=str(company_id))
        
        find_company_query = """
        SELECT id, name, gst_no, cin_no, address, is_active, created_at, updated_at
        FROM company
        WHERE id = $1;
        """
        
        await self.__set_search_path(connection, "salesforce")
        rs = await connection.fetchrow(find_company_query, company_id)
        
        if rs:
            logger.debug(
                "Company found in salesforce schema",
                company_id=str(company_id),
            )
            return CompanyInDB(
                id=rs["id"],
                name=rs["name"],
                gst_no=rs["gst_no"],
                cin_no=rs["cin_no"],
                address=rs["address"],
                is_active=rs["is_active"],
                created_at=rs["created_at"],
                updated_at=rs["updated_at"],
            )
        
        logger.warning("Company not found", company_id=str(company_id))
        raise CompanyNotFoundException(field="id")

    async def __get_company_by_gst_no(
        self, connection: Connection, gst_no: str
    ) -> CompanyInDB:
        """Retrieve a company by GST number.
        
        Queries salesforce.company table.
        
        Args:
            connection: Database connection
            gst_no: GST number to search for
            
        Returns:
            CompanyInDB: Complete company object
            
        Raises:
            CompanyNotFoundException: If company not found
        """
        logger.debug("Fetching company by GST number", gst_no=gst_no)
        
        find_company_query = """
        SELECT id, name, gst_no, cin_no, address, is_active, created_at, updated_at
        FROM company
        WHERE gst_no = $1 AND is_active = TRUE;
        """
        
        await self.__set_search_path(connection, "salesforce")
        rs = await connection.fetchrow(find_company_query, gst_no)
        
        if rs:
            logger.debug(
                "Company found in salesforce schema",
                gst_no=gst_no,
            )
            return CompanyInDB(
                id=rs["id"],
                name=rs["name"],
                gst_no=rs["gst_no"],
                cin_no=rs["cin_no"],
                address=rs["address"],
                is_active=rs["is_active"],
                created_at=rs["created_at"],
                updated_at=rs["updated_at"],
            )
        
        logger.warning("Company not found", gst_no=gst_no)
        raise CompanyNotFoundException(field="gst_no")

    async def __get_company_by_cin_no(
        self, connection: Connection, cin_no: str
    ) -> CompanyInDB:
        """Retrieve a company by CIN number.
        
        Queries salesforce.company table.
        
        Args:
            connection: Database connection
            cin_no: CIN number to search for
            
        Returns:
            CompanyInDB: Complete company object
            
        Raises:
            CompanyNotFoundException: If company not found
        """
        logger.debug("Fetching company by CIN number", cin_no=cin_no)
        
        find_company_query = """
        SELECT id, name, gst_no, cin_no, address, is_active, created_at, updated_at
        FROM company
        WHERE cin_no = $1 AND is_active = TRUE;
        """
        
        await self.__set_search_path(connection, "salesforce")
        rs = await connection.fetchrow(find_company_query, cin_no)
        
        if rs:
            logger.debug(
                "Company found in salesforce schema",
                cin_no=cin_no,
            )
            return CompanyInDB(
                id=rs["id"],
                name=rs["name"],
                gst_no=rs["gst_no"],
                cin_no=rs["cin_no"],
                address=rs["address"],
                is_active=rs["is_active"],
                created_at=rs["created_at"],
                updated_at=rs["updated_at"],
            )
        
        logger.warning("Company not found", cin_no=cin_no)
        raise CompanyNotFoundException(field="cin_no")

    async def __get_all_companies(
        self, connection: Connection
    ) -> list[CompanyInDB]:
        """Retrieve all active companies.
        
        Fetches all companies from salesforce.company table.
        
        Args:
            connection: Database connection
            
        Returns:
            list[CompanyInDB]: List of all active companies
        """
        logger.debug("Fetching all companies")
        
        find_companies_query = """
        SELECT id, name, gst_no, cin_no, address, is_active, created_at, updated_at
        FROM company
        WHERE is_active = TRUE;
        """
        
        await self.__set_search_path(connection, "salesforce")
        rs = await connection.fetch(find_companies_query)
        
        companies = []
        for record in rs:
            companies.append(
                CompanyInDB(
                    id=record["id"],
                    name=record["name"],
                    gst_no=record["gst_no"],
                    cin_no=record["cin_no"],
                    address=record["address"],
                    is_active=record["is_active"],
                    created_at=record["created_at"],
                    updated_at=record["updated_at"],
                )
            )
        
        logger.debug(
            "Companies fetched",
            company_count=len(companies),
        )
        return companies

    async def __update_company(
        self,
        connection: Connection,
        company_id: UUID,
        name: Optional[str] = None,
        gst_no: Optional[str] = None,
        cin_no: Optional[str] = None,
        address: Optional[str] = None,
    ) -> CompanyInDB:
        """Update company details.
        
        Updates company in salesforce.company table.
        
        Args:
            connection: Database connection
            company_id: UUID of the company to update
            name: New name (optional)
            gst_no: New GST number (optional)
            cin_no: New CIN number (optional)
            address: New address (optional)
            
        Returns:
            CompanyInDB: Updated company object
            
        Raises:
            ValueError: If no fields provided for update
            CompanyNotFoundException: If company not found
            CompanyAlreadyExistsException: If GST or CIN already exists
        """
        logger.debug(
            "Updating company",
            company_id=str(company_id),
            has_name=name is not None,
            has_gst=gst_no is not None,
            has_cin=cin_no is not None,
            has_address=address is not None,
        )
        
        update_fields = []
        update_values = []
        
        if name is not None:
            update_fields.append(f"name = ${len(update_values) + 2}")
            update_values.append(name)
        if gst_no is not None:
            update_fields.append(f"gst_no = ${len(update_values) + 2}")
            update_values.append(gst_no)
        if cin_no is not None:
            update_fields.append(f"cin_no = ${len(update_values) + 2}")
            update_values.append(cin_no)
        if address is not None:
            update_fields.append(f"address = ${len(update_values) + 2}")
            update_values.append(address)
        
        if not update_fields:
            logger.error("No fields provided for update", company_id=str(company_id))
            raise ValueError("At least one field must be provided for update")
        
        await self.__set_search_path(connection, "salesforce")
        
        update_query = f"""
        UPDATE company
        SET {', '.join(update_fields)}
        WHERE id = $1
        RETURNING *;
        """
        
        try:
            rs = await connection.fetchrow(update_query, company_id, *update_values)
        except UniqueViolationError as e:
            error_msg = str(e)
            field = "gst_no" if "gst_no" in error_msg else "cin_no"
            logger.error(
                "Company update failed - duplicate value",
                company_id=str(company_id),
                field=field,
                error=error_msg,
            )
            raise CompanyAlreadyExistsException(
                field=field,
                message=f"Company with this {field} already exists."
            ) from e
        
        if not rs:
            logger.warning("Company not found for update", company_id=str(company_id))
            raise CompanyNotFoundException(field="id")
        
        logger.info("Company updated successfully", company_id=str(company_id))
        return CompanyInDB(
            id=rs["id"],
            name=rs["name"],
            gst_no=rs["gst_no"],
            cin_no=rs["cin_no"],
            address=rs["address"],
            is_active=rs["is_active"],
            created_at=rs["created_at"],
            updated_at=rs["updated_at"],
        )

    async def __delete_company(
        self, connection: Connection, company_id: UUID
    ) -> None:
        """Delete a company from the database (soft delete).
        
        Marks company as inactive in salesforce.company table.
        
        Args:
            connection: Database connection
            company_id: UUID of the company to delete
            
        Raises:
            CompanyNotFoundException: If company not found
        """
        logger.debug(
            "Soft deleting company",
            company_id=str(company_id),
        )
        
        delete_company_query = """
        UPDATE company
        SET is_active = FALSE
        WHERE id = $1;
        """
        
        await self.__set_search_path(connection, "salesforce")
        result = await connection.execute(delete_company_query, company_id)
        
        if result == "UPDATE 0":
            logger.warning("Company not found for deletion", company_id=str(company_id))
            raise CompanyNotFoundException(field="id")
        
        logger.info("Company soft deleted successfully", company_id=str(company_id))

    async def create_company(
        self,
        name: str,
        gst_no: str,
        cin_no: str,
        address: str,
        *,
        connection: Optional[Connection] = None,
    ) -> CompanyInDB:
        """Create a new company in the database.
        
        Public interface for company creation. Manages connection pooling if needed.
        
        Args:
            name: Company name
            gst_no: GST number (required)
            cin_no: CIN number (required)
            address: Company address (required)
            connection: Optional existing connection (for transactions)
            
        Returns:
            CompanyInDB: Created company object
        """
        logger.info("create_company called", name=name)
        if connection is None:
            async with self.db_pool.acquire() as conn:
                return await self.__create_company(conn, name, gst_no, cin_no, address)
        return await self.__create_company(connection, name, gst_no, cin_no, address)

    async def get_company_by_id(
        self, company_id: UUID, *, connection: Optional[Connection] = None
    ) -> CompanyInDB:
        """Retrieve a company by ID.
        
        Public interface for fetching company by ID.
        
        Args:
            company_id: Company UUID
            connection: Optional existing connection
            
        Returns:
            CompanyInDB: Company object with complete details
        """
        logger.info("get_company_by_id called", company_id=str(company_id))
        if connection is None:
            async with self.db_pool.acquire() as conn:
                return await self.__get_company_by_id(conn, company_id)
        return await self.__get_company_by_id(connection, company_id)

    async def get_company_by_gst_no(
        self, gst_no: str, *, connection: Optional[Connection] = None
    ) -> CompanyInDB:
        """Retrieve a company by GST number.
        
        Public interface for fetching company by GST number.
        
        Args:
            gst_no: GST number to search for
            connection: Optional existing connection
            
        Returns:
            CompanyInDB: Company object with complete details
        """
        logger.info("get_company_by_gst_no called", gst_no=gst_no)
        if connection is None:
            async with self.db_pool.acquire() as conn:
                return await self.__get_company_by_gst_no(conn, gst_no)
        return await self.__get_company_by_gst_no(connection, gst_no)

    async def get_company_by_cin_no(
        self, cin_no: str, *, connection: Optional[Connection] = None
    ) -> CompanyInDB:
        """Retrieve a company by CIN number.
        
        Public interface for fetching company by CIN number.
        
        Args:
            cin_no: CIN number to search for
            connection: Optional existing connection
            
        Returns:
            CompanyInDB: Company object with complete details
        """
        logger.info("get_company_by_cin_no called", cin_no=cin_no)
        if connection is None:
            async with self.db_pool.acquire() as conn:
                return await self.__get_company_by_cin_no(conn, cin_no)
        return await self.__get_company_by_cin_no(connection, cin_no)

    async def get_all_companies(
        self, *, connection: Optional[Connection] = None
    ) -> list[CompanyInDB]:
        """Retrieve all active companies.
        
        Public interface for fetching all companies.
        
        Args:
            connection: Optional existing connection
            
        Returns:
            list[CompanyInDB]: List of all active companies
        """
        logger.info("get_all_companies called")
        if connection is None:
            async with self.db_pool.acquire() as conn:
                return await self.__get_all_companies(conn)
        return await self.__get_all_companies(connection)

    async def update_company(
        self,
        company_id: UUID,
        name: Optional[str] = None,
        gst_no: Optional[str] = None,
        cin_no: Optional[str] = None,
        address: Optional[str] = None,
        *,
        connection: Optional[Connection] = None,
    ) -> CompanyInDB:
        """Update company details.
        
        Public interface for updating company information.
        
        Args:
            company_id: Company UUID
            name: New name (optional)
            gst_no: New GST number (optional)
            cin_no: New CIN number (optional)
            address: New address (optional)
            connection: Optional existing connection
            
        Returns:
            CompanyInDB: Updated company object
        """
        logger.info("update_company called", company_id=str(company_id))
        if connection is None:
            async with self.db_pool.acquire() as conn:
                return await self.__update_company(conn, company_id, name, gst_no, cin_no, address)
        return await self.__update_company(connection, company_id, name, gst_no, cin_no, address)

    async def delete_company(
        self,
        company_id: UUID,
        *,
        connection: Optional[Connection] = None,
    ) -> None:
        """Delete a company from the database (soft delete).
        
        Public interface for soft-deleting companies.
        
        Args:
            company_id: Company UUID
            connection: Optional existing connection
        """
        logger.info(
            "delete_company called",
            company_id=str(company_id),
        )
        if connection is None:
            async with self.db_pool.acquire() as conn:
                return await self.__delete_company(conn, company_id)
        return await self.__delete_company(connection, company_id)
