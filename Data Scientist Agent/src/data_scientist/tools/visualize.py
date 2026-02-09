"""visualize MCP tool — generate charts and plots from data."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from claude_agent_sdk import tool

from data_scientist.state import get_df, get_model, list_dfs, list_models, get_output_dir, store_plot


def _save_fig(fig: plt.Figure, name: str) -> str:
    """Save figure to output directory and return the path."""
    out_dir = Path(get_output_dir())
    out_dir.mkdir(parents=True, exist_ok=True)
    path = str(out_dir / f"{name}.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    store_plot(path)
    return path


@tool(
    "visualize",
    "Generate a plot from a loaded dataset. Provide 'dataset' name and 'plot_type': "
    "'histogram' (distribution of a 'column', optional 'bins'), "
    "'scatter' ('x' and 'y' columns, optional 'hue' for color), "
    "'correlation' (heatmap of numeric correlations), "
    "'bar' ('x' and 'y' columns for bar chart), "
    "'line' ('x' and 'y' columns for line chart), "
    "'box' ('column' or 'y' with optional 'x' grouping), "
    "'violin' ('column' or 'y' with optional 'x' grouping), "
    "'pair_plot' (pairwise scatter of numeric columns, optional 'hue'), "
    "'feature_importance' (bar chart of model feature importances — provide 'model_name'), "
    "'confusion_matrix' (heatmap — provide 'model_name' and 'dataset'), "
    "'residuals' (residual plot — provide 'model_name' and 'dataset'). "
    "Optional 'title' and 'filename' (default auto-generated).",
    {
        "dataset": str,
        "plot_type": str,
        "column": str,
        "x": str,
        "y": str,
        "hue": str,
        "bins": int,
        "title": str,
        "filename": str,
        "model_name": str,
    },
)
async def visualize(args: dict[str, Any]) -> dict[str, Any]:
    plot_type = args.get("plot_type", "histogram")
    title = args.get("title", "")
    filename = args.get("filename", "")

    # Model-based plots
    if plot_type in ("feature_importance", "confusion_matrix", "residuals"):
        return await _model_plot(args)

    dataset_name = args.get("dataset", "")
    df = get_df(dataset_name)
    if df is None:
        available = list(list_dfs().keys())
        return {
            "content": [{"type": "text", "text": f"Error: Dataset '{dataset_name}' not found. Available: {available}"}],
            "is_error": True,
        }

    try:
        if plot_type == "histogram":
            col = args.get("column")
            if not col or col not in df.columns:
                return _col_error(df)
            bins = args.get("bins", 30)
            fig, ax = plt.subplots(figsize=(10, 6))
            df[col].hist(bins=bins, ax=ax, edgecolor="black", alpha=0.7)
            ax.set_title(title or f"Distribution of {col}")
            ax.set_xlabel(col)
            ax.set_ylabel("Count")
            fname = filename or f"hist_{col}"

        elif plot_type == "scatter":
            x, y = args.get("x"), args.get("y")
            if not x or not y or x not in df.columns or y not in df.columns:
                return _col_error(df, "Provide valid 'x' and 'y' columns.")
            fig, ax = plt.subplots(figsize=(10, 6))
            hue = args.get("hue")
            if hue and hue in df.columns:
                for val in df[hue].unique():
                    mask = df[hue] == val
                    ax.scatter(df.loc[mask, x], df.loc[mask, y], label=str(val), alpha=0.6)
                ax.legend(title=hue)
            else:
                ax.scatter(df[x], df[y], alpha=0.6)
            ax.set_title(title or f"{y} vs {x}")
            ax.set_xlabel(x)
            ax.set_ylabel(y)
            fname = filename or f"scatter_{x}_{y}"

        elif plot_type == "correlation":
            numeric_df = df.select_dtypes(include="number")
            if numeric_df.shape[1] < 2:
                return {"content": [{"type": "text", "text": "Need at least 2 numeric columns."}], "is_error": True}
            fig, ax = plt.subplots(figsize=(12, 10))
            sns.heatmap(numeric_df.corr(), annot=True, fmt=".2f", cmap="coolwarm", center=0, ax=ax)
            ax.set_title(title or "Correlation Heatmap")
            fname = filename or "correlation_heatmap"

        elif plot_type == "bar":
            x, y = args.get("x"), args.get("y")
            if not x or x not in df.columns:
                return _col_error(df, "Provide valid 'x' column.")
            fig, ax = plt.subplots(figsize=(10, 6))
            if y and y in df.columns:
                plot_df = df.groupby(x)[y].mean().sort_values(ascending=False).head(20)
                plot_df.plot(kind="bar", ax=ax, edgecolor="black")
                ax.set_ylabel(f"Mean {y}")
            else:
                plot_df = df[x].value_counts().head(20)
                plot_df.plot(kind="bar", ax=ax, edgecolor="black")
                ax.set_ylabel("Count")
            ax.set_title(title or f"Bar: {x}")
            ax.set_xlabel(x)
            plt.xticks(rotation=45, ha="right")
            fname = filename or f"bar_{x}"

        elif plot_type == "line":
            x, y = args.get("x"), args.get("y")
            if not x or not y or x not in df.columns or y not in df.columns:
                return _col_error(df, "Provide valid 'x' and 'y' columns.")
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.plot(df[x], df[y], marker="o", markersize=3, alpha=0.7)
            ax.set_title(title or f"{y} over {x}")
            ax.set_xlabel(x)
            ax.set_ylabel(y)
            fname = filename or f"line_{x}_{y}"

        elif plot_type == "box":
            col = args.get("column") or args.get("y")
            if not col or col not in df.columns:
                return _col_error(df)
            fig, ax = plt.subplots(figsize=(10, 6))
            x = args.get("x")
            if x and x in df.columns:
                df.boxplot(column=col, by=x, ax=ax)
                ax.set_title(title or f"{col} by {x}")
            else:
                df[[col]].boxplot(ax=ax)
                ax.set_title(title or f"Box plot: {col}")
            fname = filename or f"box_{col}"

        elif plot_type == "violin":
            col = args.get("column") or args.get("y")
            if not col or col not in df.columns:
                return _col_error(df)
            fig, ax = plt.subplots(figsize=(10, 6))
            x = args.get("x")
            if x and x in df.columns:
                sns.violinplot(data=df, x=x, y=col, ax=ax)
            else:
                sns.violinplot(data=df, y=col, ax=ax)
            ax.set_title(title or f"Violin: {col}")
            fname = filename or f"violin_{col}"

        elif plot_type == "pair_plot":
            numeric_df = df.select_dtypes(include="number")
            cols = list(numeric_df.columns[:6])  # limit to 6 for readability
            hue = args.get("hue")
            plot_df = df[cols + ([hue] if hue and hue in df.columns else [])]
            g = sns.pairplot(plot_df, hue=hue if hue and hue in df.columns else None, diag_kind="hist")
            g.figure.suptitle(title or "Pair Plot", y=1.02)
            path = _save_fig(g.figure, filename or "pair_plot")
            return {"content": [{"type": "text", "text": json.dumps({"plot": path, "type": "pair_plot"}, indent=2)}]}

        else:
            return {
                "content": [{"type": "text", "text": f"Unknown plot type '{plot_type}'."}],
                "is_error": True,
            }

        path = _save_fig(fig, fname)
        return {"content": [{"type": "text", "text": json.dumps({"plot": path, "type": plot_type}, indent=2)}]}

    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Error creating plot: {e}"}],
            "is_error": True,
        }


def _col_error(df: Any, msg: str = "Provide a valid 'column'.") -> dict[str, Any]:
    return {
        "content": [{"type": "text", "text": f"Error: {msg} Available: {list(df.columns)}"}],
        "is_error": True,
    }


async def _model_plot(args: dict[str, Any]) -> dict[str, Any]:
    """Handle model-based plots."""
    plot_type = args.get("plot_type", "")
    model_name = args.get("model_name", "")
    title = args.get("title", "")
    filename = args.get("filename", "")

    model_entry = get_model(model_name)
    if model_entry is None:
        available = list(list_models().keys())
        return {
            "content": [{"type": "text", "text": f"Error: Model '{model_name}' not found. Available: {available}"}],
            "is_error": True,
        }

    model = model_entry["model"]
    meta = model_entry["metadata"]

    try:
        if plot_type == "feature_importance":
            features = meta.get("features", [])
            if hasattr(model, "feature_importances_"):
                importances = model.feature_importances_
            elif hasattr(model, "coef_"):
                importances = np.abs(model.coef_.flatten() if model.coef_.ndim > 1 else model.coef_)
            else:
                return {"content": [{"type": "text", "text": "Model has no feature importances."}], "is_error": True}

            sorted_idx = np.argsort(importances)[::-1][:20]
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.barh(
                [features[i] for i in sorted_idx][::-1],
                [importances[i] for i in sorted_idx][::-1],
            )
            ax.set_title(title or f"Feature Importance: {model_name}")
            ax.set_xlabel("Importance")
            path = _save_fig(fig, filename or f"importance_{model_name}")

        elif plot_type == "confusion_matrix":
            dataset_name = args.get("dataset", "")
            df = get_df(dataset_name)
            if df is None:
                return {"content": [{"type": "text", "text": "Error: Provide 'dataset'."}], "is_error": True}

            target = meta.get("target", "")
            features = meta.get("features", [])
            X, y = df[features], df[target]
            valid = X.notna().all(axis=1) & y.notna()
            X, y = X[valid], y[valid]
            y_pred = model.predict(X)

            from sklearn.metrics import confusion_matrix as cm_func
            cm = cm_func(y, y_pred)
            fig, ax = plt.subplots(figsize=(8, 6))
            sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", ax=ax)
            ax.set_title(title or f"Confusion Matrix: {model_name}")
            ax.set_xlabel("Predicted")
            ax.set_ylabel("Actual")
            path = _save_fig(fig, filename or f"cm_{model_name}")

        elif plot_type == "residuals":
            dataset_name = args.get("dataset", "")
            df = get_df(dataset_name)
            if df is None:
                return {"content": [{"type": "text", "text": "Error: Provide 'dataset'."}], "is_error": True}

            target = meta.get("target", "")
            features = meta.get("features", [])
            X, y = df[features], df[target]
            valid = X.notna().all(axis=1) & y.notna()
            X, y = X[valid], y[valid]
            y_pred = model.predict(X)
            residuals = y - y_pred

            fig, axes = plt.subplots(1, 2, figsize=(14, 5))
            axes[0].scatter(y_pred, residuals, alpha=0.5)
            axes[0].axhline(y=0, color="r", linestyle="--")
            axes[0].set_title("Residuals vs Predicted")
            axes[0].set_xlabel("Predicted")
            axes[0].set_ylabel("Residuals")

            axes[1].hist(residuals, bins=30, edgecolor="black", alpha=0.7)
            axes[1].set_title("Residual Distribution")
            axes[1].set_xlabel("Residual")
            fig.suptitle(title or f"Residual Analysis: {model_name}")
            path = _save_fig(fig, filename or f"residuals_{model_name}")

        else:
            return {"content": [{"type": "text", "text": f"Unknown model plot type."}], "is_error": True}

        return {"content": [{"type": "text", "text": json.dumps({"plot": path, "type": plot_type}, indent=2)}]}

    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error creating model plot: {e}"}], "is_error": True}
