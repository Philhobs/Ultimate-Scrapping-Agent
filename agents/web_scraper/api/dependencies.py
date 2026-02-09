"""FastAPI dependency injectors for the scraper API."""

from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from agents.web_scraper.agent import WebScraperAgent
from common.persistence.database import get_session

# Singleton agent instance
_agent: WebScraperAgent | None = None


def get_agent() -> WebScraperAgent:
    """Get or create the WebScraperAgent singleton."""
    global _agent
    if _agent is None:
        _agent = WebScraperAgent()
    return _agent


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session."""
    async for session in get_session():
        yield session
