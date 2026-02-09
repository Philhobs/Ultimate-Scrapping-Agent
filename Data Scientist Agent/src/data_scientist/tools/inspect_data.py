"""inspect_data MCP tool — exploratory data analysis on a loaded dataset."""

from __future__ import annotations

import json
from typing import Any

import numpy as np
import pandas as pd
from claude_agent_sdk import tool

from data_scientist.state import get_df, list_dfs


def _safe_json(obj: Any) -> Any:
    """Make objects JSON-serializable."""
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return round(float(obj), 4)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if pd.isna(obj):
        return None
    return obj


@tool(
    "inspect_data",
    "Explore a loaded dataset. Provide 'name' of the dataset and an 'action': "
    "'summary' (shape, dtypes, memory), 'statistics' (describe for numeric cols), "
    "'missing' (missing value counts and percentages), 'correlations' (numeric correlations), "
    "'value_counts' (value counts for a specific 'column'), 'sample' (first/last N rows), "
    "'dtypes' (detailed column types), 'unique' (unique value counts per column).",
    {"name": str, "action": str, "column": str, "n_rows": int},
)
async def inspect_data(args: dict[str, Any]) -> dict[str, Any]:
    name = args.get("name", "")
    df = get_df(name)
    if df is None:
        available = list(list_dfs().keys())
        return {
            "content": [{"type": "text", "text": f"Error: Dataset '{name}' not found. Available: {available}"}],
            "is_error": True,
        }

    action = args.get("action", "summary")
    n_rows = args.get("n_rows", 10)

    if action == "summary":
        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        categorical_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
        result = {
            "name": name,
            "shape": {"rows": df.shape[0], "columns": df.shape[1]},
            "memory_mb": round(df.memory_usage(deep=True).sum() / 1024 / 1024, 2),
            "numeric_columns": numeric_cols,
            "categorical_columns": categorical_cols,
            "missing_total": int(df.isnull().sum().sum()),
            "duplicate_rows": int(df.duplicated().sum()),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        }

    elif action == "statistics":
        desc = df.describe(include="all").map(_safe_json)
        result = {"statistics": desc.to_dict()}

    elif action == "missing":
        missing = df.isnull().sum()
        pct = (missing / len(df) * 100).round(2)
        result = {
            "total_rows": len(df),
            "columns": {
                col: {"missing": int(missing[col]), "pct": float(pct[col])}
                for col in df.columns if missing[col] > 0
            },
            "total_missing": int(missing.sum()),
        }
        if not result["columns"]:
            result["message"] = "No missing values found."

    elif action == "correlations":
        numeric_df = df.select_dtypes(include="number")
        if numeric_df.empty:
            result = {"message": "No numeric columns for correlation."}
        else:
            corr = numeric_df.corr().map(_safe_json)
            result = {"correlation_matrix": corr.to_dict()}

    elif action == "value_counts":
        column = args.get("column")
        if not column or column not in df.columns:
            return {
                "content": [{"type": "text", "text": f"Error: Provide a valid 'column'. Available: {list(df.columns)}"}],
                "is_error": True,
            }
        vc = df[column].value_counts()
        result = {
            "column": column,
            "unique_values": int(df[column].nunique()),
            "top_values": {str(k): int(v) for k, v in vc.head(20).items()},
        }

    elif action == "sample":
        sample = df.head(n_rows)
        result = {
            "rows": n_rows,
            "data": json.loads(sample.to_json(orient="records", default_handler=str)),
        }

    elif action == "dtypes":
        result = {
            "columns": [
                {
                    "name": col,
                    "dtype": str(df[col].dtype),
                    "non_null": int(df[col].notna().sum()),
                    "null": int(df[col].isna().sum()),
                    "unique": int(df[col].nunique()),
                }
                for col in df.columns
            ]
        }

    elif action == "unique":
        result = {
            "columns": {col: int(df[col].nunique()) for col in df.columns},
        }

    else:
        result = {"error": f"Unknown action '{action}'. Use: summary, statistics, missing, correlations, value_counts, sample, dtypes, unique."}

    return {"content": [{"type": "text", "text": json.dumps(result, indent=2, default=str)}]}
