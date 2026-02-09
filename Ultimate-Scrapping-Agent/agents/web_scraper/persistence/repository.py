"""Scraper-specific database queries."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from agents.web_scraper.persistence.models import ScrapeJob, ScrapeResult


async def create_job(
    session: AsyncSession,
    prompt: str,
    url: str,
    output_format: str = "json",
    schema_fields: str | None = None,
    max_tier: int = 3,
) -> ScrapeJob:
    """Create a new scrape job record."""
    job = ScrapeJob(
        prompt=prompt,
        url=url,
        output_format=output_format,
        schema_fields=schema_fields,
        max_tier=max_tier,
        status="pending",
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job


async def update_job_status(
    session: AsyncSession, job_id: str, status: str
) -> ScrapeJob | None:
    """Update job status."""
    result = await session.exec(select(ScrapeJob).where(ScrapeJob.id == job_id))
    job = result.first()
    if job:
        job.status = status
        job.updated_at = datetime.now(timezone.utc)
        session.add(job)
        await session.commit()
        await session.refresh(job)
    return job


async def save_result(
    session: AsyncSession,
    job_id: str,
    tier_used: int = 1,
    data: str | None = None,
    raw_text: str | None = None,
    cost_usd: float | None = None,
    error: str | None = None,
) -> ScrapeResult:
    """Save a scrape result."""
    result = ScrapeResult(
        job_id=job_id,
        tier_used=tier_used,
        data=data,
        raw_text=raw_text,
        cost_usd=cost_usd,
        error=error,
    )
    session.add(result)
    await session.commit()
    await session.refresh(result)
    return result


async def get_job_with_result(
    session: AsyncSession, job_id: str
) -> tuple[ScrapeJob | None, ScrapeResult | None]:
    """Retrieve a job and its result."""
    job_result = await session.exec(select(ScrapeJob).where(ScrapeJob.id == job_id))
    job = job_result.first()
    if not job:
        return None, None

    result_query = await session.exec(
        select(ScrapeResult).where(ScrapeResult.job_id == job_id)
    )
    result = result_query.first()
    return job, result
