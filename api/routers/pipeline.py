import asyncio

from fastapi import APIRouter, HTTPException

from api.schemas.jobs import JobResponse, PipelineRunRequest, PipelineRunResponse
from api.services.collection_naming import sector_to_ai_collection
from api.services.job_store import JobStore
from api.services.pipeline_runner import run_pipeline_job


router = APIRouter()


@router.post("/pipeline/run", response_model=PipelineRunResponse)
async def run_pipeline(req: PipelineRunRequest) -> PipelineRunResponse:
    job_store = JobStore()
    params = req.model_dump()
    job_id = job_store.create_job("pipeline", params=params)

    # Fire-and-forget background task inside the running server process.
    asyncio.create_task(
        run_pipeline_job(
            job_store,
            job_id,
            sector=req.sector,
            location=req.location,
            geo_id=req.geo_id,
            limit=req.limit,
            max_pages=req.max_pages,
            llm_batch_size=req.llm_batch_size,
            llm_limit=req.llm_limit,
        )
    )

    return PipelineRunResponse(
        job_id=job_id,
        status_url=f"/jobs/{job_id}",
        results_url=f"/jobs/{job_id}/results",
    )


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str) -> JobResponse:
    job_store = JobStore()
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse(**job)


@router.get("/jobs/{job_id}/results")
async def get_results(job_id: str):
    job_store = JobStore()
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.get("status") != "succeeded":
        raise HTTPException(status_code=409, detail=f"Job not finished (status={job.get('status')})")

    sector = (job.get("params") or {}).get("sector") or ""
    if not sector:
        raise HTTPException(status_code=500, detail="Job params missing sector")

    collection_name = sector_to_ai_collection(sector)
    collection = job_store.db[collection_name]

    total = collection.count_documents({"sector": sector})
    belongs = collection.count_documents({"sector": sector, "belongs_to_sector": True})

    sample = list(
        collection.find(
            {"sector": sector},
            {"_id": 0, "company_name": 1, "belongs_to_sector": 1, "confidence": 1, "reason": 1, "website": 1},
        )
        .sort("confidence", -1)
        .limit(25)
    )

    return {
        "job_id": job_id,
        "sector": sector,
        "collection": collection_name,
        "counts": {"total": total, "belongs_to_sector": belongs, "does_not_belong": total - belongs},
        "top": sample,
    }

