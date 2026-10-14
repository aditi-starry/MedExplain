import type { ExplanationResponse, ExtractedParameter, InsightsResponse, ReportExtraction } from '../types/medical';

export const REPORT_ID = 'rep_0123456789abcdef01234567';
export const TOKEN = 'test-token-value-123456';

export const PARAMS: ExtractedParameter[] = [
  { name: 'Hemoglobin', value: 11.2, unit: 'g/dL', referenceLow: 12, referenceHigh: 15.5, referenceRaw: '12.0 - 15.5 g/dL', evaluation: 'Below Range' },
  { name: 'Ferritin', value: 9, unit: 'ng/mL', referenceLow: 13, referenceHigh: 150, referenceRaw: '13 - 150 ng/mL', evaluation: 'Below Range' },
  { name: 'TSH', value: 2.1, unit: 'uIU/mL', referenceLow: 0.4, referenceHigh: 4, referenceRaw: '0.4 - 4.0 uIU/mL', evaluation: 'Within Range' },
];

export const EXTRACTION: ReportExtraction = {
  reportId: REPORT_ID,
  status: 'completed',
  extractionMethod: 'pymupdf',
  pageCount: 1,
  text: 'fictional',
  parameters: PARAMS,
  fileName: 'Fictional_Sample_Lab_Report.pdf',
  reportDate: '2026-10-08',
  reportDateRaw: '08/10/2026',
};

const SOURCE = {
  id: 'mlp-hemoglobin-2',
  text: 'Low hemoglobin can be seen with different types of anemia.',
  sourceId: 'mlp-hemoglobin',
  title: 'Hemoglobin Test',
  publisher: 'MedlinePlus, U.S. National Library of Medicine',
  url: 'https://medlineplus.gov/lab-tests/hemoglobin-test/',
  lastUpdated: '2024-10-27',
};

export function explanation(language: 'en' | 'hi' | 'mr' = 'en', source: 'ai' | 'fallback' = 'ai'): ExplanationResponse {
  return {
    reportId: REPORT_ID,
    status: 'completed',
    language,
    source,
    model: source === 'ai' ? 'gemini-test' : null,
    notice: source === 'fallback' ? 'The AI service could not be reached.' : null,
    generatedAt: 0,
    narrativeSummary: language === 'hi' ? 'इस रिपोर्ट में दो परिणाम सीमा से कम हैं।' : 'Two results on this report are below the printed range.',
    disclaimer: 'Educational only.',
    parameters: PARAMS,
    explanations: [
      {
        name: 'Hemoglobin',
        summary: 'Your Hemoglobin of 11.2 g/dL is below the report range of 12.0 - 15.5 g/dL.',
        nextStep: 'Discuss this result with a healthcare professional.',
        source,
        evidenceStatus: source === 'ai' ? 'supported' : 'limited',
        citations: source === 'ai' ? ['mlp-hemoglobin-2'] : [],
        rationale: {
          valueConsidered: 'Hemoglobin: 11.2 g/dL',
          rangeUsed: '12.0 - 15.5 g/dL',
          comparison: '11.2 < 12',
          reason: 'The value is lower than the limit stated in the report.',
          evidenceIds: ['mlp-hemoglobin-2'],
          uncertainty: ['Reference ranges differ between laboratories.'],
        },
      },
    ],
    relationships: [],
    doctorQuestions: ['Should my Hemoglobin be re-checked?'],
    doctorQuestionsSource: source,
    sources: [SOURCE],
  };
}

export const INSIGHTS: InsightsResponse = {
  reportId: REPORT_ID,
  language: 'en',
  relationships: [
    {
      id: 'rel-iron',
      type: 'required_for',
      parameters: [
        { name: 'Ferritin', value: 9, unit: 'ng/mL', evaluation: 'Below Range' },
        { name: 'Hemoglobin', value: 11.2, unit: 'g/dL', evaluation: 'Below Range' },
      ],
      observedPattern: 'Ferritin is below range; Hemoglobin is below range',
      description: 'Iron is needed to make hemoglobin.',
      evidence: ['mlp-hemoglobin-2'],
      missingRelated: ['Serum Iron'],
      caution: 'This is an observed pattern in your report, not a diagnosis.',
    },
  ],
  doctorQuestions: ['My Ferritin was 9 ng/mL. What could this mean for me?'],
  sources: [SOURCE],
};