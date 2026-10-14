"""
Report API.

Every endpoint except upload requires the report's access token in the
`X-Report-Token` header. Unknown IDs, malformed IDs and wrong tokens all return
the same 404 so the API does not reveal which reports exist.
"""
import logging
import time
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import Response

from app.config import RATE_LIMIT_AI_PER_MINUTE, RATE_LIMIT_UPLOADS_PER_MINUTE, REPORT_RETENTION_HOURS
from app.models.report import (
    ChatRequest,
    ChatResponse,
    ComparisonRequest,
    ComparisonResponse,
    ErrorResponse,
    ExplainRequest,
    ExtractedParameter,
    InsightsResponse,
    Language,
    ReportExplanationResponse,
    ReportExtractionResponse,
    ReportUploadResponse,
)
from app.security import TOKEN_HEADER, client_key, rate_limiter, validate_report_id_or_404
from app.services.chat_service import answer_question
from app.services.comparison import compare_parameters, extract_report_date
from app.services.document_extractor import extract_document_text
from app.services.explanation_service import generate_report_explanations
from app.services.insights import doctor_questions, find_relationships
from app.services.knowledge_base import resolve_sources
from app.services.parameter_extractor import extract_parameters
from app.services.pdf_service import PdfGenerationError, build_summary_pdf
from app.services.storage import (
    delete_report,
    get_authorized_record,
    get_file_by_report_id,
    save_record,
    save_upload_file,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reports", tags=["Reports"])

NOT_FOUND = {404: {"model": ErrorResponse, "description": "Report not found or access token invalid."}}


def authorized_record(report_id: str, x_report_token: Optional[str] = Header(default=None, alias=TOKEN_HEADER)) -> dict:
    validate_report_id_or_404(report_id)
    return get_authorized_record(report_id, x_report_token)


def _ensure_extracted(record: dict) -> dict:
    """Runs text + parameter extraction once and stores the result in the report record."""
    if record.get("extraction"):
        return record
    report_id = record["reportId"]
    stored_file = get_file_by_report_id(report_id)
    if not stored_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")
    try:
        data = extract_document_text(stored_file, report_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")
    except Exception:
        logger.exception("Unexpected extraction error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Document text extraction failed due to an internal server error.")
    text = data.get("text", "")
    parameters = extract_parameters(text)
    report_date, report_date_raw = extract_report_date(text)
    record["extraction"] = {
        "extractionMethod": data["extractionMethod"],
        "pageCount": data["pageCount"],
        "text": text,
        "parameters": [p.model_dump() for p in parameters],
        "reportDate": report_date,
        "reportDateRaw": report_date_raw,
    }
    record["explanations"] = {}
    save_record(record)
    logger.info("Extraction completed: method=%s pages=%s parameters=%d",
                data["extractionMethod"], data["pageCount"], len(parameters))
    return record


def _parameters(record: dict) -> List[ExtractedParameter]:
    return [ExtractedParameter(**p) for p in (record.get("extraction") or {}).get("parameters", [])]


def _extraction_response(record: dict) -> ReportExtractionResponse:
    ex = record["extraction"]
    return ReportExtractionResponse(
        reportId=record["reportId"],
        status="completed",
        extractionMethod=ex["extractionMethod"],
        pageCount=ex["pageCount"],
        text=ex["text"],
        parameters=_parameters(record),
        fileName=record.get("fileName"),
        reportDate=ex.get("reportDate"),
        reportDateRaw=ex.get("reportDateRaw"),
        expiresAt=float(record.get("createdAt", time.time())) + REPORT_RETENTION_HOURS * 3600,
    )


@router.post(
    "/upload",
    response_model=ReportUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload Laboratory Report",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid file format or empty file."},
        413: {"model": ErrorResponse, "description": "File size exceeds maximum allowed limit."},
        429: {"model": ErrorResponse, "description": "Too many uploads."},
    },
)
async def upload_report(request: Request, file: UploadFile = File(...)) -> ReportUploadResponse:
    """Validates and stores a report (PDF, PNG, JPG, JPEG). Returns its ID and a one-time access token."""
    rate_limiter.check(client_key(request, "upload"), RATE_LIMIT_UPLOADS_PER_MINUTE)
    report_id, file_name, _, token = await save_upload_file(file)
    return ReportUploadResponse(
        reportId=report_id,
        fileName=file_name,
        accessToken=token,
        retentionHours=REPORT_RETENTION_HOURS,
    )


@router.post("/{report_id}/extract", response_model=ReportExtractionResponse, summary="Extract Report Data",
             responses={**NOT_FOUND, 400: {"model": ErrorResponse}})
async def extract_report(record: dict = Depends(authorized_record)) -> ReportExtractionResponse:
    """Extracts text (PyMuPDF or OCR), structured parameters and reference-range evaluations."""
    return _extraction_response(_ensure_extracted(record))


@router.get("/{report_id}", response_model=ReportExtractionResponse, summary="Get Extracted Report", responses=NOT_FOUND)
async def get_report(record: dict = Depends(authorized_record)) -> ReportExtractionResponse:
    return _extraction_response(_ensure_extracted(record))


@router.get("/{report_id}/parameters", response_model=List[ExtractedParameter], summary="Get Extracted Parameters",
            responses=NOT_FOUND)
async def get_report_parameters(record: dict = Depends(authorized_record)) -> List[ExtractedParameter]:
    return _parameters(_ensure_extracted(record))


@router.post("/{report_id}/explain", response_model=ReportExplanationResponse,
             summary="Evidence-grounded explanations (Gemini + RAG)", responses=NOT_FOUND)
async def explain_report(
    request: Request,
    body: Optional[ExplainRequest] = None,
    record: dict = Depends(authorized_record),
) -> ReportExplanationResponse:
    """
    Explains the stored results of this report. Values, units, ranges and statuses always
    come from the server-side extraction; they cannot be supplied or altered by the client.
    """
    body = body or ExplainRequest()
    record = _ensure_extracted(record)
    cached = (record.get("explanations") or {}).get(body.language)
    if cached and not body.refresh:
        return ReportExplanationResponse(**cached)
    rate_limiter.check(client_key(request, "ai"), RATE_LIMIT_AI_PER_MINUTE)
    response = await generate_report_explanations(
        record["reportId"], _parameters(record), body.language, record["extraction"]["extractionMethod"],
    )
    # Cache only real AI output so a temporary AI outage can be retried later
    if response.source in ("ai", "mixed"):
        record.setdefault("explanations", {})[body.language] = response.model_dump()
        save_record(record)
    return response


@router.get("/{report_id}/insights", response_model=InsightsResponse, summary="Multi-parameter insights and doctor questions",
            responses=NOT_FOUND)
async def get_insights(language: Language = Query("en"), record: dict = Depends(authorized_record)) -> InsightsResponse:
    record = _ensure_extracted(record)
    params = _parameters(record)
    relationships = find_relationships(params, language)
    return InsightsResponse(
        reportId=record["reportId"],
        language=language,
        relationships=relationships,
        doctorQuestions=doctor_questions(params, relationships, language),
        sources=resolve_sources(e for r in relationships for e in r.evidence),
    )


@router.post("/{report_id}/chat", response_model=ChatResponse, summary="Ask a question about this report",
             responses=NOT_FOUND)
async def chat_about_report(request: Request, body: ChatRequest, record: dict = Depends(authorized_record)) -> ChatResponse:
    rate_limiter.check(client_key(request, "ai"), RATE_LIMIT_AI_PER_MINUTE)
    record = _ensure_extracted(record)
    return await answer_question(body.message, body.history, _parameters(record), body.language)


@router.post("/{report_id}/compare", response_model=ComparisonResponse, summary="Compare with a previous report",
             responses=NOT_FOUND)
async def compare_reports(body: ComparisonRequest, record: dict = Depends(authorized_record)) -> ComparisonResponse:
    """Both reports must be accessible to the caller: the previous report's token is required too."""
    validate_report_id_or_404(body.previousReportId)
    if body.previousReportId == record["reportId"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Choose a different report to compare with.")
    previous = _ensure_extracted(get_authorized_record(body.previousReportId, body.previousToken))
    current = _ensure_extracted(record)
    cur_date = current["extraction"].get("reportDate")
    prev_date = previous["extraction"].get("reportDate")
    warnings = []
    if cur_date and prev_date and prev_date > cur_date:
        warnings.append("The report chosen as 'previous' has a later date than the current report.")
    if not cur_date or not prev_date:
        warnings.append("A report date could not be found in one or both reports, so the order of the reports could not be confirmed.")
    return ComparisonResponse(
        currentReportId=current["reportId"],
        previousReportId=previous["reportId"],
        currentDate=cur_date,
        previousDate=prev_date,
        rows=compare_parameters(_parameters(previous), _parameters(current)),
        warnings=warnings,
    )


@router.get("/{report_id}/summary.pdf", summary="Download a patient-friendly PDF summary",
            responses={**NOT_FOUND, 200: {"content": {"application/pdf": {}}}})
async def download_summary(language: Language = Query("en"), record: dict = Depends(authorized_record)) -> Response:
    record = _ensure_extracted(record)
    params = _parameters(record)
    cached = (record.get("explanations") or {}).get(language)
    if cached:
        explanation = ReportExplanationResponse(**cached)
    else:
        # No AI call here: use deterministic summaries so the download is fast and predictable
        explanation = await generate_report_explanations(
            record["reportId"], params, language, record["extraction"]["extractionMethod"], use_ai=False,
        )
    try:
        pdf = build_summary_pdf(record, params, explanation, language)
    except PdfGenerationError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="The PDF summary could not be generated. Please try again.")
    filename = f"MedExplain_Summary_{record['reportId']}_{language}.pdf"
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"', "Cache-Control": "no-store"})


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a report and its data",
               responses=NOT_FOUND)
async def delete_report_endpoint(record: dict = Depends(authorized_record)) -> Response:
    delete_report(record["reportId"])
    return Response(status_code=status.HTTP_204_NO_CONTENT)