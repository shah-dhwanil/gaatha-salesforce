"""
Area management tools for the agent.

Provides tools for managing hierarchical areas (NATION > ZONE > REGION > AREA > DIVISION).
"""

from api.agent.tools.base import ToolDefinition, ToolParameter


# Tool: Create a new area
create_area_tool = ToolDefinition(
    name="create_area",
    description=(
        "Create a new area in the hierarchy. Areas follow a strict hierarchy: "
        "NATION > ZONE > REGION > AREA > DIVISION. "
        "The system automatically validates parent areas and populates ancestor IDs. "
        "Rules: NATION (no parent), ZONE (requires nation_id), REGION (requires zone_id), "
        "AREA (requires region_id), DIVISION (requires area_id)."
    ),
    parameters=[
        ToolParameter(
            name="name",
            type="string",
            description="Area name (1-64 characters)",
            required=True,
        ),
        ToolParameter(
            name="type",
            type="string",
            description="Area type in hierarchy",
            required=True,
            enum=["NATION", "ZONE", "REGION", "AREA", "DIVISION"],
        ),
        ToolParameter(
            name="nation_id",
            type="integer",
            description="Parent nation ID (required for ZONE level)",
            required=False,
        ),
        ToolParameter(
            name="zone_id",
            type="integer",
            description="Parent zone ID (required for REGION level)",
            required=False,
        ),
        ToolParameter(
            name="region_id",
            type="integer",
            description="Parent region ID (required for AREA level)",
            required=False,
        ),
        ToolParameter(
            name="area_id",
            type="integer",
            description="Parent area ID (required for DIVISION level)",
            required=False,
        ),
    ],
    endpoint="/companies/{company_id}/areas",
    method="POST",
    requires_company_id=True,
)


# Tool: Get area by ID
get_area_by_id_tool = ToolDefinition(
    name="get_area_by_id",
    description=(
        "Retrieve detailed information about a specific area by its ID. "
        "Returns complete area information including all fields, parent IDs, "
        "timestamps, and active status."
    ),
    parameters=[
        ToolParameter(
            name="area_id",
            type="integer",
            description="Area ID to retrieve",
            required=True,
        ),
    ],
    endpoint="/companies/{company_id}/areas/{area_id}",
    method="GET",
    requires_company_id=True,
)


# Tool: Get area by name and type
get_area_by_name_and_type_tool = ToolDefinition(
    name="get_area_by_name_and_type",
    description=(
        "Retrieve an area by its name and type combination. "
        "Since area names must be unique within a type, this combination "
        "uniquely identifies an area. Useful when you know the area name "
        "but not its ID."
    ),
    parameters=[
        ToolParameter(
            name="name",
            type="string",
            description="Area name to search for",
            required=True,
        ),
        ToolParameter(
            name="area_type",
            type="string",
            description="Area type: NATION, ZONE, REGION, AREA, or DIVISION",
            required=True,
            enum=["NATION", "ZONE", "REGION", "AREA", "DIVISION"],
        ),
    ],
    endpoint="/companies/{company_id}/areas/by-name/{area_type}/{name}",
    method="GET",
    requires_company_id=True,
)


# Tool: List areas
list_areas_tool = ToolDefinition(
    name="list_areas",
    description=(
        "List areas with pagination and optional filtering. "
        "Returns minimal area data (id, name, type, is_active) for performance. "
        "Supports filtering by type, parent, and active status. "
        "Use get_area_by_id for complete area details. "
        "Examples: List all nations (?area_type=NATION), "
        "list zones under nation 1 (?parent_id=1&parent_type=nation), "
        "list active divisions (?area_type=DIVISION&is_active=true)."
    ),
    parameters=[
        ToolParameter(
            name="area_type",
            type="string",
            description="Filter by area type: NATION, ZONE, REGION, AREA, or DIVISION",
            required=False,
            enum=["NATION", "ZONE", "REGION", "AREA", "DIVISION"],
        ),
        ToolParameter(
            name="is_active",
            type="boolean",
            description="Filter by active status (true/false)",
            required=False,
        ),
        ToolParameter(
            name="parent_id",
            type="integer",
            description="Filter by parent area ID",
            required=False,
        ),
        ToolParameter(
            name="parent_type",
            type="string",
            description="Parent type: nation, zone, region, or area (required if parent_id is provided)",
            required=False,
            enum=["nation", "zone", "region", "area"],
        ),
        ToolParameter(
            name="limit",
            type="integer",
            description="Number of areas to return (1-100, default: 20)",
            required=False,
            default=20,
        ),
        ToolParameter(
            name="offset",
            type="integer",
            description="Number of areas to skip for pagination (default: 0)",
            required=False,
            default=0,
        ),
    ],
    endpoint="/companies/{company_id}/areas",
    method="GET",
    requires_company_id=True,
)


# Tool: Update area
update_area_tool = ToolDefinition(
    name="update_area",
    description=(
        "Update an existing area's details. "
        "The system automatically validates hierarchy when updating type or parent references. "
        "You can update name, type, and/or parent IDs. "
        "Auto-populates ancestors based on hierarchy. "
        "At least one field must be provided for update."
    ),
    parameters=[
        ToolParameter(
            name="area_id",
            type="integer",
            description="ID of the area to update",
            required=True,
        ),
        ToolParameter(
            name="name",
            type="string",
            description="New area name (1-64 characters)",
            required=False,
        ),
        ToolParameter(
            name="type",
            type="string",
            description="New area type (triggers hierarchy re-validation)",
            required=False,
            enum=["NATION", "ZONE", "REGION", "AREA", "DIVISION"],
        ),
        ToolParameter(
            name="nation_id",
            type="integer",
            description="New parent nation ID",
            required=False,
        ),
        ToolParameter(
            name="zone_id",
            type="integer",
            description="New parent zone ID",
            required=False,
        ),
        ToolParameter(
            name="region_id",
            type="integer",
            description="New parent region ID",
            required=False,
        ),
        ToolParameter(
            name="area_id",
            type="integer",
            description="New parent area ID",
            required=False,
        ),
    ],
    endpoint="/companies/{company_id}/areas/{area_id}",
    method="PATCH",
    requires_company_id=True,
)


# Export all area tools
AREA_TOOLS = [
    create_area_tool,
    get_area_by_id_tool,
    get_area_by_name_and_type_tool,
    list_areas_tool,
    update_area_tool,
]
