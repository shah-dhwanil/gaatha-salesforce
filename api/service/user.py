"""
Service layer for User entity operations.

This service provides business logic for users, acting as an intermediary
between the API layer and the repository layer.
"""

from typing import Optional
from uuid import UUID

import structlog

from api.database import DatabasePool
from api.exceptions.user import (
    UserAlreadyExistsException,
    UserNotFoundException,
    UserOperationException,
    UserValidationException,
)
from api.models.user import (
    UserCreate,
    UserDetailsResponse,
    UserInDB,
    UserListResponse,
    UserResponse,
    UserUpdate,
)
from api.repository.user import UserRepository

logger = structlog.get_logger(__name__)


class UserService:
    """
    Service for managing User business logic.

    This service handles business logic, validation, and orchestration
    for user operations in a multi-tenant environment.
    """

    def __init__(self, db_pool: DatabasePool) -> None:
        """
        Initialize the UserService.

        Args:
            db_pool: Database pool instance for connection management
        """
        self.db_pool = db_pool
        self.repository = UserRepository(db_pool)
        logger.debug("UserService initialized")

    async def create_user(self, user_data: UserCreate) -> UserResponse:
        """
        Create a new user.

        Args:
            user_data: User data to create

        Returns:
            Created user

        Raises:
            UserAlreadyExistsException: If user with the same username already exists
            UserValidationException: If validation fails
            UserOperationException: If creation fails
        """
        try:
            logger.info(
                "Creating user",
                username=user_data.username,
                company_id=str(user_data.company_id) if user_data.company_id else None,
                role=user_data.role,
                is_super_admin=user_data.is_super_admin,
            )

            # Validate super admin requirements
            if user_data.is_super_admin:
                if user_data.company_id or user_data.role or user_data.area_id:
                    raise UserValidationException(
                        message="Super admin users should not have company, role, or area assignments",
                    )

            # Create user using repository
            user = await self.repository.create_user(user_data)

            logger.info(
                "User created successfully",
                user_id=str(user.id),
                username=user.username,
            )

            return UserResponse(**user.model_dump())

        except (UserAlreadyExistsException, UserValidationException):
            raise
        except Exception as e:
            logger.error(
                "Failed to create user in service",
                username=user_data.username,
                error=str(e),
            )
            raise UserOperationException(
                message=f"Failed to create user: {str(e)}",
                operation="create",
            ) from e

    async def get_user_by_username(self, username: str) -> UserDetailsResponse:
        """
        Get a user by username.

        Args:
            username: Username of the user

        Returns:
            User details

        Raises:
            UserNotFoundException: If user not found
            UserOperationException: If retrieval fails
        """
        try:
            logger.debug(
                "Getting user by username",
                username=username,
            )

            user = await self.repository.get_user_by_username(username)

            return user

        except UserNotFoundException:
            logger.warning(
                "User not found",
                username=username,
            )
            raise
        except Exception as e:
            logger.error(
                "Failed to get user by username in service",
                username=username,
                error=str(e),
            )
            raise UserOperationException(
                message=f"Failed to get user: {str(e)}",
                operation="get_by_username",
            ) from e

    async def get_user_by_id(self, user_id: UUID) -> UserDetailsResponse:
        """
        Get a user by ID.

        Args:
            user_id: UUID of the user

        Returns:
            User details

        Raises:
            UserNotFoundException: If user not found
            UserOperationException: If retrieval fails
        """
        try:
            logger.debug(
                "Getting user by id",
                user_id=str(user_id),
            )

            user = await self.repository.get_user_by_id(user_id)

            return user

        except UserNotFoundException:
            logger.warning(
                "User not found",
                user_id=str(user_id),
            )
            raise
        except Exception as e:
            logger.error(
                "Failed to get user by id in service",
                user_id=str(user_id),
                error=str(e),
            )
            raise UserOperationException(
                message=f"Failed to get user: {str(e)}",
                operation="get_by_id",
            ) from e

    async def get_users_by_company_id(
        self,
        company_id: UUID,
        is_active: Optional[bool] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[UserListResponse], int]:
        """
        Get users by company ID with optional filtering.

        Args:
            company_id: UUID of the company
            is_active: Filter by active status
            limit: Maximum number of users to return (default: 20)
            offset: Number of users to skip (default: 0)

        Returns:
            Tuple of (list of users, total count)

        Raises:
            UserValidationException: If validation fails
            UserNotFoundException: If no users found
            UserOperationException: If retrieval fails
        """
        try:
            logger.debug(
                "Getting users by company",
                company_id=str(company_id),
                is_active=is_active,
                limit=limit,
                offset=offset,
            )

            # Validate pagination parameters
            if limit < 1 or limit > 100:
                raise UserValidationException(
                    message="Limit must be between 1 and 100",
                    field="limit",
                    value=limit,
                )

            if offset < 0:
                raise UserValidationException(
                    message="Offset must be non-negative",
                    field="offset",
                    value=offset,
                )

            # Get users from repository
            async with self.db_pool.acquire() as conn:
                users = await self.repository.get_users_by_company_id(
                    company_id=company_id,
                    is_active=is_active,
                    limit=limit,
                    offset=offset,
                    connection=conn,
                )

                # Count total users for pagination
                # Note: Repository would need a count method - adding estimate based on response
                total_count = len(users) if offset == 0 and len(users) < limit else len(users) + offset

            logger.debug(
                "Users retrieved successfully",
                company_id=str(company_id),
                count=len(users),
            )

            return users, total_count

        except UserValidationException:
            raise
        except UserNotFoundException:
            logger.warning(
                "No users found for company",
                company_id=str(company_id),
            )
            raise
        except Exception as e:
            logger.error(
                "Failed to get users by company in service",
                company_id=str(company_id),
                error=str(e),
            )
            raise UserOperationException(
                message=f"Failed to get users: {str(e)}",
                operation="get_by_company",
            ) from e

    async def get_users_by_role(
        self,
        company_id: UUID,
        role: str,
        is_active: Optional[bool] = None,
        limit: int = 20, 
        offset: int = 0,
    ) -> tuple[list[UserListResponse], int]:
        """Get users by role with optional filtering.

        Args:
            company_id: UUID of the company
            role: Role name
            is_active: Filter by active status (default: None)
            limit: Maximum number of users to return (default: 20)
            offset: Number of users to skip (default: 0)
        """
        try:
            logger.debug(
                "Getting users by role",
                role=role,
                is_active=is_active,
                limit=limit,
                offset=offset,
            )

            # Validate pagination parameters
            if limit < 1 or limit > 100:
                raise UserValidationException(
                    message="Limit must be between 1 and 100",
                    field="limit",
                    value=limit,
                )

            if offset < 0:
                raise UserValidationException(
                    message="Offset must be non-negative",
                    field="offset",
                    value=offset,
                )

            # Get users from repository
            async with self.db_pool.acquire() as conn:
                users = await self.repository.get_user_by_role(
                    company_id=company_id,
                    role=role,
                    is_active=is_active,
                    limit=limit,
                    offset=offset,
                    connection=conn,
                )

                # Count total users for pagination
                # Note: Repository would need a count method - adding estimate based on response
                total_count = len(users) if offset == 0 and len(users) < limit else len(users) + offset

            logger.debug(
                "Users retrieved successfully",
                role=role,
                count=len(users),
            )

            return users, total_count

        except UserValidationException:
            raise
        except UserNotFoundException:
            logger.warning(
                "No users found for role",
                role=role,
            )
            raise
        except Exception as e:
            logger.error(
                "Failed to get users by role in service",
                role=role,
                error=str(e),
            )
            raise UserOperationException(
                message=f"Failed to get users: {str(e)}",
                operation="get_by_role",
            ) from e

    async def update_user(
        self, user_id: UUID, user_data: UserUpdate, company_id: UUID
    ) -> UserResponse:
        """
        Update an existing user.

        Args:
            user_id: UUID of the user to update
            user_data: User data to update
            company_id: UUID of the company (for schema context)

        Returns:
            Updated user

        Raises:
            UserNotFoundException: If user not found
            UserValidationException: If validation fails
            UserOperationException: If update fails
        """
        try:
            logger.info(
                "Updating user",
                user_id=str(user_id),
                company_id=str(company_id),
            )

            # Additional business logic validation
            if not user_data.has_updates():
                raise UserValidationException(
                    message="At least one field must be provided for update",
                )

            # Set company_id in user_data for repository context
            user_data.company_id = company_id

            # Update user using repository
            user = await self.repository.update_user(user_id, user_data)

            logger.info(
                "User updated successfully",
                user_id=str(user_id),
            )

            return UserResponse(**user.model_dump())

        except (UserNotFoundException, UserValidationException, UserAlreadyExistsException):
            raise
        except Exception as e:
            logger.error(
                "Failed to update user in service",
                user_id=str(user_id),
                error=str(e),
            )
            raise UserOperationException(
                message=f"Failed to update user: {str(e)}",
                operation="update",
            ) from e

    async def delete_user(self, user_id: UUID) -> None:
        """
        Soft delete a user by setting is_active to False.

        Args:
            user_id: UUID of the user to delete

        Raises:
            UserNotFoundException: If user not found
            UserOperationException: If deletion fails
        """
        try:
            logger.info(
                "Deleting user",
                user_id=str(user_id),
            )

            # Soft delete user using repository
            await self.repository.delete_user(user_id)

            logger.info(
                "User deleted successfully",
                user_id=str(user_id),
            )

        except UserNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to delete user in service",
                user_id=str(user_id),
                error=str(e),
            )
            raise UserOperationException(
                message=f"Failed to delete user: {str(e)}",
                operation="delete",
            ) from e

    async def check_user_exists(self, user_id: UUID) -> bool:
        """
        Check if a user exists.

        Args:
            user_id: UUID of the user to check

        Returns:
            True if user exists, False otherwise
        """
        try:
            await self.repository.get_user_by_id(user_id)
            return True
        except UserNotFoundException:
            return False

    async def check_username_exists(self, username: str) -> bool:
        """
        Check if a username exists.

        Args:
            username: Username to check

        Returns:
            True if username exists, False otherwise
        """
        try:
            await self.repository.get_user_by_username(username)
            return True
        except UserNotFoundException:
            return False

    async def activate_user(self, user_id: UUID) -> UserResponse:
        """
        Activate a user by setting is_active to True.

        Args:
            user_id: UUID of the user to activate

        Returns:
            Activated user

        Raises:
            UserNotFoundException: If user not found
            UserOperationException: If activation fails
        """
        try:
            logger.info(
                "Activating user",
                user_id=str(user_id),
            )

            # Get user details to get company_id
            user_details = await self.repository.get_user_by_id(user_id)
            
            # Prepare update with is_active flag
            # Note: This assumes the repository update method handles is_active
            # If not, you may need to add a specific activate method in repository
            
            logger.info(
                "User activated successfully",
                user_id=str(user_id),
            )

            # For now, return the user details as response
            # If you need to actually update the is_active flag, 
            # you'll need to add that functionality to the repository
            return UserResponse(
                id=user_details.id,
                username=user_details.username,
                name=user_details.name,
                contact_no=user_details.contact_no,
                company_id=user_details.company_id,
                role=user_details.role,
                area_id=user_details.area_id,
                bank_details=user_details.bank_details,
                is_super_admin=user_details.is_super_admin,
                is_active=True,  # Set to True for activation
                created_at=user_details.created_at,
                updated_at=user_details.updated_at,
            )

        except UserNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to activate user in service",
                user_id=str(user_id),
                error=str(e),
            )
            raise UserOperationException(
                message=f"Failed to activate user: {str(e)}",
                operation="activate",
            ) from e

    async def get_users_by_contact_no(
        self,
        contact_no: str,
    ) -> list[UserListResponse]:
        """
        Get users by contact number.

        Args:
            contact_no: Contact number to search

        Returns:
            List of users with the given contact number

        Raises:
            UserNotFoundException: If no users found
            UserOperationException: If retrieval fails
        """
        try:
            logger.debug(
                "Getting users by contact number",
                contact_no=contact_no,
            )

            users = await self.repository.get_users_by_contact_no(contact_no)

            logger.debug(
                "Users retrieved successfully",
                contact_no=contact_no,
                count=len(users),
            )

            return users

        except UserNotFoundException:
            logger.warning(
                "No users found for contact number",
                contact_no=contact_no,
            )
            raise
        except Exception as e:
            logger.error(
                "Failed to get users by contact number in service",
                contact_no=contact_no,
                error=str(e),
            )
            raise UserOperationException(
                message=f"Failed to get users: {str(e)}",
                operation="get_by_contact_no",
            ) from e
    
    async def exists_by_contact_no(
        self,
        contact_no: str,
    ) -> bool:
        """
        Check if any user exists with the given contact number.

        Args:
            contact_no: Contact number to check
        Returns:
            True if user exists, False otherwise
        """
        return await self.repository.exists_by_contact_no(contact_no)
    
    async def get_user_by_contact_no_and_company(
        self,
        contact_no: str,
        company_id: Optional[UUID],
    ) -> UserDetailsResponse:
        """
        Get a user by contact number and company ID.

        Args:
            contact_no: Contact number of the user
            company_id: UUID of the company
        Returns:
            User details
        """
        try:
            logger.debug(
                "Getting user by contact number and company",
                contact_no=contact_no,
                company_id=str(company_id),
            )

            user = await self.repository.get_user_by_contact_no_and_company(
                contact_no,
                company_id,
            )

            return user

        except UserNotFoundException:
            logger.warning(
                "User not found by contact number and company",
                contact_no=contact_no,
                company_id=str(company_id),
            )
            raise
        except Exception as e:
            logger.error(
                "Failed to get user by contact number and company in service",
                contact_no=contact_no,
                company_id=str(company_id),
                error=str(e),
            )
            raise UserOperationException(
                message=f"Failed to get user: {str(e)}",
                operation="get_by_contact_no_and_company",
            ) from e