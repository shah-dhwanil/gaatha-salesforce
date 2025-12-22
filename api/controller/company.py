"""
Company controller for FastAPI routes.

This module defines the API endpoints for company operations including
CRUD operations and company management.
"""

from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, status
import structlog

from api.database import DatabasePool, get_db_pool
from api.repository.company import CompanyRepository
from api.service.company import CompanyService
from api.models.base import ResponseModel, ListResponseModel
from api.models.company import (
    CreateCompanyRequest,
    UpdateCompanyRequest,
    CompanyResponse,
)

logger = structlog.get_logger(__name__)

# Create router
router = APIRouter(prefix="/companies", tags=["companies"])


# Dependency to get company service
async def get_company_service(
    db: Annotated[DatabasePool, Depends(get_db_pool, scope="function")],
) -> CompanyService:
    """Dependency to create and return CompanyService instance."""
    company_repository = CompanyRepository(db)
    return CompanyService(company_repository)


@router.post(
    "/",
    response_model=ResponseModel[CompanyResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new company",
    description="Create a new company with the specified name, GST number, CIN number, and address.",
)
async def create_company(
    request: CreateCompanyRequest,
    company_service: CompanyService = Depends(get_company_service),
) -> ResponseModel[CompanyResponse]:
    """
    Create a new company.

    Args:
        request: CreateCompanyRequest with company details
        company_service: Injected CompanyService dependency

    Returns:
        CompanyResponse with created company details

    Raises:
        HTTPException: 409 if company already exists (GST or CIN)
        HTTPException: 400 if validation fails
    """
    logger.info(
        "Creating new company",
        name=request.name,
        gst_no=request.gst_no,
        cin_no=request.cin_no,
    )

    company = await company_service.create_company(
        name=request.name,
        gst_no=request.gst_no,
        cin_no=request.cin_no,
        address=request.address,
    )

    return ResponseModel(
        status_code=status.HTTP_201_CREATED,
        data=CompanyResponse(
            id=company.id,
            name=company.name,
            gst_no=company.gst_no,
            cin_no=company.cin_no,
            address=company.address,
            is_active=company.is_active,
            created_at=company.created_at,
            updated_at=company.updated_at,
        ),
    )


@router.get(
    "/",
    response_model=ListResponseModel[CompanyResponse],
    status_code=status.HTTP_200_OK,
    summary="Get all companies",
    description="Retrieve all active companies.",
)
async def get_all_companies(
    company_service: CompanyService = Depends(get_company_service),
) -> ListResponseModel[CompanyResponse]:
    """
    Get all active companies.

    Args:
        company_service: Injected CompanyService dependency

    Returns:
        ListResponseModel with list of all active companies
    """
    logger.info("Fetching all companies")

    companies = await company_service.get_all_companies()

    company_responses = [
        CompanyResponse(
            id=company.id,
            name=company.name,
            gst_no=company.gst_no,
            cin_no=company.cin_no,
            address=company.address,
            is_active=company.is_active,
            created_at=company.created_at,
            updated_at=company.updated_at,
        )
        for company in companies
    ]

    return ListResponseModel(
        status_code=status.HTTP_200_OK,
        data=company_responses,
        records_per_page=len(company_responses),
        total_count=len(company_responses),
    )


@router.get(
    "/id/{company_id}",
    response_model=ResponseModel[CompanyResponse],
    status_code=status.HTTP_200_OK,
    summary="Get company by ID",
    description="Retrieve a specific company by its UUID.",
)
async def get_company_by_id(
    company_id: UUID,
    company_service: CompanyService = Depends(get_company_service),
) -> ResponseModel[CompanyResponse]:
    """
    Get a company by ID.

    Args:
        company_id: UUID of the company
        company_service: Injected CompanyService dependency

    Returns:
        CompanyResponse with company details

    Raises:
        HTTPException: 404 if company not found
    """
    logger.info("Fetching company by ID", company_id=str(company_id))

    company = await company_service.get_company_by_id(company_id)

    return ResponseModel(
        status_code=status.HTTP_200_OK,
        data=CompanyResponse(
            id=company.id,
            name=company.name,
            gst_no=company.gst_no,
            cin_no=company.cin_no,
            address=company.address,
            is_active=company.is_active,
            created_at=company.created_at,
            updated_at=company.updated_at,
        ),
    )


@router.get(
    "/gst/{gst_no}",
    response_model=ResponseModel[CompanyResponse],
    status_code=status.HTTP_200_OK,
    summary="Get company by GST number",
    description="Retrieve a specific company by its GST number.",
)
async def get_company_by_gst_no(
    gst_no: str,
    company_service: CompanyService = Depends(get_company_service),
) -> ResponseModel[CompanyResponse]:
    """
    Get a company by GST number.

    Args:
        gst_no: GST number of the company
        company_service: Injected CompanyService dependency

    Returns:
        CompanyResponse with company details

    Raises:
        HTTPException: 404 if company not found
        HTTPException: 400 if GST number is invalid
    """
    logger.info("Fetching company by GST number", gst_no=gst_no)

    company = await company_service.get_company_by_gst_no(gst_no)

    return ResponseModel(
        status_code=status.HTTP_200_OK,
        data=CompanyResponse(
            id=company.id,
            name=company.name,
            gst_no=company.gst_no,
            cin_no=company.cin_no,
            address=company.address,
            is_active=company.is_active,
            created_at=company.created_at,
            updated_at=company.updated_at,
        ),
    )


@router.get(
    "/cin/{cin_no}",
    response_model=ResponseModel[CompanyResponse],
    status_code=status.HTTP_200_OK,
    summary="Get company by CIN number",
    description="Retrieve a specific company by its CIN number.",
)
async def get_company_by_cin_no(
    cin_no: str,
    company_service: CompanyService = Depends(get_company_service),
) -> ResponseModel[CompanyResponse]:
    """
    Get a company by CIN number.

    Args:
        cin_no: CIN number of the company
        company_service: Injected CompanyService dependency

    Returns:
        CompanyResponse with company details

    Raises:
        HTTPException: 404 if company not found
        HTTPException: 400 if CIN number is invalid
    """
    logger.info("Fetching company by CIN number", cin_no=cin_no)

    company = await company_service.get_company_by_cin_no(cin_no)

    return ResponseModel(
        status_code=status.HTTP_200_OK,
        data=CompanyResponse(
            id=company.id,
            name=company.name,
            gst_no=company.gst_no,
            cin_no=company.cin_no,
            address=company.address,
            is_active=company.is_active,
            created_at=company.created_at,
            updated_at=company.updated_at,
        ),
    )


@router.patch(
    "/{company_id}",
    response_model=ResponseModel[CompanyResponse],
    status_code=status.HTTP_200_OK,
    summary="Update a company",
    description="Update an existing company's details (name, GST, CIN, or address).",
)
async def update_company(
    company_id: UUID,
    request: UpdateCompanyRequest,
    company_service: CompanyService = Depends(get_company_service),
) -> ResponseModel[CompanyResponse]:
    """
    Update a company.

    Args:
        request: UpdateCompanyRequest with update details
        company_service: Injected CompanyService dependency

    Returns:
        CompanyResponse with updated company details

    Raises:
        HTTPException: 404 if company not found
        HTTPException: 400 if no fields provided for update or validation fails
        HTTPException: 409 if updated GST or CIN already exists
    """
    logger.info("Updating company", company_id=str(company_id))

    # Validate at least one field is provided
    if not request.has_updates():
        company = await company_service.get_company_by_id(company_id)
    else:
        company = await company_service.update_company(
            company_id=company_id,
            name=request.name,
            gst_no=request.gst_no,
            cin_no=request.cin_no,
            address=request.address,
        )

    return ResponseModel(
        status_code=status.HTTP_200_OK,
        data=CompanyResponse(
            id=company.id,
            name=company.name,
            gst_no=company.gst_no,
            cin_no=company.cin_no,
            address=company.address,
            is_active=company.is_active,
            created_at=company.created_at,
            updated_at=company.updated_at,
        ),
    )


@router.delete(
    "/{company_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a company",
    description="Soft delete a company by marking it as inactive.",
)
async def delete_company(
    company_id: UUID,
    company_service: CompanyService = Depends(get_company_service),
) -> None:
    """
    Delete a company (soft delete).

    Args:
        company_id: UUID of the company to delete
        company_service: Injected CompanyService dependency

    Returns:
        None (204 No Content)

    Raises:
        HTTPException: 404 if company not found
    """
    logger.info("Deleting company", company_id=str(company_id))

    await company_service.delete_company(company_id)

    return
