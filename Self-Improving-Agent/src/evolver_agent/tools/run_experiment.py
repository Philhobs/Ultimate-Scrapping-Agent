"""run_experiment MCP tool — compare two prompt versions with A/B evaluation."""

from __future__ import annotations

import json
from typing import Any

from claude_agent_sdk import tool

from evolver_agent.analyzers.evaluator import evaluate_prompt, compare_scores
from evolver_agent.state import get_prompt_version, add_experiment


@tool(
    "run_experiment",
    "Compare two prompt versions by evaluating both against the same criteria. "
    "Returns a winner with dimensional comparison. "
    "Provide 'version_a' and 'version_b' (version IDs), or "
    "'prompt_a' and 'prompt_b' (raw prompt texts).",
    {"version_a": int, "version_b": int, "prompt_a": str, "prompt_b": str},
)
async def run_experiment(args: dict[str, Any]) -> dict[str, Any]:
    # Get prompts
    prompt_a = args.get("prompt_a")
    prompt_b = args.get("prompt_b")
    version_a = args.get("version_a")
    version_b = args.get("version_b")
    label_a = "A"
    label_b = "B"

    if version_a is not None:
        va = get_prompt_version(version_a)
        if va:
            prompt_a = va["prompt"]
            label_a = va.get("label", f"v{version_a}")
        else:
            return {
                "content": [{"type": "text", "text": f"Error: Version {version_a} not found."}],
                "is_error": True,
            }

    if version_b is not None:
        vb = get_prompt_version(version_b)
        if vb:
            prompt_b = vb["prompt"]
            label_b = vb.get("label", f"v{version_b}")
        else:
            return {
                "content": [{"type": "text", "text": f"Error: Version {version_b} not found."}],
                "is_error": True,
            }

    if not prompt_a or not prompt_b:
        return {
            "content": [{"type": "text", "text": "Error: Provide both prompts (version IDs or raw text)."}],
            "is_error": True,
        }

    # Evaluate both
    scores_a = evaluate_prompt(prompt_a)
    scores_b = evaluate_prompt(prompt_b)

    # Compare
    comparison = compare_scores(scores_a, scores_b)

    # Determine winner
    if comparison["verdict"] == "improved":
        winner = label_b
        winner_prompt = "B"
    elif comparison["verdict"] == "degraded":
        winner = label_a
        winner_prompt = "A"
    elif comparison["verdict"] == "rejected_safety_degraded":
        winner = label_a
        winner_prompt = "A (safety degradation in B)"
    else:
        winner = "tie"
        winner_prompt = "neither"

    # Store experiment
    experiment = {
        "label_a": label_a,
        "label_b": label_b,
        "version_a": version_a,
        "version_b": version_b,
        "scores_a": scores_a.to_dict(),
        "scores_b": scores_b.to_dict(),
        "comparison": comparison,
        "winner": winner,
    }
    add_experiment(experiment)

    result = {
        "winner": winner,
        "verdict": comparison["verdict"],
        "safety_check": comparison["safety_check"],
        "scores_a": {
            "label": label_a,
            **scores_a.to_dict(),
        },
        "scores_b": {
            "label": label_b,
            **scores_b.to_dict(),
        },
        "dimension_comparison": comparison["comparison"],
        "improved_dimensions": comparison["improved_dimensions"],
        "degraded_dimensions": comparison["degraded_dimensions"],
        "recommendation": (
            f"Apply version {winner_prompt} — it shows improvement across "
            f"{comparison['improved_dimensions']} dimensions."
            if comparison["verdict"] == "improved"
            else f"Keep version {winner_prompt}. "
            + ("Safety was degraded in the variant." if comparison["verdict"] == "rejected_safety_degraded"
               else "No significant improvement detected.")
        ),
    }

    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
