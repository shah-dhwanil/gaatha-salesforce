"""
User management tools for the agent.

Provides tools for managing users across companies with role and area assignments.
"""

from api.agent.tools.base import ToolDefinition, ToolParameter


# Tool: Create a new user
create_user_tool = ToolDefinition(
    name="create_user",
    description=(
        "Create a new user with specified username, name, contact, company, role, and area. "
        "For non-super admin users: company_id, role, area_id, bank_details, and salary are required. "
        "For super admin users: these fields are optional. "
        "Username must be unique across the system."
    ),
    parameters=[
        ToolParameter(
            name="username",
            type="string",
            description="Unique username (1-100 characters, optional for non-admin users)",
            required=False,
        ),
        ToolParameter(
            name="name",
            type="string",
            description="Full name of the user (1-255 characters)",
            required=True,
        ),
        ToolParameter(
            name="contact_no",
            type="string",
            description="Contact phone number (1-20 characters)",
            required=True,
        ),
        ToolParameter(
            name="company_id",
            type="string",
            description="UUID of the company (required for non-super admin users)",
            required=False,
        ),
        ToolParameter(
            name="role",
            type="string",
            description="Role name (required for non-super admin users)",
            required=False,
        ),
        ToolParameter(
            name="area_id",
            type="integer",
            description="Area ID (required for non-super admin users)",
            required=False,
        ),
        ToolParameter(
            name="bank_details",
            type="object",
            description="Bank account details object with account_number, account_name, bank_name, bank_branch, account_type (SAVINGS/CURRENT), ifsc_code (required for non-super admin users)",
            required=False,
        ),
        ToolParameter(
            name="salary",
            type="integer",
            description="Salary of the user (required for non-super admin users except retailer, distributor, super_stockist roles)",
            required=False,
        ),
        ToolParameter(
            name="is_super_admin",
            type="boolean",
            description="Whether the user is a super admin (default: false)",
            required=False,
            default=False,
        ),
    ],
    endpoint="/users",
    method="POST",
    requires_company_id=False,
)


# Tool: Get user by ID
get_user_by_id_tool = ToolDefinition(
    name="get_user_by_id",
    description=(
        "Retrieve detailed information about a specific user by their UUID. "
        "Returns complete user information including company name, area details, "
        "role, bank details, salary, timestamps, and active status."
    ),
    parameters=[
        ToolParameter(
            name="user_id",
            type="string",
            description="User UUID to retrieve",
            required=True,
        ),
    ],
    endpoint="/users/{user_id}",
    method="GET",
    requires_company_id=False,
)


# Tool: Get user by username
get_user_by_username_tool = ToolDefinition(
    name="get_user_by_username",
    description=(
        "Retrieve user information by username. "
        "Returns complete user information for the user with the specified username. "
        "Useful when you know the username but not the user ID."
    ),
    parameters=[
        ToolParameter(
            name="username",
            type="string",
            description="Username of the user to retrieve",
            required=True,
        ),
    ],
    endpoint="/users/username/{username}",
    method="GET",
    requires_company_id=False,
)


# Tool: List users by company
list_users_by_company_tool = ToolDefinition(
    name="list_users_by_company",
    description=(
        "List all users for a specific company with pagination and optional filtering by active status. "
        "Returns minimal user data (id, username, name, contact, company_id, role, area_id, area_name, is_active). "
        "Use get_user_by_id for complete user details including bank details and full area information."
    ),
    parameters=[
        ToolParameter(
            name="company_id",
            type="string",
            description="Company UUID to filter users",
            required=True,
        ),
        ToolParameter(
            name="is_active",
            type="boolean",
            description="Filter by active status (true/false)",
            required=False,
        ),
        ToolParameter(
            name="limit",
            type="integer",
            description="Number of users to return (1-100, default: 20)",
            required=False,
            default=20,
        ),
        ToolParameter(
            name="offset",
            type="integer",
            description="Number of users to skip for pagination (default: 0)",
            required=False,
            default=0,
        ),
    ],
    endpoint="/users/companies/{company_id}/users",
    method="GET",
    requires_company_id=False,
)


# Tool: List users by role
list_users_by_role_tool = ToolDefinition(
    name="list_users_by_role",
    description=(
        "List all users with a specific role within a company with pagination and optional filtering. "
        "Returns minimal user data (id, username, name, contact, company_id, role, area_id, area_name, is_active). "
        "Use get_user_by_id for complete user details."
    ),
    parameters=[
        ToolParameter(
            name="company_id",
            type="string",
            description="Company UUID to filter users",
            required=True,
        ),
        ToolParameter(
            name="role_name",
            type="string",
            description="Role name to filter users",
            required=True,
        ),
        ToolParameter(
            name="is_active",
            type="boolean",
            description="Filter by active status (true/false)",
            required=False,
        ),
        ToolParameter(
            name="limit",
            type="integer",
            description="Number of users to return (1-100, default: 20)",
            required=False,
            default=20,
        ),
        ToolParameter(
            name="offset",
            type="integer",
            description="Number of users to skip for pagination (default: 0)",
            required=False,
            default=0,
        ),
    ],
    endpoint="/users/companies/{company_id}/roles/{role_name}/users",
    method="GET",
    requires_company_id=False,
)


# Tool: Update user
update_user_tool = ToolDefinition(
    name="update_user",
    description=(
        "Update an existing user's details. "
        "Only specified fields will be updated (partial update supported). "
        "Username and super admin status cannot be updated. "
        "All fields are optional - at least one field must be provided for update."
    ),
    parameters=[
        ToolParameter(
            name="company_id",
            type="string",
            description="Company UUID (required for authorization)",
            required=True,
        ),
        ToolParameter(
            name="user_id",
            type="string",
            description="User UUID to update",
            required=True,
        ),
        ToolParameter(
            name="name",
            type="string",
            description="New full name (1-255 characters)",
            required=False,
        ),
        ToolParameter(
            name="contact_no",
            type="string",
            description="New contact phone number (1-20 characters)",
            required=False,
        ),
        ToolParameter(
            name="role",
            type="string",
            description="New role name (1-100 characters)",
            required=False,
        ),
        ToolParameter(
            name="area_id",
            type="integer",
            description="New area assignment",
            required=False,
        ),
        ToolParameter(
            name="bank_details",
            type="object",
            description="New bank details object with account_number, account_name, bank_name, bank_branch, account_type, ifsc_code",
            required=False,
        ),
        ToolParameter(
            name="salary",
            type="integer",
            description="New salary amount",
            required=False,
        ),
    ],
    endpoint="/users/companies/{company_id}/users/{user_id}",
    method="PATCH",
    requires_company_id=False,
)


# Tool: Activate user
activate_user_tool = ToolDefinition(
    name="activate_user",
    description=(
        "Activate a user by setting is_active to true. "
        "This reactivates a previously deactivated user, allowing them to access the system again."
    ),
    parameters=[
        ToolParameter(
            name="user_id",
            type="string",
            description="User UUID to activate",
            required=True,
        ),
    ],
    endpoint="/users/{user_id}/activate",
    method="POST",
    requires_company_id=False,
)


# Tool: Check user exists
check_user_exists_tool = ToolDefinition(
    name="check_user_exists",
    description=(
        "Check if a user with the given UUID exists in the system. "
        "Returns a boolean indicating whether the user exists. "
        "Useful for validation before performing operations on a user."
    ),
    parameters=[
        ToolParameter(
            name="user_id",
            type="string",
            description="User UUID to check",
            required=True,
        ),
    ],
    endpoint="/users/{user_id}/exists",
    method="GET",
    requires_company_id=False,
)


# Tool: Check username exists
check_username_exists_tool = ToolDefinition(
    name="check_username_exists",
    description=(
        "Check if a username is already taken in the system. "
        "Returns a boolean indicating whether the username exists. "
        "Useful for validation before creating a new user or checking username availability."
    ),
    parameters=[
        ToolParameter(
            name="username",
            type="string",
            description="Username to check for existence",
            required=True,
        ),
    ],
    endpoint="/users/username/{username}/exists",
    method="GET",
    requires_company_id=False,
)


# Export all user tools
USER_TOOLS = [
    create_user_tool,
    get_user_by_id_tool,
    get_user_by_username_tool,
    list_users_by_company_tool,
    list_users_by_role_tool,
    update_user_tool,
    activate_user_tool,
    check_user_exists_tool,
    check_username_exists_tool,
]
