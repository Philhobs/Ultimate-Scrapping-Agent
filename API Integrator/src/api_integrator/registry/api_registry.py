"""API Registry — manages registered API endpoints and their configurations."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class Endpoint:
    path: str
    method: str
    description: str
    params: dict[str, str] = field(default_factory=dict)


@dataclass
class APIConfig:
    name: str
    description: str
    base_url: str
    auth_type: str  # "none", "bearer", "api_key", "basic"
    auth_env_var: str | None = None
    default_headers: dict[str, str] = field(default_factory=dict)
    endpoints: dict[str, Endpoint] = field(default_factory=dict)

    def get_auth_header(self) -> dict[str, str]:
        """Build auth header from environment variable."""
        if self.auth_type == "none" or not self.auth_env_var:
            return {}
        token = os.environ.get(self.auth_env_var, "")
        if not token:
            return {}
        if self.auth_type == "bearer":
            return {"Authorization": f"Bearer {token}"}
        if self.auth_type == "api_key":
            return {"X-API-Key": token}
        return {}


class APIRegistry:
    """Stores and retrieves API configurations."""

    def __init__(self) -> None:
        self._apis: dict[str, APIConfig] = {}

    def load_from_yaml(self, path: str | Path) -> None:
        """Load API configurations from a YAML file."""
        data = yaml.safe_load(Path(path).read_text())
        for name, cfg in (data.get("apis") or {}).items():
            endpoints = {}
            for ep_name, ep_data in (cfg.get("endpoints") or {}).items():
                endpoints[ep_name] = Endpoint(
                    path=ep_data["path"],
                    method=ep_data.get("method", "GET"),
                    description=ep_data.get("description", ""),
                    params=ep_data.get("params", {}),
                )
            self._apis[name] = APIConfig(
                name=name,
                description=cfg.get("description", ""),
                base_url=cfg["base_url"],
                auth_type=cfg.get("auth_type", "none"),
                auth_env_var=cfg.get("auth_env_var"),
                default_headers=cfg.get("default_headers", {}),
                endpoints=endpoints,
            )

    def register(
        self,
        name: str,
        base_url: str,
        description: str = "",
        auth_type: str = "none",
        auth_env_var: str | None = None,
    ) -> APIConfig:
        """Register a new API dynamically."""
        api = APIConfig(
            name=name,
            description=description,
            base_url=base_url.rstrip("/"),
            auth_type=auth_type,
            auth_env_var=auth_env_var,
        )
        self._apis[name] = api
        return api

    def get(self, name: str) -> APIConfig | None:
        return self._apis.get(name)

    def list_all(self) -> list[APIConfig]:
        return list(self._apis.values())

    def summary(self) -> list[dict[str, Any]]:
        """Return a summary of all registered APIs for display."""
        result = []
        for api in self._apis.values():
            result.append({
                "name": api.name,
                "description": api.description,
                "base_url": api.base_url,
                "auth_type": api.auth_type,
                "endpoints": [
                    {"name": k, "method": ep.method, "path": ep.path, "description": ep.description}
                    for k, ep in api.endpoints.items()
                ],
            })
        return result
