"""train_model MCP tool — train ML models with configurable algorithms."""

from __future__ import annotations

import json
from typing import Any

import numpy as np
from claude_agent_sdk import tool

from data_scientist.state import get_df, store_model, list_dfs

ALGORITHMS = {
    "logistic_regression": "sklearn.linear_model.LogisticRegression",
    "linear_regression": "sklearn.linear_model.LinearRegression",
    "random_forest": "sklearn.ensemble.RandomForestClassifier",
    "random_forest_regressor": "sklearn.ensemble.RandomForestRegressor",
    "gradient_boosting": "sklearn.ensemble.GradientBoostingClassifier",
    "gradient_boosting_regressor": "sklearn.ensemble.GradientBoostingRegressor",
    "xgboost": "xgboost.XGBClassifier",
    "xgboost_regressor": "xgboost.XGBRegressor",
    "svm": "sklearn.svm.SVC",
    "svr": "sklearn.svm.SVR",
    "knn": "sklearn.neighbors.KNeighborsClassifier",
    "knn_regressor": "sklearn.neighbors.KNeighborsRegressor",
    "decision_tree": "sklearn.tree.DecisionTreeClassifier",
    "decision_tree_regressor": "sklearn.tree.DecisionTreeRegressor",
    "ridge": "sklearn.linear_model.Ridge",
    "lasso": "sklearn.linear_model.Lasso",
}


def _import_model(algorithm: str, hyperparams: dict[str, Any]) -> Any:
    """Dynamically import and instantiate a model."""
    path = ALGORITHMS.get(algorithm)
    if not path:
        raise ValueError(f"Unknown algorithm '{algorithm}'. Available: {list(ALGORITHMS.keys())}")

    parts = path.rsplit(".", 1)
    module = __import__(parts[0], fromlist=[parts[1]])
    cls = getattr(module, parts[1])
    return cls(**hyperparams)


@tool(
    "train_model",
    "Train an ML model on a loaded dataset. Provide: "
    "'dataset' (name of loaded DataFrame), 'target' (target column name), "
    "'algorithm' (logistic_regression, linear_regression, random_forest, "
    "random_forest_regressor, gradient_boosting, gradient_boosting_regressor, "
    "xgboost, xgboost_regressor, svm, svr, knn, knn_regressor, decision_tree, "
    "decision_tree_regressor, ridge, lasso), "
    "'features' (optional JSON list of columns — uses all non-target if omitted), "
    "'test_size' (default 0.2), 'random_state' (default 42), "
    "'cross_validate' (true/false, default false, uses 5-fold CV), "
    "'hyperparams' (optional JSON object of model hyperparameters), "
    "'model_name' (name to save the trained model under, default: algorithm name).",
    {
        "dataset": str,
        "target": str,
        "algorithm": str,
        "features": str,
        "test_size": float,
        "random_state": int,
        "cross_validate": str,
        "hyperparams": str,
        "model_name": str,
    },
)
async def train_model(args: dict[str, Any]) -> dict[str, Any]:
    from sklearn.model_selection import train_test_split, cross_val_score

    dataset_name = args.get("dataset", "")
    df = get_df(dataset_name)
    if df is None:
        available = list(list_dfs().keys())
        return {
            "content": [{"type": "text", "text": f"Error: Dataset '{dataset_name}' not found. Available: {available}"}],
            "is_error": True,
        }

    target = args.get("target", "")
    if target not in df.columns:
        return {
            "content": [{"type": "text", "text": f"Error: Target '{target}' not in columns: {list(df.columns)}"}],
            "is_error": True,
        }

    algorithm = args.get("algorithm", "random_forest")
    test_size = args.get("test_size", 0.2)
    random_state = args.get("random_state", 42)
    do_cv = args.get("cross_validate", "false").lower() == "true"

    # Parse features
    features_raw = args.get("features")
    if features_raw:
        features = json.loads(features_raw) if isinstance(features_raw, str) else features_raw
    else:
        features = [c for c in df.columns if c != target]

    # Validate features exist
    missing_feats = [f for f in features if f not in df.columns]
    if missing_feats:
        return {
            "content": [{"type": "text", "text": f"Error: Features not found: {missing_feats}"}],
            "is_error": True,
        }

    # Parse hyperparameters
    hyperparams: dict[str, Any] = {}
    hp_raw = args.get("hyperparams")
    if hp_raw:
        try:
            hyperparams = json.loads(hp_raw) if isinstance(hp_raw, str) else hp_raw
        except (json.JSONDecodeError, TypeError):
            pass

    # Add random_state if supported
    if "random_state" not in hyperparams and algorithm not in ("knn", "knn_regressor", "svr"):
        hyperparams["random_state"] = random_state

    # Prepare data
    X = df[features]
    y = df[target]

    # Check for non-numeric features
    non_numeric = X.select_dtypes(exclude="number").columns.tolist()
    if non_numeric:
        return {
            "content": [{
                "type": "text",
                "text": f"Error: Non-numeric features found: {non_numeric}. "
                        "Use clean_data with 'encode' or engineer_features with 'onehot'/'label_encode' first.",
            }],
            "is_error": True,
        }

    # Drop rows with NaN
    valid_mask = X.notna().all(axis=1) & y.notna()
    X = X[valid_mask]
    y = y[valid_mask]
    dropped = int((~valid_mask).sum())

    try:
        model = _import_model(algorithm, hyperparams)
    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Error creating model: {e}"}],
            "is_error": True,
        }

    # Determine task type
    is_classification = algorithm in (
        "logistic_regression", "random_forest", "gradient_boosting",
        "xgboost", "svm", "knn", "decision_tree",
    )

    # Train/test split
    stratify = y if is_classification and y.nunique() <= 50 else None
    try:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=stratify,
        )
    except ValueError:
        # Fallback without stratification
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state,
        )

    # Train
    try:
        model.fit(X_train, y_train)
    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Error training model: {e}"}],
            "is_error": True,
        }

    train_score = round(float(model.score(X_train, y_train)), 4)
    test_score = round(float(model.score(X_test, y_test)), 4)

    # Cross-validation
    cv_scores = None
    if do_cv:
        scoring = "accuracy" if is_classification else "r2"
        cv = cross_val_score(model, X, y, cv=5, scoring=scoring)
        cv_scores = {
            "mean": round(float(cv.mean()), 4),
            "std": round(float(cv.std()), 4),
            "folds": [round(float(s), 4) for s in cv],
        }

    # Save model
    model_name = args.get("model_name", algorithm)
    metadata = {
        "algorithm": algorithm,
        "task_type": "classification" if is_classification else "regression",
        "features": features,
        "target": target,
        "train_score": train_score,
        "test_score": test_score,
        "train_size": len(X_train),
        "test_size": len(X_test),
        "hyperparams": hyperparams,
        "cv_scores": cv_scores,
    }
    store_model(model_name, model, metadata)

    result = {
        "model_name": model_name,
        "algorithm": algorithm,
        "task_type": metadata["task_type"],
        "train_score": train_score,
        "test_score": test_score,
        "train_size": len(X_train),
        "test_size_count": len(X_test),
        "features_used": len(features),
        "rows_dropped_nan": dropped,
    }
    if cv_scores:
        result["cross_validation"] = cv_scores

    overfitting = train_score - test_score
    if overfitting > 0.1:
        result["warning"] = f"Possible overfitting: train-test gap = {overfitting:.4f}"

    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
