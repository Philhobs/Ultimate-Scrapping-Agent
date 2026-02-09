"""Pydantic request/response models for the scraper API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


class ScrapeRequest(BaseModel):
    """Request body for POST /scrape."""

    prompt: str = Field(..., description="Natural language scraping instruction")
    url: str = Field(..., description="Target URL to scrape")
    output_format: str = Field("json", description="Desired output format: json, csv, markdown")
    schema_fields: list[str] | None = Field(
        None, description="List of field names to extract"
    )
    max_tier: int = Field(3, ge=1, le=4, description="Maximum scraping tier to use")


class ScrapeResponse(BaseModel):
    """Response body for POST /scrape."""

    session_id: str
    status: str
    tier_used: int | None = None
    data: str | None = None
    messages: list[dict] = Field(default_factory=list)
    cost_usd: float | None = None
    error: str | None = None


class SessionResponse(BaseModel):
    """Response body for GET /sessions/{id}."""

    job_id: str
    prompt: str
    url: str
    status: str
    output_format: str
    schema_fields: str | None = None
    tier_used: int | None = None
    data: str | None = None
    raw_text: str | None = None
    cost_usd: float | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class HealthResponse(BaseModel):
    """Response body for GET /health."""

    status: str = "ok"
    agent: str = "web-scraper"
    version: str = "0.1.0"
