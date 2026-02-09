"""analyze_agent MCP tool — introspect an agent's configuration and prompt quality."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from claude_agent_sdk import tool

from evolver_agent.analyzers.evaluator import evaluate_prompt
from evolver_agent.analyzers.prompt_evolver import analyze_prompt_structure, suggest_strategies
from evolver_agent.state import set_agent_profile, add_prompt_version


@tool(
    "analyze_agent",
    "Introspect an agent's system prompt, tools, and configuration. "
    "Scores the prompt on clarity, completeness, structure, specificity, safety, "
    "and efficiency. Provide 'path' to the agent's root directory.",
    {"path": str},
)
async def analyze_agent(args: dict[str, Any]) -> dict[str, Any]:
    path = args.get("path", ".")
    root = Path(path).resolve()

    if not root.is_dir():
        return {
            "content": [{"type": "text", "text": f"Error: Not a directory: {path}"}],
            "is_error": True,
        }

    # Find system_prompt.py
    prompt_file = None
    prompt_content = ""
    for candidate in root.rglob("system_prompt.py"):
        prompt_file = candidate
        break

    if prompt_file:
        raw = prompt_file.read_text(errors="replace")
        # Extract the SYSTEM_PROMPT string
        import re
        match = re.search(r'SYSTEM_PROMPT\s*=\s*(?:"""|\'\'\'|"")(.*?)(?:"""|\'\'\'|"")', raw, re.DOTALL)
        if match:
            prompt_content = match.group(1)
        else:
            prompt_content = raw
    else:
        return {
            "content": [{"type": "text", "text": "Error: No system_prompt.py found in the agent directory."}],
            "is_error": True,
        }

    # Find tools
    tools_dir = None
    tool_files: list[str] = []
    for candidate in root.rglob("tools"):
        if candidate.is_dir():
            tools_dir = candidate
            break

    if tools_dir:
        for tf in tools_dir.glob("*.py"):
            if tf.name != "__init__.py":
                tool_files.append(tf.name.replace(".py", ""))

    # Find other config
    has_cli = any(root.rglob("cli.py"))
    has_agent = any(root.rglob("agent.py"))
    has_state = any(root.rglob("state.py"))

    # Evaluate prompt quality
    scores = evaluate_prompt(prompt_content)

    # Analyze structure
    structure = analyze_prompt_structure(prompt_content)

    # Suggest improvements
    suggested = suggest_strategies(scores.to_dict())

    # Store profile
    profile = {
        "root": str(root),
        "name": root.name,
        "prompt_file": str(prompt_file) if prompt_file else None,
        "prompt_content": prompt_content,
        "prompt_length": len(prompt_content),
        "tools": tool_files,
        "has_cli": has_cli,
        "has_agent": has_agent,
        "has_state": has_state,
        "scores": scores.to_dict(),
        "structure": structure,
    }
    set_agent_profile(profile)

    # Store as version 0 (baseline)
    add_prompt_version({
        "prompt": prompt_content,
        "scores": scores.to_dict(),
        "label": "baseline",
        "source": "original",
    })

    result = {
        "name": root.name,
        "prompt_file": str(prompt_file.relative_to(root)) if prompt_file else None,
        "prompt_length_chars": len(prompt_content),
        "estimated_tokens": structure["estimated_tokens"],
        "tools": tool_files,
        "tool_count": len(tool_files),
        "has_cli": has_cli,
        "has_agent": has_agent,
        "scores": scores.to_dict(),
        "structure_summary": {
            "sections": structure["sections"],
            "headers": structure["headers"],
            "has_role": structure["has_role_definition"],
            "has_constraints": structure["has_constraints"],
            "has_examples": structure["has_examples"],
            "has_workflow": structure["has_workflow"],
        },
        "suggested_strategies": [s.to_dict() for s in suggested],
        "weakest_dimension": min(scores.to_dict().items(), key=lambda x: x[1] if x[0] != "overall" else 999)[0],
    }

    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
