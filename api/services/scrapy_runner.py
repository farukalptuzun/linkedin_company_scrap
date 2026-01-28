from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv

from api.services.job_store import JobStore


def _repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _scrapy_project_dir() -> str:
    return os.path.join(_repo_root(), "company_data_scraper")


async def _read_stream_and_append(job_store: JobStore, job_id: str, stream, is_stderr: bool) -> None:
    while True:
        line = await stream.readline()
        if not line:
            break
        text = line.decode("utf-8", errors="ignore")
        if is_stderr:
            job_store.append_tails(job_id, stderr_append=text)
        else:
            job_store.append_tails(job_id, stdout_append=text)


async def run_sector_scrape(
    job_store: JobStore,
    job_id: str,
    *,
    sector: str,
    limit: int,
    max_pages: int,
    location: Optional[str] = None,
    geo_id: Optional[str] = None,
) -> None:
    job_store.set_status(job_id, status="running", step="scrape", started_at=datetime.utcnow())

    cmd = [
        sys.executable,
        "-m",
        "scrapy",
        "crawl",
        "sector_based_scraper",
        "-a",
        f"sector={sector}",
        "-a",
        f"limit={limit}",
        "-a",
        f"max_pages={max_pages}",
    ]

    if location:
        cmd.extend(["-a", f"location={location}"])
    if geo_id:
        cmd.extend(["-a", f"geo_id={geo_id}"])

    cwd = _scrapy_project_dir()
    if not os.path.isdir(cwd):
        raise RuntimeError(f"Scrapy project directory not found: {cwd}")

    # Load environment variables from .env file (for MONGO_URI, CLAUDE_API_KEY, etc.)
    repo_root = _repo_root()
    env_file = os.path.join(repo_root, ".env")
    if os.path.exists(env_file):
        load_dotenv(env_file)
    
    # Pass environment variables to subprocess
    env = os.environ.copy()

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=cwd,
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    assert proc.stdout is not None
    assert proc.stderr is not None

    stdout_task = asyncio.create_task(_read_stream_and_append(job_store, job_id, proc.stdout, False))
    stderr_task = asyncio.create_task(_read_stream_and_append(job_store, job_id, proc.stderr, True))

    exit_code = await proc.wait()
    await asyncio.gather(stdout_task, stderr_task)

    if exit_code != 0:
        raise RuntimeError(f"Scrapy exited with code {exit_code}")

