"""
Query tools for database operations.

Provides tools for fetching table schemas and executing SQL queries.
"""

from api.agent.tools.base import ToolDefinition, ToolParameter


# Tool for fetching table schema
get_table_schema_tool = ToolDefinition(
    name="get_table_schema",
    description=(
        "Retrieve the schema information for specified database tables. "
        "Returns detailed information about columns, data types, constraints, "
        "indexes, and relationships for each requested table. "
        "Use this tool to understand table structure before querying data or "
        "to help construct accurate SQL queries. "
    ),
    parameters=[
        ToolParameter(
            name="table_name",
            type="array",
            description=(
                "List of table names to retrieve schema for. "
                "Use the full table name (e.g., 'users', 'products', 'orders'). "
                "Multiple tables can be requested in a single call."
            ),
            required=True,
            items={"type": "string"}
        )
    ],
    endpoint="/agents/table_schema",
    method="GET",
    requires_company_id=False
)


# Tool for executing SQL queries
execute_query_tool = ToolDefinition(
    name="execute_query",
    description=(
        "Execute a SQL query against the company's database and return the results. "
        "This tool allows you to retrieve data by running SELECT queries. "
        "IMPORTANT: Only SELECT queries are allowed for safety. "
        "Always use proper WHERE clauses to filter data appropriately. "
        "Use table schemas (get_table_schema) first to understand the structure "
        "before constructing queries. "
        "The query will automatically be scoped to the company's schema, "
        "so you don't need to prefix tables with schema names. "
        "Example: 'SELECT name, email FROM retailer WHERE is_active = true LIMIT 10'"
    ),
    parameters=[
        ToolParameter(
            name="sql_query",
            type="string",
            description=(
                "The SQL SELECT query to execute. "
                "Must be a valid PostgreSQL SELECT statement. "
                "Use proper WHERE clauses to filter results. "
                "Consider using LIMIT to restrict the number of rows returned. "
                "Do not include schema prefixes - the company schema is automatically set. "
                "Example: 'SELECT id, name, code FROM products WHERE is_active = true LIMIT 20'"
            ),
            required=True
        )
    ],
    endpoint="/agents/{company_id}/execute_query",
    method="POST",
    requires_company_id=True
)


# Export all tools
QUERY_TOOLS = [
    get_table_schema_tool,
    execute_query_tool
]


def get_query_tools() -> list[ToolDefinition]:
    """
    Get all query-related tools.
    
    Returns:
        List of ToolDefinition objects for database query operations.
    """
    return QUERY_TOOLS
