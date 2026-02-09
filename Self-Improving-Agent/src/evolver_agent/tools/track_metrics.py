"""track_metrics MCP tool — log and retrieve performance metrics over time."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from claude_agent_sdk import tool

from evolver_agent.state import (
    get_metrics_history, get_all_versions, get_output_dir, add_metrics,
)


@tool(
    "track_metrics",
    "Log evaluation scores and retrieve performance history. "
    "Shows score trends across versions (improving, stable, degrading). "
    "Optional: 'save' (bool) to persist metrics to disk.",
    {"save": bool},
)
async def track_metrics(args: dict[str, Any]) -> dict[str, Any]:
    save = args.get("save", False)

    versions = get_all_versions()
    history = get_metrics_history()

    if not versions:
        return {"content": [{"type": "text", "text": json.dumps({
            "status": "no_data",
            "message": "No versions tracked yet. Run analyze_agent first.",
        }, indent=2)}]}

    # Build version progression
    progression: list[dict] = []
    for v in versions:
        entry = {
            "version_id": v.get("version_id", 0),
            "label": v.get("label", "unknown"),
            "strategy": v.get("source", "unknown"),
            "scores": v.get("scores", {}),
        }
        progression.append(entry)

    # Compute trends
    trends: dict[str, str] = {}
    if len(versions) >= 2:
        dimensions = ["clarity", "completeness", "structure", "specificity", "safety", "efficiency", "overall"]
        first = versions[0].get("scores", {})
        last = versions[-1].get("scores", {})

        for dim in dimensions:
            start = first.get(dim, 0)
            end = last.get(dim, 0)
            delta = end - start
            if delta > 3:
                trends[dim] = f"improving (+{delta:.1f})"
            elif delta < -3:
                trends[dim] = f"degrading ({delta:.1f})"
            else:
                trends[dim] = "stable"

    # Summary stats
    if versions:
        first_overall = versions[0].get("scores", {}).get("overall", 0)
        last_overall = versions[-1].get("scores", {}).get("overall", 0)
        best_overall = max(v.get("scores", {}).get("overall", 0) for v in versions)
        total_improvement = last_overall - first_overall
    else:
        first_overall = last_overall = best_overall = total_improvement = 0

    result = {
        "total_versions": len(versions),
        "total_evaluations": len(history),
        "baseline_overall": round(first_overall, 1),
        "current_overall": round(last_overall, 1),
        "best_overall": round(best_overall, 1),
        "total_improvement": round(total_improvement, 1),
        "trends": trends,
        "version_progression": progression,
    }

    # Save to disk if requested
    if save:
        out = Path(get_output_dir())
        out.mkdir(parents=True, exist_ok=True)
        metrics_path = out / "metrics.json"
        metrics_path.write_text(json.dumps(result, indent=2))
        result["saved_to"] = str(metrics_path)

    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
