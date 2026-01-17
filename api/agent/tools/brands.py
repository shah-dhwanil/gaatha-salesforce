"""
Brand management tools for the agent.

Provides tools for managing brands with visibility and margin configurations.
"""

from api.agent.tools.base import ToolDefinition, ToolParameter


# Tool: Create a new brand
create_brand_tool = ToolDefinition(
    name="create_brand",
    description=(
        "Create a new brand with visibility and margin configurations. "
        "Brands can be visible for different trade types (general, modern, horeca) "
        "and can have area-specific or global visibility. "
        "Margins can be configured per area with different values for super_stockist, distributor, and retailer levels."
    ),
    parameters=[
        ToolParameter(
            name="name",
            type="string",
            description="Brand name (unique when active)",
            required=True,
        ),
        ToolParameter(
            name="code",
            type="string",
            description="Unique brand code",
            required=True,
        ),
        ToolParameter(
            name="for_general",
            type="boolean",
            description="Visibility for general trade",
            required=True,
        ),
        ToolParameter(
            name="for_modern",
            type="boolean",
            description="Visibility for modern trade",
            required=True,
        ),
        ToolParameter(
            name="for_horeca",
            type="boolean",
            description="Visibility for HORECA segment",
            required=True,
        ),
        ToolParameter(
            name="logo",
            type="object",
            description="Logo document information with url, name, size, mime_type (optional)",
            required=False,
        ),
        ToolParameter(
            name="area_id",
            type="array",
            description="List of area IDs for visibility (empty/null = global visibility)",
            required=False,
            items={"type": "integer"},
        ),
        ToolParameter(
            name="margins",
            type="array",
            description="List of margin configurations, each with name, area_id (optional), and margins object containing super_stockist, distributor, retailer margins (optional)",
            required=False,
            items={"type": "object"},
        ),
    ],
    endpoint="/companies/{company_id}/brands",
    method="POST",
    requires_company_id=True,
)


# Tool: Get brand by ID
get_brand_by_id_tool = ToolDefinition(
    name="get_brand_by_id",
    description=(
        "Retrieve detailed information about a specific brand by its ID. "
        "Returns complete brand information including all fields, "
        "associated areas with visibility configurations, "
        "all margin configurations with area-specific settings, "
        "and logo document information."
    ),
    parameters=[
        ToolParameter(
            name="brand_id",
            type="integer",
            description="Brand ID to retrieve",
            required=True,
        ),
    ],
    endpoint="/companies/{company_id}/brands/{brand_id}",
    method="GET",
    requires_company_id=True,
)


# Tool: Get brand by code
get_brand_by_code_tool = ToolDefinition(
    name="get_brand_by_code",
    description=(
        "Retrieve a brand by its unique code. "
        "Returns complete brand information including visibility and margin configurations. "
        "Useful when you know the brand code but not its ID."
    ),
    parameters=[
        ToolParameter(
            name="code",
            type="string",
            description="Unique brand code to search for",
            required=True,
        ),
    ],
    endpoint="/companies/{company_id}/brands/by-code/{code}",
    method="GET",
    requires_company_id=True,
)


# Tool: List brands
list_brands_tool = ToolDefinition(
    name="list_brands",
    description=(
        "List brands with pagination and optional filtering by active status. "
        "Returns brand name, code, count of active categories, count of active products, "
        "creation timestamp, and active status. "
        "Use get_brand_by_id for complete brand details including visibility and margins."
    ),
    parameters=[
        ToolParameter(
            name="is_active",
            type="boolean",
            description="Filter by active status (true/false)",
            required=False,
        ),
        ToolParameter(
            name="limit",
            type="integer",
            description="Maximum number of brands to return (1-100, default: 20)",
            required=False,
            default=20,
        ),
        ToolParameter(
            name="offset",
            type="integer",
            description="Number of brands to skip for pagination (default: 0)",
            required=False,
            default=0,
        ),
    ],
    endpoint="/companies/{company_id}/brands",
    method="GET",
    requires_company_id=True,
)


# Tool: Update brand
update_brand_tool = ToolDefinition(
    name="update_brand",
    description=(
        "Update an existing brand's details. "
        "Only provided fields will be updated (partial update supported). "
        "All fields are optional. "
        "Note: Use separate endpoints/tools for managing visibility and margins."
    ),
    parameters=[
        ToolParameter(
            name="brand_id",
            type="integer",
            description="ID of the brand to update",
            required=True,
        ),
        ToolParameter(
            name="name",
            type="string",
            description="New brand name",
            required=False,
        ),
        ToolParameter(
            name="code",
            type="string",
            description="New brand code (must be unique)",
            required=False,
        ),
        ToolParameter(
            name="for_general",
            type="boolean",
            description="New visibility for general trade",
            required=False,
        ),
        ToolParameter(
            name="for_modern",
            type="boolean",
            description="New visibility for modern trade",
            required=False,
        ),
        ToolParameter(
            name="for_horeca",
            type="boolean",
            description="New visibility for HORECA segment",
            required=False,
        ),
        ToolParameter(
            name="logo",
            type="object",
            description="New logo document information",
            required=False,
        ),
        ToolParameter(
            name="is_active",
            type="boolean",
            description="New active status",
            required=False,
        ),
    ],
    endpoint="/companies/{company_id}/brands/{brand_id}",
    method="PATCH",
    requires_company_id=True,
)


# Tool: Add brand visibility
add_brand_visibility_tool = ToolDefinition(
    name="add_brand_visibility",
    description=(
        "Add visibility for a brand in a specific area or globally. "
        "area_id null or omitted = global visibility. "
        "area_id with specific ID = visibility for that area only. "
        "Multiple visibility records can exist for different areas."
    ),
    parameters=[
        ToolParameter(
            name="brand_id",
            type="integer",
            description="Brand ID",
            required=True,
        ),
        ToolParameter(
            name="area_id",
            type="integer",
            description="Area ID (null/omitted for global visibility)",
            required=False,
        ),
    ],
    endpoint="/companies/{company_id}/brands/{brand_id}/visibility",
    method="POST",
    requires_company_id=True,
)


# Tool: Add or update brand margin
add_brand_margin_tool = ToolDefinition(
    name="add_brand_margin",
    description=(
        "Add or update margin configuration for a brand in a specific area or globally. "
        "area_id null or omitted = global margin configuration. "
        "area_id with specific ID = margin for that area only. "
        "If a margin already exists for the brand+area combination, it will be updated. "
        "Margins can include super_stockist, distributor, and retailer levels, "
        "each with type (MARKUP/MARKDOWN/FIXED) and value."
    ),
    parameters=[
        ToolParameter(
            name="brand_id",
            type="integer",
            description="Brand ID",
            required=True,
        ),
        ToolParameter(
            name="name",
            type="string",
            description="Name for this margin configuration",
            required=False,
        ),
        ToolParameter(
            name="area_id",
            type="integer",
            description="Area ID (null/omitted for global margin)",
            required=False,
        ),
        ToolParameter(
            name="margins",
            type="object",
            description="Margins object with super_stockist, distributor, retailer properties, each containing type (MARKUP/MARKDOWN/FIXED) and value",
            required=False,
        ),
    ],
    endpoint="/companies/{company_id}/brands/{brand_id}/margins",
    method="POST",
    requires_company_id=True,
)


# Export all brand tools
BRAND_TOOLS = [
    create_brand_tool,
    get_brand_by_id_tool,
    get_brand_by_code_tool,
    list_brands_tool,
    update_brand_tool,
    add_brand_visibility_tool,
    add_brand_margin_tool,
]
