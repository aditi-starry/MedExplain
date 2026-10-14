from typing import List, Literal, Optional

from pydantic import BaseModel, Field

Language = Literal["en", "hi", "mr"]


class HealthCheckResponse(BaseModel):
    status: str = "ok"
    service: str = "MedExplain API"
    aiConfigured: bool = False
    ocrAvailable: bool = False
    knowledgePassages: int = 0
    retentionHours: int = 24


class ReportUploadResponse(BaseModel):
    reportId: str
    fileName: str
    status: str = "uploaded"
    message: str = "Report uploaded successfully."
    # Secret needed for every later request about this report (sent as X-Report-Token)
    accessToken: str
    retentionHours: int


class ErrorResponse(BaseModel):
    detail: str


class ExtractedParameter(BaseModel):
    name: str = Field(..., max_length=120)
    value: Optional[float] = None
    unit: Optional[str] = Field(default=None, max_length=40)
    referenceLow: Optional[float] = None
    referenceHigh: Optional[float] = None
    referenceRaw: Optional[str] = Field(default=None, max_length=200)
    rawLine: Optional[str] = Field(default=None, max_length=500)
    evaluation: Optional[str] = "Not Evaluated"


class ReportExtractionResponse(BaseModel):
    reportId: str
    status: str = "completed"
    extractionMethod: str  # 'pymupdf' or 'paddleocr'
    pageCount: int
    text: str
    parameters: List[ExtractedParameter] = Field(default_factory=list)
    fileName: Optional[str] = None
    reportDate: Optional[str] = None      # ISO date when it could be parsed
    reportDateRaw: Optional[str] = None   # date text exactly as printed
    expiresAt: Optional[float] = None     # unix time when the report will be deleted


class SourceCitation(BaseModel):
    id: str
    text: str
    sourceId: str
    title: str
    publisher: str
    url: str
    lastUpdated: Optional[str] = None
    retrieved: Optional[str] = None
    score: float = 0.0


class Rationale(BaseModel):
    """A short, checkable account of what an explanation is based on (not model chain-of-thought)."""
    valueConsidered: str
    rangeUsed: str
    comparison: str
    reason: str
    evidenceIds: List[str] = Field(default_factory=list)
    uncertainty: List[str] = Field(default_factory=list)


class ParameterExplanation(BaseModel):
    name: str
    summary: str
    nextStep: Optional[str] = None
    source: Literal["ai", "fallback"] = "fallback"
    evidenceStatus: Literal["supported", "limited", "none"] = "none"
    citations: List[str] = Field(default_factory=list)
    rationale: Rationale


class InsightParameter(BaseModel):
    name: str
    value: Optional[float] = None
    unit: Optional[str] = None
    evaluation: Optional[str] = None


class RelationshipInsight(BaseModel):
    id: str
    type: str
    parameters: List[InsightParameter]
    observedPattern: str
    description: str                      # documented relationship (English, from the knowledge graph)
    explanation: Optional[str] = None     # AI explanation in the selected language, when available
    evidence: List[str] = Field(default_factory=list)
    missingRelated: List[str] = Field(default_factory=list)
    caution: str


class InsightsResponse(BaseModel):
    reportId: str
    language: Language
    relationships: List[RelationshipInsight] = Field(default_factory=list)
    doctorQuestions: List[str] = Field(default_factory=list)
    sources: List[SourceCitation] = Field(default_factory=list)


class ExplainRequest(BaseModel):
    language: Language = "en"
    refresh: bool = False


class ReportExplanationResponse(BaseModel):
    reportId: str
    status: str = "completed"
    language: Language = "en"
    source: Literal["ai", "fallback", "mixed"] = "fallback"
    model: Optional[str] = None
    notice: Optional[str] = None
    generatedAt: float = 0.0
    narrativeSummary: str
    disclaimer: str
    parameters: List[ExtractedParameter] = Field(default_factory=list)
    explanations: List[ParameterExplanation] = Field(default_factory=list)
    relationships: List[RelationshipInsight] = Field(default_factory=list)
    doctorQuestions: List[str] = Field(default_factory=list)
    doctorQuestionsSource: Literal["ai", "fallback"] = "fallback"
    sources: List[SourceCitation] = Field(default_factory=list)


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    history: List[ChatMessage] = Field(default_factory=list, max_length=20)
    language: Language = "en"


class ChatResponse(BaseModel):
    answer: str
    source: Literal["ai", "fallback", "safety"]
    notice: Optional[str] = None
    citations: List[SourceCitation] = Field(default_factory=list)
    usedParameters: List[str] = Field(default_factory=list)
    evidenceStatus: Literal["supported", "limited", "none"] = "none"


class ComparisonRequest(BaseModel):
    previousReportId: str = Field(..., max_length=40)
    previousToken: str = Field(..., min_length=10, max_length=200)


class ComparisonRow(BaseModel):
    name: str
    status: Literal["compared", "incompatible_units", "missing_value", "only_in_current", "only_in_previous"]
    previousValue: Optional[float] = None
    currentValue: Optional[float] = None
    previousUnit: Optional[str] = None
    currentUnit: Optional[str] = None
    previousEvaluation: Optional[str] = None
    currentEvaluation: Optional[str] = None
    difference: Optional[float] = None
    percentChange: Optional[float] = None
    direction: Optional[Literal["increased", "decreased", "unchanged"]] = None


class ComparisonResponse(BaseModel):
    currentReportId: str
    previousReportId: str
    currentDate: Optional[str] = None
    previousDate: Optional[str] = None
    rows: List[ComparisonRow] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)