from __future__ import annotations

from datetime import datetime
from typing import Optional

from api.services.job_store import JobStore
from api.services.llm_runner import run_llm_filter
from api.services.scrapy_runner import run_sector_scrape


async def run_pipeline_job(
    job_store: JobStore,
    job_id: str,
    *,
    sector: str,
    location: Optional[str],
    geo_id: Optional[str],
    limit: int,
    max_pages: int,
    llm_batch_size: int,
    llm_limit: Optional[int],
) -> None:
    try:
        await run_sector_scrape(
            job_store,
            job_id,
            sector=sector,
            location=location,
            geo_id=geo_id,
            limit=limit,
            max_pages=max_pages,
        )

        await run_llm_filter(
            job_store,
            job_id,
            sector=sector,
            batch_size=llm_batch_size,
            limit=llm_limit,
        )

        job_store.set_status(
            job_id,
            status="succeeded",
            step="done",
            finished_at=datetime.utcnow(),
        )
    except Exception as e:
        job_store.set_status(
            job_id,
            status="failed",
            step="done",
            error=str(e),
            finished_at=datetime.utcnow(),
        )

