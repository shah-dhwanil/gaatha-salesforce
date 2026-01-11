from api.models.auth import AuthUserToCompanyRequest
from api.dependencies.auth import get_temp_token
from api.models.auth import VerifyOTPRequest, VerifyOTPResponse
from api.models.auth import GenerateOtpRequest
from typing import Annotated
from fastapi import APIRouter, Depends
import structlog
from api.models.auth import AuthResponse, AuthenticatedUser
from api.models import ResponseModel
from api.service.auth import AuthService
from api.dependencies.auth import get_auth_service
from api.dependencies.user import get_user_service
from api.service.user import UserService
from api.exceptions.app import UnauthorizedException
from api.exceptions.user import UserNotFoundException

router = APIRouter(prefix="/auth", tags=["auth"])

logger = structlog.get_logger(__name__)

# @router.post("/login", response_model=ResponseModel[AuthResponse])
# async def login(
#     request: AuthRequest,
#     auth_service: Annotated[AuthService, Depends(get_auth_service)],
#     user_service: Annotated[UserService, Depends(get_user_service)],
# ) -> ResponseModel[AuthResponse]:

#     logger.info("Login attempt", username=request.username)

#     try:
#         # Get user by username
#         user = await user_service.get_user_by_username(request.username)
#         # Check if user is active
#         if not user.is_active:
#             logger.warning("Inactive user login attempt", username=request.username)
#             raise UnauthorizedException("User account is inactive")

#         # TODO: Verify OTP code (implement OTP verification logic)
#         # For now, we'll skip OTP verification
#         # if not verify_otp(user.id, request.otp_code):
#         #     raise UnauthorizedException("Invalid OTP code")
#         if user.is_super_admin:
#             authenticated_user = AuthenticatedUser(
#                 user_id=user.id,
#                 area_id=user.area_id,
#                 company_id=None,
#                 role="SUPER_ADMIN",
#             )
#         else:
#             # Create authenticated user
#             authenticated_user = AuthenticatedUser(
#                 user_id=user.id,
#                 area_id=user.area_id,
#                 company_id=user.company_id,
#                 role=user.role,
#             )
#         # Generate access token
#         access_token = auth_service.create_access_token(
#             user_id=authenticated_user.user_id,
#             company_id=authenticated_user.company_id,
#             role=authenticated_user.role,
#             area_id=authenticated_user.area_id,
#         )

#         logger.info("Login successful", user_id=str(user.id), username=request.username)

#         return ResponseModel(
#             status_code=200,
#             data=AuthResponse(user=authenticated_user, access_token=access_token),
#         )
#     except UserNotFoundException:
#         logger.warning("Login failed - user not found", username=request.username)
#         raise UnauthorizedException("Invalid credentials")


@router.post("/generate-otp", status_code=204)
async def generate_otp(
    request: GenerateOtpRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> None:
    """
    Generate OTP for user authentication.
    Either username or contact_no must be provided.
    """
    logger.info(
        "OTP generation request received",
        username=request.username,
        contact_no=request.contact_no,
    )

    contact_no = None
    if request.username:
        print("Username provided:", request.username)
        try:
            user = await user_service.get_user_by_username(request.username)
            print(user)
            contact_no = user.contact_no
        except UserNotFoundException:
            logger.warning(
                "OTP generation failed - user not found by username",
                username=request.username,
            )
            raise
    elif request.contact_no:
        user_exists = await user_service.exists_by_contact_no(request.contact_no)
        if not user_exists:
            raise UserNotFoundException(field="contact_no")
        contact_no = request.contact_no
    if contact_no:
        # await auth_service.generate_and_send_otp(user)
        logger.info("OTP generated and sent", contact_no=contact_no)
    else:
        raise UserNotFoundException(field=None)


@router.post("/verify-otp", response_model=ResponseModel[VerifyOTPResponse])
async def verify_otp(
    request: VerifyOTPRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> ResponseModel[str]:
    """
    Verify OTP code for user authentication.
    """
    logger.info(
        "OTP verification request received",
        contact_no=request.contact_no,
        username=request.username,
    )
    users_company = []
    if request.username:
        try:
            user = await user_service.get_user_by_username(request.username)
            print("User found:", user)
            if user.is_super_admin:
                users_company = None
            else:
                users_company.append(
                    VerifyOTPResponse.Company(
                        company_id=user.company_id, company_name=user.company_name
                    )
                )
            token = auth_service.generate_temporary_token(user.contact_no)
            return ResponseModel(
                status_code=200,
                data=VerifyOTPResponse(token=token, companies=users_company),
            )
        except UserNotFoundException:
            logger.warning(
                "OTP verification failed - user not found by username",
                username=request.username,
            )
            raise UnauthorizedException("Invalid credentials")
    elif request.contact_no:
        users = await user_service.get_users_by_contact_no(request.contact_no)
        if not users:
            logger.warning(
                "OTP verification failed - user not found by contact_no",
                contact_no=request.contact_no,
            )
            raise UnauthorizedException("Invalid credentials")
        for user in users:
            if user.company_id is None:
                users_company = None
                break
            else:
                users_company.append(
                    VerifyOTPResponse.Company(
                        company_id=user.company_id, company_name=user.company_name
                    )
                )
        token = auth_service.generate_temporary_token(request.contact_no)
        return ResponseModel(
            status_code=200,
            data=VerifyOTPResponse(token=token, companies=users_company),
        )


@router.post("/auth-user-to-company", response_model=ResponseModel[AuthResponse])
async def auth_user_to_company(
    request: AuthUserToCompanyRequest,
    temp_token: Annotated[str, Depends(get_temp_token)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> ResponseModel[AuthResponse]:
    """
    Authenticate user to a specific company using temporary token.
    """
    logger.info("Authenticating user to company", company_id=str(request.company_id))
    contact_no = auth_service.verify_temp_token(temp_token)
    user = await user_service.get_user_by_contact_no_and_company(
        contact_no, request.company_id
    )
    if not user:
        logger.warning(
            "Authentication to company failed - user not associated with company",
            company_id=str(request.company_id),
        )
        raise UnauthorizedException("User not associated with the specified company")

    authenticated_user = AuthenticatedUser(
        user_id=user.id,
        area_id=user.area_id,
        company_id=user.company_id,
        role=user.role,
    )
    access_token = auth_service.create_access_token(
        user_id=authenticated_user.user_id,
        company_id=authenticated_user.company_id,
        role=authenticated_user.role,
        area_id=authenticated_user.area_id,
    )

    logger.info(
        "User authenticated to company successfully",
        user_id=str(user.id),
        company_id=str(request.company_id),
    )

    return ResponseModel(
        status_code=200,
        data=AuthResponse(user=authenticated_user, access_token=access_token),
    )
