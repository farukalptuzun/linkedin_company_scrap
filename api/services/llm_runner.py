from __future__ import annotations

from datetime import datetime
from typing import Optional

import anyio

from api.services.job_store import JobStore
from llm_sector_filter import LLMSectorFilter


async def run_llm_filter(
    job_store: JobStore,
    job_id: str,
    *,
    sector: str,
    batch_size: int = 15,
    limit: Optional[int] = None,
) -> None:
    job_store.set_status(job_id, status="running", step="llm")

    def _run() -> None:
        inst = LLMSectorFilter()
        try:
            inst.filter_by_sector(sector_name=sector, batch_size=batch_size, limit=limit)
        finally:
            inst.close()

    # Run in thread to avoid blocking event loop
    await anyio.to_thread.run_sync(_run)

