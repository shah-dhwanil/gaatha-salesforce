"""
Tool definitions for the Sales Management Agent.

Each tool maps to one or more FastAPI endpoints and provides
the agent with capabilities to query and modify data.
"""

from api.agent.tools.areas import AREA_TOOLS
from api.agent.tools.brands import BRAND_TOOLS
from api.agent.tools.products import PRODUCT_TOOLS
from api.agent.tools.routes import ROUTE_TOOLS
from api.agent.tools.users import USER_TOOLS
from api.agent.tools.brand_categories import BRAND_CATEGORY_TOOLS
from api.agent.tools.query import QUERY_TOOLS

# All available tools
ALL_TOOLS = [
    *AREA_TOOLS,
    *BRAND_TOOLS,
    *PRODUCT_TOOLS,
    *ROUTE_TOOLS,
    *USER_TOOLS,
    *BRAND_CATEGORY_TOOLS,
    *QUERY_TOOLS,
]

__all__ = [
    "ALL_TOOLS",
]
