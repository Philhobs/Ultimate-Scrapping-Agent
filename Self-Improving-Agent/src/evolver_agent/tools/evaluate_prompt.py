"""evaluate_prompt MCP tool — score a prompt version against quality criteria."""

from __future__ import annotations

import json
from typing import Any

from claude_agent_sdk import tool

from evolver_agent.analyzers.evaluator import evaluate_prompt as score_prompt
from evolver_agent.analyzers.prompt_evolver import analyze_prompt_structure
from evolver_agent.state import add_metrics


@tool(
    "evaluate_prompt",
    "Score a prompt version on clarity, completeness, structure, specificity, "
    "safety, and efficiency. Returns a detailed scorecard. "
    "Provide 'prompt' (the text to evaluate) or 'version_id' to evaluate a stored version.",
    {"prompt": str, "version_id": int},
)
async def evaluate_prompt(args: dict[str, Any]) -> dict[str, Any]:
    prompt_text = args.get("prompt")
    version_id = args.get("version_id")

    if prompt_text is None and version_id is not None:
        from evolver_agent.state import get_prompt_version
        version = get_prompt_version(version_id)
        if version is None:
            return {
                "content": [{"type": "text", "text": f"Error: Version {version_id} not found."}],
                "is_error": True,
            }
        prompt_text = version["prompt"]

    if not prompt_text:
        return {
            "content": [{"type": "text", "text": "Error: Provide 'prompt' text or 'version_id'."}],
            "is_error": True,
        }

    # Score the prompt
    scores = score_prompt(prompt_text)
    structure = analyze_prompt_structure(prompt_text)

    # Log metrics
    add_metrics({
        "version_id": version_id,
        "scores": scores.to_dict(),
    })

    # Dimension breakdown with ratings
    breakdown: dict[str, dict] = {}
    ratings = {
        (90, 101): "Excellent",
        (75, 90): "Good",
        (60, 75): "Fair",
        (40, 60): "Needs Work",
        (0, 40): "Poor",
    }

    for dim, score in scores.to_dict().items():
        if dim == "overall":
            continue
        rating = "Unknown"
        for (lo, hi), label in ratings.items():
            if lo <= score < hi:
                rating = label
                break
        breakdown[dim] = {
            "score": round(score, 1),
            "rating": rating,
            "weight": {"clarity": "20%", "completeness": "15%", "structure": "15%",
                       "specificity": "15%", "safety": "20%", "efficiency": "15%"}.get(dim, ""),
        }

    # Overall grade
    overall = scores.overall
    if overall >= 90:
        grade = "A"
    elif overall >= 80:
        grade = "B+"
    elif overall >= 70:
        grade = "B"
    elif overall >= 60:
        grade = "C"
    elif overall >= 50:
        grade = "D"
    else:
        grade = "F"

    result = {
        "overall_score": round(overall, 1),
        "grade": grade,
        "breakdown": breakdown,
        "structure": {
            "estimated_tokens": structure["estimated_tokens"],
            "sections": len(structure["sections"]),
            "has_role": structure["has_role_definition"],
            "has_constraints": structure["has_constraints"],
            "has_examples": structure["has_examples"],
            "has_workflow": structure["has_workflow"],
            "has_output_format": structure["has_output_format"],
        },
        "prompt_length": len(prompt_text),
    }

    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
