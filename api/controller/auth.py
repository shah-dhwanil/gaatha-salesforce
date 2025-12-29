from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends
import structlog
from api.models.auth import AuthRequest, AuthResponse, AuthenticatedUser
from api.models import ResponseModel
from api.service.auth import AuthService
from api.dependencies.auth import get_auth_service
from api.dependencies.user import get_user_service
from api.service.user import UserService
from api.exceptions.app import UnauthorizedException
from api.exceptions.user import UserNotFoundException

router = APIRouter(prefix="/auth", tags=["auth"])

logger = structlog.get_logger(__name__)

@router.post("/login", response_model=ResponseModel[AuthResponse])
async def login(
    request: AuthRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> ResponseModel[AuthResponse]:
    
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
        if user.is_super_admin:
            authenticated_user = AuthenticatedUser(
                user_id=user.id,
                area_id=user.area_id,
                company_id=None,
                role="SUPER_ADMIN",
            )
        else:
            # Create authenticated user
            authenticated_user = AuthenticatedUser(
                user_id=user.id,
                area_id=user.area_id,
                company_id=user.company_id,
                role=user.role,
            )
        # Generate access token
        access_token = auth_service.create_access_token(
            user_id=authenticated_user.user_id,
            company_id=authenticated_user.company_id,
            role=authenticated_user.role,
            area_id=authenticated_user.area_id,
        )

        logger.info("Login successful", user_id=str(user.id), username=request.username)

        return ResponseModel(
            status_code=200,
            data=AuthResponse(user=authenticated_user, access_token=access_token),
        )
    except UserNotFoundException:
        logger.warning("Login failed - user not found", username=request.username)
        raise UnauthorizedException("Invalid credentials")