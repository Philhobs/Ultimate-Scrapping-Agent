"""SQLModel ORM models for scrape jobs and results."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class ScrapeJob(SQLModel, table=True):
    """A scrape job initiated via the API."""

    __tablename__ = "scrape_jobs"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    prompt: str
    url: str
    output_format: str = "json"
    schema_fields: str | None = None  # JSON-encoded list of field names
    max_tier: int = 3
    status: str = "pending"  # pending, running, completed, failed
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ScrapeResult(SQLModel, table=True):
    """Result of a completed scrape job."""

    __tablename__ = "scrape_results"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    job_id: str = Field(foreign_key="scrape_jobs.id", index=True)
    tier_used: int = 1
    data: str | None = None  # JSON-encoded extracted data
    raw_text: str | None = None  # Agent's full text response
    cost_usd: Optional[float] = None
    error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
