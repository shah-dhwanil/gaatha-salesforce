"""
Company controller/router for FastAPI endpoints.

This module defines all REST API endpoints for company management.
Companies are global entities stored in the salesforce schema.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Query, status
import structlog

from api.dependencies.company import CompanyServiceDep
from api.exceptions.company import (
    CompanyAlreadyExistsException,
    CompanyNotFoundException,
    CompanyOperationException,
    CompanyValidationException,
)
from api.models import ListResponseModel, ResponseModel
from api.models.company import CompanyCreate, CompanyListItem, CompanyResponse, CompanyUpdate

logger = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/companies",
    tags=["Companies"],
    responses={
        400: {"description": "Bad Request - Invalid input"},
        404: {"description": "Resource Not Found"},
        500: {"description": "Internal Server Error"},
    },
)


@router.post(
    "",
    response_model=ResponseModel[CompanyResponse],
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Company created successfully with schema and migrations"},
        400: {"description": "Validation error"},
        409: {"description": "Company already exists (duplicate GST/CIN)"},
    },
    summary="Create a new company",
    description="Create a new company with automatic schema creation and migration application",
)
async def create_company(
    company_data: CompanyCreate,
    company_service: CompanyServiceDep,
):
    """
    Create a new company with schema and migrations.

    This endpoint:
    1. Creates the company record in the salesforce schema
    2. Creates a dedicated tenant schema for the company
    3. Applies all migrations to the new schema (roles, areas, members tables, etc.)

    - **name**: Company name (1-255 characters)
    - **gst_no**: GST number (exactly 15 characters, auto-uppercase)
    - **cin_no**: CIN number (exactly 21 characters, auto-uppercase)
    - **address**: Company address
    - **is_active**: Whether the company is active (default: true)

    **Note**: If any step fails, the operation is automatically rolled back and cleaned up.
    """
    try:
        company = await company_service.create_company(company_data)
        return ResponseModel(status_code=status.HTTP_201_CREATED, data=company)

    except CompanyAlreadyExistsException as e:
        logger.warning(
            "Company already exists",
            gst_no=company_data.gst_no,
            cin_no=company_data.cin_no,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        )

    except CompanyValidationException as e:
        logger.warning(
            "Company validation failed",
            company_name=company_data.name,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )

    except CompanyOperationException as e:
        logger.error(
            "Failed to create company",
            company_name=company_data.name,
            error=e.message,
            operation=e.operation,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create company: {e.message}",
        )

    except Exception as e:
        logger.error(
            "Unexpected error creating company",
            company_name=company_data.name,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create company",
        )


@router.get(
    "/{company_id}",
    response_model=ResponseModel[CompanyResponse],
    responses={
        200: {"description": "Company retrieved successfully"},
        404: {"description": "Company not found"},
    },
    summary="Get company by ID",
    description="Retrieve detailed information about a specific company",
)
async def get_company_by_id(
    company_id: Annotated[UUID, Path(description="Company UUID")],
    company_service: CompanyServiceDep,
):
    """
    Get a company by ID.

    Returns complete company information including GST, CIN, address, and timestamps.
    """
    try:
        company = await company_service.get_company_by_id(company_id)
        return ResponseModel(status_code=status.HTTP_200_OK, data=company)

    except CompanyNotFoundException as e:
        logger.info(
            "Company not found",
            company_id=str(company_id),
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to get company",
            company_id=str(company_id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve company",
        )


@router.get(
    "/gst/{gst_no}",
    response_model=ResponseModel[CompanyResponse],
    responses={
        200: {"description": "Company retrieved successfully"},
        404: {"description": "Company not found"},
    },
    summary="Get company by GST number",
    description="Retrieve company information by GST number",
)
async def get_company_by_gst(
    gst_no: Annotated[str, Path(description="GST number (15 characters)")],
    company_service: CompanyServiceDep,
):
    """
    Get a company by GST number.

    Returns complete company information for the company with the specified GST number.
    """
    try:
        company = await company_service.get_company_by_gst(gst_no.upper())
        return ResponseModel(status_code=status.HTTP_200_OK, data=company)

    except CompanyNotFoundException as e:
        logger.info(
            "Company not found by GST",
            gst_no=gst_no,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to get company by GST",
            gst_no=gst_no,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve company",
        )


@router.get(
    "/cin/{cin_no}",
    response_model=ResponseModel[CompanyResponse],
    responses={
        200: {"description": "Company retrieved successfully"},
        404: {"description": "Company not found"},
    },
    summary="Get company by CIN number",
    description="Retrieve company information by CIN number",
)
async def get_company_by_cin(
    cin_no: Annotated[str, Path(description="CIN number (21 characters)")],
    company_service: CompanyServiceDep,
):
    """
    Get a company by CIN number.

    Returns complete company information for the company with the specified CIN number.
    """
    try:
        company = await company_service.get_company_by_cin(cin_no.upper())
        return ResponseModel(status_code=status.HTTP_200_OK, data=company)

    except CompanyNotFoundException as e:
        logger.info(
            "Company not found by CIN",
            cin_no=cin_no,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to get company by CIN",
            cin_no=cin_no,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve company",
        )


@router.get(
    "",
    response_model=ListResponseModel[CompanyListItem],
    responses={
        200: {"description": "Companies retrieved successfully"},
        400: {"description": "Invalid pagination parameters"},
    },
    summary="List all companies",
    description="List all companies with pagination and optional filtering by active status",
)
async def list_companies(
    company_service: CompanyServiceDep,
    is_active: Annotated[
        bool | None,
        Query(description="Filter by active status (true/false, optional)"),
    ] = None,
    limit: Annotated[
        int,
        Query(ge=1, le=100, description="Number of companies to return (1-100)"),
    ] = 20,
    offset: Annotated[
        int,
        Query(ge=0, description="Number of companies to skip (pagination)"),
    ] = 0,
):
    """
    List all companies with pagination.

    Returns minimal company data (id, name, is_active) for performance.
    Use the detail endpoint (GET /{company_id}) to get complete company information.

    - **is_active**: Optional filter by active status
    - **limit**: Number of results to return (default: 20, max: 100)
    - **offset**: Number of results to skip (default: 0)
    """
    try:
        companies, total_count = await company_service.list_companies(
            is_active=is_active,
            limit=limit,
            offset=offset,
        )

        return ListResponseModel(
            status_code=status.HTTP_200_OK,
            data=companies,
            records_per_page=limit,
            total_count=total_count,
        )

    except CompanyValidationException as e:
        logger.warning(
            "Invalid pagination parameters",
            limit=limit,
            offset=offset,
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to list companies",
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list companies",
        )


@router.patch(
    "/{company_id}",
    response_model=ResponseModel[CompanyResponse],
    responses={
        200: {"description": "Company updated successfully"},
        400: {"description": "Validation error"},
        404: {"description": "Company not found"},
    },
    summary="Update a company",
    description="Update company name and/or address (GST and CIN cannot be updated)",
)
async def update_company(
    company_id: Annotated[UUID, Path(description="Company UUID")],
    company_data: CompanyUpdate,
    company_service: CompanyServiceDep,
):
    """
    Update an existing company.

    Only name and address can be updated. GST and CIN numbers are immutable.
    Use delete endpoint to deactivate a company.

    - **name**: Optional new company name
    - **address**: Optional new address
    """
    try:
        company = await company_service.update_company(company_id, company_data)
        return ResponseModel(status_code=status.HTTP_200_OK, data=company)

    except CompanyNotFoundException as e:
        logger.info(
            "Company not found for update",
            company_id=str(company_id),
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except CompanyValidationException as e:
        logger.warning(
            "Company update validation failed",
            company_id=str(company_id),
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to update company",
            company_id=str(company_id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update company",
        )


@router.delete(
    "/{company_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Company deactivated successfully"},
        404: {"description": "Company not found"},
    },
    summary="Delete a company (soft delete)",
    description="Soft delete a company by setting is_active to false. Schema is retained.",
)
async def delete_company(
    company_id: Annotated[UUID, Path(description="Company UUID")],
    company_service: CompanyServiceDep,
):
    """
    Delete a company (soft delete).

    Sets is_active to false instead of permanently deleting the company.
    The company and its schema will still exist but the company won't be active.

    **Important**: The tenant schema is retained for data retention and compliance.
    """
    try:
        await company_service.delete_company(company_id)
        return None  # 204 No Content

    except CompanyNotFoundException as e:
        logger.info(
            "Company not found for deletion",
            company_id=str(company_id),
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to delete company",
            company_id=str(company_id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete company",
        )


@router.get(
    "/{company_id}/schema",
    response_model=ResponseModel[dict],
    responses={
        200: {"description": "Schema name retrieved successfully"},
        404: {"description": "Company not found"},
    },
    summary="Get company schema name",
    description="Get the database schema name for a company",
)
async def get_company_schema(
    company_id: Annotated[UUID, Path(description="Company UUID")],
    company_service: CompanyServiceDep,
):
    """
    Get the schema name for a company.

    Returns the tenant-specific schema name used for storing company data.
    This is useful for understanding the multi-tenant architecture.
    """
    try:
        schema_name = await company_service.get_company_schema_name(company_id)
        return ResponseModel(
            status_code=status.HTTP_200_OK,
            data={"company_id": str(company_id), "schema_name": schema_name},
        )

    except CompanyNotFoundException as e:
        logger.info(
            "Company not found",
            company_id=str(company_id),
            error=e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )

    except Exception as e:
        logger.error(
            "Failed to get company schema",
            company_id=str(company_id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get company schema",
        )


@router.get(
    "/{company_id}/exists",
    response_model=ResponseModel[dict],
    responses={
        200: {"description": "Existence check completed"},
    },
    summary="Check if company exists",
    description="Check if a company with the given ID exists",
)
async def check_company_exists(
    company_id: Annotated[UUID, Path(description="Company UUID")],
    company_service: CompanyServiceDep,
):
    """
    Check if a company exists.

    Returns a boolean indicating whether the company exists.
    """
    try:
        exists = await company_service.check_company_exists(company_id)
        return ResponseModel(
            status_code=status.HTTP_200_OK,
            data={"company_id": str(company_id), "exists": exists},
        )

    except Exception as e:
        logger.error(
            "Failed to check company existence",
            company_id=str(company_id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check company existence",
        )


@router.get(
    "/stats/count",
    response_model=ResponseModel[dict],
    responses={
        200: {"description": "Count retrieved successfully"},
    },
    summary="Get active companies count",
    description="Get the total count of active companies",
)
async def get_active_companies_count(
    company_service: CompanyServiceDep,
):
    """
    Get count of active companies.

    Returns the total number of companies with is_active=true.
    """
    try:
        count = await company_service.get_active_companies_count()
        return ResponseModel(
            status_code=status.HTTP_200_OK,
            data={"active_count": count},
        )

    except Exception as e:
        logger.error(
            "Failed to get active companies count",
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get active companies count",
        )

