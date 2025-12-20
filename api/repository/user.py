from uuid import UUID
from api.database import DatabasePool
from typing import Optional
from asyncpg import Connection, UniqueViolationError, ForeignKeyViolationError
from uuid_utils.compat import uuid7
from api.exceptions.users import UserAlreadyExistsException, UserNotFoundException
from api.exceptions.company import CompanyNotFoundException
from api.exceptions.areas import AreaNotFoundException
from api.exceptions.roles import RoleNotFoundException
from api.models.users import UserInDB
import structlog

logger = structlog.get_logger(__name__)

#019b368a7f187fd19501ae8814b5c588
class UserRepository:
    """Repository for managing user data across salesforce and company-specific schemas.
    
    This repository handles user operations in a multi-tenant architecture where:
    - User basic info is stored in the 'salesforce' schema
    - User membership details are stored in company-specific schemas (named by company_id)
    
    Attributes:
        db_pool: Database connection pool for executing queries
    """
    
    def __init__(self, db_pool: DatabasePool):
        """Initialize the UserRepository with a database pool.
        
        Args:
            db_pool: DatabasePool instance for managing database connections
        """
        self.db_pool = db_pool
        logger.debug("UserRepository initialized")

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
    
    def __get_schema_name(self, company_id: UUID) -> str:
        """Get the schema name for a given company ID.
        
        Args:
            company_id: UUID of the company
        Returns:
            str: Schema name derived from company ID
        """
        return f"_{str(company_id).replace("-", "")}_"

    async def __create_user(
        self,
        connection: Connection,
        username: str,
        name: str,
        contact_no: str,
        company_id: UUID,
        role: str,
        area_id: Optional[int] = None,
    ) -> UserInDB:
        """Create a new user in the database.
        
        Creates user records in both:
        1. salesforce.users table (basic user info)
        2. <company_id>.members table (company-specific membership info)
        
        Args:
            connection: Database connection
            username: Unique username for the user
            name: Full name of the user
            contact_no: Contact phone number
            company_id: UUID of the company the user belongs to
            role: Role of the user in the company
            area_id: Optional area assignment for the user
            
        Returns:
            UserInDB: Created user object with all details
            
        Raises:
            UserAlreadyExistsError: If username already exists
        """
        uid = uuid7()
        logger.debug(
            "Creating new user",
            user_id=str(uid),
            username=username,
            company_id=str(company_id),
            role=role,
        )
        
        query1 = """
        INSERT INTO users (id, username, name, contact_no,company_id) VALUES ($1, $2, $3, $4,$5)
        RETURNING *;
        """
        query2 = """
        INSERT INTO members (id, role, area_id) VALUES ($1, $2, $3)
        RETURNING *;
        """
        try:
            await self.__set_search_path(connection, "salesforce")
            rs1 = await connection.fetchrow(
                query1, uid, username, name, contact_no, company_id
            )
            logger.debug("User record created in salesforce schema", user_id=str(uid))
            
            await self.__set_search_path(connection, self.__get_schema_name(company_id))
            rs2 = await connection.fetchrow(query2, uid, role, area_id)
            logger.debug(
                "Member record created in company schema",
                user_id=str(uid),
                schema=self.__get_schema_name(company_id),
            )
        except UniqueViolationError as e:
            logger.error(
                "User creation failed - username already exists",
                username=username,
                error=str(e),
            )
            raise UserAlreadyExistsException(
                field="username",
                message="User with this username already exists."
            ) from e
        except ForeignKeyViolationError as e:
            logger.error(
                "User creation failed - foreign key violation",
                username=username,
                company_id=str(company_id),
                area_id=area_id,
                error=str(e),
            )
            # Determine which foreign key failed
            error_msg = str(e).lower()
            if "company" in error_msg:
                raise CompanyNotFoundException(
                    field="company_id",
                    message=f"Company with id {company_id} does not exist."
                ) from e
            elif "role" in error_msg:
                raise RoleNotFoundException(
                    field="role",
                    message=f"Role '{role}' does not exist."
                ) from e
            elif "area" in error_msg:
                raise AreaNotFoundException(
                    field="area_id",
                    message=f"Area with id {area_id} does not exist."
                ) from e
            else:
                raise UserNotFoundException(
                    field="foreign_key",
                    message="Referenced entity does not exist."
                ) from e
        
        logger.info("User created successfully", user_id=str(uid), username=username)
        return UserInDB(
            id=rs1["id"],
            username=rs1["username"],
            name=rs1["name"],
            contact_no=rs1["contact_no"],
            company_id=rs1["company_id"],
            role=rs2["role"],
            area_id=rs2["area_id"],
            is_active=rs1["is_active"],
            created_at=rs2["created_at"],
            updated_at=rs2["updated_at"],
        )

    async def __get_user_by_username(
        self, connection: Connection, username: str
    ) -> UserInDB:
        """Retrieve a user by username.
        
        Queries both salesforce.users and <company_id>.members tables to get complete user info.
        
        Args:
            connection: Database connection
            username: Username to search for
            
        Returns:
            UserInDB: Complete user object with membership details
            
        Raises:
            UserNotFoundException: If user not found in either schema
        """
        logger.debug("Fetching user by username", username=username)
        
        find_user_query = """
        SELECT id, username, name, contact_no, company_id, is_active, created_at, updated_at
        FROM users
        WHERE username = $1;
        """
        find_user_in_company_query = """
        SELECT id, role, area_id,is_active, created_at, updated_at
        FROM members
        WHERE id = $1;
        """
        await self.__set_search_path(connection, "salesforce")
        rs = await connection.fetchrow(find_user_query, username)
        
        if rs:
            company_id = rs["company_id"]
            user_id = rs["id"]
            logger.debug(
                "User found in salesforce schema",
                user_id=str(user_id),
                username=username,
                company_id=str(company_id),
            )
            
            await self.__set_search_path(connection, self.__get_schema_name(company_id))
            rs_company = await connection.fetchrow(
                find_user_in_company_query, user_id
            )
            
            if rs_company:
                logger.debug(
                    "User membership found in company schema",
                    user_id=str(user_id),
                    role=rs_company["role"],
                )
                return UserInDB(
                    id=rs["id"],
                    username=rs["username"],
                    name=rs["name"],
                    contact_no=rs["contact_no"],
                    company_id=rs["company_id"],
                    role=rs_company["role"],
                    area_id=rs_company["area_id"],
                    is_active=rs_company["is_active"],
                    created_at=rs_company["created_at"],
                    updated_at=rs_company["updated_at"],
                )
            logger.warning(
                "User found but no membership record",
                user_id=str(user_id),
                username=username,
            )
        
        logger.warning("User not found", username=username)
        raise UserNotFoundException(field="username")

    async def __get_user_by_id(
        self, connection: Connection, user_id: UUID, company_id: UUID
    ) -> UserInDB:
        """Retrieve a user by ID.
        
        Args:
            connection: Database connection
            user_id: UUID of the user
            company_id: UUID of the company for schema context
            
        Returns:
            UserInDB: Complete user object with membership details
            
        Raises:
            UserNotFoundException: If user not found
        """
        logger.debug(
            "Fetching user by ID",
            user_id=str(user_id),
            company_id=str(company_id),
        )
        
        find_user_query = """
        SELECT id, username, name, contact_no, company_id, is_active, created_at, updated_at
        FROM users
        WHERE id = $1;
        """
        find_user_in_company_query = """
        SELECT id, role, area_id,is_active, created_at, updated_at
        FROM members
        WHERE id = $1;
        """
        await self.__set_search_path(connection, "salesforce")
        rs = await connection.fetchrow(find_user_query, user_id)
        
        if rs:
            logger.debug("User found in salesforce schema", user_id=str(user_id))
            await self.__set_search_path(connection, self.__get_schema_name(company_id))
            rs_company = await connection.fetchrow(
                find_user_in_company_query, user_id
            )
            
            if rs_company:
                logger.debug(
                    "User membership found",
                    user_id=str(user_id),
                    role=rs_company["role"],
                )
                return UserInDB(
                    id=rs["id"],
                    username=rs["username"],
                    name=rs["name"],
                    contact_no=rs["contact_no"],
                    company_id=rs["company_id"],
                    role=rs_company["role"],
                    area_id=rs_company["area_id"],
                    is_active=rs_company["is_active"],
                    created_at=rs_company["created_at"],
                    updated_at=rs_company["updated_at"],
                )
            logger.warning(
                "User found but no membership record",
                user_id=str(user_id),
            )

        logger.warning("User not found", user_id=str(user_id))
        raise UserNotFoundException(field="id")

    async def __get_users_by_company_id(
        self, connection: Connection, company_id: UUID
    ) -> list[UserInDB]:
        """Retrieve all users by company ID.
        
        Joins salesforce.users with company-specific members table.
        
        Args:
            connection: Database connection
            company_id: UUID of the company
            
        Returns:
            list[UserInDB]: List of all users in the company
        """
        logger.debug("Fetching all users for company", company_id=str(company_id))
        
        find_users_query = """
        SELECT u.id, u.username, u.name, u.contact_no, u.company_id, m.role, m.area_id, m.is_active, m.created_at, m.updated_at
        FROM salesforce.users u
        JOIN members m ON u.id = m.id
        WHERE u.company_id = $1;
        """
        await self.__set_search_path(connection, self.__get_schema_name(company_id))
        rs = await connection.fetch(find_users_query, company_id)
        
        users = []
        for record in rs:
            users.append(
                UserInDB(
                    id=record["id"],
                    username=record["username"],
                    name=record["name"],
                    contact_no=record["contact_no"],
                    company_id=record["company_id"],
                    role=record["role"],
                    area_id=record["area_id"],
                    is_active=record["is_active"],
                    created_at=record["created_at"],
                    updated_at=record["updated_at"],
                )
            )
        
        logger.debug(
            "Users fetched for company",
            company_id=str(company_id),
            user_count=len(users),
        )
        return users

    async def __get_user_by_role(
        self, connection: Connection, role: str, company_id: UUID
    ) -> list[UserInDB]:
        """Retrieve users by role within a company.
        
        Args:
            connection: Database connection
            role: Role name to filter by
            company_id: UUID of the company
            
        Returns:
            list[UserInDB]: List of users with the specified role
        """
        logger.debug(
            "Fetching users by role",
            role=role,
            company_id=str(company_id),
        )
        
        find_users_query = """
        SELECT u.id, u.username, u.name, u.contact_no, u.company_id, m.role, m.area_id, m.is_active, m.created_at, m.updated_at
        FROM salesforce.users u
        JOIN members m ON u.id = m.id
        WHERE m.role = $1 AND u.company_id = $2;
        """
        await self.__set_search_path(connection, self.__get_schema_name(company_id))
        rs = await connection.fetch(find_users_query, role, company_id)
        
        users = []
        for record in rs:
            users.append(
                UserInDB(
                    id=record["id"],
                    username=record["username"],
                    name=record["name"],
                    contact_no=record["contact_no"],
                    company_id=record["company_id"],
                    role=record["role"],
                    area_id=record["area_id"],
                    is_active=record["is_active"],
                    created_at=record["created_at"],
                    updated_at=record["updated_at"],
                )
            )
        
        logger.debug(
            "Users fetched by role",
            role=role,
            company_id=str(company_id),
            user_count=len(users),
        )
        return users

    async def __update_user(
        self,
        connection: Connection,
        company_id: UUID,
        user_id: UUID,
        name: Optional[str] = None,
        contact_no: Optional[str] = None,
        role: Optional[str] = None,
        area_id: Optional[int] = None,
    ) -> UserInDB:
        """Update user details.
        
        Updates can span both salesforce.users (name, contact_no) and 
        company-specific members (role, area_id) tables.
        
        Args:
            connection: Database connection
            company_id: UUID of the company for schema context
            user_id: UUID of the user to update
            name: New name (optional)
            contact_no: New contact number (optional)
            role: New role (optional)
            area_id: New area assignment (optional)
            
        Returns:
            UserInDB: Updated user object
            
        Raises:
            ValueError: If no fields provided for update
        """
        logger.debug(
            "Updating user",
            user_id=str(user_id),
            company_id=str(company_id),
            has_name=name is not None,
            has_contact=contact_no is not None,
            has_role=role is not None,
            has_area=area_id is not None,
        )
        
        # Update salesforce.users table
        update_fields = []
        update_values = []
        if name is not None:
            update_fields.append("name = $" + str(len(update_values) + 1))
            update_values.append(name)
        if contact_no is not None:
            update_fields.append("contact_no = $" + str(len(update_values) + 1))
            update_values.append(contact_no)
        
        if not update_fields and role is None and area_id is None:
            logger.error("Update failed - no fields provided", user_id=str(user_id))
            raise ValueError("No fields to update.")
        
        rs1 = None
        if update_fields:
            update_query = f"""
            UPDATE users
            SET {", ".join(update_fields)}, updated_at = NOW()
            WHERE id = ${len(update_values) + 1}
            RETURNING *;
            """
            update_values.append(user_id)
            try:
                await self.__set_search_path(connection, "salesforce")
                rs1 = await connection.fetchrow(update_query, *update_values)
                logger.debug("User record updated in salesforce schema", user_id=str(user_id))
            except UniqueViolationError as e:
                logger.error(
                    "User update failed - unique violation in salesforce schema",
                    user_id=str(user_id),
                    error=str(e),
                )
                field = "contact_no" if contact_no is not None else "name"
                raise UserAlreadyExistsException(
                    field=field,
                    message=f"User with this {field} already exists."
                ) from e
        
        # Update company-specific members table
        update_fields = []
        update_values = []
        if role is not None:
            update_fields.append("role = $" + str(len(update_values) + 1))
            update_values.append(role)
        if area_id is not None:
            update_fields.append("area_id = $" + str(len(update_values) + 1))
            update_values.append(area_id)
        
        rs2 = None
        if update_fields:
            update_query = f"""
            UPDATE members
            SET {", ".join(update_fields)}, updated_at = NOW()
            WHERE id = ${len(update_values) + 1}
            RETURNING *;
            """
            update_values.append(user_id)
            try:
                await self.__set_search_path(connection, self.__get_schema_name(company_id))
                rs2 = await connection.fetchrow(update_query, *update_values)
                logger.debug("Member record updated in company schema", user_id=str(user_id))
            except UniqueViolationError as e:
                logger.error(
                    "User update failed - unique violation in company schema",
                    user_id=str(user_id),
                    error=str(e),
                )
                field = "role" if role is not None else "area_id"
                raise UserAlreadyExistsException(
                    field=field,
                    message=f"A constraint violation occurred for {field}."
                ) from e
            except ForeignKeyViolationError as e:
                logger.error(
                    "User update failed - foreign key violation in company schema",
                    user_id=str(user_id),
                    role=role,
                    area_id=area_id,
                    error=str(e),
                )
                # Determine which foreign key failed
                error_msg = str(e).lower()
                if "role" in error_msg:
                    raise RoleNotFoundException(
                        field="role",
                        message=f"Role '{role}' does not exist."
                    ) from e
                elif "area" in error_msg:
                    raise AreaNotFoundException(
                        field="area_id",
                        message=f"Area with id {area_id} does not exist."
                    ) from e
                else:
                    raise UserNotFoundException(
                        field="foreign_key",
                        message="Referenced entity does not exist."
                    ) from e
        
        # Fetch complete user data if only one table was updated
        if rs1 is None:
            await self.__set_search_path(connection, "salesforce")
            rs1 = await connection.fetchrow(
                "SELECT * FROM users WHERE id = $1", user_id
            )
        if rs2 is None:
            await self.__set_search_path(connection, self.__get_schema_name(company_id))
            rs2 = await connection.fetchrow(
                "SELECT * FROM members WHERE id = $1", user_id
            )
        
        logger.info("User updated successfully", user_id=str(user_id))
        return UserInDB(
            id=rs1["id"],
            username=rs1["username"],
            name=rs1["name"],
            contact_no=rs1["contact_no"],
            company_id=rs1["company_id"],
            role=rs2["role"],
            area_id=rs2["area_id"],
            is_active=rs1["is_active"],
            created_at=rs2["created_at"],
            updated_at=rs2["updated_at"],
        )

    async def __delete_user(
        self, connection: Connection, user_id: UUID, company_id: UUID
    ) -> None:
        """Delete a user from the database (soft delete).
        
        Marks user as inactive in both salesforce.users and company-specific members tables.
        
        Args:
            connection: Database connection
            user_id: UUID of the user to delete
            company_id: UUID of the company for schema context
        """
        logger.debug(
            "Soft deleting user",
            user_id=str(user_id),
            company_id=str(company_id),
        )
        
        delete_user_query = """
        UPDATE users
        SET is_active = FALSE
        WHERE id = $1 AND company_id = $2;
        """
        await self.__set_search_path(connection, "salesforce")
        await connection.execute(delete_user_query, user_id, company_id)
        logger.debug("User marked inactive in salesforce schema", user_id=str(user_id))
        
        delete_member_query = """
        UPDATE members
        SET is_active = FALSE
        WHERE id = $1;
        """
        await self.__set_search_path(connection, self.__get_schema_name(company_id))
        await connection.execute(delete_member_query, user_id)
        logger.debug("Member marked inactive in company schema", user_id=str(user_id))
        
        logger.info("User soft deleted successfully", user_id=str(user_id))

    async def create_user(
        self,
        username: str,
        name: str,
        contact_no: str,
        company_id: UUID,
        role: str,
        area_id: Optional[int] = None,
        *,
        connection: Optional[Connection] = None,
    ) -> UserInDB:
        """Create a new user in the database.
        
        Public interface for user creation. Manages connection pooling if needed.
        
        Args:
            username: Unique username
            name: Full name
            contact_no: Contact phone number
            company_id: Company UUID
            role: User role
            area_id: Optional area assignment
            connection: Optional existing connection (for transactions)
            
        Returns:
            UserInDB: Created user object
        """
        logger.info("create_user called", username=username, company_id=str(company_id))
        if connection is None:
            async with self.db_pool.acquire() as connection:
                return await self.__create_user(
                    connection, username, name, contact_no, company_id, role, area_id
                )
        return await self.__create_user(
            connection, username, name, contact_no, company_id, role, area_id
        )

    async def get_user_by_username(
        self, username: str, *, connection: Optional[Connection] = None
    ) -> UserInDB:
        """Retrieve a user by username.
        
        Public interface for fetching user by username.
        
        Args:
            username: Username to search for
            connection: Optional existing connection
            
        Returns:
            UserInDB: User object with complete details
        """
        logger.info("get_user_by_username called", username=username)
        if connection is None:
            async with self.db_pool.acquire() as connection:
                return await self.__get_user_by_username(connection, username)
        return await self.__get_user_by_username(connection, username)

    async def get_user_by_id(
        self,
        user_id: UUID,
        company_id: UUID,
        *,
        connection: Optional[Connection] = None,
    ) -> UserInDB:
        """Retrieve a user by ID.
        
        Public interface for fetching user by ID.
        
        Args:
            user_id: User UUID
            company_id: Company UUID
            connection: Optional existing connection
            
        Returns:
            UserInDB: User object with complete details
        """
        logger.info(
            "get_user_by_id called",
            user_id=str(user_id),
            company_id=str(company_id),
        )
        if connection is None:
            async with self.db_pool.acquire() as connection:
                return await self.__get_user_by_id(connection, user_id, company_id)
        return await self.__get_user_by_id(connection, user_id, company_id)

    async def get_users_by_company_id(
        self, company_id: UUID, *, connection: Optional[Connection] = None
    ) -> list[UserInDB]:
        """Retrieve all users by company ID.
        
        Public interface for fetching all company users.
        
        Args:
            company_id: Company UUID
            connection: Optional existing connection
            
        Returns:
            list[UserInDB]: List of all users in the company
        """
        logger.info("get_users_by_company_id called", company_id=str(company_id))
        if connection is None:
            async with self.db_pool.acquire() as connection:
                return await self.__get_users_by_company_id(connection, company_id)
        return await self.__get_users_by_company_id(connection, company_id)

    async def get_user_by_role(
        self, role: str, company_id: UUID, *, connection: Optional[Connection] = None
    ) -> list[UserInDB]:
        """Retrieve users by role within a company.
        
        Public interface for fetching users by role.
        
        Args:
            role: Role name to filter by
            company_id: Company UUID
            connection: Optional existing connection
            
        Returns:
            list[UserInDB]: List of users with the specified role
        """
        logger.info(
            "get_user_by_role called",
            role=role,
            company_id=str(company_id),
        )
        if connection is None:
            async with self.db_pool.acquire() as connection:
                return await self.__get_user_by_role(connection, role, company_id)
        return await self.__get_user_by_role(connection, role, company_id)

    async def update_user(
        self,
        company_id: UUID,
        user_id: UUID,
        name: Optional[str] = None,
        contact_no: Optional[str] = None,
        role: Optional[str] = None,
        area_id: Optional[int] = None,
        *,
        connection: Optional[Connection] = None,
    ) -> UserInDB:
        """Update user details.
        
        Public interface for updating user information.
        
        Args:
            company_id: Company UUID
            user_id: User UUID to update
            name: New name (optional)
            contact_no: New contact number (optional)
            role: New role (optional)
            area_id: New area assignment (optional)
            connection: Optional existing connection
            
        Returns:
            UserInDB: Updated user object
        """
        logger.info("update_user called", user_id=str(user_id), company_id=str(company_id))
        if connection is None:
            async with self.db_pool.acquire() as connection:
                return await self.__update_user(
                    connection, company_id, user_id, name, contact_no, role, area_id
                )
        return await self.__update_user(
            connection, company_id, user_id, name, contact_no, role, area_id
        )

    async def delete_user(
        self,
        user_id: UUID,
        company_id: UUID,
        *,
        connection: Optional[Connection] = None,
    ) -> None:
        """Delete a user from the database (soft delete).
        
        Public interface for soft-deleting users.
        
        Args:
            user_id: User UUID to delete
            company_id: Company UUID
            connection: Optional existing connection
        """
        logger.info(
            "delete_user called",
            user_id=str(user_id),
            company_id=str(company_id),
        )
        if connection is None:
            async with self.db_pool.acquire() as connection:
                return await self.__delete_user(connection, user_id, company_id)
        return await self.__delete_user(connection, user_id, company_id)
