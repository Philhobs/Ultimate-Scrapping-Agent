"""API routes for the Web Scraper Agent."""

from __future__ import annotations

import json

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from agents.web_scraper.agent import WebScraperAgent
from agents.web_scraper.api.dependencies import get_agent, get_db
from agents.web_scraper.api.schemas import (
    HealthResponse,
    ScrapeRequest,
    ScrapeResponse,
    SessionResponse,
)
from agents.web_scraper.persistence.repository import (
    create_job,
    get_job_with_result,
    save_result,
    update_job_status,
)
from agents.web_scraper.tools.fetch_url import reset_tier_manager

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/scraper", tags=["scraper"])


@router.post("/scrape", response_model=ScrapeResponse)
async def scrape(
    request: ScrapeRequest,
    agent: WebScraperAgent = Depends(get_agent),
    session: AsyncSession = Depends(get_db),
) -> ScrapeResponse:
    """Run the scraper agent with the given prompt and URL."""
    schema_fields_json = json.dumps(request.schema_fields) if request.schema_fields else None

    # Create job record
    job = await create_job(
        session,
        prompt=request.prompt,
        url=request.url,
        output_format=request.output_format,
        schema_fields=schema_fields_json,
        max_tier=request.max_tier,
    )

    await update_job_status(session, job.id, "running")

    # Reset tier state for fresh scrape
    reset_tier_manager()

    # Build the full prompt for the agent
    parts = [request.prompt, f"\nTarget URL: {request.url}"]
    if request.schema_fields:
        parts.append(f"Schema fields to extract: {request.schema_fields}")
    parts.append(f"Output format: {request.output_format}")
    parts.append(f"Maximum tier: {request.max_tier}")
    full_prompt = "\n".join(parts)

    try:
        logger.info("scraper.run.start", job_id=job.id, url=request.url)
        result = await agent.run(full_prompt)

        # Determine tier used from tool calls
        tier_used = 1
        for tc in result.tool_calls:
            if tc.get("tool") == "mcp__scraper_agent__fetch_url":
                try:
                    output = json.loads(tc.get("input", {}).get("url", ""))
                except (json.JSONDecodeError, AttributeError):
                    pass

        # Check tool call results for tier info
        for msg in result.messages:
            if isinstance(msg.get("text"), str) and '"tier_used"' in msg["text"]:
                try:
                    parsed = json.loads(msg["text"])
                    tier_used = parsed.get("tier_used", tier_used)
                except json.JSONDecodeError:
                    pass

        await save_result(
            session,
            job_id=job.id,
            tier_used=tier_used,
            data=result.text,
            raw_text=result.text,
            cost_usd=result.cost_usd,
        )
        await update_job_status(session, job.id, "completed")

        logger.info("scraper.run.completed", job_id=job.id)

        return ScrapeResponse(
            session_id=job.id,
            status="completed",
            tier_used=tier_used,
            data=result.text,
            messages=result.messages,
            cost_usd=result.cost_usd,
        )

    except Exception as exc:
        logger.error("scraper.run.failed", job_id=job.id, error=str(exc))
        await save_result(session, job_id=job.id, error=str(exc))
        await update_job_status(session, job.id, "failed")

        return ScrapeResponse(
            session_id=job.id,
            status="failed",
            error=str(exc),
        )


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session_details(
    session_id: str,
    session: AsyncSession = Depends(get_db),
) -> SessionResponse:
    """Retrieve past scrape results by session ID."""
    job, result = await get_job_with_result(session, session_id)
    if not job:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionResponse(
        job_id=job.id,
        prompt=job.prompt,
        url=job.url,
        status=job.status,
        output_format=job.output_format,
        schema_fields=job.schema_fields,
        tier_used=result.tier_used if result else None,
        data=result.data if result else None,
        raw_text=result.raw_text if result else None,
        cost_usd=result.cost_usd if result else None,
        error=result.error if result else None,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse()
