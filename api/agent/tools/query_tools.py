"""
LangChain tools for the Query Sub-Agent.

These tools let the agent inspect database schemas and run read-only SQL
queries against the tenant-specific PostgreSQL schema. They call directly
into the database pool (no HTTP round-trip) since they run in-process.
"""

from __future__ import annotations

import json
from typing import Any

import structlog
from langchain_core.tools import tool

from api.agent.schema import TABLE_SCHEMA_DICT, get_all_table_names
from api.agent.tools.api_tools import _company_id_var
from api.database import get_db_pool
from api.repository.utils import get_schema_name, set_search_path

logger = structlog.get_logger(__name__)

# Statements that are forbidden in read-only mode
_WRITE_KEYWORDS = {
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "TRUNCATE",
    "CREATE",
    "GRANT",
    "REVOKE",
    "COPY",
}


@tool
def get_table_schema(table_names: list[str]) -> str:
    """Return the column definitions, types, constraints and indexes for the
    requested database tables.

    Use this tool BEFORE writing any SQL so that you know the exact column
    names and types.  Pass a list of table names (e.g. ``["orders", "areas"]``).
    Call ``get_table_schema(["__list__"])`` to get a list of all available
    table names.

    Args:
        table_names: List of table names to inspect. Pass ``["__list__"]`` to
            get all table names instead.

    Returns:
        JSON string with the schema information for each requested table.
    """
    logger.debug(
        "[TOOL] get_table_schema called",
        table_names=table_names,
    )

    if table_names == ["__list__"]:
        all_names = get_all_table_names()
        logger.debug("[TOOL] Listing all tables", count=len(all_names))
        return json.dumps({"available_tables": all_names})

    result: dict[str, Any] = {}
    for name in table_names:
        schema = TABLE_SCHEMA_DICT.get(name)
        result[name] = schema if schema is not None else "Table not found"
        if schema is None:
            logger.warning("[TOOL] Table not found in schema dict", table=name)

    logger.debug("[TOOL] get_table_schema result", tables_found=list(result.keys()))
    return json.dumps(result, indent=2)


@tool
async def execute_read_query(sql_query: str) -> str:
    """Execute a **read-only** SQL SELECT query against the company database
    and return the results as a JSON string.

    Only SELECT statements are allowed. The search path is set automatically
    to the company's tenant schema, so you do NOT need to prefix table names.

    Args:
        sql_query: A SQL SELECT statement.

    Returns:
        JSON array of row objects, or an error message.
    """
    company_id = _company_id_var.get()
    logger.info(
        "[TOOL] execute_read_query called",
        sql_query=sql_query[:200],
        company_id=company_id,
    )

    # Validate read-only
    normalised = sql_query.strip().upper()
    first_word = normalised.split()[0] if normalised else ""
    if first_word in _WRITE_KEYWORDS:
        logger.warning(
            "[TOOL] Rejected write operation",
            keyword=first_word,
            sql=sql_query[:200],
        )
        return json.dumps(
            {"error": f"Write operations are not allowed. Found: {first_word}"}
        )

    # Extra safety: reject if any write keyword appears as a leading statement
    for kw in _WRITE_KEYWORDS:
        if normalised.startswith(kw):
            logger.warning(
                "[TOOL] Rejected write operation (starts-with check)",
                keyword=kw,
                sql=sql_query[:200],
            )
            return json.dumps(
                {"error": f"Write operations are not allowed. Statement starts with: {kw}"}
            )

    try:
        db_pool = get_db_pool()
        schema_name = get_schema_name(company_id)
        logger.debug(
            "[TOOL] Executing SQL",
            schema=schema_name,
            company_id=company_id,
        )

        async with db_pool.acquire() as connection:
            await set_search_path(connection, schema_name)
            rows = await connection.fetch(sql_query)

            # Convert asyncpg Record objects to plain dicts
            results = [dict(row) for row in rows]

            logger.info(
                "[TOOL] SQL query executed successfully",
                row_count=len(results),
                sql=sql_query[:200],
            )

            # Serialise with default=str to handle dates, UUIDs, Decimals, etc.
            return json.dumps(results, default=str)

    except Exception as exc:
        logger.error(
            "[TOOL] execute_read_query failed",
            sql=sql_query,
            company_id=company_id,
            error=str(exc),
        )
        return json.dumps({"error": str(exc)})


# Convenience list for importing
QUERY_TOOLS = [get_table_schema, execute_read_query]
