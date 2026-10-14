"""
Patient-friendly PDF summary, generated locally with ReportLab (no external service).

English, Hindi and Marathi are supported: Latin text uses Noto Sans and Devanagari
text uses Noto Sans Devanagari, with HarfBuzz text shaping (via uharfbuzz) so that
conjuncts and vowel signs render correctly.
"""
import io
import logging
import re
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.config import FONT_DIR
from app.models.report import ExtractedParameter, ReportExplanationResponse
from app.services.i18n import status_label, t
from app.services.insights import format_value, range_text

logger = logging.getLogger(__name__)

INK = colors.HexColor("#0f172a")
MUTED = colors.HexColor("#475569")
BRAND = colors.HexColor("#0f766e")
LINE = colors.HexColor("#e2e8f0")
SOFT = colors.HexColor("#f1f5f9")
STATUS_COLORS = {
    "Within Range": colors.HexColor("#047857"),
    "Above Range": colors.HexColor("#b45309"),
    "Below Range": colors.HexColor("#1d4ed8"),
    "Not Evaluated": colors.HexColor("#475569"),
}

_DEVANAGARI_RUN = re.compile(r"([\u0900-\u097F\u1CD0-\u1CFF\uA8E0-\uA8FF]+(?:[\s,.;:!?()\-]*[\u0900-\u097F\u1CD0-\u1CFF\uA8E0-\uA8FF]+)*)")
_fonts_registered = False


class PdfGenerationError(Exception):
    pass


def _register_fonts() -> None:
    global _fonts_registered
    if _fonts_registered:
        return
    files = {
        "NotoSans": "NotoSans-Regular.ttf",
        "NotoSans-Bold": "NotoSans-Bold.ttf",
        "NotoDeva": "NotoSansDevanagari-Regular.ttf",
        "NotoDeva-Bold": "NotoSansDevanagari-Bold.ttf",
    }
    for name, filename in files.items():
        pdfmetrics.registerFont(TTFont(name, str(FONT_DIR / filename)))
    pdfmetrics.registerFontFamily("NotoSans", normal="NotoSans", bold="NotoSans-Bold", italic="NotoSans", boldItalic="NotoSans-Bold")
    pdfmetrics.registerFontFamily("NotoDeva", normal="NotoDeva", bold="NotoDeva-Bold", italic="NotoDeva", boldItalic="NotoDeva-Bold")
    _fonts_registered = True


def rich(text: Optional[str]) -> str:
    """Escapes text for Paragraph markup and switches font for Devanagari runs."""
    safe = escape(text or "")
    return _DEVANAGARI_RUN.sub(lambda m: f'<font name="NotoDeva">{m.group(1)}</font>', safe)


def _styles() -> Dict[str, ParagraphStyle]:
    base = dict(fontName="NotoSans", textColor=INK, shaping=1, alignment=TA_LEFT)
    return {
        "brand": ParagraphStyle("brand", fontSize=10, leading=13, textColor=BRAND, **{k: v for k, v in base.items() if k != "textColor"}),
        "title": ParagraphStyle("title", fontSize=20, leading=26, **base),
        "subtitle": ParagraphStyle("subtitle", fontSize=9.5, leading=13, **{**base, "textColor": MUTED}),
        "h2": ParagraphStyle("h2", fontSize=13, leading=18, spaceBefore=10, spaceAfter=4, **{**base, "textColor": BRAND}),
        "body": ParagraphStyle("body", fontSize=9.5, leading=14, **base),
        "small": ParagraphStyle("small", fontSize=8, leading=11, **{**base, "textColor": MUTED}),
        "cell": ParagraphStyle("cell", fontSize=8.5, leading=11.5, **base),
        "cellb": ParagraphStyle("cellb", fontSize=8.5, leading=11.5, **{**base, "fontName": "NotoSans-Bold"}),
    }


def _footer(language: str):
    def draw(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(LINE)
        canvas.line(18 * mm, 14 * mm, A4[0] - 18 * mm, 14 * mm)
        canvas.setFont("NotoSans", 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(18 * mm, 9.5 * mm, "MedExplain AI - educational use only, not a medical diagnosis")
        canvas.drawRightString(A4[0] - 18 * mm, 9.5 * mm, f"{doc.page}")
        canvas.restoreState()
    return draw


def build_summary_pdf(
    record: Dict,
    parameters: List[ExtractedParameter],
    explanation: ReportExplanationResponse,
    language: str,
) -> bytes:
    try:
        _register_fonts()
        s = _styles()
        L = lambda key, **kw: t(language, key, **kw)  # noqa: E731
        extraction = record.get("extraction") or {}
        story = []

        # Header
        story.append(Paragraph("MedExplain AI", s["brand"]))
        story.append(Paragraph(rich(L("pdf.title")), s["title"]))
        story.append(Paragraph(rich(L("pdf.subtitle")), s["subtitle"]))
        story.append(Spacer(1, 6 * mm))

        # Report information (no patient identifiers are included)
        method = extraction.get("extractionMethod", "")
        method_label = "Digital PDF text (PyMuPDF)" if method == "pymupdf" else ("OCR (PaddleOCR)" if method == "paddleocr" else method or "-")
        generated = datetime.fromtimestamp(time.time(), tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        info_rows = [
            [L("pdf.report_id"), record.get("reportId", "-")],
            [L("pdf.file"), record.get("fileName", "-")],
            [L("pdf.report_date"), extraction.get("reportDateRaw") or L("pdf.not_found")],
            [L("pdf.extraction"), method_label],
            [L("pdf.generated"), generated],
        ]
        info = Table(
            [[Paragraph(rich(k), s["cellb"]), Paragraph(rich(v), s["cell"])] for k, v in info_rows],
            colWidths=[45 * mm, 129 * mm],
        )
        info.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), SOFT),
            ("BOX", (0, 0), (-1, -1), 0.5, LINE),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(Paragraph(rich(L("pdf.report_info")), s["h2"]))
        story.append(info)

        # Overview
        story.append(Paragraph(rich(L("pdf.overview")), s["h2"]))
        story.append(Paragraph(rich(explanation.narrativeSummary), s["body"]))

        # Results table
        story.append(Paragraph(rich(L("pdf.results")), s["h2"]))
        header = [Paragraph(rich(L(k)), s["cellb"]) for k in ("pdf.col_test", "pdf.col_value", "pdf.col_range", "pdf.col_status")]
        rows = [header]
        for p in parameters:
            ev = p.evaluation or "Not Evaluated"
            color = STATUS_COLORS.get(ev, MUTED).hexval().replace("0x", "#")
            rows.append([
                Paragraph(rich(p.name), s["cellb"]),
                Paragraph(rich(format_value(p)), s["cell"]),
                Paragraph(rich(range_text(p, language)), s["cell"]),
                Paragraph(f'<font color="{color}">{rich(status_label(language, ev))}</font>', s["cell"]),
            ])
        table = Table(rows, colWidths=[52 * mm, 34 * mm, 52 * mm, 36 * mm], repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), SOFT),
            ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
            ("BOX", (0, 0), (-1, -1), 0.5, LINE),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(table)

        # Explanations, with numbered references into the source list
        source_index = {src.id: i + 1 for i, src in enumerate(explanation.sources)}
        story.append(Paragraph(rich(L("pdf.explanations")), s["h2"]))
        if explanation.explanations:
            note_key = "pdf.explanation_source_ai" if explanation.source in ("ai", "mixed") else "pdf.explanation_source_fallback"
            story.append(Paragraph(rich(L(note_key)), s["small"]))
            story.append(Spacer(1, 2 * mm))
            for exp in explanation.explanations:
                refs = exp.citations or []
                ref_text = " " + "".join(f"[{source_index[r]}]" for r in refs if r in source_index) if refs else ""
                block = [Paragraph(f"<b>{rich(exp.name)}</b>", s["body"]),
                         Paragraph(rich(exp.summary) + ref_text, s["body"])]
                if exp.nextStep:
                    block.append(Paragraph(rich(exp.nextStep), s["small"]))
                block.append(Spacer(1, 2.5 * mm))
                story.append(KeepTogether(block))
        else:
            story.append(Paragraph(rich(L("pdf.no_explanations")), s["body"]))

        # Relationship insights
        for rel in explanation.relationships:
            text = rel.explanation or rel.description
            refs = "".join(f"[{source_index[r]}]" for r in rel.evidence if r in source_index)
            story.append(KeepTogether([
                Paragraph(f"<b>{rich(rel.observedPattern)}</b>", s["body"]),
                Paragraph(rich(text) + (" " + refs if refs else ""), s["body"]),
                Paragraph(rich(rel.caution), s["small"]),
                Spacer(1, 2.5 * mm),
            ]))

        # Questions for a healthcare professional
        story.append(Paragraph(rich(L("pdf.questions")), s["h2"]))
        story.append(Paragraph(rich(L("pdf.questions_note")), s["small"]))
        for i, q in enumerate(explanation.doctorQuestions, start=1):
            story.append(Paragraph(f"{i}. {rich(q)}", s["body"]))

        # Sources
        if explanation.sources:
            story.append(Paragraph(rich(L("pdf.sources")), s["h2"]))
            for i, src in enumerate(explanation.sources, start=1):
                updated = f" (updated {src.lastUpdated})" if src.lastUpdated else ""
                story.append(Paragraph(
                    f'[{i}] {rich(src.title)} - {rich(src.publisher)}{updated}. '
                    f'<link href="{escape(src.url)}" color="#0f766e">{escape(src.url)}</link>',
                    s["small"],
                ))

        # Disclaimer
        story.append(Spacer(1, 4 * mm))
        disclaimer = [Paragraph(f"<b>{rich(L('pdf.disclaimer_title'))}</b>", s["body"]),
                      Paragraph(rich(L("pdf.disclaimer")), s["small"])]
        if L("pdf.translation_note"):
            disclaimer.append(Paragraph(rich(L("pdf.translation_note")), s["small"]))
        box = Table([[disclaimer]], colWidths=[174 * mm])
        box.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fffbeb")),
            ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#f59e0b")),
            ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(KeepTogether([box]))

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=20 * mm,
            title="MedExplain AI - Lab Report Summary", author="MedExplain AI",
        )
        footer = _footer(language)
        doc.build(story, onFirstPage=footer, onLaterPages=footer)
        return buffer.getvalue()
    except Exception as exc:
        logger.exception("PDF generation failed")
        raise PdfGenerationError(str(exc)) from exc