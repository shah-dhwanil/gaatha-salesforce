"""
Product management tools for the agent.

Provides tools for managing products with pricing and visibility configurations.
"""

from api.agent.tools.base import ToolDefinition, ToolParameter


# Tool: Create a new product
create_product_tool = ToolDefinition(
    name="create_product",
    description=(
        "Create a new product with pricing and visibility configurations. "
        "Products belong to a brand and category, and can have area-specific pricing "
        "and visibility settings for different shop types (general, modern, horeca) "
        "and retailer categories (type A, B, C)."
    ),
    parameters=[
        ToolParameter(
            name="brand_id",
            type="integer",
            description="Brand ID",
            required=True,
        ),
        ToolParameter(
            name="brand_category_id",
            type="integer",
            description="Brand category ID",
            required=True,
        ),
        ToolParameter(
            name="brand_subcategory_id",
            type="integer",
            description="Brand subcategory ID (optional)",
            required=False,
        ),
        ToolParameter(
            name="name",
            type="string",
            description="Product name",
            required=True,
        ),
        ToolParameter(
            name="code",
            type="string",
            description="Unique product code",
            required=True,
        ),
        ToolParameter(
            name="description",
            type="string",
            description="Product description (optional)",
            required=False,
        ),
        ToolParameter(
            name="barcode",
            type="string",
            description="Product barcode (optional)",
            required=False,
        ),
        ToolParameter(
            name="hsn_code",
            type="string",
            description="HSN code (optional)",
            required=False,
        ),
        ToolParameter(
            name="gst_rate",
            type="number",
            description="GST rate percentage",
            required=True,
        ),
        ToolParameter(
            name="gst_category",
            type="string",
            description="GST category",
            required=True,
        ),
        ToolParameter(
            name="packaging_type",
            type="string",
            description="Packaging type",
            required=True,
        ),
        ToolParameter(
            name="packaging_details",
            type="array",
            description="List of packaging details objects with name, qty, parent, base_qty, base_unit, is_default",
            required=True,
            items={"type": "object"},
        ),
        ToolParameter(
            name="prices",
            type="array",
            description="List of price configurations per area with area_id (can be null for global), mrp, margins, min_order_quantity",
            required=True,
            items={"type": "object"},
        ),
        ToolParameter(
            name="visibility",
            type="array",
            description="List of visibility configurations per area with area_id (can be null for global), for_general, for_modern, for_horeca, for_type_a, for_type_b, for_type_c",
            required=True,
            items={"type": "object"},
        ),
        ToolParameter(
            name="dimensions",
            type="object",
            description="Dimensions object with length, width, height, weight, unit (optional)",
            required=False,
        ),
        ToolParameter(
            name="compliance",
            type="string",
            description="Compliance information (optional)",
            required=False,
        ),
        ToolParameter(
            name="measurement_details",
            type="object",
            description="Measurement details object with type, shelf_life, net, net_unit, gross, gross_unit (optional)",
            required=False,
        ),
        ToolParameter(
            name="images",
            type="array",
            description="List of product images (optional)",
            required=False,
            items={"type": "object"},
        ),
    ],
    endpoint="/companies/{company_id}/products",
    method="POST",
    requires_company_id=True,
)


# Tool: Get product by ID
get_product_by_id_tool = ToolDefinition(
    name="get_product_by_id",
    description=(
        "Retrieve detailed information about a specific product by its ID. "
        "Returns complete product information including all fields, brand and category names, "
        "dimensions, measurement details, packaging details, images, "
        "all price configurations with area-specific settings, "
        "and all visibility configurations per area and shop type."
    ),
    parameters=[
        ToolParameter(
            name="product_id",
            type="integer",
            description="Product ID to retrieve",
            required=True,
        ),
    ],
    endpoint="/companies/{company_id}/products/{product_id}",
    method="GET",
    requires_company_id=True,
)


# Tool: Get product by code
get_product_by_code_tool = ToolDefinition(
    name="get_product_by_code",
    description=(
        "Retrieve a product by its unique code. "
        "Returns complete product information including pricing and visibility configurations. "
        "Useful when you know the product code but not its ID."
    ),
    parameters=[
        ToolParameter(
            name="code",
            type="string",
            description="Unique product code to search for",
            required=True,
        ),
    ],
    endpoint="/companies/{company_id}/products/by-code/{code}",
    method="GET",
    requires_company_id=True,
)


# Tool: List products
list_products_tool = ToolDefinition(
    name="list_products",
    description=(
        "List products with pagination and optional filtering. "
        "Returns basic product data including id, name, brand name, category name, "
        "packaging type, measurement details, images, base price (MRP from default area), "
        "and active status. "
        "Use get_product_by_id for complete product details including all prices and visibility. "
        "Supports filtering by active status, brand, and category."
    ),
    parameters=[
        ToolParameter(
            name="is_active",
            type="boolean",
            description="Filter by active status (true/false)",
            required=False,
        ),
        ToolParameter(
            name="brand_id",
            type="integer",
            description="Filter by brand ID",
            required=False,
        ),
        ToolParameter(
            name="category_id",
            type="integer",
            description="Filter by category ID",
            required=False,
        ),
        ToolParameter(
            name="limit",
            type="integer",
            description="Maximum number of products to return (1-100, default: 20)",
            required=False,
            default=20,
        ),
        ToolParameter(
            name="offset",
            type="integer",
            description="Number of products to skip for pagination (default: 0)",
            required=False,
            default=0,
        ),
    ],
    endpoint="/companies/{company_id}/products",
    method="GET",
    requires_company_id=True,
)


# Tool: Update product
update_product_tool = ToolDefinition(
    name="update_product",
    description=(
        "Update an existing product's details. "
        "Only provided fields will be updated (partial update supported). "
        "All fields are optional. "
        "Note: This updates only the main product information. "
        "Use separate endpoints for managing prices and visibility configurations if needed."
    ),
    parameters=[
        ToolParameter(
            name="product_id",
            type="integer",
            description="ID of the product to update",
            required=True,
        ),
        ToolParameter(
            name="brand_id",
            type="integer",
            description="New brand ID",
            required=False,
        ),
        ToolParameter(
            name="brand_category_id",
            type="integer",
            description="New brand category ID",
            required=False,
        ),
        ToolParameter(
            name="brand_subcategory_id",
            type="integer",
            description="New brand subcategory ID",
            required=False,
        ),
        ToolParameter(
            name="name",
            type="string",
            description="New product name",
            required=False,
        ),
        ToolParameter(
            name="code",
            type="string",
            description="New product code (must be unique)",
            required=False,
        ),
        ToolParameter(
            name="description",
            type="string",
            description="New product description",
            required=False,
        ),
        ToolParameter(
            name="barcode",
            type="string",
            description="New product barcode",
            required=False,
        ),
        ToolParameter(
            name="hsn_code",
            type="string",
            description="New HSN code",
            required=False,
        ),
        ToolParameter(
            name="gst_rate",
            type="number",
            description="New GST rate percentage",
            required=False,
        ),
        ToolParameter(
            name="gst_category",
            type="string",
            description="New GST category",
            required=False,
        ),
        ToolParameter(
            name="dimensions",
            type="object",
            description="New dimensions object",
            required=False,
        ),
        ToolParameter(
            name="compliance",
            type="string",
            description="New compliance information",
            required=False,
        ),
        ToolParameter(
            name="measurement_details",
            type="object",
            description="New measurement details object",
            required=False,
        ),
        ToolParameter(
            name="packaging_type",
            type="string",
            description="New packaging type",
            required=False,
        ),
        ToolParameter(
            name="packaging_details",
            type="array",
            description="New packaging details list",
            required=False,
            items={"type": "object"},
        ),
        ToolParameter(
            name="images",
            type="array",
            description="New product images list",
            required=False,
            items={"type": "object"},
        ),
        ToolParameter(
            name="is_active",
            type="boolean",
            description="New active status",
            required=False,
        ),
    ],
    endpoint="/companies/{company_id}/products/{product_id}",
    method="PATCH",
    requires_company_id=True,
)


# Tool: Get products for shop
get_products_for_shop_tool = ToolDefinition(
    name="get_products_for_shop",
    description=(
        "Retrieve products available for a specific shop based on route and area assignments. "
        "This considers the shop's assigned route, the route's area hierarchy "
        "(division, area, zone, region, nation), and area-specific pricing with priority: "
        "division > area > zone > region > nation > default. "
        "Returns id, name, category name, images, area-specific price, and active status."
    ),
    parameters=[
        ToolParameter(
            name="shop_id",
            type="string",
            description="Shop/Retailer UUID",
            required=True,
        ),
        ToolParameter(
            name="limit",
            type="integer",
            description="Maximum number of products to return (1-100, default: 20)",
            required=False,
            default=20,
        ),
        ToolParameter(
            name="offset",
            type="integer",
            description="Number of products to skip for pagination (default: 0)",
            required=False,
            default=0,
        ),
    ],
    endpoint="/companies/{company_id}/products/shop/{shop_id}",
    method="GET",
    requires_company_id=True,
)


# Export all product tools
PRODUCT_TOOLS = [
    create_product_tool,
    get_product_by_id_tool,
    get_product_by_code_tool,
    list_products_tool,
    update_product_tool,
    get_products_for_shop_tool,
]
