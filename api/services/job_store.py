from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from pymongo import MongoClient

from api.core.config import settings


class JobStore:
    def __init__(
        self,
        mongo_uri: str = settings.mongo_uri,
        mongo_db: str = settings.mongo_db,
        jobs_collection: str = settings.mongo_jobs_collection,
    ) -> None:
        self.client = MongoClient(mongo_uri)
        self.db = self.client[mongo_db]
        self.collection = self.db[jobs_collection]

        # Ensure indexes
        self.collection.create_index("job_id", unique=True)
        self.collection.create_index("status")
        self.collection.create_index("created_at")

    def create_job(self, job_type: str, params: Dict[str, Any]) -> str:
        job_id = str(uuid.uuid4())
        doc = {
            "job_id": job_id,
            "type": job_type,
            "status": "queued",
            "step": "scrape",
            "params": params,
            "created_at": datetime.utcnow(),
            "started_at": None,
            "finished_at": None,
            "stdout_tail": "",
            "stderr_tail": "",
            "error": None,
        }
        self.collection.insert_one(doc)
        return job_id

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self.collection.find_one({"job_id": job_id}, {"_id": 0})

    def set_status(
        self,
        job_id: str,
        *,
        status: str,
        step: Optional[str] = None,
        error: Optional[str] = None,
        stdout_tail: Optional[str] = None,
        stderr_tail: Optional[str] = None,
        started_at: Optional[datetime] = None,
        finished_at: Optional[datetime] = None,
    ) -> None:
        update: Dict[str, Any] = {"status": status}
        if step is not None:
            update["step"] = step
        if error is not None:
            update["error"] = error
        if stdout_tail is not None:
            update["stdout_tail"] = stdout_tail
        if stderr_tail is not None:
            update["stderr_tail"] = stderr_tail
        if started_at is not None:
            update["started_at"] = started_at
        if finished_at is not None:
            update["finished_at"] = finished_at

        self.collection.update_one({"job_id": job_id}, {"$set": update})

    def append_tails(
        self,
        job_id: str,
        *,
        stdout_append: str = "",
        stderr_append: str = "",
        stdout_limit: int = settings.stdout_tail_bytes,
        stderr_limit: int = settings.stderr_tail_bytes,
    ) -> None:
        job = self.get_job(job_id)
        if not job:
            return

        stdout = (job.get("stdout_tail") or "") + (stdout_append or "")
        stderr = (job.get("stderr_tail") or "") + (stderr_append or "")

        if len(stdout.encode("utf-8", errors="ignore")) > stdout_limit:
            # keep last N bytes approximately by trimming chars
            stdout = stdout[-stdout_limit:]
        if len(stderr.encode("utf-8", errors="ignore")) > stderr_limit:
            stderr = stderr[-stderr_limit:]

        self.collection.update_one(
            {"job_id": job_id},
            {"$set": {"stdout_tail": stdout, "stderr_tail": stderr}},
        )

    def close(self) -> None:
        if self.client:
            self.client.close()

