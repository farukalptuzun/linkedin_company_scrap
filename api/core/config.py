import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    mongo_uri: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    mongo_db: str = os.getenv("MONGO_DB", "leads_db")
    mongo_jobs_collection: str = os.getenv("MONGO_JOBS_COLLECTION", "jobs")

    # Tail storage limits (bytes)
    stdout_tail_bytes: int = int(os.getenv("JOB_STDOUT_TAIL_BYTES", "16384"))
    stderr_tail_bytes: int = int(os.getenv("JOB_STDERR_TAIL_BYTES", "16384"))


settings = Settings()

