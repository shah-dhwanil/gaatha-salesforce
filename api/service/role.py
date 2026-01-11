"""
Service layer for Role entity operations.

This service provides business logic for roles, acting as an intermediary
between the API layer and the repository layer.
"""

from typing import Optional
from uuid import UUID

import structlog

from api.database import DatabasePool
from api.exceptions.role import (
    RoleAlreadyExistsException,
    RoleNotFoundException,
    RoleOperationException,
    RoleValidationException,
)
from api.models.role import (
    RoleCreate,
    RoleListItem,
    RoleResponse,
    RoleUpdate,
)
from api.repository.role import RoleRepository

logger = structlog.get_logger(__name__)


class RoleService:
    """
    Service for managing Role business logic.

    This service handles business logic, validation, and orchestration
    for role operations in a multi-tenant environment.
    """

    def __init__(self, db_pool: DatabasePool, company_id: UUID) -> None:
        """
        Initialize the RoleService.

        Args:
            db_pool: Database pool instance for connection management
            company_id: UUID of the company (tenant) for schema isolation
        """
        self.db_pool = db_pool
        self.company_id = company_id
        self.repository = RoleRepository(db_pool, company_id)
        logger.debug(
            "RoleService initialized",
            company_id=str(company_id),
        )

    async def create_role(self, role_data: RoleCreate) -> RoleResponse:
        """
        Create a new role.

        Args:
            role_data: Role data to create

        Returns:
            Created role

        Raises:
            RoleAlreadyExistsException: If role with the same name already exists
            RoleValidationException: If validation fails
            RoleOperationException: If creation fails
        """
        try:
            logger.info(
                "Creating role",
                role_name=role_data.name,
                company_id=str(self.company_id),
            )

            # Create role using repository
            role = await self.repository.create_role(role_data)

            logger.info(
                "Role created successfully",
                role_name=role.name,
                company_id=str(self.company_id),
            )

            return RoleResponse(**role.model_dump())

        except (RoleAlreadyExistsException, RoleValidationException):
            raise
        except Exception as e:
            logger.error(
                "Failed to create role in service",
                role_name=role_data.name,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def get_role_by_name(self, role_name: str) -> RoleResponse:
        """
        Get a role by name.

        Args:
            role_name: Name of the role

        Returns:
            Role

        Raises:
            RoleNotFoundException: If role not found
            RoleOperationException: If retrieval fails
        """
        try:
            logger.debug(
                "Getting role by name",
                role_name=role_name,
                company_id=str(self.company_id),
            )

            role = await self.repository.get_role_by_name(role_name)

            return RoleResponse(**role.model_dump())

        except RoleNotFoundException:
            logger.warning(
                "Role not found",
                role_name=role_name,
                company_id=str(self.company_id),
            )
            raise
        except Exception as e:
            logger.error(
                "Failed to get role in service",
                role_name=role_name,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def list_roles(
        self,
        is_active: Optional[bool] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[RoleListItem], int]:
        """
        List all roles with optional filtering and return total count.

        Args:
            is_active: Filter by active status
            limit: Maximum number of roles to return (default: 20)
            offset: Number of roles to skip (default: 0)

        Returns:
            Tuple of (list of roles with minimal data, total count)

        Raises:
            RoleOperationException: If listing fails
        """
        try:
            logger.debug(
                "Listing roles",
                is_active=is_active,
                limit=limit,
                offset=offset,
                company_id=str(self.company_id),
            )

            # Validate pagination parameters
            if limit < 1 or limit > 100:
                raise RoleValidationException(
                    message="Limit must be between 1 and 100",
                    field="limit",
                    value=limit,
                )

            if offset < 0:
                raise RoleValidationException(
                    message="Offset must be non-negative",
                    field="offset",
                    value=offset,
                )

            # Get roles and count in parallel for better performance
            async with self.db_pool.acquire() as conn:
                roles = await self.repository.list_roles(
                    is_active=is_active,
                    limit=limit,
                    offset=offset,
                    connection=conn,
                )
                total_count = await self.repository.count_roles(
                    is_active=is_active,
                    connection=conn,
                )

            logger.debug(
                "Roles listed successfully",
                count=len(roles),
                total_count=total_count,
                company_id=str(self.company_id),
            )

            return roles, total_count

        except RoleValidationException:
            raise
        except Exception as e:
            logger.error(
                "Failed to list roles in service",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def update_role(self, role_name: str, role_data: RoleUpdate) -> RoleResponse:
        """
        Update an existing role.

        Args:
            role_name: Name of the role to update
            role_data: Role data to update

        Returns:
            Updated role

        Raises:
            RoleNotFoundException: If role not found
            RoleValidationException: If validation fails
            RoleOperationException: If update fails
        """
        try:
            logger.info(
                "Updating role",
                role_name=role_name,
                company_id=str(self.company_id),
            )

            # Additional business logic validation
            if not role_data.description and not role_data.permissions:
                raise RoleValidationException(
                    message="At least one field must be provided for update",
                )

            # Update role using repository
            role = await self.repository.update_role(role_name, role_data)

            logger.info(
                "Role updated successfully",
                role_name=role_name,
                company_id=str(self.company_id),
            )

            return RoleResponse(**role.model_dump())

        except (RoleNotFoundException, RoleValidationException):
            raise
        except Exception as e:
            logger.error(
                "Failed to update role in service",
                role_name=role_name,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def delete_role(self, role_name: str) -> None:
        """
        Soft delete a role by setting is_active to False.

        Args:
            role_name: Name of the role to delete

        Raises:
            RoleNotFoundException: If role not found
            RoleValidationException: If role is protected
            RoleOperationException: If deletion fails
        """
        try:
            logger.info(
                "Deleting role",
                role_name=role_name,
                company_id=str(self.company_id),
            )

            # Soft delete role using repository
            await self.repository.delete_role(role_name)

            logger.info(
                "Role deleted successfully",
                role_name=role_name,
                company_id=str(self.company_id),
            )

        except (RoleNotFoundException, RoleValidationException):
            raise
        except Exception as e:
            logger.error(
                "Failed to delete role in service",
                role_name=role_name,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def bulk_create_roles(
        self, roles_data: list[RoleCreate]
    ) -> list[RoleResponse]:
        """
        Bulk create multiple roles in a transaction.

        Args:
            roles_data: List of role data to create

        Returns:
            List of created roles

        Raises:
            RoleAlreadyExistsException: If any role already exists
            RoleValidationException: If validation fails
            RoleOperationException: If creation fails
        """
        try:
            logger.info(
                "Bulk creating roles",
                count=len(roles_data),
                company_id=str(self.company_id),
            )

            # Validate input
            if not roles_data:
                raise RoleValidationException(
                    message="At least one role must be provided",
                )

            # Bulk create roles using repository (in transaction)
            roles = await self.repository.bulk_create_roles(roles_data)

            logger.info(
                "Roles bulk created successfully",
                count=len(roles),
                company_id=str(self.company_id),
            )

            return [RoleResponse(**role.model_dump()) for role in roles]

        except (
            RoleAlreadyExistsException,
            RoleValidationException,
            RoleOperationException,
        ):
            raise
        except Exception as e:
            logger.error(
                "Failed to bulk create roles in service",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def check_role_exists(self, role_name: str) -> bool:
        """
        Check if a role exists.

        Args:
            role_name: Name of the role to check

        Returns:
            True if role exists, False otherwise
        """
        try:
            await self.repository.get_role_by_name(role_name)
            return True
        except RoleNotFoundException:
            return False

    async def get_active_roles_count(self) -> int:
        """
        Get count of active roles.

        Returns:
            Count of active roles

        Raises:
            RoleOperationException: If counting fails
        """
        try:
            logger.debug(
                "Getting active roles count",
                company_id=str(self.company_id),
            )

            count = await self.repository.count_roles(is_active=True)

            return count

        except Exception as e:
            logger.error(
                "Failed to get active roles count in service",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def get_role_permissions(self, role_name: str) -> list[str]:
        """
        Get permissions for a specific role.

        Args:
            role_name: Name of the role

        Returns:
            List of permissions

        Raises:
            RoleNotFoundException: If role not found
            RoleOperationException: If retrieval fails
        """
        try:
            logger.debug(
                "Getting role permissions",
                role_name=role_name,
                company_id=str(self.company_id),
            )

            role = await self.repository.get_role_by_name(role_name)

            return role.permissions

        except RoleNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to get role permissions in service",
                role_name=role_name,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    # async def add_permissions_to_role(
    #     self, role_name: str, permissions: list[str]
    # ) -> RoleResponse:
    #     """
    #     Add permissions to an existing role.

    #     Args:
    #         role_name: Name of the role
    #         permissions: List of permissions to add

    #     Returns:
    #         Updated role

    #     Raises:
    #         RoleNotFoundException: If role not found
    #         RoleValidationException: If validation fails
    #         RoleOperationException: If update fails
    #     """
    #     try:
    #         logger.info(
    #             "Adding permissions to role",
    #             role_name=role_name,
    #             permissions_count=len(permissions),
    #             company_id=str(self.company_id),
    #         )

    #         # Validate input
    #         if not permissions:
    #             raise RoleValidationException(
    #                 message="At least one permission must be provided",
    #             )

    #         # Get current role
    #         role = await self.repository.get_role_by_name(role_name)

    #         # Merge permissions (avoid duplicates)
    #         current_permissions = set(role.permissions)
    #         new_permissions = current_permissions.union(set(permissions))

    #         # Update role
    #         updated_role = await self.repository.update_role(
    #             role_name, RoleUpdate(permissions=list(new_permissions))
    #         )

    #         logger.info(
    #             "Permissions added to role successfully",
    #             role_name=role_name,
    #             total_permissions=len(updated_role.permissions),
    #             company_id=str(self.company_id),
    #         )

    #         return RoleResponse(**updated_role.model_dump())

    #     except (RoleNotFoundException, RoleValidationException):
    #         raise
    #     except Exception as e:
    #         logger.error(
    #             "Failed to add permissions to role in service",
    #             role_name=role_name,
    #             error=str(e),
    #             company_id=str(self.company_id),
    #         )
    #         raise

    # async def remove_permissions_from_role(
    #     self, role_name: str, permissions: list[str]
    # ) -> RoleResponse:
    #     """
    #     Remove permissions from an existing role.

    #     Args:
    #         role_name: Name of the role
    #         permissions: List of permissions to remove

    #     Returns:
    #         Updated role

    #     Raises:
    #         RoleNotFoundException: If role not found
    #         RoleValidationException: If validation fails
    #         RoleOperationException: If update fails
    #     """
    #     try:
    #         logger.info(
    #             "Removing permissions from role",
    #             role_name=role_name,
    #             permissions_count=len(permissions),
    #             company_id=str(self.company_id),
    #         )

    #         # Validate input
    #         if not permissions:
    #             raise RoleValidationException(
    #                 message="At least one permission must be provided",
    #             )

    #         # Get current role
    #         role = await self.repository.get_role_by_name(role_name)

    #         # Remove permissions
    #         current_permissions = set(role.permissions)
    #         new_permissions = current_permissions.difference(set(permissions))

    #         # Update role
    #         updated_role = await self.repository.update_role(
    #             role_name, RoleUpdate(permissions=list(new_permissions))
    #         )

    #         logger.info(
    #             "Permissions removed from role successfully",
    #             role_name=role_name,
    #             total_permissions=len(updated_role.permissions),
    #             company_id=str(self.company_id),
    #         )

    #         return RoleResponse(**updated_role.model_dump())

    #     except (RoleNotFoundException, RoleValidationException):
    #         raise
    #     except Exception as e:
    #         logger.error(
    #             "Failed to remove permissions from role in service",
    #             role_name=role_name,
    #             error=str(e),
    #             company_id=str(self.company_id),
    #         )
    #         raise
