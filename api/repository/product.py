"""
Repository for Product entity operations.

This repository handles all database operations for products in a multi-tenant architecture.
Products are stored per tenant schema and include related entities:
- products: main product information
- product_prices: area-based pricing configurations
- product_visibility: area and shop type visibility settings
"""

import json
from typing import Optional
from uuid import UUID

import asyncpg
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
    ProductInDB,
    ProductListItem,
    ProductPriceCreate,
    ProductPriceInDB,
    ProductUpdate,
    ProductVisibilityCreate,
    ProductVisibilityInDB,
    Dimensions,
    MeasurementDetails,
    PackagingDetails,
    ProductMargins,
    MinOrderQuantities,
)
from api.models.docuemnts import DocumentInDB
from api.repository.utils import get_schema_name, set_search_path

logger = structlog.get_logger(__name__)


class ProductRepository:
    """
    Repository for managing Product entities in a multi-tenant database.

    This repository provides methods for CRUD operations on products,
    handling schema-per-tenant isolation using asyncpg.
    Treats product, product_prices, and product_visibility as a single unit.
    """

    def __init__(self, db_pool: DatabasePool, company_id: UUID) -> None:
        """
        Initialize the ProductRepository.

        Args:
            db_pool: Database pool instance for connection management
            company_id: UUID of the company (tenant) for schema isolation
        """
        self.db_pool = db_pool
        self.company_id = company_id
        self.schema_name = get_schema_name(company_id)

    async def _create_product(
        self, product_data: ProductCreate, connection: asyncpg.Connection
    ) -> ProductInDB:
        """
        Private method to create a product with a provided connection.

        Args:
            product_data: Product data to create
            connection: Database connection

        Returns:
            Created product

        Raises:
            ProductAlreadyExistsException: If product with same code exists
            ProductOperationException: If creation fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Convert JSONB fields to JSON strings
            dimensions_json = (
                product_data.dimensions.model_dump_json()
                if product_data.dimensions
                else None
            )
            measurement_json = (
                product_data.measurement_details.model_dump_json()
                if product_data.measurement_details
                else None
            )
            packaging_json = (
                json.dumps([p.model_dump(mode="json") for p in product_data.packaging_details])
                if product_data.packaging_details
                else None
            )
            images_json = (
                json.dumps([img.model_dump(mode="json") for img in product_data.images])
                if product_data.images
                else None
            )

            # Insert the product
            row = await connection.fetchrow(
                """
                INSERT INTO products (
                    brand_id, brand_category_id, brand_subcategory_id,
                    name, code, description, barcode, hsn_code,
                    gst_rate, gst_category, dimensions, compliance,
                    measurement_details, packaging_type, packaging_details, images
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
                RETURNING id, brand_id, brand_category_id, brand_subcategory_id,
                          name, code, description, barcode, hsn_code,
                          gst_rate, gst_category, dimensions, compliance,
                          measurement_details, packaging_type, packaging_details,
                          images, is_active, created_at, updated_at
                """,
                product_data.brand_id,
                product_data.brand_category_id,
                product_data.brand_subcategory_id,
                product_data.name,
                product_data.code,
                product_data.description,
                product_data.barcode,
                product_data.hsn_code,
                product_data.gst_rate,
                product_data.gst_category,
                dimensions_json,
                product_data.compliance,
                measurement_json,
                product_data.packaging_type,
                packaging_json,
                images_json,
            )

            product_id = row["id"]

            # Handle product prices
            if product_data.prices and len(product_data.prices) > 0:
                for price_data in product_data.prices:
                    margins_json = (
                        price_data.margins.model_dump_json()
                        if price_data.margins
                        else None
                    )
                    moq_json = (
                        price_data.min_order_quantity.model_dump_json()
                        if price_data.min_order_quantity
                        else None
                    )

                    await connection.execute(
                        """
                        INSERT INTO product_prices (product_id, area_id, mrp, margins, min_order_quantity)
                        VALUES ($1, $2, $3, $4, $5)
                        """,
                        product_id,
                        price_data.area_id,
                        price_data.mrp,
                        margins_json,
                        moq_json,
                    )

            # Handle product visibility
            if product_data.visibility and len(product_data.visibility) > 0:
                for visibility_data in product_data.visibility:
                    await connection.execute(
                        """
                        INSERT INTO product_visibility (
                            product_id, area_id, for_general, for_modern,
                            for_horeca, for_type_a, for_type_b, for_type_c
                        )
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        """,
                        product_id,
                        visibility_data.area_id,
                        visibility_data.for_general,
                        visibility_data.for_modern,
                        visibility_data.for_horeca,
                        visibility_data.for_type_a,
                        visibility_data.for_type_b,
                        visibility_data.for_type_c,
                    )

            logger.info(
                "Product created successfully",
                product_id=product_id,
                product_name=product_data.name,
                company_id=str(self.company_id),
            )

            return self._row_to_product_in_db(row)

        except asyncpg.UniqueViolationError as e:
            if "uniq_products_brand_category_code" in str(e):
                raise ProductAlreadyExistsException(
                    product_code=product_data.code,
                )
            else:
                raise ProductOperationException(
                    message=f"Failed to create product: {str(e)}",
                    operation="create",
                ) from e
        except asyncpg.ForeignKeyViolationError as e:
            error_msg = "Foreign key violation"
            if "brand_id" in str(e):
                error_msg = "Brand not found"
            elif "brand_category_id" in str(e):
                error_msg = "Brand category not found"
            elif "area_id" in str(e):
                error_msg = "One or more area IDs not found"
            
            raise ProductOperationException(
                message=error_msg,
                operation="create",
            ) from e
        except Exception as e:
            logger.error(
                "Failed to create product",
                product_name=product_data.name,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise ProductOperationException(
                message=f"Failed to create product: {str(e)}",
                operation="create",
            ) from e

    def _row_to_product_in_db(self, row: asyncpg.Record) -> ProductInDB:
        """Helper method to convert database row to ProductInDB model."""
        print("Packaging Details",json.loads(row["packaging_details"]))
        return ProductInDB(
            id=row["id"],
            brand_id=row["brand_id"],
            brand_category_id=row["brand_category_id"],
            brand_subcategory_id=row["brand_subcategory_id"],
            name=row["name"],
            code=row["code"],
            description=row["description"],
            barcode=row["barcode"],
            hsn_code=row["hsn_code"],
            gst_rate=row["gst_rate"],
            gst_category=row["gst_category"],
            dimensions=(
                Dimensions.model_validate_json(row["dimensions"])
                if row["dimensions"]
                else None
            ),
            compliance=row["compliance"],
            measurement_details=(
                MeasurementDetails.model_validate_json(row["measurement_details"])
                if row["measurement_details"]
                else None
            ),
            packaging_type=row["packaging_type"],
            packaging_details=(
                [PackagingDetails(**p) for p in json.loads(row["packaging_details"])]
                if row["packaging_details"]
                else None
            ),
            images=(
                [DocumentInDB(**img) for img in json.loads(row["images"])]
                if row["images"]
                else None
            ),
            is_active=row["is_active"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    async def create_product(
        self, product_data: ProductCreate, connection: Optional[asyncpg.Connection] = None
    ) -> ProductInDB:
        """
        Create a new product.

        Args:
            product_data: Product data to create
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Created product

        Raises:
            ProductAlreadyExistsException: If product with same code exists
            ProductOperationException: If creation fails
        """
        if connection:
            return await self._create_product(product_data, connection)

        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                return await self._create_product(product_data, conn)

    async def _get_product_by_id(
        self, product_id: int, connection: asyncpg.Connection
    ) -> ProductDetailItem:
        """
        Private method to get a product by ID with a provided connection.
        Returns detailed product information with prices and visibility.

        Args:
            product_id: ID of the product
            connection: Database connection

        Returns:
            Detailed product information

        Raises:
            ProductNotFoundException: If product not found
            ProductOperationException: If retrieval fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Get product basic information with brand and category names
            row = await connection.fetchrow(
                """
                SELECT 
                    p.id, p.brand_id, p.brand_category_id, p.brand_subcategory_id,
                    p.name, p.code, p.description, p.barcode, p.hsn_code,
                    p.gst_rate, p.gst_category, p.dimensions, p.compliance,
                    p.measurement_details, p.packaging_type, p.packaging_details,
                    p.images, p.is_active, p.created_at, p.updated_at,
                    b.name as brand_name,
                    bc.name as category_name,
                    bsc.name as subcategory_name
                FROM products p
                INNER JOIN brand b ON p.brand_id = b.id
                INNER JOIN brand_categories bc ON p.brand_category_id = bc.id
                LEFT JOIN brand_categories bsc ON p.brand_subcategory_id = bsc.id
                WHERE p.id = $1 AND p.is_active = TRUE
                """,
                product_id,
            )

            if not row:
                raise ProductNotFoundException(
                    product_id=product_id,
                )

            # Get product prices
            price_rows = await connection.fetch(
                """
                SELECT id, product_id, area_id, mrp, margins, min_order_quantity,
                       is_active, created_at, updated_at
                FROM product_prices
                WHERE product_id = $1 AND is_active = TRUE
                ORDER BY area_id NULLS FIRST
                """,
                product_id,
            )

            prices = []
            for price_row in price_rows:
                price_dict = dict(price_row)
                if price_dict.get("margins"):
                    price_dict["margins"] = ProductMargins.model_validate_json(
                        price_dict["margins"]
                    )
                if price_dict.get("min_order_quantity"):
                    price_dict["min_order_quantity"] = MinOrderQuantities.model_validate_json(
                        price_dict["min_order_quantity"]
                    )
                prices.append(ProductPriceInDB(**price_dict))

            # Get product visibility
            visibility_rows = await connection.fetch(
                """
                SELECT id, product_id, area_id, for_general, for_modern,
                       for_horeca, for_type_a, for_type_b, for_type_c,
                       is_active, created_at, updated_at
                FROM product_visibility
                WHERE product_id = $1 AND is_active = TRUE
                ORDER BY area_id
                """,
                product_id,
            )

            visibility = [
                ProductVisibilityInDB(**dict(vis_row)) for vis_row in visibility_rows
            ]

            logger.info(
                "Product retrieved successfully",
                product_id=product_id,
                company_id=str(self.company_id),
            )

            return ProductDetailItem(
                id=row["id"],
                brand_id=row["brand_id"],
                brand_name=row["brand_name"],
                brand_category_id=row["brand_category_id"],
                category_name=row["category_name"],
                brand_subcategory_id=row["brand_subcategory_id"],
                subcategory_name=row["subcategory_name"],
                name=row["name"],
                code=row["code"],
                description=row["description"],
                barcode=row["barcode"],
                hsn_code=row["hsn_code"],
                gst_rate=row["gst_rate"],
                gst_category=row["gst_category"],
                dimensions=(
                    Dimensions.model_validate_json(row["dimensions"])
                    if row["dimensions"]
                    else None
                ),
                compliance=row["compliance"],
                measurement_details=(
                    MeasurementDetails.model_validate_json(row["measurement_details"])
                    if row["measurement_details"]
                    else None
                ),
                packaging_type=row["packaging_type"],
                packaging_details=(
                    [PackagingDetails(**p) for p in json.loads(row["packaging_details"])]
                    if row["packaging_details"]
                    else None
                ),
                images=(
                    [DocumentInDB(**img) for img in json.loads(row["images"])]
                    if row["images"]
                    else None
                ),
                prices=prices if prices else None,
                visibility=visibility if visibility else None,
                is_active=row["is_active"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

        except ProductNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to get product by id",
                product_id=product_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise ProductOperationException(
                message=f"Failed to get product: {str(e)}",
                operation="get",
            ) from e

    async def get_product_by_id(
        self, product_id: int, connection: Optional[asyncpg.Connection] = None
    ) -> ProductDetailItem:
        """
        Get a product by ID with detailed information.

        Args:
            product_id: ID of the product
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Detailed product information

        Raises:
            ProductNotFoundException: If product not found
            ProductOperationException: If retrieval fails
        """
        if connection:
            return await self._get_product_by_id(product_id, connection)

        async with self.db_pool.acquire() as conn:
            return await self._get_product_by_id(product_id, conn)

    async def _get_product_by_code(
        self, code: str, connection: asyncpg.Connection
    ) -> ProductDetailItem:
        """
        Private method to get a product by code with a provided connection.

        Args:
            code: Code of the product
            connection: Database connection

        Returns:
            Detailed product information

        Raises:
            ProductNotFoundException: If product not found
            ProductOperationException: If retrieval fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Get product ID first
            row = await connection.fetchrow(
                """
                SELECT id
                FROM products
                WHERE code = $1 AND is_active = TRUE
                """,
                code,
            )

            if not row:
                raise ProductNotFoundException(
                    product_code=code,
                )

            # Reuse the get_product_by_id logic
            return await self._get_product_by_id(row["id"], connection)

        except ProductNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to get product by code",
                product_code=code,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise ProductOperationException(
                message=f"Failed to get product: {str(e)}",
                operation="get",
            ) from e

    async def get_product_by_code(
        self, code: str, connection: Optional[asyncpg.Connection] = None
    ) -> ProductDetailItem:
        """
        Get a product by code with detailed information.

        Args:
            code: Code of the product
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Detailed product information

        Raises:
            ProductNotFoundException: If product not found
            ProductOperationException: If retrieval fails
        """
        if connection:
            return await self._get_product_by_code(code, connection)

        async with self.db_pool.acquire() as conn:
            return await self._get_product_by_code(code, conn)

    async def _list_products(
        self,
        connection: asyncpg.Connection,
        is_active: Optional[bool] = None,
        brand_id: Optional[int] = None,
        category_id: Optional[int] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[ProductListItem]:
        """
        Private method to list products with a provided connection.
        Returns minimal data with images, name, category_name, price, and is_active.

        Args:
            connection: Database connection
            is_active: Filter by active status
            brand_id: Filter by brand ID
            category_id: Filter by category ID
            limit: Maximum number of products to return
            offset: Number of products to skip

        Returns:
            List of products with minimal data

        Raises:
            ProductOperationException: If listing fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Build query to get product list
            query = """
                SELECT 
                        p.id,
                        p.name,
                        bc.name AS category_name,
                        p.images,
                        p.is_active,
                        COALESCE(
                            (
                                SELECT pp.mrp
                                FROM product_prices pp
                                WHERE pp.product_id = p.id
                                AND pp.is_active = TRUE
                                AND pp.area_id IS NULL
                                LIMIT 1
                            ),
                            (
                                SELECT pp.mrp
                                FROM product_prices pp
                                WHERE pp.product_id = p.id
                                INNER JOIN areas a ON pp.area_id = a.id
                                AND pp.is_active = TRUE
                                ORDER BY get_area_priority(a.type) ASC
                                LIMIT 1
                            )
                        ) AS price
                    FROM products p
                    INNER JOIN brand_categories bc 
                        ON p.brand_category_id = bc.id
                    WHERE p.is_active = TRUE

            """
            params = []
            param_count = 0

            # Add WHERE clauses for filters
            if is_active is not None:
                param_count += 1
                query += f" AND p.is_active = ${param_count}"
                params.append(is_active)

            if brand_id is not None:
                param_count += 1
                query += f" AND p.brand_id = ${param_count}"
                params.append(brand_id)

            if category_id is not None:
                param_count += 1
                query += f" AND p.brand_category_id = ${param_count}"
                params.append(category_id)

            # Add ordering
            query += " ORDER BY p.name ASC"

            # Add limit and offset
            if limit is not None:
                param_count += 1
                query += f" LIMIT ${param_count}"
                params.append(limit)

            if offset is not None:
                param_count += 1
                query += f" OFFSET ${param_count}"
                params.append(offset)

            rows = await connection.fetch(query, *params)

            products = []
            for row in rows:
                products.append(
                    ProductListItem(
                        id=row["id"],
                        name=row["name"],
                        category_name=row["category_name"],
                        images=(
                            [DocumentInDB(**img) for img in json.loads(row["images"])]
                            if row["images"]
                            else None
                        ),
                        price=row["price"],
                        is_active=row["is_active"],
                    )
                )

            return products

        except Exception as e:
            logger.error(
                "Failed to list products",
                error=str(e),
                company_id=str(self.company_id),
            )
            raise ProductOperationException(
                message=f"Failed to list products: {str(e)}",
                operation="list",
            ) from e

    async def list_products(
        self,
        is_active: Optional[bool] = None,
        brand_id: Optional[int] = None,
        category_id: Optional[int] = None,
        limit: int = 20,
        offset: int = 0,
        connection: Optional[asyncpg.Connection] = None,
    ) -> list[ProductListItem]:
        """
        List products with minimal data.

        Args:
            is_active: Filter by active status
            brand_id: Filter by brand ID
            category_id: Filter by category ID
            limit: Maximum number of products to return
            offset: Number of products to skip
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            List of products with minimal data

        Raises:
            ProductOperationException: If listing fails
        """
        if connection:
            return await self._list_products(
                connection, is_active, brand_id, category_id, limit, offset
            )

        async with self.db_pool.acquire() as conn:
            return await self._list_products(
                conn, is_active, brand_id, category_id, limit, offset
            )

    async def _update_product(
        self, product_id: int, product_data: ProductUpdate, connection: asyncpg.Connection
    ) -> ProductInDB:
        """
        Private method to update a product with a provided connection.

        Args:
            product_id: ID of the product to update
            product_data: Product data to update
            connection: Database connection

        Returns:
            Updated product

        Raises:
            ProductNotFoundException: If product not found
            ProductOperationException: If update fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            # Build dynamic update query
            update_fields = []
            params = []
            param_count = 0

            for field, value in product_data.model_dump(exclude_unset=True).items():
                param_count += 1
                update_fields.append(f"{field} = ${param_count}")
                
                # Convert complex types to JSON
                if field == "dimensions" and value:
                    params.append(value.model_dump_json() if hasattr(value, "model_dump_json") else json.dumps(value))
                elif field == "measurement_details" and value:
                    params.append(value.model_dump_json() if hasattr(value, "model_dump_json") else json.dumps(value))
                elif field == "packaging_details" and value:
                    params.append(json.dumps([p if isinstance(p, dict) else p.model_dump() for p in value]))
                elif field == "images" and value:
                    params.append(json.dumps([img if isinstance(img, dict) else img.model_dump() for img in value]))
                else:
                    params.append(value)

            if not update_fields:
                # Nothing to update, just return the existing product
                return await self._get_product_by_id(product_id, connection)

            param_count += 1
            params.append(product_id)

            query = f"""
                UPDATE products
                SET {', '.join(update_fields)}
                WHERE id = ${param_count} AND is_active = TRUE
                RETURNING id, brand_id, brand_category_id, brand_subcategory_id,
                          name, code, description, barcode, hsn_code,
                          gst_rate, gst_category, dimensions, compliance,
                          measurement_details, packaging_type, packaging_details,
                          images, is_active, created_at, updated_at
            """

            row = await connection.fetchrow(query, *params)

            if not row:
                raise ProductNotFoundException(
                    product_id=product_id,
                )

            logger.info(
                "Product updated successfully",
                product_id=product_id,
                company_id=str(self.company_id),
            )

            return self._row_to_product_in_db(row)

        except asyncpg.UniqueViolationError as e:
            if "uniq_products_brand_category_code" in str(e):
                raise ProductAlreadyExistsException(
                    product_code=product_data.code,
                )
            else:
                raise ProductOperationException(
                    message=f"Failed to update product: {str(e)}",
                    operation="update",
                ) from e
        except asyncpg.ForeignKeyViolationError as e:
            error_msg = "Foreign key violation"
            if "brand_id" in str(e):
                error_msg = "Brand not found"
            elif "brand_category_id" in str(e):
                error_msg = "Brand category not found"
            
            raise ProductOperationException(
                message=error_msg,
                operation="update",
            ) from e
        except ProductNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to update product",
                product_id=product_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise ProductOperationException(
                message=f"Failed to update product: {str(e)}",
                operation="update",
            ) from e

    async def update_product(
        self,
        product_id: int,
        product_data: ProductUpdate,
        connection: Optional[asyncpg.Connection] = None,
    ) -> ProductInDB:
        """
        Update a product.

        Args:
            product_id: ID of the product to update
            product_data: Product data to update
            connection: Optional database connection. If not provided, a new one is acquired.

        Returns:
            Updated product

        Raises:
            ProductNotFoundException: If product not found
            ProductOperationException: If update fails
        """
        if connection:
            return await self._update_product(product_id, product_data, connection)

        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                return await self._update_product(product_id, product_data, conn)

    async def _delete_product(
        self, product_id: int, connection: asyncpg.Connection
    ) -> None:
        """
        Private method to soft delete a product with a provided connection.

        Args:
            product_id: ID of the product to delete
            connection: Database connection

        Raises:
            ProductNotFoundException: If product not found
            ProductOperationException: If deletion fails
        """
        try:
            await set_search_path(connection, self.schema_name)

            result = await connection.execute(
                """
                UPDATE products
                SET is_active = FALSE
                WHERE id = $1 AND is_active = TRUE
                """,
                product_id,
            )

            if result == "UPDATE 0":
                raise ProductNotFoundException(
                    product_id=product_id,
                )

            logger.info(
                "Product deleted successfully",
                product_id=product_id,
                company_id=str(self.company_id),
            )

        except ProductNotFoundException:
            raise
        except Exception as e:
            logger.error(
                "Failed to delete product",
                product_id=product_id,
                error=str(e),
                company_id=str(self.company_id),
            )
            raise ProductOperationException(
                message=f"Failed to delete product: {str(e)}",
                operation="delete",
            ) from e

    async def delete_product(
        self, product_id: int, connection: Optional[asyncpg.Connection] = None
    ) -> None:
        """
        Soft delete a product.

        Args:
            product_id: ID of the product to delete
            connection: Optional database connection. If not provided, a new one is acquired.

        Raises:
            ProductNotFoundException: If product not found
            ProductOperationException: If deletion fails
        """
        if connection:
            return await self._delete_product(product_id, connection)

        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                return await self._delete_product(product_id, conn)

    async def __get_products_for_shop_id(self, shop_id: UUID, limit: int,offset:int, connection: asyncpg.Connection) -> list[ProductListItem]:
        """
        Private method to get products available for a specific shop.

        Args:
            shop_id: ID of the shop
            limit: Maximum number of products to return
            offset: Number of products to skip
            connection: Database connection
        Returns:
            List of products available for the shop
        """
        await set_search_path(connection, self.schema_name)
        areas_releated_shop_id = await connection.fetchrow(
            """
            SELECT r.id  AS route_id, r.is_general as is_general,r.is_modern as is_modern,r.is_horeca as is_horeca, a.id AS division_id, a.area_id as area_id, a.zone_id as zone_id, a.region_id as region_id, a.nation_id as nation_id
            FROM retailer
            INNER JOIN routes r ON retailer.route_id = r.id
            INNER JOIN areas a ON r.area_id = a.id
            WHERE retailer.id = $1
            LIMIT 1;
            """,
            shop_id,
        )
        get_products_query ="""
        SELECT 
            p.id,
            p.name,
            bc.name AS category_name,
            p.images,
            p.is_active,
            COALESCE(
                (
                    SELECT pp.mrp
                    FROM product_prices pp
                    JOIN areas a ON a.id = pp.area_id
                    WHERE pp.product_id = p.id
                    AND pp.area_id = ANY ($1)
                    AND pp.is_active = TRUE
                    ORDER BY get_area_priority(a.type) DESC
                    LIMIT 1
                ),
                (
                    SELECT pp.mrp
                    FROM product_prices pp
                    WHERE pp.product_id = p.id
                    AND pp.area_id IS NULL
                    AND pp.is_active = TRUE
                    LIMIT 1
                )
            ) AS price
            FROM products p
            JOIN brand_categories bc ON bc.id = p.brand_category_id
            WHERE p.is_active = TRUE
            AND EXISTS (
                    SELECT 1
                    FROM product_visibility pv
                    WHERE pv.product_id = p.id
                    AND (pv.area_id = ANY ($1) OR pv.area_id IS NULL)
                    AND {shop_type} = $2
                    AND pv.is_active = TRUE
                )
            LIMIT $3 OFFSET $4;

        """
        shop_type = None
        if areas_releated_shop_id['is_general']:
            shop_type = 'for_general'
        elif areas_releated_shop_id['is_modern']:
            shop_type = 'for_modern'
        elif areas_releated_shop_id['is_horeca']:
            shop_type = 'for_horeca'
        else:
            shop_type = 'for_general'  # Defaulting to general if none matched
        print("Areas related to shop id",areas_releated_shop_id)
        rows =  await connection.fetch(
            get_products_query.format(shop_type=shop_type),
            [areas_releated_shop_id['division_id'],areas_releated_shop_id['area_id'],areas_releated_shop_id['zone_id'],areas_releated_shop_id['region_id'],areas_releated_shop_id['nation_id']],
            True,
            limit,
            offset,
        )
        products = []
        for row in rows:
            products.append(
                ProductListItem(
                    id=row["id"],
                    name=row["name"],
                    category_name=row["category_name"],
                    images=(
                        [DocumentInDB(**img) for img in json.loads(row["images"])]
                        if row["images"]
                        else None
                    ),
                    price=row["price"],
                    is_active=row["is_active"],
                )
            )

        return products
    async def get_products_for_shop_id(self, shop_id: UUID, limit: int = 20, offset: int =0, connection: Optional[asyncpg.Connection] = None) -> list[ProductListItem]:
        """
        Get products available for a specific shop.

        Args:
            shop_id: ID of the shop
            limit: Maximum number of products to return
            offset: Number of products to skip
            connection: Optional database connection. If not provided, a new one is acquired.
        Returns:
            List of products available for the shop
        """
        if connection:
            return await self.__get_products_for_shop_id(shop_id, limit, offset,connection)

        async with self.db_pool.acquire() as conn:
            return await self.__get_products_for_shop_id(shop_id, limit, offset,conn)