"""
Role service module for business logic.

This service provides business logic layer for role operations,
acting as an intermediary between API handlers and the role repository.
It handles validation, business rules, and coordinates repository operations.
"""

from uuid import UUID
import structlog

from api.repository.role import RoleRepository
from api.models.role import RoleInDB
from api.exceptions.role import RoleNotFoundException

logger = structlog.get_logger(__name__)


class RoleService:
    """Service class for role business logic.

    This service handles business logic and validation for role operations,
    coordinating between the API layer and the RoleRepository.

    Attributes:
        role_repository: Repository for role data operations
    """

    def __init__(self, role_repository: RoleRepository):
        """Initialize the RoleService with a repository.

        Args:
            role_repository: RoleRepository instance for data operations
        """
        self.role_repository = role_repository
        logger.debug("RoleService initialized")

    async def create_role(
        self,
        company_id: UUID,
        name: str,
        description: str | None = None,
        permissions: list[str] | None = None,
    ) -> RoleInDB:
        """Create a new role.

        Creates a new role through the repository. All validation is handled
        by the CreateRoleRequest Pydantic model.

        Args:
            company_id: UUID of the company the role belongs to
            name: Name of the role (pre-validated)
            description: Optional description of the role (pre-validated)
            permissions: Optional list of permissions for the role (pre-validated)

        Returns:
            RoleInDB: Created role object with all details

        Raises:
            RoleAlreadyExistsException: If role name already exists
        """
        logger.info(
            "Creating role",
            name=name,
            company_id=str(company_id),
        )

        # Create role through repository
        role = await self.role_repository.create_role(
            company_id=company_id,
            name=name,
            description=description,
            permissions=permissions,
        )

        logger.info("Role created successfully", name=name, company_id=str(company_id))
        return role

    async def get_role_by_name(self, company_id: UUID, name: str) -> RoleInDB:
        """Retrieve a role by name.

        Args:
            company_id: UUID of the company
            name: Role name to search for (pre-validated)

        Returns:
            RoleInDB: Role object with complete details

        Raises:
            RoleNotFoundException: If role not found
        """
        logger.info("Fetching role by name", name=name, company_id=str(company_id))

        role = await self.role_repository.get_role_by_name(company_id, name)

        logger.info("Role retrieved by name", name=name, company_id=str(company_id))
        return role

    async def get_roles_by_company(
        self, company_id: UUID, limit: int = 10, offset: int = 0
    ) -> tuple[list[RoleInDB], int]:
        """Retrieve roles in a company with pagination.

        Args:
            company_id: UUID of the company
            limit: Maximum number of records to return (default: 10)
            offset: Number of records to skip (default: 0)

        Returns:
            tuple: (list of RoleInDB objects, total count of roles)
        """
        logger.info(
            "Fetching roles for company with pagination",
            company_id=str(company_id),
            limit=limit,
            offset=offset,
        )

        roles, total_count = await self.role_repository.get_roles_by_company_id(
            company_id, limit, offset
        )

        logger.info(
            "Roles retrieved for company",
            company_id=str(company_id),
            role_count=len(roles),
            total_count=total_count,
        )
        return roles, total_count

    async def update_role(
        self,
        company_id: UUID,
        name: str,
        description: str | None = None,
        permissions: list[str] | None = None,
    ) -> RoleInDB:
        """Update role details.

        Note: Role name cannot be updated as it's the primary key.
        Only description and permissions can be modified. All validation
        is handled by the UpdateRoleRequest Pydantic model.

        Args:
            company_id: UUID of the company
            name: Name of the role to update (identifier only, cannot be changed, pre-validated)
            description: New description (optional, pre-validated)
            permissions: New permissions list (optional, pre-validated)

        Returns:
            RoleInDB: Updated role object

        Raises:
            RoleNotFoundException: If role not found
        """
        logger.info(
            "Updating role",
            name=name,
            company_id=str(company_id),
        )

        role = await self.role_repository.update_role(
            company_id=company_id,
            name=name,
            description=description,
            permissions=permissions,
        )

        logger.info("Role updated successfully", name=name, company_id=str(company_id))
        return role

    async def delete_role(self, company_id: UUID, name: str) -> None:
        """Soft delete a role.

        Marks the role as inactive rather than permanently deleting.
        All validation is handled by the DeleteRoleRequest Pydantic model.

        Args:
            company_id: UUID of the company
            name: Name of the role to delete (pre-validated)

        Raises:
            RoleNotFoundException: If role not found
        """
        logger.info(
            "Deleting role",
            name=name,
            company_id=str(company_id),
        )

        await self.role_repository.delete_role(company_id, name)

        logger.info("Role deleted successfully", name=name, company_id=str(company_id))

    async def check_role_exists(self, company_id: UUID, name: str) -> bool:
        """Check if a role exists by name.

        Useful for validation before attempting operations.

        Args:
            company_id: UUID of the company
            name: Role name to check (pre-validated)

        Returns:
            bool: True if role exists, False otherwise
        """
        logger.debug("Checking if role exists", name=name, company_id=str(company_id))

        try:
            await self.role_repository.get_role_by_name(company_id, name)
            logger.debug("Role exists", name=name, company_id=str(company_id))
            return True
        except RoleNotFoundException:
            logger.debug("Role does not exist", name=name, company_id=str(company_id))
            return False
