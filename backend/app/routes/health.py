from fastapi import APIRouter

from app.config import REPORT_RETENTION_HOURS
from app.models.report import HealthCheckResponse
from app.services import llm_client
from app.services.knowledge_base import get_knowledge_base
from app.services.ocr_service import ocr_available

router = APIRouter(prefix="/api", tags=["Health"])


@router.get("/health", response_model=HealthCheckResponse, summary="Check Backend Health")
async def get_health_status() -> HealthCheckResponse:
    """Reports whether the API is online and which optional capabilities are configured (never secrets)."""
    return HealthCheckResponse(
        status="ok",
        service="MedExplain API",
        aiConfigured=llm_client.is_configured(),
        ocrAvailable=ocr_available(),
        knowledgePassages=len(get_knowledge_base().passages),
        retentionHours=REPORT_RETENTION_HOURS,
    )