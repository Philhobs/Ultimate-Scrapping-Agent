"""call_api MCP tool — make HTTP requests to any URL or registered API."""

from __future__ import annotations

import json
from typing import Any

import httpx
from claude_agent_sdk import tool

from api_integrator.state import get_api_registry

MAX_RESPONSE_CHARS = 10000


@tool(
    "call_api",
    "Make an HTTP request. Provide either a full 'url' OR an 'api_name' + 'endpoint' "
    "to use a registered API. Supports GET, POST, PUT, DELETE. "
    "Pass 'params' for query parameters and 'body' for request body (JSON).",
    {
        "url": str,
        "method": str,
        "api_name": str,
        "endpoint": str,
        "path_params": str,
        "params": str,
        "body": str,
        "headers": str,
    },
)
async def call_api(args: dict[str, Any]) -> dict[str, Any]:
    method = (args.get("method") or "GET").upper()
    headers: dict[str, str] = {"Accept": "application/json"}

    # Build URL from either direct url or registry lookup
    url = args.get("url")
    if not url:
        api_name = args.get("api_name")
        endpoint_name = args.get("endpoint")
        if not api_name:
            return {
                "content": [{"type": "text", "text": "Error: Provide either 'url' or 'api_name'."}],
                "is_error": True,
            }

        registry = get_api_registry()
        api = registry.get(api_name)
        if not api:
            available = [a.name for a in registry.list_all()]
            return {
                "content": [{"type": "text", "text": f"Error: API '{api_name}' not found. Available: {available}"}],
                "is_error": True,
            }

        # Build URL from base + endpoint path
        if endpoint_name and endpoint_name in api.endpoints:
            ep = api.endpoints[endpoint_name]
            path = ep.path
            method = method or ep.method
        elif endpoint_name:
            path = endpoint_name if endpoint_name.startswith("/") else f"/{endpoint_name}"
        else:
            path = ""

        # Substitute path parameters like {id}, {name}
        path_params_raw = args.get("path_params")
        if path_params_raw:
            try:
                path_params = json.loads(path_params_raw) if isinstance(path_params_raw, str) else path_params_raw
                for k, v in path_params.items():
                    path = path.replace(f"{{{k}}}", str(v))
            except (json.JSONDecodeError, AttributeError):
                pass

        url = f"{api.base_url}{path}"
        headers.update(api.default_headers)
        headers.update(api.get_auth_header())

    # Parse extra headers
    extra_headers_raw = args.get("headers")
    if extra_headers_raw:
        try:
            extra = json.loads(extra_headers_raw) if isinstance(extra_headers_raw, str) else extra_headers_raw
            headers.update(extra)
        except (json.JSONDecodeError, AttributeError):
            pass

    # Parse query params
    params: dict[str, str] | None = None
    params_raw = args.get("params")
    if params_raw:
        try:
            params = json.loads(params_raw) if isinstance(params_raw, str) else params_raw
        except (json.JSONDecodeError, AttributeError):
            params = None

    # Parse body
    body: Any = None
    body_raw = args.get("body")
    if body_raw:
        try:
            body = json.loads(body_raw) if isinstance(body_raw, str) else body_raw
        except (json.JSONDecodeError, AttributeError):
            body = body_raw

    # Make the request
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=method,
                url=url,
                params=params,
                json=body if method in ("POST", "PUT", "PATCH") and body else None,
                headers=headers,
            )

        # Format response
        try:
            resp_data = response.json()
            resp_text = json.dumps(resp_data, indent=2)
        except (json.JSONDecodeError, ValueError):
            resp_text = response.text

        # Truncate if too long
        if len(resp_text) > MAX_RESPONSE_CHARS:
            resp_text = resp_text[:MAX_RESPONSE_CHARS] + f"\n... (truncated, {len(response.text)} total chars)"

        result = {
            "status_code": response.status_code,
            "url": str(response.url),
            "response": resp_text,
        }

        if response.status_code >= 400:
            return {
                "content": [{"type": "text", "text": json.dumps(result, indent=2)}],
                "is_error": True,
            }

        return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}

    except httpx.TimeoutException:
        return {
            "content": [{"type": "text", "text": f"Error: Request to {url} timed out (30s limit)."}],
            "is_error": True,
        }
    except httpx.RequestError as e:
        return {
            "content": [{"type": "text", "text": f"Error: Request failed — {e}"}],
            "is_error": True,
        }
