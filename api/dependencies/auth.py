"""
Authentication dependencies for FastAPI routes.

This module provides FastAPI dependency functions for authentication,
including JWT token verification and user extraction from requests.
"""

from api.service.role import RoleService
from uuid import UUID
from typing import Annotated
from fastapi import Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import structlog

from api.service.auth import AuthService
from api.models.auth import AuthenticatedUser
from api.settings.settings import get_settings
from api.exceptions.app import UnauthorizedException
from api.dependencies.role import get_role_service

logger = structlog.get_logger(__name__)

# HTTP Bearer token scheme
security = HTTPBearer()


def get_auth_service() -> AuthService:
    """Dependency to get AuthService instance.

    Returns:
        AuthService instance configured with application settings

    Example:
        ```python
        @router.get("/protected")
        async def protected_route(
            auth_service: AuthService = Depends(get_auth_service)
        ):
            pass
        ```
    """
    settings = get_settings()
    return AuthService(config=settings.JWT)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthenticatedUser:
    """Dependency to get the current authenticated user from JWT token.

    This dependency extracts and validates the JWT token from the Authorization header
    and returns the authenticated user information.

    Args:
        credentials: HTTP Bearer credentials from Authorization header
        auth_service: AuthService instance for token verification

    Returns:
        AuthenticatedUser instance with user information

    Raises:
        UnauthorizedException: If token is invalid or expired

    Example:
        ```python
        @router.get("/profile")
        async def get_profile(
            current_user: AuthenticatedUser = Depends(get_current_user)
        ):
            return {"username": current_user.username}
        ```
    """
    token = credentials.credentials

    if not token:
        logger.warning("No token provided in request")
        raise UnauthorizedException("Authentication token required")

    try:
        user = auth_service.verify_token(token, token_type="access")
        logger.debug(
            "User authenticated successfully",
            user_id=str(user.user_id),
        )
        return user
    except Exception as e:
        logger.warning("Authentication failed", error=str(e))
        raise


async def get_current_user_optional(
    authorization: str = Header(None),
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthenticatedUser | None:
    """Dependency to optionally get the current authenticated user.

    This dependency extracts and validates the JWT token if present,
    but returns None if no token is provided instead of raising an error.

    Args:
        authorization: Authorization header value
        auth_service: AuthService instance for token verification

    Returns:
        AuthenticatedUser instance if token is valid, None otherwise

    Example:
        ```python
        @router.get("/public")
        async def public_route(
            current_user: AuthenticatedUser | None = Depends(get_current_user_optional)
        ):
            if current_user:
                return {"message": f"Hello, {current_user.username}"}
            return {"message": "Hello, guest"}
        ```
    """
    if not authorization:
        return None

    try:
        # Extract token from "Bearer <token>" format
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            return None

        user = auth_service.verify_token(token, token_type="access")
        return user
    except Exception as e:
        logger.debug("Optional authentication failed", error=str(e))
        return None


def require_role(required_role: str):
    """Dependency factory to require a specific role for access.

    Args:
        required_role: The role required to access the endpoint

    Returns:
        Dependency function that checks user role

    Raises:
        UnauthorizedException: If user doesn't have the required role

    Example:
        ```python
        @router.delete("/users/{user_id}")
        async def delete_user(
            user_id: UUID,
            current_user: AuthenticatedUser = Depends(require_role("admin"))
        ):
            pass
        ```
    """

    async def role_checker(
        current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    ) -> AuthenticatedUser:
        if current_user.role != required_role:
            logger.warning(
                "Access denied - insufficient role",
                user_id=str(current_user.user_id),
                user_role=current_user.role,
                required_role=required_role,
            )
            raise UnauthorizedException(
                f"Access denied. Required role: {required_role}"
            )
        return current_user

    return role_checker


def require_roles(*required_roles: str):
    """Dependency factory to require one of multiple roles for access.

    Args:
        *required_roles: Variable number of roles that grant access

    Returns:
        Dependency function that checks if user has one of the required roles

    Raises:
        UnauthorizedException: If user doesn't have any of the required roles

    Example:
        ```python
        @router.put("/settings")
        async def update_settings(
            current_user: AuthenticatedUser = Depends(require_roles("admin", "manager"))
        ):
            pass
        ```
    """

    async def role_checker(
        current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    ) -> AuthenticatedUser:
        if current_user.role not in required_roles:
            logger.warning(
                "Access denied - insufficient role",
                user_id=str(current_user.user_id),
                user_role=current_user.role,
                required_roles=list(required_roles),
            )
            raise UnauthorizedException(
                f"Access denied. Required roles: {', '.join(required_roles)}"
            )
        return current_user

    return role_checker


async def role_permission_dependency(
    company_id: UUID,
    role_service: RoleService,
) -> dict[str, list[str]]:
    roles = await role_service.get_roles_by_company(company_id=company_id)
    role_dict = {role.name: role.permissions for role in roles[0]}
    return role_dict


# A dependency which check is user has given role or the permission to access the route


def require_role_or_permission(required_role: str, required_permission: str):
    """Dependency factory to require a specific role or permission for access.

    Args:
        required_role: The role required to access the endpoint
        required_permission: The permission required to access the endpoint
    Returns:
        Dependency function that checks user role or permission
    Raises:
        UnauthorizedException: If user doesn't have the required role or permission
    """

    async def role_or_permission_checker(
        current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
        role_service: Annotated[RoleService, Depends(get_role_service)],
    ) -> AuthenticatedUser:
        role_permissions = await role_permission_dependency(
            company_id=current_user.company_id,
            role_service=role_service,
        )
        user_permissions = role_permissions.get(current_user.role, [])
        if (
            current_user.role != required_role
            and required_permission not in user_permissions
        ):
            logger.warning(
                "Access denied - insufficient role or permission",
                user_id=str(current_user.user_id),
                user_role=current_user.role,
                required_role=required_role,
                required_permission=required_permission,
            )
            raise UnauthorizedException(
                f"Access denied. Required role: {required_role} or permission: {required_permission}"
            )
        return current_user

    return role_or_permission_checker
