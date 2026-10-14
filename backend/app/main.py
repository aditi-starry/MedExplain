import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import ALLOWED_ORIGIN_REGEX, ALLOWED_ORIGINS, ENVIRONMENT
from app.routes.health import router as health_router
from app.routes.reports import router as reports_router
from app.services.knowledge_base import get_knowledge_base
from app.services.storage import ensure_upload_dir_exists, purge_expired_reports

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
# httpx logs full request URLs at INFO level; keep it quiet
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger("medexplain")

PURGE_INTERVAL_SECONDS = 3600


async def _purge_loop() -> None:
    while True:
        await asyncio.sleep(PURGE_INTERVAL_SECONDS)
        try:
            removed = purge_expired_reports()
            if removed:
                logger.info("Retention policy removed %d expired report files", removed)
        except Exception:
            logger.exception("Retention purge failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_upload_dir_exists()
    purge_expired_reports()
    get_knowledge_base()  # load and validate the knowledge base at startup
    task = asyncio.create_task(_purge_loop())
    yield
    task.cancel()


app = FastAPI(
    title="MedExplain AI API",
    description="Educational laboratory report explanations with evidence-grounded AI. Not a medical device.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=ALLOWED_ORIGIN_REGEX,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Accept", "X-Report-Token"],
    expose_headers=["Content-Disposition"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("X-Frame-Options", "DENY")
    if request.url.path.startswith("/api/reports"):
        response.headers.setdefault("Cache-Control", "no-store")
    return response


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    # Return field locations and messages only (never echo submitted values back)
    errors = [{"loc": list(e.get("loc", [])), "msg": e.get("msg", "")} for e in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": "Invalid request.", "errors": errors})


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    # Never leak stack traces or internal details to clients
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "An unexpected server error occurred."})


@app.get("/", include_in_schema=False)
async def root():
    return {"service": "MedExplain API", "environment": ENVIRONMENT, "docs": "/docs", "health": "/api/health"}


app.include_router(health_router)
app.include_router(reports_router)