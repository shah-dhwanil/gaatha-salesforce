"""
Route management tools for the agent.

Provides tools for managing routes associated with areas (divisions) in the hierarchy.
"""

from api.agent.tools.base import ToolDefinition, ToolParameter


# Tool: Create a new route
create_route_tool = ToolDefinition(
    name="create_route",
    description=(
        "Create a new route associated with an area (division). "
        "Routes can have multiple type flags: is_general (general trade), "
        "is_modern (modern trade), or is_horeca (hotel/restaurant/café). "
        "Exactly one trade type must be selected. "
        "Each route must have a unique code."
    ),
    parameters=[
        ToolParameter(
            name="name",
            type="string",
            description="Route name (1-32 characters)",
            required=True,
        ),
        ToolParameter(
            name="code",
            type="string",
            description="Unique route code (1-32 characters)",
            required=True,
        ),
        ToolParameter(
            name="area_id",
            type="integer",
            description="ID of the area (division) this route belongs to",
            required=True,
        ),
        ToolParameter(
            name="is_general",
            type="boolean",
            description="Whether this is a general trade route",
            required=False,
            default=False,
        ),
        ToolParameter(
            name="is_modern",
            type="boolean",
            description="Whether this is a modern trade route",
            required=False,
            default=False,
        ),
        ToolParameter(
            name="is_horeca",
            type="boolean",
            description="Whether this is a horeca route",
            required=False,
            default=False,
        ),
        ToolParameter(
            name="is_active",
            type="boolean",
            description="Whether the route is active",
            required=False,
            default=True,
        ),
    ],
    endpoint="/companies/{company_id}/routes",
    method="POST",
    requires_company_id=True,
)


# Tool: Get route by ID
get_route_by_id_tool = ToolDefinition(
    name="get_route_by_id",
    description=(
        "Retrieve detailed information about a specific route by its ID. "
        "Returns complete route information including all route fields, "
        "full hierarchical context (division, area, region, zone, nation names), "
        "timestamps, and active status."
    ),
    parameters=[
        ToolParameter(
            name="route_id",
            type="integer",
            description="Route ID to retrieve",
            required=True,
        ),
    ],
    endpoint="/companies/{company_id}/routes/{route_id}",
    method="GET",
    requires_company_id=True,
)


# Tool: Get route by code
get_route_by_code_tool = ToolDefinition(
    name="get_route_by_code",
    description=(
        "Retrieve a route by its unique code. "
        "Returns complete route information including full hierarchical context. "
        "Only returns active routes. "
        "Useful when you know the route code but not its ID."
    ),
    parameters=[
        ToolParameter(
            name="code",
            type="string",
            description="Unique route code to search for",
            required=True,
        ),
    ],
    endpoint="/companies/{company_id}/routes/by-code/{code}",
    method="GET",
    requires_company_id=True,
)


# Tool: List routes
list_routes_tool = ToolDefinition(
    name="list_routes",
    description=(
        "List routes with pagination and optional filtering. "
        "Returns optimized route data with minimal hierarchical information "
        "(division, area, region) and retailer count for each route. "
        "Use get_route_by_id for complete route details. "
        "Examples: List all active general routes (?is_active=true&is_general=true), "
        "list routes in area 5 (?area_id=5), "
        "list modern and horeca routes (?is_modern=true&is_horeca=true)."
    ),
    parameters=[
        ToolParameter(
            name="area_id",
            type="integer",
            description="Filter by area (division) ID",
            required=False,
        ),
        ToolParameter(
            name="is_active",
            type="boolean",
            description="Filter by active status (true/false)",
            required=False,
        ),
        ToolParameter(
            name="is_general",
            type="boolean",
            description="Filter by general trade route status",
            required=False,
        ),
        ToolParameter(
            name="is_modern",
            type="boolean",
            description="Filter by modern trade route status",
            required=False,
        ),
        ToolParameter(
            name="is_horeca",
            type="boolean",
            description="Filter by horeca route status",
            required=False,
        ),
        ToolParameter(
            name="limit",
            type="integer",
            description="Number of routes to return (1-100, default: 20)",
            required=False,
            default=20,
        ),
        ToolParameter(
            name="offset",
            type="integer",
            description="Number of routes to skip for pagination (default: 0)",
            required=False,
            default=0,
        ),
    ],
    endpoint="/companies/{company_id}/routes",
    method="GET",
    requires_company_id=True,
)


# Tool: Update route
update_route_tool = ToolDefinition(
    name="update_route",
    description=(
        "Update an existing route's details. "
        "You can update name, area_id, and/or trade type flags (is_general, is_modern, is_horeca). "
        "Route code cannot be updated after creation. "
        "Exactly one trade type must remain selected if any trade type is being updated. "
        "At least one field must be provided for update."
    ),
    parameters=[
        ToolParameter(
            name="route_id",
            type="integer",
            description="ID of the route to update",
            required=True,
        ),
        ToolParameter(
            name="name",
            type="string",
            description="New route name (1-32 characters)",
            required=False,
        ),
        ToolParameter(
            name="area_id",
            type="integer",
            description="New area (division) ID",
            required=False,
        ),
        ToolParameter(
            name="is_general",
            type="boolean",
            description="Update general trade route flag",
            required=False,
        ),
        ToolParameter(
            name="is_modern",
            type="boolean",
            description="Update modern trade route flag",
            required=False,
        ),
        ToolParameter(
            name="is_horeca",
            type="boolean",
            description="Update horeca route flag",
            required=False,
        ),
    ],
    endpoint="/companies/{company_id}/routes/{route_id}",
    method="PATCH",
    requires_company_id=True,
)


# Export all route tools
ROUTE_TOOLS = [
    create_route_tool,
    get_route_by_id_tool,
    get_route_by_code_tool,
    list_routes_tool,
    update_route_tool,
]
