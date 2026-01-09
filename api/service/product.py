"""
Service layer for Product entity operations.

This service provides business logic for products, including price and visibility management,
acting as an intermediary between the API layer and the repository layer.
"""

from typing import Optional
from uuid import UUID

import structlog

from api.database import DatabasePool
from api.exceptions.product import (
    ProductAlreadyExistsException,
    ProductNotFoundException,
    ProductOperationException,
)
from api.models.product import (
    ProductCreate,
    ProductDetailItem,
    ProductListItem,
    ProductUpdate,
)
from api.repository.product import ProductRepository

logger = structlog.get_logger(__name__)


class ProductService:
    """
    Service for managing Product business logic.

    This service handles business logic, validation, and orchestration
    for product operations including price and visibility management
    in a multi-tenant environment.
    """

    def __init__(self, db_pool: DatabasePool, company_id: UUID) -> None:
        """
        Initialize the ProductService.

        Args:
            db_pool: Database pool instance for connection management
            company_id: UUID of the company (tenant) for schema isolation
        """
        self.db_pool = db_pool
        self.company_id = company_id
        self.repository = ProductRepository(db_pool, company_id)
        logger.debug(
            "ProductService initialized",
            company_id=str(company_id),
        )

    async def create_product(self, product_data: ProductCreate) -> ProductDetailItem:
        """
        Create a new product.

        Args:
            product_data: Product data to create

        Returns:
            Created product with full details

        Raises:
            ProductAlreadyExistsException: If product with same code exists
            ProductOperationException: If creation fails
        """
        try:
            logger.info(
                "Creating product",
                product_name=product_data.name,
                product_code=product_data.code,
                company_id=str(self.company_id),
            )

            # Create product using repository
            product = await self.repository.create_product(product_data)

            # Fetch full details to return
            product_detail = await self.repository.get_product_by_id(product.id)

            logger.info(
                "Product created successfully",
                product_id=product.id,
                product_name=product.name,
                company_id=str(self.company_id),
            )

            return product_detail

        except (ProductAlreadyExistsException, ProductNotFoundException, ProductOperationException):
            raise
        except Exception as e:
            logger.error(
                "Failed to create product in service",
                product_name=product_data.name,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def get_product_by_id(self, product_id: int) -> ProductDetailItem:
        """
        Get a product by ID with full details.

        Args:
            product_id: ID of the product

        Returns:
            Product with full details

        Raises:
            ProductNotFoundException: If product not found
            ProductOperationException: If retrieval fails
        """
        try:
            logger.debug(
                "Getting product by ID",
                product_id=product_id,
                company_id=str(self.company_id),
            )

            product = await self.repository.get_product_by_id(product_id)

            return product

        except ProductNotFoundException:
            logger.warning(
                "Product not found",
                product_id=product_id,
                company_id=str(self.company_id),
            )
            raise
        except Exception as e:
            logger.error(
                "Failed to get product in service",
                product_id=product_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def get_product_by_code(self, code: str) -> ProductDetailItem:
        """
        Get a product by code with full details.

        Args:
            code: Code of the product

        Returns:
            Product with full details

        Raises:
            ProductNotFoundException: If product not found
            ProductOperationException: If retrieval fails
        """
        try:
            logger.debug(
                "Getting product by code",
                product_code=code,
                company_id=str(self.company_id),
            )

            product = await self.repository.get_product_by_code(code)

            return product

        except ProductNotFoundException:
            logger.warning(
                "Product not found",
                product_code=code,
                company_id=str(self.company_id),
            )
            raise
        except Exception as e:
            logger.error(
                "Failed to get product in service",
                product_code=code,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def list_products(
        self,
        is_active: Optional[bool] = None,
        brand_id: Optional[int] = None,
        category_id: Optional[int] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[ProductListItem]:
        """
        List products with minimal data.

        Args:
            is_active: Filter by active status
            brand_id: Filter by brand ID
            category_id: Filter by category ID
            limit: Maximum number of products to return
            offset: Number of products to skip

        Returns:
            List of products

        Raises:
            ProductOperationException: If listing fails
        """
        try:
            logger.debug(
                "Listing products",
                is_active=is_active,
                brand_id=brand_id,
                category_id=category_id,
                limit=limit,
                offset=offset,
                company_id=str(self.company_id),
            )

            products = await self.repository.list_products(
                is_active, brand_id, category_id, limit, offset
            )

            logger.debug(
                "Products listed successfully",
                count=len(products),
                company_id=str(self.company_id),
            )

            return products

        except Exception as e:
            logger.error(
                "Failed to list products in service",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def update_product(
        self, product_id: int, product_data: ProductUpdate
    ) -> ProductDetailItem:
        """
        Update a product.

        Args:
            product_id: ID of the product to update
            product_data: Product data to update

        Returns:
            Updated product with full details

        Raises:
            ProductNotFoundException: If product not found
            ProductAlreadyExistsException: If updated code conflicts
            ProductOperationException: If update fails
        """
        try:
            logger.info(
                "Updating product",
                product_id=product_id,
                company_id=str(self.company_id),
            )

            # Update product using repository
            await self.repository.update_product(product_id, product_data)

            # Fetch full details to return
            product_detail = await self.repository.get_product_by_id(product_id)

            logger.info(
                "Product updated successfully",
                product_id=product_id,
                company_id=str(self.company_id),
            )

            return product_detail

        except (ProductNotFoundException, ProductAlreadyExistsException, ProductOperationException):
            raise
        except Exception as e:
            logger.error(
                "Failed to update product in service",
                product_id=product_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def delete_product(self, product_id: int) -> None:
        """
        Soft delete a product.

        Args:
            product_id: ID of the product to delete

        Raises:
            ProductNotFoundException: If product not found
            ProductOperationException: If deletion fails
        """
        try:
            logger.info(
                "Deleting product",
                product_id=product_id,
                company_id=str(self.company_id),
            )

            await self.repository.delete_product(product_id)

            logger.info(
                "Product deleted successfully",
                product_id=product_id,
                company_id=str(self.company_id),
            )

        except (ProductNotFoundException, ProductOperationException):
            raise
        except Exception as e:
            logger.error(
                "Failed to delete product in service",
                product_id=product_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise

    async def get_products_for_shop_id(
        self, shop_id: UUID, limit: int = 20, offset: int = 0
    ) -> list[ProductListItem]:
        """
        Get products available for a specific shop based on route and area.

        This method retrieves products that are available for a shop considering:
        - The shop's assigned route
        - The route's area hierarchy (division, area, zone, region, nation)
        - Area-specific pricing

        Args:
            shop_id: ID of the shop/retailer
            limit: Maximum number of products to return (default: 20)
            offset: Number of products to skip for pagination (default: 0)

        Returns:
            List of products available for the shop with pricing

        Raises:
            ProductOperationException: If retrieval fails
        """
        try:
            logger.debug(
                "Getting products for shop",
                shop_id=shop_id,
                limit=limit,
                offset=offset,
                company_id=str(self.company_id),
            )

            products = await self.repository.get_products_for_shop_id(
                shop_id=shop_id, limit=limit, offset=offset
            )

            logger.debug(
                "Products retrieved for shop successfully",
                shop_id=shop_id,
                count=len(products),
                company_id=str(self.company_id),
            )

            return products

        except Exception as e:
            logger.error(
                "Failed to get products for shop in service",
                shop_id=shop_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise
