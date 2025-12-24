"""
JWT configuration settings.

This module contains JWT-specific configuration settings for token generation,
validation, and security parameters.
"""

from pydantic import BaseModel, Field


class JWTConfig(BaseModel):
    """JWT configuration settings."""

    SECRET_KEY: str = Field(
        default="your-secret-key-change-this-in-production",
        description="Secret key for JWT token encoding/decoding",
    )
    ALGORITHM: str = Field(
        default="HS256", description="Algorithm used for JWT token encoding"
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30, description="Access token expiration time in minutes"
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7, description="Refresh token expiration time in days"
    )
    TOKEN_TYPE: str = Field(
        default="Bearer", description="Token type for authorization header"
    )
