"""YAML + environment variable configuration loader."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

load_dotenv()

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_CONFIG_DIR = _PROJECT_ROOT / "config"


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base."""
    merged = base.copy()
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _apply_env_overrides(config: dict, prefix: str = "AGENT_") -> dict:
    """Overlay environment variables onto config.

    Env vars like AGENT_SCRAPER_MAX_TIER=4 map to config["scraper"]["max_tier"].
    """
    for key, value in os.environ.items():
        if not key.startswith(prefix):
            continue
        parts = key[len(prefix) :].lower().split("_")
        target = config
        for part in parts[:-1]:
            target = target.setdefault(part, {})
        # Attempt numeric conversion
        final_key = parts[-1]
        if value.isdigit():
            target[final_key] = int(value)
        elif value.replace(".", "", 1).isdigit():
            target[final_key] = float(value)
        elif value.lower() in ("true", "false"):
            target[final_key] = value.lower() == "true"
        else:
            target[final_key] = value
    return config


def load_config(agent_name: str, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    """Load agent configuration from YAML with env var overrides.

    Args:
        agent_name: Name of the agent config file (without extension).
        overrides: Optional dict to merge on top of file + env config.
    """
    config_path = _CONFIG_DIR / f"{agent_name}.yaml"
    if config_path.exists():
        with open(config_path) as f:
            config = yaml.safe_load(f) or {}
    else:
        config = {}

    config = _apply_env_overrides(config)

    if overrides:
        config = _deep_merge(config, overrides)

    return config
