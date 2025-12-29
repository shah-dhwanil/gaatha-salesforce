"""
Custom exceptions for Company operations.
"""

from typing import Any, Optional
from uuid import UUID

from api.exceptions.app import AppException, ErrorTypes


class CompanyNotFoundException(AppException):
    """Exception raised when a company is not found."""

    def __init__(
        self,
        company_id: Optional[UUID] = None,
        gst_no: Optional[str] = None,
        cin_no: Optional[str] = None,
        message: Optional[str] = None,
        **kwargs,
    ) -> None:
        if message is None:
            if company_id:
                message = f"Company with id '{company_id}' not found"
            elif gst_no:
                message = f"Company with GST number '{gst_no}' not found"
            elif cin_no:
                message = f"Company with CIN number '{cin_no}' not found"
            else:
                message = "Company not found"

        value = company_id or gst_no or cin_no
        field = "id" if company_id else "gst_no" if gst_no else "cin_no" if cin_no else None

        super().__init__(
            type=ErrorTypes.ResourceNotFound,
            message=message,
            resource="company",
            field=field,
            value=str(value) if value else None,
            **kwargs,
        )


class CompanyAlreadyExistsException(AppException):
    """Exception raised when trying to create a company that already exists."""

    def __init__(
        self,
        gst_no: Optional[str] = None,
        cin_no: Optional[str] = None,
        message: Optional[str] = None,
        **kwargs,
    ) -> None:
        if message is None:
            if gst_no and cin_no:
                message = f"Company with GST '{gst_no}' or CIN '{cin_no}' already exists"
            elif gst_no:
                message = f"Company with GST number '{gst_no}' already exists"
            elif cin_no:
                message = f"Company with CIN number '{cin_no}' already exists"
            else:
                message = "Company already exists"

        super().__init__(
            type=ErrorTypes.ResourceAlreadyExists,
            message=message,
            resource="company",
            field="gst_no" if gst_no else "cin_no",
            value=gst_no or cin_no,
            **kwargs,
        )


class CompanyValidationException(AppException):
    """Exception raised when company validation fails."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        **kwargs,
    ) -> None:
        super().__init__(
            type=ErrorTypes.InputValidationError,
            message=message,
            resource="company",
            field=field,
            value=value,
            **kwargs,
        )


class CompanyOperationException(AppException):
    """Exception raised when a company operation fails."""

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        **kwargs,
    ) -> None:
        super().__init__(
            type=ErrorTypes.InvalidOperation,
            message=message,
            resource="company",
            **kwargs,
        )
        self.operation = operation

