"""
Exceptions module for custom application exceptions.

This module contains all custom exception classes that extend from AppException
and are used throughout the application for error handling.
"""

from api.exceptions.app import AppException, ErrorTypes, UnkownAppException

__all__ = [
    # Base exceptions
    "AppException",
    "ErrorTypes",
    "UnkownAppException",
]
