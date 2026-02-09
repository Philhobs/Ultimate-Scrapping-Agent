"""generate_variant MCP tool — create a mutated/improved version of a system prompt."""

from __future__ import annotations

import json
from typing import Any

from claude_agent_sdk import tool

from evolver_agent.analyzers.prompt_evolver import (
    get_strategies, get_strategy, generate_mutation_prompt, suggest_strategies,
)
from evolver_agent.analyzers.evaluator import evaluate_prompt
from evolver_agent.state import get_agent_profile, add_prompt_version


@tool(
    "generate_variant",
    "Create a mutated/improved version of a system prompt using evolution strategies. "
    "Strategies: clarification, restructuring, example_addition, constraint_tightening, "
    "simplification, chain_of_thought, role_enhancement, output_formatting. "
    "Provide 'strategy' (name) and 'new_prompt' (the improved text you generated). "
    "Optional: 'version_id' to mutate a specific version (default: latest).",
    {"strategy": str, "new_prompt": str, "version_id": int},
)
async def generate_variant(args: dict[str, Any]) -> dict[str, Any]:
    strategy_name = args.get("strategy")
    new_prompt = args.get("new_prompt")
    version_id = args.get("version_id")

    if not strategy_name:
        # Return available strategies with recommendations
        try:
            profile = get_agent_profile()
            scores = profile.get("scores", {})
            suggested = suggest_strategies(scores)
            return {"content": [{"type": "text", "text": json.dumps({
                "error": "Provide 'strategy' name.",
                "available_strategies": [s.to_dict() for s in get_strategies()],
                "recommended_for_this_agent": [s.to_dict() for s in suggested],
            }, indent=2)}]}
        except RuntimeError:
            return {"content": [{"type": "text", "text": json.dumps({
                "error": "Provide 'strategy' name.",
                "available_strategies": [s.to_dict() for s in get_strategies()],
            }, indent=2)}]}

    strategy = get_strategy(strategy_name)
    if not strategy:
        return {
            "content": [{"type": "text", "text": f"Unknown strategy: {strategy_name}. "
                         "Use: clarification, restructuring, example_addition, "
                         "constraint_tightening, simplification, chain_of_thought, "
                         "role_enhancement, output_formatting."}],
            "is_error": True,
        }

    # If the agent provides the new prompt directly, store it
    if new_prompt:
        scores = evaluate_prompt(new_prompt)
        vid = add_prompt_version({
            "prompt": new_prompt,
            "scores": scores.to_dict(),
            "label": f"variant_{strategy_name}",
            "source": f"mutation:{strategy_name}",
            "strategy": strategy_name,
        })

        result = {
            "version_id": vid,
            "strategy": strategy_name,
            "scores": scores.to_dict(),
            "prompt_length": len(new_prompt),
            "status": "variant_stored",
        }
        return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}

    # Otherwise, provide mutation instructions for the agent to apply
    try:
        profile = get_agent_profile()
        original_prompt = profile["prompt_content"]
    except RuntimeError:
        return {
            "content": [{"type": "text", "text": "Error: Run analyze_agent first."}],
            "is_error": True,
        }

    if version_id is not None:
        from evolver_agent.state import get_prompt_version
        version = get_prompt_version(version_id)
        if version:
            original_prompt = version["prompt"]

    mutation_instructions = generate_mutation_prompt(original_prompt, strategy_name)

    result = {
        "strategy": strategy.to_dict(),
        "mutation_instructions": mutation_instructions,
        "original_prompt": original_prompt,
        "action_needed": "Apply the mutation instructions to the original prompt and call "
                         "generate_variant again with 'new_prompt' set to your improved version.",
    }

    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
