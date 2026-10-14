import os
from pathlib import Path
from dotenv import load_dotenv

# Base backend directory path
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from backend/.env (never committed; see .env.example)
load_dotenv(BASE_DIR / ".env")


def _env_list(name: str, default: str) -> list:
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


# Runtime environment: "development" or "production"
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").strip().lower()

# Gemini API configuration (never exposed to the frontend, never logged)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite").strip()
# Tried in order after GEMINI_MODEL if it fails (e.g. quota or model retired)
GEMINI_FALLBACK_MODELS = _env_list("GEMINI_FALLBACK_MODELS", "gemini-flash-lite-latest")
GEMINI_TIMEOUT_SECONDS = _env_int("GEMINI_TIMEOUT_SECONDS", 40)

# Storage for uploaded reports and their extracted data.
# On hosts with an ephemeral filesystem, data is lost on restart/redeploy.
DATA_DIR = Path(os.getenv("DATA_DIR", str(BASE_DIR / "uploads"))).resolve()
UPLOAD_DIR = DATA_DIR

# Reports (files and extracted data) are deleted automatically after this many hours
REPORT_RETENTION_HOURS = _env_int("REPORT_RETENTION_HOURS", 24)

# Knowledge base (RAG) location
KNOWLEDGE_DIR = Path(os.getenv("KNOWLEDGE_DIR", str(BASE_DIR / "knowledge"))).resolve()

# Fonts used for PDF summaries (Latin + Devanagari)
FONT_DIR = BASE_DIR / "app" / "assets" / "fonts"

# OCR for scanned PDFs/images needs PaddleOCR, which is optional (heavy dependency)
ENABLE_OCR = os.getenv("ENABLE_OCR", "true").strip().lower() in {"1", "true", "yes"}

# CORS configuration: comma-separated list of allowed frontend origins
ALLOWED_ORIGINS = _env_list(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
)
# Optional regex for preview deployments, e.g. https://medexplain-.*\.vercel\.app
ALLOWED_ORIGIN_REGEX = os.getenv("ALLOWED_ORIGIN_REGEX", "").strip() or None

# Simple per-client rate limits (requests per minute)
RATE_LIMIT_UPLOADS_PER_MINUTE = _env_int("RATE_LIMIT_UPLOADS_PER_MINUTE", 10)
RATE_LIMIT_AI_PER_MINUTE = _env_int("RATE_LIMIT_AI_PER_MINUTE", 20)

# File validation rules
MAX_UPLOAD_SIZE_MB = 10
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024  # 10 MB
MAX_PDF_PAGES = 20

ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/jpg",
}

SUPPORTED_LANGUAGES = ("en", "hi", "mr")