"""
User service module for business logic.

This service provides business logic layer for user operations,
acting as an intermediary between API handlers and the user repository.
It handles validation, business rules, and coordinates repository operations.
"""

from uuid import UUID
from typing import Optional
import structlog

from api.repository.user import UserRepository
from api.models.users import UserInDB
from api.exceptions.users import UserNotFoundException

logger = structlog.get_logger(__name__)


class UserService:
    """Service class for user business logic.

    This service handles business logic and validation for user operations,
    coordinating between the API layer and the UserRepository.

    Attributes:
        user_repository: Repository for user data operations
    """

    def __init__(self, user_repository: UserRepository):
        """Initialize the UserService with a repository.

        Args:
            user_repository: UserRepository instance for data operations
        """
        self.user_repository = user_repository
        logger.debug("UserService initialized")

    async def create_user(
        self,
        username: str,
        name: str,
        contact_no: str,
        company_id: UUID,
        role: str,
        area_id: Optional[int] = None,
    ) -> UserInDB:
        """Create a new user with validation.

        Validates input data and creates a new user through the repository.

        Args:
            username: Unique username for the user
            name: Full name of the user
            contact_no: Contact phone number
            company_id: UUID of the company the user belongs to
            role: Role of the user in the company
            area_id: Optional area assignment for the user

        Returns:
            UserInDB: Created user object with all details

        Raises:
            UserAlreadyExistsException: If username already exists
            CompanyNotFoundException: If company doesn't exist
            RoleNotFoundException: If role doesn't exist
            AreaNotFoundException: If area doesn't exist
            ValueError: If validation fails
        """
        logger.info(
            "Creating user",
            username=username,
            company_id=str(company_id),
            role=role,
        )

        # Validate input data
        if not username or not username.strip():
            raise ValueError("Username cannot be empty")
        if not name or not name.strip():
            raise ValueError("Name cannot be empty")
        if not contact_no or not contact_no.strip():
            raise ValueError("Contact number cannot be empty")
        if not role or not role.strip():
            raise ValueError("Role cannot be empty")

        # Create user through repository
        user = await self.user_repository.create_user(
            username=username.strip(),
            name=name.strip(),
            contact_no=contact_no.strip(),
            company_id=company_id,
            role=role.strip(),
            area_id=area_id,
        )

        logger.info(
            "User created successfully", user_id=str(user.id), username=username
        )
        return user

    async def get_user_by_username(self, username: str) -> UserInDB:
        """Retrieve a user by username.

        Args:
            username: Username to search for

        Returns:
            UserInDB: User object with complete details

        Raises:
            UserNotFoundException: If user not found
            ValueError: If username is empty
        """
        logger.info("Fetching user by username", username=username)

        if not username or not username.strip():
            raise ValueError("Username cannot be empty")

        user = await self.user_repository.get_user_by_username(username.strip())

        logger.info(
            "User retrieved by username", user_id=str(user.id), username=username
        )
        return user

    async def get_user_by_id(self, user_id: UUID, company_id: UUID) -> UserInDB:
        """Retrieve a user by ID.

        Args:
            user_id: User UUID
            company_id: Company UUID

        Returns:
            UserInDB: User object with complete details

        Raises:
            UserNotFoundException: If user not found
        """
        logger.info(
            "Fetching user by ID",
            user_id=str(user_id),
            company_id=str(company_id),
        )

        user = await self.user_repository.get_user_by_id(user_id, company_id)

        logger.info("User retrieved by ID", user_id=str(user_id))
        return user

    async def get_users_by_company(self, company_id: UUID) -> list[UserInDB]:
        """Retrieve all users in a company.

        Args:
            company_id: Company UUID

        Returns:
            list[UserInDB]: List of all users in the company
        """
        logger.info("Fetching all users for company", company_id=str(company_id))

        users = await self.user_repository.get_users_by_company_id(company_id)

        logger.info(
            "Users retrieved for company",
            company_id=str(company_id),
            user_count=len(users),
        )
        return users

    async def get_users_by_role(self, role: str, company_id: UUID) -> list[UserInDB]:
        """Retrieve users by role within a company.

        Args:
            role: Role name to filter by
            company_id: Company UUID

        Returns:
            list[UserInDB]: List of users with the specified role

        Raises:
            ValueError: If role is empty
        """
        logger.info(
            "Fetching users by role",
            role=role,
            company_id=str(company_id),
        )

        if not role or not role.strip():
            raise ValueError("Role cannot be empty")

        users = await self.user_repository.get_user_by_role(role.strip(), company_id)

        logger.info(
            "Users retrieved by role",
            role=role,
            company_id=str(company_id),
            user_count=len(users),
        )
        return users

    async def update_user(
        self,
        user_id: UUID,
        company_id: UUID,
        name: Optional[str] = None,
        contact_no: Optional[str] = None,
        role: Optional[str] = None,
        area_id: Optional[int] = None,
    ) -> UserInDB:
        """Update user details with validation.

        Args:
            user_id: User UUID to update
            company_id: Company UUID
            name: New name (optional)
            contact_no: New contact number (optional)
            role: New role (optional)
            area_id: New area assignment (optional)

        Returns:
            UserInDB: Updated user object

        Raises:
            UserNotFoundException: If user not found
            RoleNotFoundException: If new role doesn't exist
            AreaNotFoundException: If new area doesn't exist
            ValueError: If no fields provided or validation fails
        """
        logger.info(
            "Updating user",
            user_id=str(user_id),
            company_id=str(company_id),
        )

        # Validate at least one field is provided
        if name is None and contact_no is None and role is None and area_id is None:
            raise ValueError("At least one field must be provided for update")

        # Validate non-empty strings
        if name is not None and not name.strip():
            raise ValueError("Name cannot be empty")
        if contact_no is not None and not contact_no.strip():
            raise ValueError("Contact number cannot be empty")
        if role is not None and not role.strip():
            raise ValueError("Role cannot be empty")

        # Strip whitespace from string fields
        name_stripped = name.strip() if name is not None else None
        contact_no_stripped = contact_no.strip() if contact_no is not None else None
        role_stripped = role.strip() if role is not None else None

        user = await self.user_repository.update_user(
            company_id=company_id,
            user_id=user_id,
            name=name_stripped,
            contact_no=contact_no_stripped,
            role=role_stripped,
            area_id=area_id,
        )

        logger.info("User updated successfully", user_id=str(user_id))
        return user

    async def delete_user(self, user_id: UUID, company_id: UUID) -> None:
        """Soft delete a user.

        Marks the user as inactive rather than permanently deleting.

        Args:
            user_id: User UUID to delete
            company_id: Company UUID

        Raises:
            UserNotFoundException: If user not found
        """
        logger.info(
            "Deleting user",
            user_id=str(user_id),
            company_id=str(company_id),
        )

        await self.user_repository.delete_user(user_id, company_id)

        logger.info("User deleted successfully", user_id=str(user_id))

    async def check_user_exists(self, username: str) -> bool:
        """Check if a user exists by username.

        Useful for validation before attempting operations.

        Args:
            username: Username to check

        Returns:
            bool: True if user exists, False otherwise
        """
        logger.debug("Checking if user exists", username=username)

        try:
            await self.user_repository.get_user_by_username(username)
            logger.debug("User exists", username=username)
            return True
        except UserNotFoundException:
            logger.debug("User does not exist", username=username)
            return False

    async def get_active_users_by_company(self, company_id: UUID) -> list[UserInDB]:
        """Retrieve only active users in a company.

        Filters out inactive/deleted users.

        Args:
            company_id: Company UUID

        Returns:
            list[UserInDB]: List of active users in the company
        """
        logger.info("Fetching active users for company", company_id=str(company_id))

        all_users = await self.user_repository.get_users_by_company_id(company_id)
        active_users = [user for user in all_users if user.is_active]

        logger.info(
            "Active users retrieved for company",
            company_id=str(company_id),
            active_user_count=len(active_users),
            total_user_count=len(all_users),
        )
        return active_users

    async def get_active_users_by_role(
        self, role: str, company_id: UUID
    ) -> list[UserInDB]:
        """Retrieve only active users by role within a company.

        Filters out inactive/deleted users from the role query.

        Args:
            role: Role name to filter by
            company_id: Company UUID

        Returns:
            list[UserInDB]: List of active users with the specified role
        """
        logger.info(
            "Fetching active users by role",
            role=role,
            company_id=str(company_id),
        )

        all_users = await self.user_repository.get_user_by_role(role, company_id)
        active_users = [user for user in all_users if user.is_active]

        logger.info(
            "Active users retrieved by role",
            role=role,
            company_id=str(company_id),
            active_user_count=len(active_users),
            total_user_count=len(all_users),
        )
        return active_users
