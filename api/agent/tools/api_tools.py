"""
Explicit LangChain tools that call the REST API directly via HTTP.

``company_id`` is **not** exposed to the LLM.  It is injected at runtime
via a ``contextvars.ContextVar`` that must be set before the agent runs
(see ``set_company_id``).  This prevents the model from ever asking the
user for a company UUID.

Each ``@tool`` function maps to one (or a small group of) REST endpoints.
Tools are organised by domain: areas, products, brands, routes, distributors,
retailers, orders, users, and companies.

All endpoints are prefixed with ``/api/v1``.
"""

from __future__ import annotations

import contextvars
from typing import Optional

from langchain_core.tools import tool

from api.agent.tools._http import api_delete, api_get, api_patch, api_post

P = "/api/v1"

# ---------------------------------------------------------------------------
# Runtime context – company_id injection
# ---------------------------------------------------------------------------

_company_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("company_id")


def set_company_id(company_id: str) -> contextvars.Token:
    """Set the company_id for the current async context.

    Must be called **before** the agent is invoked so every tool call
    automatically picks up the correct tenant.
    """
    return _company_id_var.set(str(company_id))


def _cid() -> str:
    """Return the current company_id from context."""
    return _company_id_var.get()


# =====================================================================
# AREAS
# =====================================================================


@tool
async def list_areas(
    area_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    parent_id: Optional[int] = None,
    parent_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> str:
    """List areas with optional filters.

    Args:
        area_type: Filter by type: NATION, ZONE, REGION, AREA, DIVISION.
        is_active: Filter by active status.
        parent_id: Filter by parent area ID.
        parent_type: Parent type (nation/zone/region/area) – required when parent_id is set.
        limit: Max rows (default 50).
        offset: Pagination offset.
    """
    return await api_get(
        f"{P}/companies/{_cid()}/areas",
        {"area_type": area_type, "is_active": is_active, "parent_id": parent_id,
         "parent_type": parent_type, "limit": limit, "offset": offset},
    )


@tool
async def get_area_by_id(area_id: int) -> str:
    """Get a single area by its numeric ID.

    Args:
        area_id: Area ID (integer).
    """
    return await api_get(f"{P}/companies/{_cid()}/areas/{area_id}")


@tool
async def get_area_by_name(area_type: str, name: str) -> str:
    """Find an area by name and type (e.g. ZONE + 'North Zone').

    Args:
        area_type: NATION, ZONE, REGION, AREA, or DIVISION.
        name: Area name to look up.
    """
    return await api_get(f"{P}/companies/{_cid()}/areas/by-name/{area_type}/{name}")


@tool
async def create_area(name: str, area_type: str,
                      nation_id: Optional[int] = None, zone_id: Optional[int] = None,
                      region_id: Optional[int] = None, area_id: Optional[int] = None) -> str:
    """Create a new area in the hierarchy.

    Args:
        name: Area name.
        area_type: NATION, ZONE, REGION, AREA, or DIVISION.
        nation_id: Parent nation ID (for ZONE).
        zone_id: Parent zone ID (for REGION).
        region_id: Parent region ID (for AREA).
        area_id: Parent area ID (for DIVISION).
    """
    body: dict = {"name": name, "type": area_type}
    if nation_id is not None: body["nation_id"] = nation_id
    if zone_id is not None:   body["zone_id"] = zone_id
    if region_id is not None: body["region_id"] = region_id
    if area_id is not None:   body["area_id"] = area_id
    return await api_post(f"{P}/companies/{_cid()}/areas", body)


@tool
async def update_area(area_id: int, name: Optional[str] = None,
                      area_type: Optional[str] = None) -> str:
    """Update an existing area's name or type.

    Args:
        area_id: Area ID to update.
        name: New name (optional).
        area_type: New type (optional).
    """
    body: dict = {}
    if name is not None: body["name"] = name
    if area_type is not None: body["type"] = area_type
    return await api_patch(f"{P}/companies/{_cid()}/areas/{area_id}", body)


# =====================================================================
# PRODUCTS
# =====================================================================


@tool
async def list_products(
    is_active: Optional[bool] = None,
    brand_id: Optional[int] = None,
    category_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
) -> str:
    """List products with optional filters.

    Args:
        is_active: Filter active/inactive.
        brand_id: Filter by brand.
        category_id: Filter by brand category.
        limit: Max rows.
        offset: Pagination offset.
    """
    return await api_get(
        f"{P}/companies/{_cid()}/products",
        {"is_active": is_active, "brand_id": brand_id,
         "category_id": category_id, "limit": limit, "offset": offset},
    )


@tool
async def get_product_by_id(product_id: int) -> str:
    """Get full product detail by ID (includes prices, visibility).

    Args:
        product_id: Product ID (integer).
    """
    return await api_get(f"{P}/companies/{_cid()}/products/{product_id}")


@tool
async def get_product_by_code(code: str) -> str:
    """Get full product detail by its unique product code.

    Args:
        code: Product code string.
    """
    return await api_get(f"{P}/companies/{_cid()}/products/by-code/{code}")


@tool
async def create_product(product_data: dict) -> str:
    """Create a new product. Pass the full product creation payload as a dict.

    Required keys in product_data: brand_id, brand_category_id, name, code,
    gst_rate, gst_category. Optional: description, barcode, hsn_code,
    packaging_type, packaging_details, images, prices, visibility.

    Args:
        product_data: Dict with all product fields.
    """
    return await api_post(f"{P}/companies/{_cid()}/products", product_data)


@tool
async def update_product(product_id: int, product_data: dict) -> str:
    """Update a product (partial update – only include changed fields).

    Args:
        product_id: Product ID.
        product_data: Dict of fields to update.
    """
    return await api_patch(f"{P}/companies/{_cid()}/products/{product_id}", product_data)


# =====================================================================
# BRANDS
# =====================================================================


@tool
async def list_brands(is_active: Optional[bool] = None,
                      limit: int = 50, offset: int = 0) -> str:
    """List brands with optional active filter.

    Args:
        is_active: Filter active/inactive.
        limit: Max rows.
        offset: Pagination offset.
    """
    return await api_get(
        f"{P}/companies/{_cid()}/brands",
        {"is_active": is_active, "limit": limit, "offset": offset},
    )


@tool
async def get_brand_by_id(brand_id: int) -> str:
    """Get full brand detail by ID (includes visibility and margins).

    Args:
        brand_id: Brand ID.
    """
    return await api_get(f"{P}/companies/{_cid()}/brands/{brand_id}")


@tool
async def create_brand(brand_data: dict) -> str:
    """Create a new brand. Required keys: name, code, for_general, for_modern, for_horeca.
    Optional: logo, area_id (list of area IDs for visibility), margins.

    Args:
        brand_data: Dict with all brand fields.
    """
    return await api_post(f"{P}/companies/{_cid()}/brands", brand_data)


@tool
async def update_brand(brand_id: int, brand_data: dict) -> str:
    """Update a brand (partial update).

    Args:
        brand_id: Brand ID.
        brand_data: Dict of fields to update.
    """
    return await api_patch(f"{P}/companies/{_cid()}/brands/{brand_id}", brand_data)


@tool
async def add_brand_visibility(brand_id: int,
                               area_id: Optional[int] = None) -> str:
    """Add visibility for a brand in a specific area (or globally if area_id is null).

    Args:
        brand_id: Brand ID.
        area_id: Area ID, or null for global visibility.
    """
    return await api_post(
        f"{P}/companies/{_cid()}/brands/{brand_id}/visibility",
        {"area_id": area_id},
    )


# =====================================================================
# BRAND CATEGORIES
# =====================================================================


@tool
async def list_brand_categories(brand_id: Optional[int] = None,
                                is_active: Optional[bool] = None,
                                limit: int = 50, offset: int = 0) -> str:
    """List brand categories with optional filters.

    Args:
        brand_id: Filter by brand.
        is_active: Filter active/inactive.
        limit: Max rows.
        offset: Pagination offset.
    """
    return await api_get(
        f"{P}/companies/{_cid()}/brand-categories",
        {"brand_id": brand_id, "is_active": is_active, "limit": limit, "offset": offset},
    )


@tool
async def get_brand_category_by_id(brand_category_id: int) -> str:
    """Get full brand category detail by ID.

    Args:
        brand_category_id: Brand category ID.
    """
    return await api_get(f"{P}/companies/{_cid()}/brand-categories/{brand_category_id}")


@tool
async def create_brand_category(data: dict) -> str:
    """Create a new brand category. Required keys: name, code, brand_id.
    Optional: parent_category_id, for_general, for_modern, for_horeca, area_id, margins.

    Args:
        data: Dict with brand category fields.
    """
    return await api_post(f"{P}/companies/{_cid()}/brand-categories", data)


@tool
async def update_brand_category(brand_category_id: int, data: dict) -> str:
    """Update a brand category (partial update).

    Args:
        brand_category_id: Brand category ID.
        data: Dict of fields to update.
    """
    return await api_patch(f"{P}/companies/{_cid()}/brand-categories/{brand_category_id}", data)


# =====================================================================
# ROUTES
# =====================================================================


@tool
async def list_routes(
    area_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    is_general: Optional[bool] = None,
    is_modern: Optional[bool] = None,
    is_horeca: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
) -> str:
    """List routes with optional filters.

    Args:
        area_id: Filter by area (division) ID.
        is_active: Filter active/inactive.
        is_general: Filter general trade routes.
        is_modern: Filter modern trade routes.
        is_horeca: Filter HORECA routes.
        limit: Max rows.
        offset: Pagination offset.
    """
    return await api_get(
        f"{P}/companies/{_cid()}/routes",
        {"area_id": area_id, "is_active": is_active, "is_general": is_general,
         "is_modern": is_modern, "is_horeca": is_horeca, "limit": limit, "offset": offset},
    )


@tool
async def get_route_by_id(route_id: int) -> str:
    """Get full route detail by ID (includes hierarchy names).

    Args:
        route_id: Route ID.
    """
    return await api_get(f"{P}/companies/{_cid()}/routes/{route_id}")


@tool
async def create_route(name: str, code: str, area_id: int,
                       is_general: bool = False, is_modern: bool = False,
                       is_horeca: bool = False) -> str:
    """Create a new route.

    Args:
        name: Route name.
        code: Unique route code.
        area_id: Area (division) ID.
        is_general: General trade route.
        is_modern: Modern trade route.
        is_horeca: HORECA route.
    """
    return await api_post(f"{P}/companies/{_cid()}/routes", {
        "name": name, "code": code, "area_id": area_id,
        "is_general": is_general, "is_modern": is_modern, "is_horeca": is_horeca,
    })


@tool
async def update_route(route_id: int, data: dict) -> str:
    """Update a route (partial update). Updatable: name, is_general, is_modern, is_horeca.

    Args:
        route_id: Route ID.
        data: Dict of fields to update.
    """
    return await api_patch(f"{P}/companies/{_cid()}/routes/{route_id}", data)


# =====================================================================
# DISTRIBUTORS
# =====================================================================


@tool
async def list_distributors(area_id: Optional[int] = None,
                            is_active: Optional[bool] = None,
                            limit: int = 50, offset: int = 0) -> str:
    """List distributors with optional filters.

    Args:
        area_id: Filter by area ID.
        is_active: Filter active/inactive.
        limit: Max rows.
        offset: Pagination offset.
    """
    return await api_get(
        f"{P}/companies/{_cid()}/distributors",
        {"area_id": area_id, "is_active": is_active, "limit": limit, "offset": offset},
    )


@tool
async def get_distributor_by_id(distributor_id: str) -> str:
    """Get full distributor detail by UUID.

    Args:
        distributor_id: Distributor UUID string.
    """
    return await api_get(f"{P}/companies/{_cid()}/distributors/{distributor_id}")


@tool
async def get_distributors_by_area(area_id: int) -> str:
    """Get all active distributors for a specific area.

    Args:
        area_id: Area ID (integer).
    """
    return await api_get(f"{P}/companies/{_cid()}/distributors/area/{area_id}/distributors")


@tool
async def create_distributor(distributor_data: dict) -> str:
    """Create a new distributor. Required keys: name, contact_person_name,
    mobile_number, gst_no, pan_no, address, pin_code, area_id, bank_details.

    Args:
        distributor_data: Dict with all distributor fields.
    """
    return await api_post(f"{P}/companies/{_cid()}/distributors", distributor_data)


@tool
async def update_distributor(distributor_id: str, data: dict) -> str:
    """Update a distributor (partial update).

    Args:
        distributor_id: Distributor UUID.
        data: Dict of fields to update.
    """
    return await api_patch(f"{P}/companies/{_cid()}/distributors/{distributor_id}", data)


# =====================================================================
# RETAILERS
# =====================================================================


@tool
async def list_retailers(route_id: Optional[int] = None,
                         category_id: Optional[int] = None,
                         is_active: Optional[bool] = None,
                         limit: int = 50, offset: int = 0) -> str:
    """List retailers with optional filters.

    Args:
        route_id: Filter by route ID.
        category_id: Filter by shop category ID.
        is_active: Filter active/inactive.
        limit: Max rows.
        offset: Pagination offset.
    """
    return await api_get(
        f"{P}/companies/{_cid()}/retailers",
        {"route_id": route_id, "category_id": category_id,
         "is_active": is_active, "limit": limit, "offset": offset},
    )


@tool
async def get_retailer_by_id(retailer_id: str) -> str:
    """Get full retailer detail by UUID.

    Args:
        retailer_id: Retailer UUID string.
    """
    return await api_get(f"{P}/companies/{_cid()}/retailers/{retailer_id}")


@tool
async def get_retailers_by_route(route_id: int) -> str:
    """Get all active retailers for a specific route.

    Args:
        route_id: Route ID (integer).
    """
    return await api_get(f"{P}/companies/{_cid()}/retailers/route/{route_id}/retailers")


@tool
async def create_retailer(retailer_data: dict) -> str:
    """Create a new retailer. Required keys: name, code, contact_person_name,
    mobile_number, gst_no, pan_no, address, pin_code, category_id, route_id.

    Args:
        retailer_data: Dict with all retailer fields.
    """
    return await api_post(f"{P}/companies/{_cid()}/retailers", retailer_data)


@tool
async def update_retailer(retailer_id: str, data: dict) -> str:
    """Update a retailer (partial update).

    Args:
        retailer_id: Retailer UUID.
        data: Dict of fields to update.
    """
    return await api_patch(f"{P}/companies/{_cid()}/retailers/{retailer_id}", data)


# =====================================================================
# ORDERS
# =====================================================================


@tool
async def list_orders(
    retailer_id: Optional[str] = None,
    member_id: Optional[str] = None,
    order_status: Optional[str] = None,
    order_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
) -> str:
    """List orders with optional filters.

    Args:
        retailer_id: Filter by retailer UUID.
        member_id: Filter by member UUID.
        order_status: DRAFT, CONFIRMED, DELIVERED, or CANCELLED.
        order_type: TELEPHONE, IN_STORE, or OTHERS.
        is_active: Filter active/inactive.
        limit: Max rows.
        offset: Pagination offset.
    """
    return await api_get(
        f"{P}/companies/{_cid()}/orders",
        {"retailer_id": retailer_id, "member_id": member_id,
         "order_status": order_status, "order_type": order_type,
         "is_active": is_active, "limit": limit, "offset": offset},
    )


@tool
async def get_order_by_id(order_id: str) -> str:
    """Get order info by UUID (basic view with items).

    Args:
        order_id: Order UUID string.
    """
    return await api_get(f"{P}/companies/{_cid()}/orders/{order_id}")


@tool
async def get_order_detail(order_id: str) -> str:
    """Get detailed order with retailer name, member name, and product names.

    Args:
        order_id: Order UUID string.
    """
    return await api_get(f"{P}/companies/{_cid()}/orders/{order_id}/detail")


@tool
async def create_order(order_data: dict) -> str:
    """Create a new order. Required keys: retailer_id, member_id, items (list).
    Each item: {product_id, quantity}. Optional: order_type, order_status.

    Args:
        order_data: Dict with order fields.
    """
    return await api_post(f"{P}/companies/{_cid()}/orders", order_data)


@tool
async def update_order_status(order_id: str, new_status: str) -> str:
    """Update order status. Valid transitions: DRAFT→CONFIRMED/CANCELLED,
    CONFIRMED→DELIVERED/CANCELLED. DELIVERED and CANCELLED are terminal.

    Args:
        order_id: Order UUID.
        new_status: CONFIRMED, DELIVERED, or CANCELLED.
    """
    return await api_patch(
        f"{P}/companies/{_cid()}/orders/{order_id}/status",
        params={"new_status": new_status},
    )


# =====================================================================
# USERS / MEMBERS
# =====================================================================


@tool
async def list_users_by_company() -> str:
    """List all users/members for the current company."""
    return await api_get(f"{P}/users/companies/{_cid()}/users")


@tool
async def get_user_by_id(user_id: str) -> str:
    """Get user info by UUID.

    Args:
        user_id: User UUID string.
    """
    return await api_get(f"{P}/users/{user_id}")


# =====================================================================
# COMPANIES
# =====================================================================


@tool
async def get_company() -> str:
    """Get current company info."""
    return await api_get(f"{P}/companies/{_cid()}")


# =====================================================================
# SHOP CATEGORIES
# =====================================================================


@tool
async def list_shop_categories(limit: int = 50, offset: int = 0) -> str:
    """List all shop categories.

    Args:
        limit: Max rows.
        offset: Pagination offset.
    """
    return await api_get(
        f"{P}/companies/{_cid()}/shop-categories",
        {"limit": limit, "offset": offset},
    )


# =====================================================================
# ROUTE ASSIGNMENTS
# =====================================================================


@tool
async def list_route_assignments(route_id: Optional[int] = None,
                                 user_id: Optional[str] = None,
                                 limit: int = 50, offset: int = 0) -> str:
    """List route assignments with optional filters.

    Args:
        route_id: Filter by route.
        user_id: Filter by user UUID.
        limit: Max rows.
        offset: Pagination offset.
    """
    return await api_get(
        f"{P}/companies/{_cid()}/route-assignments",
        {"limit": limit, "offset": offset},
    )


# =====================================================================
# ROLES
# =====================================================================


@tool
async def list_roles() -> str:
    """List all roles for the current company."""
    return await api_get(f"{P}/companies/{_cid()}/roles")


# =====================================================================
# COLLECTED TOOL LISTS
# =====================================================================

READ_TOOLS = [
    list_areas, get_area_by_id, get_area_by_name,
    list_products, get_product_by_id, get_product_by_code,
    list_brands, get_brand_by_id,
    list_brand_categories, get_brand_category_by_id,
    list_routes, get_route_by_id,
    list_distributors, get_distributor_by_id, get_distributors_by_area,
    list_retailers, get_retailer_by_id, get_retailers_by_route,
    list_orders, get_order_by_id, get_order_detail,
    list_users_by_company, get_user_by_id,
    get_company,
    list_shop_categories,
    list_route_assignments,
    list_roles,
]

WRITE_TOOLS = [
    create_area, update_area,
    create_product, update_product,
    create_brand, update_brand, add_brand_visibility,
    create_brand_category, update_brand_category,
    create_route, update_route,
    create_distributor, update_distributor,
    create_retailer, update_retailer,
    create_order, update_order_status,
]

ALL_API_TOOLS = READ_TOOLS + WRITE_TOOLS
