"""RFC 7807 problem details schema."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ProblemDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str = "about:blank"
    code: str | None = None
    title: str
    status: int
    detail: str
    instance: str | None = None


__all__ = ["ProblemDetail"]
