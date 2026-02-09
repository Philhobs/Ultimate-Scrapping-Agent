"""report MCP tool — generate a Markdown analysis report."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from claude_agent_sdk import tool

from data_scientist.state import (
    list_dfs, list_models, list_evaluations, list_plots,
    get_df, get_output_dir,
)


@tool(
    "report",
    "Generate a Markdown analysis report. Provide 'dataset' name and optional "
    "'title'. The report includes: data overview, cleaning summary, model results, "
    "visualizations, and a section for your insights. "
    "Provide 'insights' as a text string with your analysis conclusions. "
    "The report is saved to the output directory.",
    {"dataset": str, "title": str, "insights": str, "filename": str},
)
async def report(args: dict[str, Any]) -> dict[str, Any]:
    dataset_name = args.get("dataset", "")
    title = args.get("title", f"Data Analysis Report: {dataset_name}")
    insights = args.get("insights", "")
    out_filename = args.get("filename", "report")

    sections: list[str] = []

    # Header
    sections.append(f"# {title}\n")
    sections.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n")

    # Data Overview
    sections.append("## Data Overview\n")
    all_dfs = list_dfs()
    if all_dfs:
        sections.append("| Dataset | Rows | Columns |")
        sections.append("|---------|------|---------|")
        for name, shape in all_dfs.items():
            sections.append(f"| {name} | {shape[0]:,} | {shape[1]} |")
        sections.append("")

    df = get_df(dataset_name)
    if df is not None:
        sections.append(f"**Primary dataset:** `{dataset_name}` — {df.shape[0]:,} rows, {df.shape[1]} columns\n")
        sections.append("**Column Types:**\n")
        numeric = df.select_dtypes(include="number").columns.tolist()
        categorical = df.select_dtypes(include=["object", "category"]).columns.tolist()
        if numeric:
            sections.append(f"- Numeric ({len(numeric)}): {', '.join(numeric[:10])}")
            if len(numeric) > 10:
                sections.append(f"  ... and {len(numeric) - 10} more")
        if categorical:
            sections.append(f"- Categorical ({len(categorical)}): {', '.join(categorical[:10])}")
        sections.append("")

        # Missing values
        missing = df.isnull().sum()
        total_missing = missing.sum()
        if total_missing > 0:
            sections.append(f"**Missing Values:** {total_missing:,} total\n")
            for col in missing[missing > 0].head(10).index:
                pct = round(missing[col] / len(df) * 100, 1)
                sections.append(f"- `{col}`: {missing[col]:,} ({pct}%)")
            sections.append("")
        else:
            sections.append("**Missing Values:** None\n")

    # Models
    models = list_models()
    if models:
        sections.append("## Model Results\n")
        sections.append("| Model | Algorithm | Train Score | Test Score | CV Mean |")
        sections.append("|-------|-----------|-------------|------------|---------|")
        for name, meta in models.items():
            cv = meta.get("cv_scores", {}).get("mean", "—")
            sections.append(
                f"| {name} | {meta.get('algorithm', '?')} | "
                f"{meta.get('train_score', '?')} | "
                f"{meta.get('test_score', '?')} | "
                f"{cv} |"
            )
        sections.append("")

        # Best model
        best = max(models.items(), key=lambda x: x[1].get("test_score", 0))
        sections.append(f"**Best model:** `{best[0]}` (test score: {best[1].get('test_score', '?')})\n")

    # Evaluations
    evals = list_evaluations()
    if evals:
        sections.append("## Evaluation Details\n")
        for name, keys in evals.items():
            sections.append(f"- **{name}**: {keys}")
        sections.append("")

    # Visualizations
    plots = list_plots()
    if plots:
        sections.append("## Visualizations\n")
        for p in plots:
            fname = Path(p).name
            sections.append(f"![{fname}]({p})\n")

    # Insights
    if insights:
        sections.append("## Key Insights\n")
        sections.append(insights)
        sections.append("")

    # Write report
    report_text = "\n".join(sections)
    out_dir = Path(get_output_dir())
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = str(out_dir / f"{out_filename}.md")
    Path(report_path).write_text(report_text)

    result = {
        "report_path": report_path,
        "sections": ["Data Overview", "Model Results", "Evaluation Details", "Visualizations", "Key Insights"],
        "length_chars": len(report_text),
    }

    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
