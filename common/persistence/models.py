"""SQLModel base classes shared across agents."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


class TimestampMixin(SQLModel):
    """Mixin providing created_at / updated_at timestamps."""

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
