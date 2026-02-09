"""engineer_features MCP tool — create and transform features."""

from __future__ import annotations

import json
from typing import Any

import numpy as np
import pandas as pd
from claude_agent_sdk import tool

from data_scientist.state import get_df, store_df, list_dfs


@tool(
    "engineer_features",
    "Create or transform features in a dataset. Provide 'name' and an 'action': "
    "'expression' (create column from pandas expression, e.g. 'col_a * col_b'), "
    "'polynomial' (polynomial features for given 'columns', 'degree' default 2), "
    "'interaction' (pairwise interactions for given 'columns'), "
    "'binning' (bin a 'column' into 'n_bins' equal-width or 'quantile' bins), "
    "'log' (log1p transform for 'columns'), "
    "'sqrt' (square root transform for 'columns'), "
    "'date_extract' (extract year/month/day/dayofweek/hour from a datetime 'column'), "
    "'onehot' (one-hot encode 'columns'), "
    "'label_encode' (integer encode 'columns'). "
    "Provide 'new_column' name for expression/binning. Optional 'save_as'.",
    {
        "name": str,
        "action": str,
        "column": str,
        "columns": str,
        "new_column": str,
        "expression": str,
        "degree": int,
        "n_bins": int,
        "bin_method": str,
        "save_as": str,
    },
)
async def engineer_features(args: dict[str, Any]) -> dict[str, Any]:
    name = args.get("name", "")
    df = get_df(name)
    if df is None:
        available = list(list_dfs().keys())
        return {
            "content": [{"type": "text", "text": f"Error: Dataset '{name}' not found. Available: {available}"}],
            "is_error": True,
        }

    df = df.copy()
    action = args.get("action", "")
    before_cols = list(df.columns)

    try:
        if action == "expression":
            expr = args.get("expression", "")
            new_col = args.get("new_column", "new_feature")
            if not expr:
                return {
                    "content": [{"type": "text", "text": "Error: 'expression' is required."}],
                    "is_error": True,
                }
            df[new_col] = df.eval(expr)

        elif action == "polynomial":
            cols_raw = args.get("columns", "[]")
            cols = json.loads(cols_raw) if isinstance(cols_raw, str) else cols_raw
            degree = args.get("degree", 2)
            for c in cols:
                if c in df.columns:
                    for d in range(2, degree + 1):
                        df[f"{c}_pow{d}"] = df[c] ** d

        elif action == "interaction":
            cols_raw = args.get("columns", "[]")
            cols = json.loads(cols_raw) if isinstance(cols_raw, str) else cols_raw
            valid = [c for c in cols if c in df.columns]
            for i, c1 in enumerate(valid):
                for c2 in valid[i + 1:]:
                    df[f"{c1}_x_{c2}"] = df[c1] * df[c2]

        elif action == "binning":
            col = args.get("column")
            if not col or col not in df.columns:
                return {
                    "content": [{"type": "text", "text": f"Error: Valid 'column' required. Available: {list(df.columns)}"}],
                    "is_error": True,
                }
            n_bins = args.get("n_bins", 5)
            new_col = args.get("new_column", f"{col}_binned")
            method = args.get("bin_method", "equal_width")
            if method == "quantile":
                df[new_col] = pd.qcut(df[col], q=n_bins, labels=False, duplicates="drop")
            else:
                df[new_col] = pd.cut(df[col], bins=n_bins, labels=False)

        elif action == "log":
            cols_raw = args.get("columns", "[]")
            cols = json.loads(cols_raw) if isinstance(cols_raw, str) else cols_raw
            for c in cols:
                if c in df.columns:
                    df[f"{c}_log"] = np.log1p(df[c])

        elif action == "sqrt":
            cols_raw = args.get("columns", "[]")
            cols = json.loads(cols_raw) if isinstance(cols_raw, str) else cols_raw
            for c in cols:
                if c in df.columns:
                    df[f"{c}_sqrt"] = np.sqrt(df[c].clip(lower=0))

        elif action == "date_extract":
            col = args.get("column")
            if not col or col not in df.columns:
                return {
                    "content": [{"type": "text", "text": "Error: Valid datetime 'column' required."}],
                    "is_error": True,
                }
            dt = pd.to_datetime(df[col], errors="coerce")
            df[f"{col}_year"] = dt.dt.year
            df[f"{col}_month"] = dt.dt.month
            df[f"{col}_day"] = dt.dt.day
            df[f"{col}_dayofweek"] = dt.dt.dayofweek
            if dt.dt.hour.any():
                df[f"{col}_hour"] = dt.dt.hour

        elif action == "onehot":
            cols_raw = args.get("columns", "[]")
            cols = json.loads(cols_raw) if isinstance(cols_raw, str) else cols_raw
            valid = [c for c in cols if c in df.columns]
            df = pd.get_dummies(df, columns=valid, drop_first=True, dtype=int)

        elif action == "label_encode":
            cols_raw = args.get("columns", "[]")
            cols = json.loads(cols_raw) if isinstance(cols_raw, str) else cols_raw
            from sklearn.preprocessing import LabelEncoder
            for c in cols:
                if c in df.columns:
                    le = LabelEncoder()
                    df[c] = le.fit_transform(df[c].astype(str))

        else:
            return {
                "content": [{"type": "text", "text": f"Unknown action '{action}'. See tool description."}],
                "is_error": True,
            }

    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Error during '{action}': {e}"}],
            "is_error": True,
        }

    save_as = args.get("save_as", name)
    store_df(save_as, df)

    new_cols = [c for c in df.columns if c not in before_cols]
    result = {
        "action": action,
        "new_columns": new_cols,
        "total_columns": len(df.columns),
        "shape": list(df.shape),
        "saved_as": save_as,
    }

    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
