"""chain_pipeline MCP tool — execute a multi-step pipeline of API calls and model inferences."""

from __future__ import annotations

import json
import os
from typing import Any

import httpx
from claude_agent_sdk import tool

from api_integrator.state import get_api_registry, get_model_registry, store_result

HF_API_BASE = "https://api-inference.huggingface.co/models"


async def _call_api_step(step: dict[str, Any]) -> dict[str, Any]:
    """Execute an API call step."""
    url = step.get("url", "")
    method = step.get("method", "GET").upper()
    headers: dict[str, str] = {"Accept": "application/json"}
    params = step.get("params")
    body = step.get("body")

    # If api_name is provided, resolve from registry
    api_name = step.get("api_name")
    if api_name:
        registry = get_api_registry()
        api = registry.get(api_name)
        if api:
            endpoint = step.get("endpoint", "")
            if endpoint and endpoint in api.endpoints:
                path = api.endpoints[endpoint].path
            else:
                path = endpoint if endpoint.startswith("/") else f"/{endpoint}"
            url = f"{api.base_url}{path}"
            headers.update(api.default_headers)
            headers.update(api.get_auth_header())

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.request(
            method=method,
            url=url,
            params=params,
            json=body if method in ("POST", "PUT", "PATCH") and body else None,
            headers=headers,
        )

    try:
        return {"status": response.status_code, "data": response.json()}
    except (json.JSONDecodeError, ValueError):
        return {"status": response.status_code, "data": response.text}


async def _run_model_step(step: dict[str, Any], input_override: str | None = None) -> dict[str, Any]:
    """Execute a model inference step."""
    model_id = step["model_id"]
    input_data = input_override or step.get("input_data", "")

    token = os.environ.get("HF_API_TOKEN", "")
    if not token:
        return {"error": "HF_API_TOKEN not set"}

    # Parse input
    try:
        parsed_input = json.loads(input_data) if isinstance(input_data, str) else input_data
    except (json.JSONDecodeError, TypeError):
        parsed_input = input_data

    payload: dict[str, Any] = {
        "inputs": parsed_input,
        "options": {"wait_for_model": True},
    }
    parameters = step.get("parameters")
    if parameters:
        payload["parameters"] = parameters

    url = f"{HF_API_BASE}/{model_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(url, json=payload, headers=headers)

    try:
        return {"status": response.status_code, "data": response.json()}
    except (json.JSONDecodeError, ValueError):
        return {"status": response.status_code, "data": response.text}


def _extract_text(result: dict[str, Any]) -> str:
    """Extract text output from a step result to feed into the next step."""
    data = result.get("data")
    if isinstance(data, str):
        return data
    if isinstance(data, list) and data:
        first = data[0]
        if isinstance(first, dict):
            # Common HF response formats
            for key in ("generated_text", "translation_text", "summary_text", "text"):
                if key in first:
                    return first[key]
            return json.dumps(first)
        return str(first)
    if isinstance(data, dict):
        for key in ("generated_text", "translation_text", "summary_text", "text", "response"):
            if key in data:
                return data[key]
        return json.dumps(data)
    return str(data)


@tool(
    "chain_pipeline",
    "Execute a multi-step pipeline. Provide 'steps' as a JSON array where each step "
    "has a 'type' ('api' or 'model'), plus step-specific fields. "
    "For 'api' steps: url/api_name, method, params, body. "
    "For 'model' steps: model_id, input_data (optional — uses previous output if omitted). "
    "Each step's output feeds into the next step's input automatically. "
    "Optionally provide a 'result_key' to store the final result.",
    {"steps": str, "result_key": str},
)
async def chain_pipeline(args: dict[str, Any]) -> dict[str, Any]:
    steps_raw = args.get("steps")
    if not steps_raw:
        return {
            "content": [{"type": "text", "text": "Error: 'steps' is required (JSON array)."}],
            "is_error": True,
        }

    try:
        steps = json.loads(steps_raw) if isinstance(steps_raw, str) else steps_raw
    except (json.JSONDecodeError, TypeError):
        return {
            "content": [{"type": "text", "text": "Error: 'steps' must be valid JSON array."}],
            "is_error": True,
        }

    if not isinstance(steps, list) or not steps:
        return {
            "content": [{"type": "text", "text": "Error: 'steps' must be a non-empty array."}],
            "is_error": True,
        }

    results: list[dict[str, Any]] = []
    previous_output: str | None = None

    for i, step in enumerate(steps):
        step_type = step.get("type", "api")
        step_name = step.get("name", f"step_{i + 1}")

        try:
            if step_type == "api":
                result = await _call_api_step(step)
            elif step_type == "model":
                result = await _run_model_step(step, input_override=previous_output)
            else:
                result = {"error": f"Unknown step type: {step_type}"}
        except Exception as e:
            result = {"error": str(e)}

        # Extract text for chaining
        previous_output = _extract_text(result)

        results.append({
            "step": i + 1,
            "name": step_name,
            "type": step_type,
            "result": result,
            "extracted_output": previous_output[:500] if previous_output else None,
        })

        # Stop on error
        if "error" in result:
            break

    # Store final result if requested
    result_key = args.get("result_key")
    if result_key and results:
        store_result(result_key, results[-1])

    output = {
        "pipeline_steps": len(steps),
        "completed_steps": len(results),
        "results": results,
    }

    return {"content": [{"type": "text", "text": json.dumps(output, indent=2)}]}
