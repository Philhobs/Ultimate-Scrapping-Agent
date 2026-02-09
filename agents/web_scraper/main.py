"""Uvicorn entrypoint for the Web Scraper Agent API."""

from __future__ import annotations

import uvicorn

from agents.web_scraper.api.router import router
from common.api.app_factory import create_app
from common.config_loader import load_config


def create_scraper_app():
    """Create the FastAPI application for the scraper agent."""
    config = load_config("scraper_agent")
    db_url = config.get("persistence", {}).get("db_url", "sqlite+aiosqlite:///data/scraper.db")

    return create_app(
        title="Web Scraper Agent",
        db_url=db_url,
        routers=[router],
    )


app = create_scraper_app()

if __name__ == "__main__":
    config = load_config("scraper_agent")
    api_config = config.get("api", {})

    uvicorn.run(
        "agents.web_scraper.main:app",
        host=api_config.get("host", "0.0.0.0"),
        port=api_config.get("port", 8001),
        reload=True,
    )
