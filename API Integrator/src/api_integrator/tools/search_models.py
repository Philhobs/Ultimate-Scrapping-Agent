"""search_models MCP tool — search HuggingFace models by task or keyword."""

from __future__ import annotations

import json
from typing import Any

from claude_agent_sdk import tool

from api_integrator.state import get_model_registry


@tool(
    "search_models",
    "Search available HuggingFace models. Provide a 'task' (e.g., summarization, "
    "translation, text-classification, image-classification, automatic-speech-recognition) "
    "or a 'query' keyword to search across all models. Use 'list_tasks' to see all task categories.",
    {"task": str, "query": str, "list_tasks": str},
)
async def search_models(args: dict[str, Any]) -> dict[str, Any]:
    registry = get_model_registry()

    # List all task categories
    if args.get("list_tasks"):
        tasks = registry.get_tasks()
        summary = registry.summary()
        return {
            "content": [{
                "type": "text",
                "text": json.dumps({
                    "available_tasks": tasks,
                    "details": summary,
                }, indent=2),
            }]
        }

    task = args.get("task")
    query = args.get("query")

    if task:
        models = registry.get_models_for_task(task)
        if not models:
            # Try fuzzy match
            all_tasks = registry.get_tasks()
            suggestions = [t for t in all_tasks if task.lower() in t.lower()]
            return {
                "content": [{
                    "type": "text",
                    "text": json.dumps({
                        "error": f"No models found for task '{task}'.",
                        "available_tasks": all_tasks,
                        "suggestions": suggestions,
                    }, indent=2),
                }]
            }

        return {
            "content": [{
                "type": "text",
                "text": json.dumps({
                    "task": task,
                    "models": [
                        {
                            "model_id": m.model_id,
                            "description": m.description,
                            "input_type": m.input_type,
                            "output_type": m.output_type,
                        }
                        for m in models
                    ],
                }, indent=2),
            }]
        }

    if query:
        models = registry.search(query)
        return {
            "content": [{
                "type": "text",
                "text": json.dumps({
                    "query": query,
                    "results": [
                        {
                            "model_id": m.model_id,
                            "task": m.task,
                            "description": m.description,
                        }
                        for m in models
                    ],
                }, indent=2),
            }]
        }

    return {
        "content": [{
            "type": "text",
            "text": "Provide either 'task', 'query', or set 'list_tasks' to 'true'.",
        }],
        "is_error": True,
    }
