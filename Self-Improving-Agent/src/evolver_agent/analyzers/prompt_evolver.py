"""Prompt evolver — mutation strategies for evolving system prompts."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class MutationStrategy:
    """A prompt mutation strategy."""
    name: str
    description: str
    applies_to: str  # "weak_clarity", "weak_structure", etc.
    priority: int     # lower = higher priority

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "applies_to": self.applies_to,
            "priority": self.priority,
        }


# -- Available Mutation Strategies --

STRATEGIES = [
    MutationStrategy(
        "clarification",
        "Replace vague instructions with specific, actionable directives. "
        "Turn 'handle errors well' into 'catch exceptions, log the error, and return a structured error response'.",
        "weak_clarity",
        1,
    ),
    MutationStrategy(
        "restructuring",
        "Reorganize prompt sections for better cognitive flow: "
        "Role → Context → Instructions → Constraints → Output Format. "
        "Group related instructions. Use headers and numbered lists.",
        "weak_structure",
        2,
    ),
    MutationStrategy(
        "example_addition",
        "Add few-shot examples for complex or ambiguous behaviors. "
        "Show the expected input-output format. Use 2-3 diverse examples.",
        "weak_specificity",
        3,
    ),
    MutationStrategy(
        "constraint_tightening",
        "Add explicit boundaries and edge case handling. "
        "Define what the agent should NOT do. Add 'if X then Y' rules for ambiguous situations.",
        "weak_safety",
        1,
    ),
    MutationStrategy(
        "simplification",
        "Remove redundant instructions, compress verbose explanations, "
        "eliminate dead weight. Make every sentence earn its place. "
        "Goal: same capability in fewer tokens.",
        "weak_efficiency",
        4,
    ),
    MutationStrategy(
        "chain_of_thought",
        "Add structured reasoning steps: 'Before taking action, first analyze X, "
        "then consider Y, then decide Z.' Improves complex decision-making.",
        "weak_completeness",
        3,
    ),
    MutationStrategy(
        "role_enhancement",
        "Strengthen the persona and expertise framing. "
        "Make the agent 'own' its role with confidence. "
        "Add domain-specific language and mental models.",
        "weak_clarity",
        5,
    ),
    MutationStrategy(
        "output_formatting",
        "Specify exact output structure: headings, bullet points, code blocks, "
        "tables. Add format templates. Define what the response should look like.",
        "weak_structure",
        4,
    ),
]


def get_strategies() -> list[MutationStrategy]:
    """Return all available mutation strategies."""
    return sorted(STRATEGIES, key=lambda s: s.priority)


def get_strategy(name: str) -> MutationStrategy | None:
    """Get a specific strategy by name."""
    for s in STRATEGIES:
        if s.name == name:
            return s
    return None


def suggest_strategies(scores: dict[str, float]) -> list[MutationStrategy]:
    """Suggest mutation strategies based on evaluation scores.

    Args:
        scores: Dict mapping dimension names to scores (0-100).
                Keys: clarity, completeness, structure, specificity, safety, efficiency

    Returns:
        List of recommended strategies, ordered by priority.
    """
    suggestions: list[MutationStrategy] = []

    # Map weak dimensions to strategies
    dimension_to_weakness = {
        "clarity": "weak_clarity",
        "completeness": "weak_completeness",
        "structure": "weak_structure",
        "specificity": "weak_specificity",
        "safety": "weak_safety",
        "efficiency": "weak_efficiency",
    }

    for dim, score in scores.items():
        if score < 70:  # below threshold
            weakness = dimension_to_weakness.get(dim)
            if weakness:
                for s in STRATEGIES:
                    if s.applies_to == weakness and s not in suggestions:
                        suggestions.append(s)

    return sorted(suggestions, key=lambda s: s.priority)


def analyze_prompt_structure(prompt: str) -> dict:
    """Analyze a system prompt's structural properties."""
    lines = prompt.split("\n")
    non_empty = [l for l in lines if l.strip()]

    # Count structural elements
    headers = sum(1 for l in lines if l.strip().startswith("#"))
    bullet_points = sum(1 for l in lines if l.strip().startswith(("-", "*", "•")))
    numbered_items = sum(1 for l in lines if re.match(r"\s*\d+\.", l))
    code_blocks = prompt.count("```")
    bold_text = len(re.findall(r"\*\*[^*]+\*\*", prompt))

    # Detect sections
    sections: list[str] = []
    for l in lines:
        m = re.match(r"^#+\s+(.+)", l)
        if m:
            sections.append(m.group(1).strip())

    # Detect key prompt elements
    has_role = bool(re.search(r"(?:you are|your role|act as|you're an?)\s", prompt, re.IGNORECASE))
    has_constraints = bool(re.search(r"(?:must not|never|do not|don't|constraint|boundary|limit)", prompt, re.IGNORECASE))
    has_examples = bool(re.search(r"(?:example|for instance|e\.g\.|such as|here's how)", prompt, re.IGNORECASE))
    has_output_format = bool(re.search(r"(?:format|output|respond with|return|structure)", prompt, re.IGNORECASE))
    has_workflow = bool(re.search(r"(?:workflow|step|first|then|finally|process)", prompt, re.IGNORECASE))
    has_tools = bool(re.search(r"(?:tool|function|available|use the)", prompt, re.IGNORECASE))

    # Token estimate (rough: ~4 chars per token)
    estimated_tokens = len(prompt) // 4

    return {
        "total_lines": len(lines),
        "non_empty_lines": len(non_empty),
        "total_chars": len(prompt),
        "estimated_tokens": estimated_tokens,
        "headers": headers,
        "bullet_points": bullet_points,
        "numbered_items": numbered_items,
        "code_blocks": code_blocks // 2,  # pairs
        "bold_emphasis": bold_text,
        "sections": sections,
        "has_role_definition": has_role,
        "has_constraints": has_constraints,
        "has_examples": has_examples,
        "has_output_format": has_output_format,
        "has_workflow": has_workflow,
        "has_tool_descriptions": has_tools,
    }


def generate_mutation_prompt(original: str, strategy_name: str) -> str:
    """Generate instructions for the LLM to apply a mutation strategy.

    The LLM agent will use these instructions to create the variant.
    """
    strategy = get_strategy(strategy_name)
    if not strategy:
        return f"Unknown strategy: {strategy_name}"

    instructions = {
        "clarification": (
            "Rewrite the following system prompt to be more clear and specific:\n"
            "- Replace vague language ('handle well', 'be careful') with concrete instructions\n"
            "- Turn abstract goals into step-by-step actions\n"
            "- Define all ambiguous terms\n"
            "- Keep the same overall purpose and capabilities\n"
        ),
        "restructuring": (
            "Restructure the following system prompt for better organization:\n"
            "- Use this order: Role → Context → Tools → Workflow → Constraints → Output Format\n"
            "- Group related instructions under clear headers\n"
            "- Use numbered lists for sequential steps\n"
            "- Use bullet points for non-sequential items\n"
            "- Keep all original content, just reorganize\n"
        ),
        "example_addition": (
            "Add concrete examples to the following system prompt:\n"
            "- Add 2-3 few-shot examples for the most complex behaviors\n"
            "- Show exact input → output format expected\n"
            "- Include an edge case example\n"
            "- Keep examples concise but illustrative\n"
        ),
        "constraint_tightening": (
            "Add safety constraints and boundaries to the following system prompt:\n"
            "- Add explicit 'DO NOT' rules for dangerous edge cases\n"
            "- Define behavior for ambiguous situations\n"
            "- Add input validation expectations\n"
            "- Ensure error handling instructions exist\n"
            "- NEVER remove existing safety constraints\n"
        ),
        "simplification": (
            "Simplify the following system prompt without losing capability:\n"
            "- Remove redundant instructions (said twice in different ways)\n"
            "- Compress verbose explanations into concise directives\n"
            "- Merge overlapping sections\n"
            "- Target: 20-30% fewer tokens, same functionality\n"
            "- KEEP all safety constraints and tool descriptions\n"
        ),
        "chain_of_thought": (
            "Add reasoning steps to the following system prompt:\n"
            "- Add 'Before X, first consider Y' patterns\n"
            "- Add decision trees for complex choices\n"
            "- Add explicit analysis steps before actions\n"
            "- Keep the overall structure intact\n"
        ),
        "role_enhancement": (
            "Strengthen the persona and expertise in the following system prompt:\n"
            "- Make the role definition more authoritative and domain-expert\n"
            "- Add domain-specific terminology and mental models\n"
            "- Strengthen the agent's confidence in its expertise\n"
            "- Keep existing safety constraints\n"
        ),
        "output_formatting": (
            "Improve output formatting instructions in the following system prompt:\n"
            "- Add specific format templates (markdown structure, tables, etc.)\n"
            "- Define section headers for typical responses\n"
            "- Specify when to use code blocks, tables, lists\n"
            "- Add examples of well-formatted output\n"
        ),
    }

    return instructions.get(strategy_name, f"Apply the '{strategy_name}' strategy to improve the prompt.")
