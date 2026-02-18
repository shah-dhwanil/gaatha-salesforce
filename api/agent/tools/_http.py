"""
Shared async HTTP client for API tools.

Every tool calls the REST API via HTTP. This module provides a thin
helper that builds URLs, makes the request, and returns a JSON-serialised
string (which is what LangChain tool functions must return).
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import structlog

logger = structlog.get_logger(__name__)

_BASE_URL: str | None = None


def set_base_url(url: str) -> None:
    """Set the base URL for all API calls (called once at startup)."""
    global _BASE_URL
    _BASE_URL = url.rstrip("/")
    logger.info("[HTTP] Base URL configured", base_url=_BASE_URL)


def _get_base_url() -> str:
    if _BASE_URL:
        return _BASE_URL
    from api.settings import get_settings
    return get_settings().AGENT.BACKEND_URL.rstrip("/")


async def api_get(
    path: str,
    params: dict[str, Any] | None = None,
    timeout: float = 30.0,
) -> str:
    """Perform an async GET request and return the JSON body as a string."""
    url = f"{_get_base_url()}{path}"
    clean_params = {k: v for k, v in (params or {}).items() if v is not None}

    logger.debug("[HTTP] GET", url=url, params=clean_params)
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.get(url, params=clean_params)

    logger.debug("[HTTP] Response", status=resp.status_code, length=len(resp.content))
    if resp.status_code >= 400:
        return json.dumps({"error": f"HTTP {resp.status_code}", "detail": resp.text[:500]})
    try:
        return json.dumps(resp.json(), default=str)
    except Exception:
        return resp.text


async def api_post(
    path: str,
    body: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    timeout: float = 30.0,
) -> str:
    """Perform an async POST request and return the JSON body as a string."""
    url = f"{_get_base_url()}{path}"
    clean_params = {k: v for k, v in (params or {}).items() if v is not None}

    logger.debug("[HTTP] POST", url=url, body_keys=list((body or {}).keys()))
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, json=body, params=clean_params)

    logger.debug("[HTTP] Response", status=resp.status_code, length=len(resp.content))
    if resp.status_code >= 400:
        return json.dumps({"error": f"HTTP {resp.status_code}", "detail": resp.text[:500]})
    if resp.status_code == 204:
        return json.dumps({"success": True})
    try:
        return json.dumps(resp.json(), default=str)
    except Exception:
        return resp.text


async def api_patch(
    path: str,
    body: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    timeout: float = 30.0,
) -> str:
    """Perform an async PATCH request and return the JSON body as a string."""
    url = f"{_get_base_url()}{path}"
    clean_params = {k: v for k, v in (params or {}).items() if v is not None}

    logger.debug("[HTTP] PATCH", url=url, body_keys=list((body or {}).keys()))
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.patch(url, json=body, params=clean_params)

    logger.debug("[HTTP] Response", status=resp.status_code, length=len(resp.content))
    if resp.status_code >= 400:
        return json.dumps({"error": f"HTTP {resp.status_code}", "detail": resp.text[:500]})
    try:
        return json.dumps(resp.json(), default=str)
    except Exception:
        return resp.text


async def api_delete(
    path: str,
    params: dict[str, Any] | None = None,
    timeout: float = 30.0,
) -> str:
    """Perform an async DELETE request and return the JSON body as a string."""
    url = f"{_get_base_url()}{path}"
    clean_params = {k: v for k, v in (params or {}).items() if v is not None}

    logger.debug("[HTTP] DELETE", url=url, params=clean_params)
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.delete(url, params=clean_params)

    logger.debug("[HTTP] Response", status=resp.status_code, length=len(resp.content))
    if resp.status_code >= 400:
        return json.dumps({"error": f"HTTP {resp.status_code}", "detail": resp.text[:500]})
    return json.dumps({"success": True})
