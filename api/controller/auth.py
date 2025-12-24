from api.models.base import ResponseModel
from api.settings.settings import get_settings
from api.controller.user import get_user_service
from fastapi import Depends, APIRouter
from typing import Annotated
from api.service.auth import AuthService
from api.service.user import UserService
from api.models.auth import LoginRequest, LoginResponse, AuthenticatedUser
from api.exceptions.users import UserNotFoundException
from api.exceptions.app import UnauthorizedException
import structlog


router = APIRouter(prefix="/auth", tags=["auth"])

logger = structlog.get_logger(__name__)


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


@router.post("/login", response_model=ResponseModel[LoginResponse])
async def login(
    request: LoginRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> ResponseModel[LoginResponse]:
    """
    Authenticate user and generate access token.

    Args:
        request: Login credentials (username and OTP)
        auth_service: Authentication service instance
        user_service: User service instance

    Returns:
        LoginResponse with user info and access token

    Raises:
        UnauthorizedException: If credentials are invalid
    """
    logger.info("Login attempt", username=request.username)

    try:
        # Get user by username
        user = await user_service.get_user_by_username(request.username)

        # Check if user is active
        if not user.is_active:
            logger.warning("Inactive user login attempt", username=request.username)
            raise UnauthorizedException("User account is inactive")

        # TODO: Verify OTP code (implement OTP verification logic)
        # For now, we'll skip OTP verification
        # if not verify_otp(user.id, request.otp_code):
        #     raise UnauthorizedException("Invalid OTP code")

        # Create authenticated user
        authenticated_user = AuthenticatedUser(
            user_id=user.id,
            area_id=user.area_id,
            company_id=user.company_id,
            role=user.role,
        )

        # Generate access token
        access_token = auth_service.create_access_token(
            user_id=user.id,
            company_id=user.company_id,
            role=user.role,
            area_id=user.area_id,
        )

        logger.info("Login successful", user_id=str(user.id), username=request.username)

        return ResponseModel(
            status_code=200,
            data=LoginResponse(user=authenticated_user, access_token=access_token),
        )
    except UserNotFoundException:
        logger.warning("Login failed - user not found", username=request.username)
        raise UnauthorizedException("Invalid credentials")
