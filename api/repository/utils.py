from uuid import UUID


def get_schema_name(company_id: UUID) -> str:
    """Get the schema name for a given company ID.

    Args:
        company_id: UUID of the company
    Returns:
        str: Schema name derived from company ID
    """
    return f"_{str(company_id).replace('-', '')}_"


async def set_search_path(connection, schema_name: str) -> None:
    """Set the search path for the database connection based on company ID.

    Args:
        company_id: UUID of the company
        conn: Database connection object
    """
    await connection.execute(f'SET search_path TO "{schema_name}", public;')
