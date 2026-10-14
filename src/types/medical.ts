// Types mirroring the FastAPI response models (backend/app/models/report.py).
import type { Language } from '../i18n/types';

export type EvaluationResult = 'Within Range' | 'Below Range' | 'Above Range' | 'Not Evaluated';

export interface ExtractedParameter {
  name: string;
  value: number | null;
  unit: string | null;
  referenceLow: number | null;
  referenceHigh: number | null;
  referenceRaw: string | null;
  rawLine?: string | null;
  evaluation?: EvaluationResult | string | null;
}

export interface HealthResponse {
  status: string;
  service: string;
  aiConfigured: boolean;
  ocrAvailable: boolean;
  knowledgePassages: number;
  retentionHours: number;
}

export interface UploadResponse {
  reportId: string;
  fileName: string;
  status: string;
  message: string;
  accessToken: string;
  retentionHours: number;
}

export interface ReportExtraction {
  reportId: string;
  status: string;
  extractionMethod: 'pymupdf' | 'paddleocr' | string;
  pageCount: number;
  text: string;
  parameters: ExtractedParameter[];
  fileName?: string | null;
  reportDate?: string | null;
  reportDateRaw?: string | null;
  expiresAt?: number | null;
}

export interface SourceCitation {
  id: string;
  text: string;
  sourceId: string;
  title: string;
  publisher: string;
  url: string;
  lastUpdated?: string | null;
  retrieved?: string | null;
  score?: number;
}

export interface Rationale {
  valueConsidered: string;
  rangeUsed: string;
  comparison: string;
  reason: string;
  evidenceIds: string[];
  uncertainty: string[];
}

export interface ParameterExplanation {
  name: string;
  summary: string;
  nextStep?: string | null;
  source: 'ai' | 'fallback';
  evidenceStatus: 'supported' | 'limited' | 'none';
  citations: string[];
  rationale: Rationale;
}

export interface InsightParameter {
  name: string;
  value: number | null;
  unit: string | null;
  evaluation: string | null;
}

export interface RelationshipInsight {
  id: string;
  type: string;
  parameters: InsightParameter[];
  observedPattern: string;
  description: string;
  explanation?: string | null;
  evidence: string[];
  missingRelated: string[];
  caution: string;
}

export interface InsightsResponse {
  reportId: string;
  language: Language;
  relationships: RelationshipInsight[];
  doctorQuestions: string[];
  sources: SourceCitation[];
}

export interface ExplanationResponse {
  reportId: string;
  status: string;
  language: Language;
  source: 'ai' | 'fallback' | 'mixed';
  model?: string | null;
  notice?: string | null;
  generatedAt: number;
  narrativeSummary: string;
  disclaimer: string;
  parameters: ExtractedParameter[];
  explanations: ParameterExplanation[];
  relationships: RelationshipInsight[];
  doctorQuestions: string[];
  doctorQuestionsSource: 'ai' | 'fallback';
  sources: SourceCitation[];
}

export interface ChatTurn {
  role: 'user' | 'assistant';
  content: string;
}

export interface ChatResponse {
  answer: string;
  source: 'ai' | 'fallback' | 'safety';
  notice?: string | null;
  citations: SourceCitation[];
  usedParameters: string[];
  evidenceStatus: 'supported' | 'limited' | 'none';
}

export interface ComparisonRow {
  name: string;
  status: 'compared' | 'incompatible_units' | 'missing_value' | 'only_in_current' | 'only_in_previous';
  previousValue: number | null;
  currentValue: number | null;
  previousUnit: string | null;
  currentUnit: string | null;
  previousEvaluation: string | null;
  currentEvaluation: string | null;
  difference: number | null;
  percentChange: number | null;
  direction: 'increased' | 'decreased' | 'unchanged' | null;
}

export interface ComparisonResponse {
  currentReportId: string;
  previousReportId: string;
  currentDate: string | null;
  previousDate: string | null;
  rows: ComparisonRow[];
  warnings: string[];
}