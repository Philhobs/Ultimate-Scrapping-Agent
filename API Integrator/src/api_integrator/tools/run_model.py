"""run_model MCP tool — run inference on a HuggingFace model via Inference API."""

from __future__ import annotations

import json
import os
from typing import Any

import httpx
from claude_agent_sdk import tool

from api_integrator.state import get_model_registry

HF_API_BASE = "https://api-inference.huggingface.co/models"
MAX_RESPONSE_CHARS = 10000


@tool(
    "run_model",
    "Run inference on a HuggingFace model using the Inference API. "
    "Provide a 'model_id' (e.g., 'facebook/bart-large-cnn') and 'input_data'. "
    "For text models, input_data is a string. For QA models, input_data should be "
    "JSON with 'question' and 'context'. For zero-shot, include 'candidate_labels'. "
    "Requires HF_API_TOKEN environment variable.",
    {
        "model_id": str,
        "input_data": str,
        "parameters": str,
        "wait_for_model": str,
    },
)
async def run_model(args: dict[str, Any]) -> dict[str, Any]:
    model_id = args["model_id"]
    input_data_raw = args["input_data"]
    wait_for_model = args.get("wait_for_model", "true").lower() == "true"

    # Get API token
    token = os.environ.get("HF_API_TOKEN", "")
    if not token:
        return {
            "content": [{
                "type": "text",
                "text": "Error: HF_API_TOKEN environment variable is not set. "
                        "Get a free token at https://huggingface.co/settings/tokens",
            }],
            "is_error": True,
        }

    # Look up model info for context
    registry = get_model_registry()
    model_info = registry.get_model(model_id)

    # Parse input data — could be plain text or JSON
    try:
        input_data = json.loads(input_data_raw)
    except (json.JSONDecodeError, TypeError):
        input_data = input_data_raw

    # Parse optional parameters
    parameters: dict[str, Any] = {}
    params_raw = args.get("parameters")
    if params_raw:
        try:
            parameters = json.loads(params_raw)
        except (json.JSONDecodeError, TypeError):
            pass

    # Build request payload
    if isinstance(input_data, str):
        payload: dict[str, Any] = {"inputs": input_data}
    elif isinstance(input_data, dict):
        payload = {"inputs": input_data}
    else:
        payload = {"inputs": input_data}

    if parameters:
        payload["parameters"] = parameters

    if wait_for_model:
        payload["options"] = {"wait_for_model": True}

    url = f"{HF_API_BASE}/{model_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, json=payload, headers=headers)

        if response.status_code == 503:
            # Model is loading
            try:
                error_data = response.json()
                estimated = error_data.get("estimated_time", "unknown")
                return {
                    "content": [{
                        "type": "text",
                        "text": f"Model '{model_id}' is loading (estimated: {estimated}s). "
                                "It will be set to wait_for_model=true by default. "
                                "Try again in a moment.",
                    }],
                    "is_error": True,
                }
            except (json.JSONDecodeError, ValueError):
                pass

        if response.status_code >= 400:
            return {
                "content": [{
                    "type": "text",
                    "text": f"Error {response.status_code} from HuggingFace: {response.text[:2000]}",
                }],
                "is_error": True,
            }

        # Parse response
        try:
            result = response.json()
            result_text = json.dumps(result, indent=2)
        except (json.JSONDecodeError, ValueError):
            result_text = response.text

        if len(result_text) > MAX_RESPONSE_CHARS:
            result_text = result_text[:MAX_RESPONSE_CHARS] + "\n... (truncated)"

        output = {
            "model_id": model_id,
            "task": model_info.task if model_info else "unknown",
            "result": result_text,
        }

        return {"content": [{"type": "text", "text": json.dumps(output, indent=2)}]}

    except httpx.TimeoutException:
        return {
            "content": [{"type": "text", "text": f"Error: Request to model '{model_id}' timed out (120s)."}],
            "is_error": True,
        }
    except httpx.RequestError as e:
        return {
            "content": [{"type": "text", "text": f"Error: Request failed — {e}"}],
            "is_error": True,
        }
