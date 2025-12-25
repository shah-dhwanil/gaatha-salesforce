"""
Authentication service for JWT token management.

This service handles JWT token generation, validation, and user authentication
using PyJWT library. It provides methods for creating access and refresh tokens,
verifying tokens, and extracting user information from tokens.
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID
from typing import Optional
import jwt
import structlog

from api.settings.jwt import JWTConfig
from api.models.auth import AuthenticatedUser
from api.exceptions.app import UnauthorizedException

logger = structlog.get_logger(__name__)


class AuthService:
    """Service for JWT authentication and token management.

    This service provides methods for generating and validating JWT tokens,
    including both access and refresh tokens. It handles token encoding/decoding
    using PyJWT and manages token expiration.

    Attributes:
        config: JWTConfig instance with JWT settings
    """

    def __init__(self, config: Optional[JWTConfig] = None):
        """Initialize AuthService with JWT configuration.

        Args:
            config: JWTConfig instance. If None, uses default configuration.
        """
        self.config = config or JWTConfig()
        logger.debug("AuthService initialized", algorithm=self.config.ALGORITHM)

    def create_access_token(
        self,
        user_id: UUID,
        company_id: Optional[UUID],
        role: str,
        area_id: Optional[int] = None,
    ) -> str:
        """Create a JWT access token for a user.

        Args:
            user_id: Unique identifier for the user
            username: Username of the user
            company_id: Company identifier for the user
            role: Role of the user

        Returns:
            Encoded JWT access token as string

        Example:
            >>> token = auth_service.create_access_token(
            ...     user_id=uuid4(),
            ...     username="john.doe",
            ...     company_id=uuid4(),
            ...     role="admin"
            ... )
        """
        now = datetime.now(timezone.utc)
        expires_delta = timedelta(minutes=self.config.ACCESS_TOKEN_EXPIRE_MINUTES)
        expire = now + expires_delta

        payload = {
            "user_id": str(user_id),
            "area_id": area_id,
            "company_id": str(company_id),
            "role": role,
            "exp": expire,
            "iat": now,
            "token_type": "access",
        }

        token = jwt.encode(
            payload, self.config.SECRET_KEY, algorithm=self.config.ALGORITHM
        )

        logger.info(
            "Access token created",
            user_id=str(user_id),
            area_id=area_id,
            expires_at=expire.isoformat(),
        )

        return token

    def create_refresh_token(
        self,
        user_id: UUID,
        company_id: UUID,
        role: str,
        area_id: Optional[int] = None,
    ) -> str:
        """Create a JWT refresh token for a user.

        Args:
            user_id: Unique identifier for the user
            username: Username of the user
            company_id: Company identifier for the user
            role: Role of the user

        Returns:
            Encoded JWT refresh token as string

        Example:
            >>> token = auth_service.create_refresh_token(
            ...     user_id=uuid4(),
            ...     username="john.doe",
            ...     company_id=uuid4(),
            ...     role="admin"
            ... )
        """
        now = datetime.now(timezone.utc)
        expires_delta = timedelta(days=self.config.REFRESH_TOKEN_EXPIRE_DAYS)
        expire = now + expires_delta

        payload = {
            "user_id": str(user_id),
            "area_id": area_id,
            "company_id": str(company_id),
            "role": role,
            "exp": expire,
            "iat": now,
            "token_type": "refresh",
        }

        token = jwt.encode(
            payload, self.config.SECRET_KEY, algorithm=self.config.ALGORITHM
        )

        logger.info(
            "Refresh token created",
            user_id=str(user_id),
            area_id=area_id,
            expires_at=expire.isoformat(),
        )

        return token

    def verify_token(self, token: str, token_type: str = "access") -> AuthenticatedUser:
        """Verify and decode a JWT token.

        Args:
            token: JWT token string to verify
            token_type: Expected token type ("access" or "refresh")

        Returns:
            AuthenticatedUser instance with user information from token

        Raises:
            UnauthorizedException: If token is invalid, expired, or wrong type

        Example:
            >>> user = auth_service.verify_token(token, "access")
            >>> print(user.username)
        """
        try:
            payload = jwt.decode(
                token, self.config.SECRET_KEY, algorithms=[self.config.ALGORITHM]
            )

            # Verify token type
            if payload.get("token_type") != token_type:
                logger.warning(
                    "Invalid token type",
                    expected=token_type,
                    actual=payload.get("token_type"),
                )
                raise UnauthorizedException("Invalid token type")

            # Extract user information
            user = AuthenticatedUser(
                user_id=UUID(payload["user_id"]),
                area_id=payload["area_id"],
                company_id=UUID(payload["company_id"]),
                role=payload["role"],
            )

            logger.debug(
                "Token verified successfully",
                user_id=str(user.user_id),
            )

            return user

        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            raise UnauthorizedException("Token has expired")
        except jwt.InvalidTokenError as e:
            logger.warning("Invalid token", error=str(e))
            raise UnauthorizedException("Invalid token")
        except (KeyError, ValueError) as e:
            logger.warning("Invalid token payload", error=str(e))
            raise UnauthorizedException("Invalid token payload")

    def decode_token(self, token: str) -> dict:
        """Decode a JWT token without verification (for debugging).

        Args:
            token: JWT token string to decode

        Returns:
            Dictionary containing token payload

        Note:
            This method does NOT verify the token signature.
            Use verify_token() for secure token validation.

        Example:
            >>> payload = auth_service.decode_token(token)
            >>> print(payload['username'])
        """
        try:
            payload = jwt.decode(token, options={"verify_signature": False})
            return payload
        except jwt.InvalidTokenError as e:
            logger.warning("Failed to decode token", error=str(e))
            raise UnauthorizedException("Invalid token format")

    def get_token_expiry(self, token: str) -> Optional[datetime]:
        """Get the expiration time of a token.

        Args:
            token: JWT token string

        Returns:
            Datetime of token expiration or None if cannot be determined

        Example:
            >>> expiry = auth_service.get_token_expiry(token)
            >>> print(f"Token expires at: {expiry}")
        """
        try:
            payload = self.decode_token(token)
            exp_timestamp = payload.get("exp")
            if exp_timestamp:
                return datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
            return None
        except Exception as e:
            logger.warning("Failed to get token expiry", error=str(e))
            return None
