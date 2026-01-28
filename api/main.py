from fastapi import FastAPI

from api.routers.pipeline import router as pipeline_router


def create_app() -> FastAPI:
    app = FastAPI(title="LinkedIn Scraping Orchestrator", version="0.1.0")
    app.include_router(pipeline_router)
    return app


app = create_app()

