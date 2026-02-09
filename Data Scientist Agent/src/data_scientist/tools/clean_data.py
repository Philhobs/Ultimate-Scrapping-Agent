"""clean_data MCP tool — data preprocessing and cleaning operations."""

from __future__ import annotations

import json
from typing import Any

import numpy as np
import pandas as pd
from claude_agent_sdk import tool

from data_scientist.state import get_df, store_df, list_dfs


@tool(
    "clean_data",
    "Clean and preprocess a loaded dataset. Provide 'name' of the dataset and an 'action': "
    "'fill_missing' (fill NaN — strategy: mean/median/mode/constant, optional 'column' and 'value'), "
    "'drop_missing' (drop rows/cols with NaN — 'axis': row/column, optional 'threshold' pct), "
    "'remove_outliers' (method: iqr/zscore, optional 'column' or all numeric, 'factor' for IQR multiplier), "
    "'encode' (encode categoricals — method: onehot/label/ordinal, optional 'columns' as JSON list), "
    "'normalize' (method: minmax/standard/robust, optional 'columns' as JSON list), "
    "'drop_duplicates' (remove duplicate rows), "
    "'drop_columns' (drop columns — 'columns' as JSON list), "
    "'rename_columns' (rename — 'mapping' as JSON object), "
    "'cast_types' (cast dtypes — 'mapping' as JSON: {col: type}), "
    "'filter_rows' (keep rows matching 'expression', e.g. \"age > 18\"). "
    "Optional 'save_as' to store result under a new name (default: overwrite).",
    {
        "name": str,
        "action": str,
        "column": str,
        "columns": str,
        "strategy": str,
        "method": str,
        "value": str,
        "axis": str,
        "threshold": float,
        "factor": float,
        "mapping": str,
        "expression": str,
        "save_as": str,
    },
)
async def clean_data(args: dict[str, Any]) -> dict[str, Any]:
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
    before_shape = df.shape

    try:
        if action == "fill_missing":
            strategy = args.get("strategy", "mean")
            col = args.get("column")
            cols = [col] if col else df.columns.tolist()

            for c in cols:
                if c not in df.columns:
                    continue
                if strategy == "mean" and pd.api.types.is_numeric_dtype(df[c]):
                    df[c] = df[c].fillna(df[c].mean())
                elif strategy == "median" and pd.api.types.is_numeric_dtype(df[c]):
                    df[c] = df[c].fillna(df[c].median())
                elif strategy == "mode":
                    mode_val = df[c].mode()
                    if not mode_val.empty:
                        df[c] = df[c].fillna(mode_val.iloc[0])
                elif strategy == "constant":
                    fill_val = args.get("value", "0")
                    if pd.api.types.is_numeric_dtype(df[c]):
                        df[c] = df[c].fillna(float(fill_val))
                    else:
                        df[c] = df[c].fillna(fill_val)
                elif strategy in ("ffill", "bfill"):
                    df[c] = df[c].fillna(method=strategy)

        elif action == "drop_missing":
            axis_str = args.get("axis", "row")
            axis = 0 if axis_str == "row" else 1
            threshold = args.get("threshold")
            if threshold is not None:
                # Keep rows/cols with at least (1 - threshold%) non-null
                thresh_val = int(df.shape[1 - axis] * (1 - threshold / 100))
                df = df.dropna(axis=axis, thresh=thresh_val)
            else:
                df = df.dropna(axis=axis)

        elif action == "remove_outliers":
            method = args.get("method", "iqr")
            factor = args.get("factor", 1.5)
            col = args.get("column")
            numeric_cols = [col] if col else df.select_dtypes(include="number").columns.tolist()

            mask = pd.Series(True, index=df.index)
            for c in numeric_cols:
                if c not in df.columns:
                    continue
                if method == "iqr":
                    q1 = df[c].quantile(0.25)
                    q3 = df[c].quantile(0.75)
                    iqr = q3 - q1
                    mask &= (df[c] >= q1 - factor * iqr) & (df[c] <= q3 + factor * iqr)
                elif method == "zscore":
                    z = (df[c] - df[c].mean()) / df[c].std()
                    mask &= z.abs() <= factor
            df = df[mask].reset_index(drop=True)

        elif action == "encode":
            method = args.get("method", "onehot")
            cols_raw = args.get("columns")
            if cols_raw:
                cols = json.loads(cols_raw) if isinstance(cols_raw, str) else cols_raw
            else:
                cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

            if method == "onehot":
                df = pd.get_dummies(df, columns=cols, drop_first=True, dtype=int)
            elif method == "label":
                from sklearn.preprocessing import LabelEncoder
                for c in cols:
                    if c in df.columns:
                        le = LabelEncoder()
                        df[c] = le.fit_transform(df[c].astype(str))
            elif method == "ordinal":
                from sklearn.preprocessing import OrdinalEncoder
                enc = OrdinalEncoder()
                valid_cols = [c for c in cols if c in df.columns]
                df[valid_cols] = enc.fit_transform(df[valid_cols].astype(str))

        elif action == "normalize":
            method = args.get("method", "standard")
            cols_raw = args.get("columns")
            if cols_raw:
                cols = json.loads(cols_raw) if isinstance(cols_raw, str) else cols_raw
            else:
                cols = df.select_dtypes(include="number").columns.tolist()

            valid_cols = [c for c in cols if c in df.columns]
            if method == "minmax":
                from sklearn.preprocessing import MinMaxScaler
                df[valid_cols] = MinMaxScaler().fit_transform(df[valid_cols])
            elif method == "standard":
                from sklearn.preprocessing import StandardScaler
                df[valid_cols] = StandardScaler().fit_transform(df[valid_cols])
            elif method == "robust":
                from sklearn.preprocessing import RobustScaler
                df[valid_cols] = RobustScaler().fit_transform(df[valid_cols])

        elif action == "drop_duplicates":
            df = df.drop_duplicates().reset_index(drop=True)

        elif action == "drop_columns":
            cols_raw = args.get("columns", "[]")
            cols = json.loads(cols_raw) if isinstance(cols_raw, str) else cols_raw
            df = df.drop(columns=[c for c in cols if c in df.columns])

        elif action == "rename_columns":
            mapping_raw = args.get("mapping", "{}")
            mapping = json.loads(mapping_raw) if isinstance(mapping_raw, str) else mapping_raw
            df = df.rename(columns=mapping)

        elif action == "cast_types":
            mapping_raw = args.get("mapping", "{}")
            mapping = json.loads(mapping_raw) if isinstance(mapping_raw, str) else mapping_raw
            for col, dtype in mapping.items():
                if col in df.columns:
                    df[col] = df[col].astype(dtype)

        elif action == "filter_rows":
            expression = args.get("expression", "")
            if not expression:
                return {
                    "content": [{"type": "text", "text": "Error: 'expression' is required for filter_rows."}],
                    "is_error": True,
                }
            df = df.query(expression).reset_index(drop=True)

        else:
            return {
                "content": [{"type": "text", "text": f"Unknown action '{action}'. See tool description for options."}],
                "is_error": True,
            }

    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Error during '{action}': {e}"}],
            "is_error": True,
        }

    save_as = args.get("save_as", name)
    store_df(save_as, df)

    result = {
        "action": action,
        "before_shape": list(before_shape),
        "after_shape": list(df.shape),
        "saved_as": save_as,
        "missing_remaining": int(df.isnull().sum().sum()),
    }

    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
