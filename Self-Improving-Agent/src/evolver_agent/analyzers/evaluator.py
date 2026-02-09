"""Evaluator — scoring framework for system prompt quality."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class PromptScore:
    """Evaluation scores for a system prompt."""
    clarity: float        # 0-100: how clear and unambiguous
    completeness: float   # 0-100: covers all necessary instructions
    structure: float      # 0-100: well-organized with headers, lists
    specificity: float    # 0-100: concrete vs vague instructions
    safety: float         # 0-100: guardrails, constraints, boundaries
    efficiency: float     # 0-100: concise without losing info
    overall: float        # weighted average

    def to_dict(self) -> dict:
        return {
            "clarity": round(self.clarity, 1),
            "completeness": round(self.completeness, 1),
            "structure": round(self.structure, 1),
            "specificity": round(self.specificity, 1),
            "safety": round(self.safety, 1),
            "efficiency": round(self.efficiency, 1),
            "overall": round(self.overall, 1),
        }


def evaluate_prompt(prompt: str) -> PromptScore:
    """Evaluate a system prompt across multiple quality dimensions.

    Uses heuristic analysis — the LLM agent can supplement with
    deeper qualitative assessment.
    """
    clarity = _score_clarity(prompt)
    completeness = _score_completeness(prompt)
    structure = _score_structure(prompt)
    specificity = _score_specificity(prompt)
    safety = _score_safety(prompt)
    efficiency = _score_efficiency(prompt)

    # Weighted overall (safety and clarity weighted higher)
    overall = (
        clarity * 0.20
        + completeness * 0.15
        + structure * 0.15
        + specificity * 0.15
        + safety * 0.20
        + efficiency * 0.15
    )

    return PromptScore(
        clarity=clarity,
        completeness=completeness,
        structure=structure,
        specificity=specificity,
        safety=safety,
        efficiency=efficiency,
        overall=overall,
    )


def compare_scores(before: PromptScore, after: PromptScore) -> dict:
    """Compare two prompt scores and determine if improvement occurred."""
    dimensions = ["clarity", "completeness", "structure", "specificity", "safety", "efficiency", "overall"]
    comparison: dict[str, dict] = {}

    improved = 0
    degraded = 0
    unchanged = 0

    for dim in dimensions:
        old_val = getattr(before, dim)
        new_val = getattr(after, dim)
        delta = new_val - old_val

        if abs(delta) < 1.0:
            status = "unchanged"
            unchanged += 1
        elif delta > 0:
            status = "improved"
            improved += 1
        else:
            status = "degraded"
            degraded += 1

        comparison[dim] = {
            "before": round(old_val, 1),
            "after": round(new_val, 1),
            "delta": round(delta, 1),
            "status": status,
        }

    # Safety check: never accept if safety degraded
    safety_degraded = comparison["safety"]["status"] == "degraded"

    verdict = "improved"
    if safety_degraded:
        verdict = "rejected_safety_degraded"
    elif degraded > improved:
        verdict = "degraded"
    elif improved == 0:
        verdict = "no_change"

    return {
        "verdict": verdict,
        "improved_dimensions": improved,
        "degraded_dimensions": degraded,
        "unchanged_dimensions": unchanged,
        "safety_check": "FAIL" if safety_degraded else "PASS",
        "comparison": comparison,
    }


def _score_clarity(prompt: str) -> float:
    """Score how clear and unambiguous the prompt is."""
    score = 50.0  # baseline

    # Positive signals
    if re.search(r"(?:you are|your role|act as)", prompt, re.IGNORECASE):
        score += 10  # clear role definition
    if re.search(r"(?:must|always|never|do not)", prompt, re.IGNORECASE):
        score += 10  # definitive language
    if len(re.findall(r"\*\*[^*]+\*\*", prompt)) >= 3:
        score += 5  # emphasis on key terms

    # Negative signals
    vague_words = len(re.findall(r"\b(?:maybe|perhaps|might|could|try to|consider|generally|usually)\b", prompt, re.IGNORECASE))
    score -= vague_words * 3

    # Sentence clarity (shorter sentences = clearer)
    sentences = re.split(r"[.!?]\s", prompt)
    avg_sentence_len = sum(len(s.split()) for s in sentences) / max(len(sentences), 1)
    if avg_sentence_len < 20:
        score += 10
    elif avg_sentence_len > 35:
        score -= 10

    return max(0, min(100, score))


def _score_completeness(prompt: str) -> float:
    """Score whether the prompt covers all necessary elements."""
    score = 0.0
    elements = [
        (r"(?:you are|role|persona)", 15, "role definition"),
        (r"(?:tool|function|available|capability)", 15, "tool descriptions"),
        (r"(?:workflow|step|process|procedure)", 15, "workflow instructions"),
        (r"(?:constraint|boundary|limit|must not|never)", 15, "constraints"),
        (r"(?:format|output|respond|structure)", 10, "output format"),
        (r"(?:example|e\.g\.|for instance)", 10, "examples"),
        (r"(?:error|fail|invalid|edge case)", 10, "error handling"),
        (r"(?:principle|best practice|guideline)", 10, "principles"),
    ]

    for pattern, points, _ in elements:
        if re.search(pattern, prompt, re.IGNORECASE):
            score += points

    return min(100, score)


def _score_structure(prompt: str) -> float:
    """Score the organizational structure of the prompt."""
    score = 30.0  # baseline

    lines = prompt.split("\n")
    headers = sum(1 for l in lines if l.strip().startswith("#"))
    bullets = sum(1 for l in lines if re.match(r"\s*[-*•]\s", l))
    numbered = sum(1 for l in lines if re.match(r"\s*\d+\.\s", l))

    # Headers
    if headers >= 3:
        score += 20
    elif headers >= 1:
        score += 10

    # Lists (organized content)
    if bullets >= 5:
        score += 15
    elif bullets >= 2:
        score += 8

    if numbered >= 3:
        score += 15
    elif numbered >= 1:
        score += 8

    # Code blocks (if applicable)
    if "```" in prompt:
        score += 5

    # Bold/emphasis
    if len(re.findall(r"\*\*[^*]+\*\*", prompt)) >= 3:
        score += 5

    # Logical grouping (headers followed by content)
    if headers >= 2 and (bullets + numbered) >= 5:
        score += 10

    return max(0, min(100, score))


def _score_specificity(prompt: str) -> float:
    """Score how concrete and specific the instructions are."""
    score = 40.0  # baseline

    # Specific patterns
    specific_patterns = [
        r"(?:always|never|must|exactly|precisely)",
        r"(?:if .+ then|when .+ do)",
        r"(?:\d+ (?:steps?|items?|results?))",
        r"(?:e\.g\.|for example|such as)",
        r"(?:format:|return:|output:)",
    ]
    for pat in specific_patterns:
        if re.search(pat, prompt, re.IGNORECASE):
            score += 8

    # Vague patterns (penalty)
    vague_patterns = [
        r"\b(?:appropriate|suitable|reasonable|proper|good)\b",
        r"\b(?:etc|and so on|and more|stuff|things)\b",
        r"\b(?:try|attempt|consider|think about)\b",
    ]
    for pat in vague_patterns:
        matches = len(re.findall(pat, prompt, re.IGNORECASE))
        score -= matches * 4

    # Named tools/functions (very specific)
    tool_refs = len(re.findall(r"\*\*\w+\*\*\s*[-—]", prompt))
    score += min(tool_refs * 3, 15)

    return max(0, min(100, score))


def _score_safety(prompt: str) -> float:
    """Score safety guardrails and ethical constraints."""
    score = 20.0  # baseline

    safety_patterns = [
        (r"(?:must not|never|do not|don't)\s+(?:generate|create|produce|output)", 15, "negative constraints"),
        (r"(?:safety|secure|ethical|responsible)", 10, "safety mentions"),
        (r"(?:harm|dangerous|malicious|attack)", 10, "threat awareness"),
        (r"(?:validate|sanitize|check|verify)", 10, "input validation"),
        (r"(?:authorized|permission|consent|scope)", 10, "authorization"),
        (r"(?:rollback|revert|backup|undo)", 10, "recovery mechanisms"),
        (r"(?:log|audit|track|monitor)", 5, "auditing"),
        (r"(?:boundary|limit|constraint|guardrail)", 10, "explicit boundaries"),
    ]

    for pattern, points, _ in safety_patterns:
        if re.search(pattern, prompt, re.IGNORECASE):
            score += points

    return max(0, min(100, score))


def _score_efficiency(prompt: str) -> float:
    """Score token efficiency — concise without losing information."""
    total_chars = len(prompt)
    lines = prompt.split("\n")
    non_empty = [l for l in lines if l.strip()]

    # Ideal range: 500-3000 chars for a system prompt
    if 500 <= total_chars <= 3000:
        score = 80.0
    elif 3000 < total_chars <= 5000:
        score = 65.0
    elif total_chars > 5000:
        score = 50.0 - (total_chars - 5000) / 200  # penalty for very long
    else:
        score = 60.0  # too short

    # Repetition penalty
    words = prompt.lower().split()
    if words:
        unique_ratio = len(set(words)) / len(words)
        if unique_ratio < 0.4:
            score -= 20  # very repetitive
        elif unique_ratio > 0.6:
            score += 10  # good vocabulary diversity

    # Empty line ratio (too many = wasted space)
    empty_lines = len(lines) - len(non_empty)
    if len(lines) > 0:
        empty_ratio = empty_lines / len(lines)
        if empty_ratio > 0.4:
            score -= 10

    return max(0, min(100, score))
