"""load_data MCP tool — load datasets from file into memory."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
from claude_agent_sdk import tool

from data_scientist.state import store_df, list_dfs


@tool(
    "load_data",
    "Load a dataset from a file into memory. Supports CSV, JSON, Excel (.xlsx), "
    "and Parquet. Provide 'file_path' and an optional 'name' (defaults to filename). "
    "Optional: 'separator' for CSV, 'sheet_name' for Excel, 'sample_rows' to load "
    "only a subset, 'encoding' for character encoding.",
    {
        "file_path": str,
        "name": str,
        "separator": str,
        "sheet_name": str,
        "sample_rows": int,
        "encoding": str,
    },
)
async def load_data(args: dict[str, Any]) -> dict[str, Any]:
    file_path = args["file_path"]
    path = Path(file_path)

    if not path.exists():
        return {
            "content": [{"type": "text", "text": f"Error: File not found: {file_path}"}],
            "is_error": True,
        }

    name = args.get("name") or path.stem
    encoding = args.get("encoding", "utf-8")
    sample_rows = args.get("sample_rows")

    suffix = path.suffix.lower()
    try:
        if suffix == ".csv":
            sep = args.get("separator", ",")
            df = pd.read_csv(path, sep=sep, encoding=encoding)
        elif suffix == ".json":
            df = pd.read_json(path, encoding=encoding)
        elif suffix in (".xlsx", ".xls"):
            sheet = args.get("sheet_name", 0)
            df = pd.read_excel(path, sheet_name=sheet)
        elif suffix == ".parquet":
            df = pd.read_parquet(path)
        elif suffix in (".tsv", ".txt"):
            sep = args.get("separator", "\t")
            df = pd.read_csv(path, sep=sep, encoding=encoding)
        else:
            return {
                "content": [{"type": "text", "text": f"Error: Unsupported format '{suffix}'. Use CSV, JSON, Excel, or Parquet."}],
                "is_error": True,
            }
    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Error loading file: {e}"}],
            "is_error": True,
        }

    if sample_rows and sample_rows < len(df):
        df = df.sample(n=sample_rows, random_state=42).reset_index(drop=True)

    store_df(name, df)

    # Build summary
    info = {
        "name": name,
        "shape": list(df.shape),
        "columns": list(df.columns),
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "memory_mb": round(df.memory_usage(deep=True).sum() / 1024 / 1024, 2),
        "sample": df.head(5).to_dict(orient="records"),
        "loaded_datasets": dict(list_dfs()),
    }

    return {"content": [{"type": "text", "text": json.dumps(info, indent=2, default=str)}]}
