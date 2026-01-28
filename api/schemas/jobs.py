from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field


JobStatus = Literal["queued", "running", "succeeded", "failed", "cancelled"]
JobStep = Literal["scrape", "llm", "done"]


class PipelineRunRequest(BaseModel):
    sector: str = Field(..., min_length=1)
    location: Optional[str] = None
    geo_id: Optional[str] = None

    limit: int = Field(20, ge=1)
    max_pages: int = Field(20, ge=1)

    llm_batch_size: int = Field(15, ge=1, le=50)
    llm_limit: Optional[int] = Field(None, ge=1)


class PipelineRunResponse(BaseModel):
    job_id: str
    status_url: str
    results_url: str


class JobResponse(BaseModel):
    job_id: str
    type: str
    status: JobStatus
    step: JobStep

    params: Dict[str, Any]

    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    stdout_tail: str = ""
    stderr_tail: str = ""
    error: Optional[str] = None

