"""FastAPI application entry point.

Configures lifespan (startup/shutdown), CORS, exception handlers, and routers.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from google import genai

from src.config.settings import Settings
from src.extraction.claim_extractor import ClaimExtractor
from src.extraction.topic_extractor import TopicExtractor
from src.routers.generate import router as generate_router
from src.routers.health import router as health_router
from src.services.claim_generation import ClaimGenerationService

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: validate config and initialize services."""
    settings = Settings()
    logging.basicConfig(level=settings.log_level)
    logger.info("Starting Claim API on port %d", settings.port)
    logger.info("Gemini model: %s", settings.gemini_model)

    app.state.settings = settings

    if settings.gemini_api_key:
        client = genai.Client(api_key=settings.gemini_api_key)
        app.state.gemini_client = client

        topic_extractor = TopicExtractor(
            client, settings.gemini_model, settings.gemini_temperature
        )
        claim_extractor = ClaimExtractor(
            client, settings.gemini_model, settings.gemini_temperature
        )
        app.state.claim_generation_service = ClaimGenerationService(
            topic_extractor, claim_extractor
        )
    else:
        logger.warning(
            "GEMINI_API_KEY not set -- /generate endpoints will return 503"
        )
        app.state.claim_generation_service = None

    yield

    logger.info("Shutting down Claim API")


app = FastAPI(
    lifespan=lifespan,
    title="Claim Extraction API",
    version="1.0.0",
)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """Serve the Claim Extractor web UI."""
    return templates.TemplateResponse(request=request, name="index.html")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions with a safe error response."""
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred"},
    )


app.include_router(health_router)
app.include_router(generate_router)
