from typing import Optional
from uuid import UUID

from uuid_utils.compat import uuid7
from api.database import DatabasePool
from api.exceptions.area import AreaNotFoundException
from api.exceptions.company import CompanyNotFoundException
from api.exceptions.role import RoleNotFoundException
from api.exceptions.user import (
    UserAlreadyExistsException,
    UserException,
    UserNotFoundException,
)
from api.models.user import (
    BankDetails,
    UserCreate,
    UserDetailsResponse,
    UserInDB,
    UserListResponse,
    UserUpdate,
)
from asyncpg import Connection, UniqueViolationError, ForeignKeyViolationError
import structlog

from api.repository.utils import get_schema_name, set_search_path

logger = structlog.get_logger(__name__)


class UserRepository:
    def __init__(self, db_pool: DatabasePool):
        self.db_pool = db_pool

    async def __create_normal_user(
        self, connection: Connection, user: UserCreate
    ) -> UserInDB:
        """Create a new normal user in the database."""
        uid = uuid7()
        logger.debug(
            "Creating new user",
            user_id=str(uid),
            username=user.username,
            company_id=str(user.company_id),
            role=user.role,
            area_id=user.area_id,
        )

        query1 = """
        INSERT INTO users (id, username, name, contact_no,company_id) VALUES ($1, $2, $3, $4,$5)
        RETURNING *;
        """
        query2 = """
        INSERT INTO members (id, role, area_id, bank_details) VALUES ($1, $2, $3, $4)
        RETURNING *;
        """
        try:
            await set_search_path(connection, "salesforce")
            rs1 = await connection.fetchrow(
                query1, uid, user.username, user.name, user.contact_no, user.company_id
            )
            logger.debug("User record created in salesforce schema", user_id=str(uid))

            await set_search_path(connection, get_schema_name(user.company_id))
            rs2 = await connection.fetchrow(
                query2,
                uid,
                user.role,
                user.area_id,
                user.bank_details.model_dump_json() if user.bank_details else None,
            )
            logger.debug(
                "Member record created in company schema",
                user_id=str(uid),
                schema=get_schema_name(user.company_id),
            )
        except UniqueViolationError as e:
            logger.error(
                "User creation failed - username already exists",
                username=user.username,
                error=str(e),
            )
            raise UserAlreadyExistsException(
                field="username", message="User with this username already exists."
            ) from e
        except ForeignKeyViolationError as e:
            logger.error(
                "User creation failed - foreign key violation",
                username=user.username,
                company_id=str(user.company_id),
                area_id=user.area_id,
                error=str(e),
            )
            # Determine which foreign key failed
            error_msg = str(e).lower()
            if "company" in error_msg:
                raise CompanyNotFoundException(
                    field="company_id",
                    message=f"Company with id {user.company_id} does not exist.",
                ) from e
            elif "role" in error_msg:
                raise RoleNotFoundException(
                    field="role", message=f"Role '{user.role}' does not exist."
                ) from e
            elif "area" in error_msg:
                raise AreaNotFoundException(
                    field="area_id",
                    message=f"Area with id {user.area_id} does not exist.",
                ) from e
            else:
                raise UserNotFoundException(
                    field="foreign_key", message="Referenced entity does not exist."
                ) from e
        if not rs1 or not rs2:
            logger.error(
                "User creation failed - incomplete records",
                username=user.username,
            )
            raise UserException(message="Failed to create user record.")
        logger.info(
            "User created successfully", user_id=str(uid), username=user.username
        )
        return UserInDB(
            id=rs1["id"],
            username=rs1["username"],
            name=rs1["name"],
            contact_no=rs1["contact_no"],
            company_id=rs1["company_id"],
            role=rs2["role"],
            area_id=rs2["area_id"],
            is_super_admin=rs1["is_super_admin"],
            is_active=rs1["is_active"],
            created_at=rs2["created_at"],
            bank_details=BankDetails.model_validate_json(rs2["bank_details"]) if rs2["bank_details"] else None,
            updated_at=rs2["updated_at"],
        )

    async def __create_super_admin(
        self, connection: Connection, user: UserCreate
    ) -> UserInDB:
        """Create a new super admin user in the database."""
        uid = uuid7()
        logger.debug(
            "Creating new super admin user",
            user_id=str(uid),
            username=user.username,
        )
        query1 = """
        INSERT INTO users (id, username, name, contact_no,is_super_admin) VALUES ($1, $2, $3, $4,TRUE)
        RETURNING *;
        """
        try:
            await set_search_path(connection, "salesforce")
            rs1 = await connection.fetchrow(
                query1, uid, user.username, user.name, user.contact_no
            )
            logger.debug(
                "Super admin user record created in salesforce schema", user_id=str(uid)
            )

        except UniqueViolationError as e:
            logger.error(
                "Super admin user creation failed - username already exists",
                username=user.username,
                error=str(e),
            )
            raise UserAlreadyExistsException(
                field="username", message="User with this username already exists."
            ) from e

        if not rs1:
            logger.error(
                "Super admin user creation failed - incomplete records",
                username=user.username,
            )
            raise Exception("Failed to create super admin user record.")
        logger.info(
            "Super admin user created successfully",
            user_id=str(uid),
            username=user.username,
        )
        return UserInDB(
            id=rs1["id"],
            username=rs1["username"],
            name=rs1["name"],
            contact_no=rs1["contact_no"],
            company_id=None,
            role="SUPER_ADMIN",
            area_id=None,
            is_super_admin=rs1["is_super_admin"],
            bank_details=None,
            is_active=rs1["is_active"],
            created_at=rs1["created_at"],
            updated_at=rs1["updated_at"],
        )

    async def create_user(
        self, user: UserCreate, connection: Optional[Connection] = None
    ) -> UserInDB:
        """Create a new user in the database."""
        create_user_func = (
            self.__create_normal_user
            if not user.is_super_admin
            else self.__create_super_admin
        )
        if connection is None:
            async with self.db_pool.transaction() as connection:
                return await create_user_func(connection, user)
        return await create_user_func(connection, user)

    async def get_user_by_username(
        self, username: str, connection: Optional[Connection] = None
    ) -> UserDetailsResponse:
        """Get a user by username."""
        if connection is None:
            async with self.db_pool.acquire() as connection:
                return await self.__get_user_by_username(connection, username)
        return await self.__get_user_by_username(connection, username)

    async def __get_user_by_username(
        self, connection: Connection, username: str
    ) -> UserDetailsResponse:
        """Get a user by username."""
        company_id = await connection.fetchval(
            "SELECT company_id FROM salesforce.users WHERE username = $1", username
        )
        print("Company ID:", company_id)
        if not company_id:
            user = await connection.fetchrow(
                """
            SELECT u.id, u.username, u.name, u.contact_no, u.company_id, u.is_super_admin, u.is_active, u.created_at, u.updated_at
            FROM salesforce.users u
            WHERE u.username = $1;
            """,
                username,
            )
            if not user or not user["is_super_admin"]:
                raise UserNotFoundException(field="username", message="User not found.")
            return UserDetailsResponse(
                id=user["id"],
                username=user["username"],
                name=user["name"],
                contact_no=user["contact_no"],
                company_id=None,
                company_name=None,
                is_super_admin=user["is_super_admin"],
                is_active=user["is_active"],
                created_at=user["created_at"],
                updated_at=user["updated_at"],
                role="SUPER_ADMIN",
                area_id=None,
                area_name=None,
                area_type=None,
                bank_details=None,
            )
        await set_search_path(connection, get_schema_name(company_id))
        query = """
        SELECT u.id, u.username, u.name, u.contact_no, u.company_id, u.is_super_admin, u.is_active, u.created_at, u.updated_at,
        m.role, m.area_id, m.bank_details,c.name as company_name, a.name as area_name, a.type as area_type
        FROM salesforce.users u
        JOIN salesforce.company c ON u.company_id = c.id
        JOIN members m ON u.id = m.id
        LEFT JOIN areas a ON m.area_id = a.id
        WHERE u.username = $1;
        """
        rs = await connection.fetchrow(query, username)
        if not rs:
            raise UserNotFoundException(field="username", message="User not found.")
        return UserDetailsResponse(
            id=rs["id"],
            username=rs["username"],
            name=rs["name"],
            contact_no=rs["contact_no"],
            company_id=rs["company_id"],
            company_name=rs["company_name"],
            is_super_admin=rs["is_super_admin"],
            is_active=rs["is_active"],
            created_at=rs["created_at"],
            updated_at=rs["updated_at"],
            role=rs["role"],
            area_id=rs["area_id"],
            area_name=rs["area_name"],
            area_type=rs["area_type"],
            bank_details=BankDetails.model_validate_json(rs["bank_details"])
            if rs["bank_details"]
            else None,
        )

    async def get_user_by_id(
        self, user_id: UUID, connection: Optional[Connection] = None
    ) -> UserDetailsResponse:
        """Get a user by id."""
        if connection is None:
            async with self.db_pool.acquire() as connection:
                return await self.__get_user_by_id(connection, user_id)
        return await self.__get_user_by_id(connection, user_id)

    async def __get_user_by_id(
        self, connection: Connection, user_id: UUID
    ) -> UserDetailsResponse:
        """Get a user by id."""
        company_id = await connection.fetchval(
            "SELECT company_id FROM salesforce.users WHERE id = $1", user_id
        )
        if not company_id:
            user = await connection.fetchrow(
                """
            SELECT u.id, u.username, u.name, u.contact_no, u.company_id, u.is_super_admin, u.is_active, u.created_at, u.updated_at
            FROM salesforce.users u
            WHERE u.id = $1;
            """,
                user_id,
            )
            if not user or not user["is_super_admin"]:
                raise UserNotFoundException(field="username", message="User not found.")
            return UserDetailsResponse(
                id=user["id"],
                username=user["username"],
                name=user["name"],
                contact_no=user["contact_no"],
                company_id=None,
                company_name=None,
                is_super_admin=user["is_super_admin"],
                is_active=user["is_active"],
                created_at=user["created_at"],
                updated_at=user["updated_at"],
                role="SUPER_ADMIN",
                area_id=None,
                area_name=None,
                area_type=None,
                bank_details=None,
            )
        await set_search_path(connection, get_schema_name(company_id))
        query = """
        SELECT u.id, u.username, u.name, u.contact_no, u.company_id, u.is_super_admin, u.is_active, u.created_at, u.updated_at,
        m.role, m.area_id, m.bank_details,c.name as company_name, a.name as area_name, a.type as area_type
        FROM salesforce.users u
        JOIN salesforce.company c ON u.company_id = c.id
        JOIN members m ON u.id = m.id
        LEFT JOIN areas a ON m.area_id = a.id
        WHERE u.id = $1;
        """
        rs = await connection.fetchrow(query, user_id)
        if not rs:
            raise UserNotFoundException(field="user_id", message="User not found.")
        return UserDetailsResponse(
            id=rs["id"],
            username=rs["username"],
            name=rs["name"],
            contact_no=rs["contact_no"],
            company_id=rs["company_id"],
            company_name=rs["company_name"],
            is_super_admin=rs["is_super_admin"],
            is_active=rs["is_active"],
            created_at=rs["created_at"],
            updated_at=rs["updated_at"],
            role=rs["role"],
            area_id=rs["area_id"],
            area_name=rs["area_name"],
            area_type=rs["area_type"],
            bank_details=BankDetails.model_validate_json(rs["bank_details"])
            if rs["bank_details"]
            else None,
        )

    async def get_users_by_company_id(
        self,
        company_id: UUID,
        is_active: Optional[bool] = None,
        limit: int = 20,
        offset: int = 0,
        connection: Optional[Connection] = None,
    ) -> list[UserListResponse]:
        """Get users by company id."""
        if connection is None:
            async with self.db_pool.acquire() as connection:
                return await self.__get_users_by_company_id(
                    connection, company_id, is_active, limit, offset
                )
        return await self.__get_users_by_company_id(
            connection, company_id, is_active, limit, offset
        )

    async def __get_users_by_company_id(
        self,
        connection: Connection,
        company_id: UUID,
        is_active: Optional[bool] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[UserListResponse]:
        """Get users by company id."""
        query = """
        SELECT u.id, u.username, u.name, u.contact_no, u.company_id, u.is_super_admin, u.is_active, u.created_at, u.updated_at,
        m.role, m.area_id, m.bank_details,c.name as company_name, a.name as area_name, a.type as area_type
        FROM salesforce.users u
        JOIN salesforce.company c ON u.company_id = c.id
        JOIN members m ON u.id = m.id
        LEFT JOIN areas a ON m.area_id = a.id
        WHERE u.company_id = $1
        """
        if is_active is not None:
            query += " AND u.is_active = $4"
        query += " ORDER BY u.created_at DESC LIMIT $2 OFFSET $3;"
        await set_search_path(connection, get_schema_name(company_id))
        if is_active is not None:
            rs = await connection.fetch(query, company_id, limit, offset, is_active)
        else:
            rs = await connection.fetch(query, company_id, limit, offset)
        if not rs:
            raise UserNotFoundException(field="company_id", message="Users not found.")
        return [
            UserListResponse(
                id=record["id"],
                username=record["username"],
                name=record["name"],
                contact_no=record["contact_no"],
                company_id=record["company_id"],
                role=record["role"],
                area_id=record["area_id"],
                area_name=record["area_name"],
                is_active=record["is_active"],
            )
            for record in rs
        ]

    async def get_user_by_role(
        self,
        company_id: UUID,
        role: str,
        is_active: Optional[bool] = None,
        limit: int = 20,
        offset: int = 0,
        connection: Optional[Connection] = None,
    ) -> list[UserListResponse]:
        """Get users by role."""
        if connection is None:
            async with self.db_pool.acquire() as connection:
                return await self.__get_user_by_role(
                    connection, company_id, role, is_active, limit, offset
                )
        return await self.__get_user_by_role(
            connection, company_id, role, is_active, limit, offset
        )

    async def __get_user_by_role(
        self,
        connection: Connection,
        company_id: UUID,
        role: str,
        is_active: Optional[bool] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[UserListResponse]:
        """Get users by role."""
        await set_search_path(connection, get_schema_name(company_id))
        query = """
        SELECT u.id, u.username, u.name, u.contact_no, u.company_id, u.is_super_admin, u.is_active, u.created_at, u.updated_at,
        m.role, m.area_id, m.bank_details,c.name as company_name, a.name as area_name, a.type as area_type
        FROM salesforce.users u
        JOIN salesforce.company c ON u.company_id = c.id
        JOIN members m ON u.id = m.id
        JOIN areas a ON m.area_id = a.id
        WHERE m.role = $1
        """
        if is_active is not None:
            query += " AND u.is_active = $4"
        query += " ORDER BY u.created_at DESC LIMIT $2 OFFSET $3;"
        if is_active is not None:
            rs = await connection.fetch(query, role, limit, offset, is_active)
        else:
            rs = await connection.fetch(query, role, limit, offset)
        if not rs:
            raise UserNotFoundException(field="role", message="Users not found.")
        return [
            UserListResponse(
                id=record["id"],
                username=record["username"],
                name=record["name"],
                contact_no=record["contact_no"],
                company_id=record["company_id"],
                role=record["role"],
                area_id=record["area_id"],
                area_name=record["area_name"],
                is_active=record["is_active"],
            )
            for record in rs
        ]

    async def update_user(
        self, user_id: UUID, user: UserUpdate, connection: Optional[Connection] = None
    ) -> UserInDB:
        """Update a user."""
        if connection is None:
            async with self.db_pool.acquire() as connection:
                return await self.__update_user(connection, user_id, user)
        return await self.__update_user(connection, user_id, user)

    async def __update_user(
        self, connection: Connection, user_id: UUID, user: UserUpdate
    ) -> UserInDB:
        logger.debug(
            "Updating user",
            user_id=str(user_id),
            company_id=str(user.company_id),
            has_name=user.name is not None,
            has_contact=user.contact_no is not None,
            has_role=user.role is not None,
            has_area=user.area_id is not None,
        )

        # Update salesforce.users table
        update_fields = []
        update_values = []
        if user.name is not None:
            update_fields.append("name = $" + str(len(update_values) + 1))
            update_values.append(user.name)
        if user.contact_no is not None:
            update_fields.append("contact_no = $" + str(len(update_values) + 1))
            update_values.append(user.contact_no)

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
                await set_search_path(connection, "salesforce")
                rs1 = await connection.fetchrow(update_query, *update_values)
                logger.debug(
                    "User record updated in salesforce schema", user_id=str(user_id)
                )
            except UniqueViolationError as e:
                logger.error(
                    "User update failed - unique violation in salesforce schema",
                    user_id=str(user_id),
                    error=str(e),
                )
                field = "contact_no" if user.contact_no is not None else "name"
                raise UserAlreadyExistsException(
                    field=field, message=f"User with this {field} already exists."
                ) from e

        # Update company-specific members table
        update_fields = []
        update_values = []
        if user.role is not None:
            update_fields.append("role = $" + str(len(update_values) + 1))
            update_values.append(user.role)
        if user.area_id is not None:
            update_fields.append("area_id = $" + str(len(update_values) + 1))
            update_values.append(user.area_id)
        if user.bank_details is not None:
            update_fields.append("bank_details = $" + str(len(update_values) + 1))
            update_values.append(user.bank_details.model_dump_json())

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
                await set_search_path(connection, get_schema_name(user.company_id))
                rs2 = await connection.fetchrow(update_query, *update_values)
                logger.debug(
                    "Member record updated in company schema", user_id=str(user_id)
                )
            except UniqueViolationError as e:
                logger.error(
                    "User update failed - unique violation in company schema",
                    user_id=str(user_id),
                    error=str(e),
                )
                field = "role" if user.role is not None else "area_id"
                raise UserAlreadyExistsException(
                    field=field, message=f"A constraint violation occurred for {field}."
                ) from e
            except ForeignKeyViolationError as e:
                logger.error(
                    "User update failed - foreign key violation in company schema",
                    user_id=str(user_id),
                    role=user.role,
                    area_id=user.area_id,
                    error=str(e),
                )
                # Determine which foreign key failed
                error_msg = str(e).lower()
                if "role" in error_msg:
                    raise RoleNotFoundException(
                        field="role", message=f"Role '{user.role}' does not exist."
                    ) from e
                elif "area" in error_msg:
                    raise AreaNotFoundException(
                        field="area_id",
                        message=f"Area with id {user.area_id} does not exist.",
                    ) from e
                else:
                    raise UserNotFoundException(
                        field="foreign_key", message="Referenced entity does not exist."
                    ) from e

        # Fetch complete user data if only one table was updated
        if rs1 is None:
            await set_search_path(connection, "salesforce")
            rs1 = await connection.fetchrow(
                "SELECT * FROM users WHERE id = $1", user_id
            )
        if rs2 is None:
            await set_search_path(connection, get_schema_name(user.company_id))
            rs2 = await connection.fetchrow(
                "SELECT * FROM members WHERE id = $1", user_id
            )
        if rs1 is not None and rs1["is_super_admin"]:
            logger.debug("Super admin user updated", user_id=str(user_id))
            return UserInDB(
                id=rs1["id"],
                username=rs1["username"],
                name=rs1["name"],
                contact_no=rs1["contact_no"],
                company_id=None,
                role="SUPER_ADMIN",
                area_id=None,
                bank_details=None,
                is_active=rs1["is_active"],
                is_super_admin=rs1["is_super_admin"],
                created_at=rs1["created_at"],
                updated_at=rs1["updated_at"],
            )
        if rs1 is None or rs2 is None:
            logger.error(
                "User update failed - user not found after update", user_id=str(user_id)
            )
            raise UserNotFoundException(field="id")
        logger.info("User updated successfully", user_id=str(user_id))
        return UserInDB(
            id=rs1["id"],
            username=rs1["username"],
            name=rs1["name"],
            contact_no=rs1["contact_no"],
            company_id=rs1["company_id"],
            role=rs2["role"],
            area_id=rs2["area_id"],
            bank_details=BankDetails.model_validate_json(rs2["bank_details"])
            if rs2["bank_details"]
            else None,
            is_active=rs1["is_active"],
            is_super_admin=rs1["is_super_admin"],
            created_at=rs2["created_at"],
            updated_at=rs2["updated_at"],
        )

    async def delete_user(
        self, user_id: UUID, connection: Optional[Connection] = None
    ) -> None:
        """Delete a user."""
        if connection is None:
            async with self.db_pool.transaction() as connection:
                return await self.__delete_user(connection, user_id)
        return await self.__delete_user(connection, user_id)

    async def __delete_user(self, connection: Connection, user_id: UUID) -> None:
        """Delete a user."""
        delete_user_query = """
        UPDATE users
        SET is_active = FALSE
        WHERE id = $1
        RETURNING company_id;
        """
        await set_search_path(connection, "salesforce")
        rs = await connection.fetchrow(delete_user_query, user_id)
        if not rs:
            raise UserNotFoundException(field="user_id", message="User not found.")
        company_id = rs["company_id"]
        logger.debug("User deleted in salesforce schema", user_id=str(user_id))
        if company_id:
            delete_member_query = """
            UPDATE members
            SET is_active = FALSE
            WHERE id = $1;
            """
            await set_search_path(connection, get_schema_name(company_id))
            await connection.execute(delete_member_query, user_id)
            logger.debug("Member deleted in company schema", user_id=str(user_id))

        logger.info("User soft deleted successfully", user_id=str(user_id))

    async def get_users_by_contact_no(
        self, contact_no: str, connection: Optional[Connection] = None
    ) -> list[UserListResponse]:
        """Get users by contact number."""
        if connection is None:
            async with self.db_pool.acquire() as connection:
                return await self.__get_users_by_contact_no(connection, contact_no)
        return await self.__get_users_by_contact_no(connection, contact_no)

    async def __get_users_by_contact_no(
        self, connection: Connection, contact_no: str
    ) -> list[UserListResponse]:
        """Get users by contact number."""
        query = """
        SELECT u.id, u.username, u.name, u.contact_no, u.company_id, u.is_super_admin, u.is_active, u.created_at, u.updated_at,
        c.name as company_name
        FROM salesforce.users u
        JOIN salesforce.company c ON u.company_id = c.id
        WHERE u.contact_no = $1 AND u.is_active = TRUE;
        """
        rs = await connection.fetch(query, contact_no)
        if not rs:
            raise UserNotFoundException(field="contact_no", message="Users not found.")
        return [
            UserListResponse(
                id=record["id"],
                username=record["username"],
                name=record["name"],
                contact_no=record["contact_no"],
                company_id=record["company_id"],
                company_name=record["company_name"],
                role=None,
                area_id=None,
                area_name=None,
                is_active=True,
            )
            for record in rs
        ]

    async def exists_by_contact_no(
        self, contact_no: str, connection: Optional[Connection] = None
    ) -> bool:
        """Check if a user exists by contact number."""
        if connection is None:
            async with self.db_pool.acquire() as connection:
                return await self.__exists_by_contact_no(connection, contact_no)
        return await self.__exists_by_contact_no(connection, contact_no)

    async def __exists_by_contact_no(
        self, connection: Connection, contact_no: str
    ) -> bool:
        """Check if a user exists by contact number."""
        query = """
        SELECT 1
        FROM salesforce.users
        WHERE contact_no = $1 AND is_active = TRUE;
        """
        rs = await connection.fetchval(query, contact_no)
        print("Exists result:", rs == 1)
        return rs == 1

    async def get_user_by_contact_no_and_company(
        self, contact_no: str, company_id: UUID, connection: Optional[Connection] = None
    ) -> UserDetailsResponse:
        """Get a user by contact number and company id."""
        if connection is None:
            async with self.db_pool.acquire() as connection:
                return await self.__get_user_by_contact_no_and_company(
                    connection, contact_no, company_id
                )
        return await self.__get_user_by_contact_no_and_company(
            connection, contact_no, company_id
        )

    async def __get_user_by_contact_no_and_company(
        self, connection: Connection, contact_no: str, company_id: Optional[UUID]
    ) -> UserDetailsResponse:
        """Get a user by contact number and company id."""
        if company_id is None:
            query = """
            SELECT u.id, u.username, u.name, u.contact_no, u.company_id, u.is_super_admin, u.is_active, u.created_at, u.updated_at
            FROM salesforce.users u
            WHERE u.contact_no = $1 AND u.is_super_admin = TRUE;
            """
            rs = await connection.fetchrow(query, contact_no)
            if not rs:
                raise UserNotFoundException(
                    field="contact_no", message="User not found."
                )
            if not rs["is_super_admin"]:
                raise UserNotFoundException(
                    field="contact_no", message="User not found."
                )
            return UserDetailsResponse(
                id=rs["id"],
                username=rs["username"],
                name=rs["name"],
                contact_no=rs["contact_no"],
                company_id=None,
                company_name=None,
                is_super_admin=rs["is_super_admin"],
                is_active=rs["is_active"],
                created_at=rs["created_at"],
                updated_at=rs["updated_at"],
                role="SUPER_ADMIN",
                area_id=None,
                area_name=None,
                area_type=None,
                bank_details=None,
            )
        await set_search_path(connection, get_schema_name(company_id))
        query = """
        SELECT u.id, u.username, u.name, u.contact_no, u.company_id, u.is_super_admin, u.is_active, u.created_at, u.updated_at,
        m.role, m.area_id, m.bank_details,c.name as company_name, a.name as area_name, a.type as area_type
        FROM salesforce.users u
        JOIN salesforce.company c ON u.company_id = c.id
        JOIN members m ON u.id = m.id
        LEFT JOIN areas a ON m.area_id = a.id
        WHERE u.contact_no = $1 AND u.company_id = $2;
        """
        rs = await connection.fetchrow(query, contact_no, company_id)
        if not rs:
            raise UserNotFoundException(field="contact_no", message="User not found.")
        return UserDetailsResponse(
            id=rs["id"],
            username=rs["username"],
            name=rs["name"],
            contact_no=rs["contact_no"],
            company_id=rs["company_id"],
            company_name=rs["company_name"],
            is_super_admin=rs["is_super_admin"],
            is_active=rs["is_active"],
            created_at=rs["created_at"],
            updated_at=rs["updated_at"],
            role=rs["role"],
            area_id=rs["area_id"],
            area_name=rs["area_name"],
            area_type=rs["area_type"],
            bank_details=BankDetails.model_validate_json(rs["bank_details"])
            if rs["bank_details"]
            else None,
        )
