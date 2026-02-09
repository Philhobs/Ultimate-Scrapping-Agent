"""evaluate_model MCP tool — evaluate trained models with comprehensive metrics."""

from __future__ import annotations

import json
from typing import Any

import numpy as np
from claude_agent_sdk import tool

from data_scientist.state import get_df, get_model, list_models, list_dfs, store_evaluation


@tool(
    "evaluate_model",
    "Evaluate a trained model. Provide 'model_name' and 'dataset'. Actions: "
    "'metrics' (full classification or regression metrics), "
    "'confusion_matrix' (classification only), "
    "'feature_importance' (tree-based and linear models), "
    "'predictions' (get predictions on the dataset, optional 'n_rows' to limit), "
    "'compare' (compare all trained models on same dataset). "
    "Optional 'target' and 'features' if different from training.",
    {
        "model_name": str,
        "dataset": str,
        "action": str,
        "target": str,
        "features": str,
        "n_rows": int,
    },
)
async def evaluate_model(args: dict[str, Any]) -> dict[str, Any]:
    action = args.get("action", "metrics")

    # Handle compare action separately
    if action == "compare":
        return await _compare_models(args)

    model_name = args.get("model_name", "")
    model_entry = get_model(model_name)
    if model_entry is None:
        available = list(list_models().keys())
        return {
            "content": [{"type": "text", "text": f"Error: Model '{model_name}' not found. Available: {available}"}],
            "is_error": True,
        }

    model = model_entry["model"]
    meta = model_entry["metadata"]

    dataset_name = args.get("dataset", "")
    df = get_df(dataset_name)
    if df is None:
        available = list(list_dfs().keys())
        return {
            "content": [{"type": "text", "text": f"Error: Dataset '{dataset_name}' not found. Available: {available}"}],
            "is_error": True,
        }

    target = args.get("target") or meta.get("target", "")
    features_raw = args.get("features")
    if features_raw:
        features = json.loads(features_raw) if isinstance(features_raw, str) else features_raw
    else:
        features = meta.get("features", [c for c in df.columns if c != target])

    if target not in df.columns:
        return {
            "content": [{"type": "text", "text": f"Error: Target '{target}' not in columns."}],
            "is_error": True,
        }

    X = df[features]
    y = df[target]
    valid = X.notna().all(axis=1) & y.notna()
    X, y = X[valid], y[valid]

    is_classification = meta.get("task_type") == "classification"

    try:
        y_pred = model.predict(X)
    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Error predicting: {e}"}],
            "is_error": True,
        }

    if action == "metrics":
        if is_classification:
            from sklearn.metrics import (
                accuracy_score, precision_score, recall_score, f1_score,
                classification_report,
            )
            avg = "weighted" if y.nunique() > 2 else "binary"
            result = {
                "model": model_name,
                "task": "classification",
                "accuracy": round(float(accuracy_score(y, y_pred)), 4),
                "precision": round(float(precision_score(y, y_pred, average=avg, zero_division=0)), 4),
                "recall": round(float(recall_score(y, y_pred, average=avg, zero_division=0)), 4),
                "f1": round(float(f1_score(y, y_pred, average=avg, zero_division=0)), 4),
                "classification_report": classification_report(y, y_pred, zero_division=0),
            }
            # ROC AUC for binary
            if y.nunique() == 2 and hasattr(model, "predict_proba"):
                from sklearn.metrics import roc_auc_score
                try:
                    y_proba = model.predict_proba(X)[:, 1]
                    result["roc_auc"] = round(float(roc_auc_score(y, y_proba)), 4)
                except Exception:
                    pass
        else:
            from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
            result = {
                "model": model_name,
                "task": "regression",
                "r2": round(float(r2_score(y, y_pred)), 4),
                "mse": round(float(mean_squared_error(y, y_pred)), 4),
                "rmse": round(float(np.sqrt(mean_squared_error(y, y_pred))), 4),
                "mae": round(float(mean_absolute_error(y, y_pred)), 4),
            }

        store_evaluation(model_name, result)
        return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}

    elif action == "confusion_matrix":
        if not is_classification:
            return {
                "content": [{"type": "text", "text": "Confusion matrix is only for classification models."}],
                "is_error": True,
            }
        from sklearn.metrics import confusion_matrix as cm_func
        cm = cm_func(y, y_pred)
        labels = sorted(y.unique().tolist())
        result = {
            "model": model_name,
            "labels": [str(l) for l in labels],
            "matrix": cm.tolist(),
        }
        return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}

    elif action == "feature_importance":
        importance = None
        if hasattr(model, "feature_importances_"):
            importance = dict(zip(features, [round(float(v), 4) for v in model.feature_importances_]))
        elif hasattr(model, "coef_"):
            coefs = model.coef_.flatten() if model.coef_.ndim > 1 else model.coef_
            importance = dict(zip(features, [round(float(v), 4) for v in coefs]))

        if importance is None:
            return {
                "content": [{"type": "text", "text": "This model does not support feature importance."}],
                "is_error": True,
            }

        sorted_imp = dict(sorted(importance.items(), key=lambda x: abs(x[1]), reverse=True))
        result = {"model": model_name, "feature_importance": sorted_imp}
        return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}

    elif action == "predictions":
        n = args.get("n_rows", 20)
        preds = y_pred[:n].tolist()
        actual = y.iloc[:n].tolist()
        result = {
            "model": model_name,
            "predictions": [
                {"actual": a, "predicted": p}
                for a, p in zip(actual, preds)
            ],
        }
        return {"content": [{"type": "text", "text": json.dumps(result, indent=2, default=str)}]}

    return {
        "content": [{"type": "text", "text": f"Unknown action '{action}'."}],
        "is_error": True,
    }


async def _compare_models(args: dict[str, Any]) -> dict[str, Any]:
    """Compare all trained models."""
    models = list_models()
    if not models:
        return {"content": [{"type": "text", "text": "No trained models to compare."}]}

    comparison = []
    for name, meta in models.items():
        entry = {"model": name, "algorithm": meta.get("algorithm", "?")}
        entry["train_score"] = meta.get("train_score")
        entry["test_score"] = meta.get("test_score")
        if meta.get("cv_scores"):
            entry["cv_mean"] = meta["cv_scores"]["mean"]
            entry["cv_std"] = meta["cv_scores"]["std"]
        comparison.append(entry)

    # Sort by test score
    comparison.sort(key=lambda x: x.get("test_score") or 0, reverse=True)

    result = {
        "total_models": len(comparison),
        "best_model": comparison[0]["model"] if comparison else None,
        "comparison": comparison,
    }
    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
