"""
Report Export Service

Generates PDF and DOCX exports from HTML report content with OppGrid branding.
"""

import html
import io
import re
from datetime import datetime
from typing import Optional

from bs4 import BeautifulSoup
from xhtml2pdf import pisa
from docx import Document
from docx.shared import Inches, Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT


# OppGrid brand colors
BRAND_PURPLE = "#7c3aed"
BRAND_PURPLE_RGB = RGBColor(0x7C, 0x3A, 0xED)
BRAND_DARK = "#1e293b"
BRAND_DARK_RGB = RGBColor(0x1E, 0x29, 0x3B)
BRAND_GRAY = "#475569"
BRAND_GRAY_RGB = RGBColor(0x47, 0x55, 0x69)


def _branded_html_wrapper(content: str, title: str, report_type: str, generated_at: str) -> str:
    """Wrap report HTML content with OppGrid-branded PDF template."""
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  @page {{
    size: letter;
    margin: 0.75in;
    @frame footer {{
      -pdf-frame-content: page-footer;
      bottom: 0.3in;
      margin-left: 0.75in;
      margin-right: 0.75in;
      height: 0.4in;
    }}
  }}
  body {{
    font-family: Helvetica, Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.6;
    color: #374151;
  }}
  .cover-header {{
    background-color: {BRAND_PURPLE};
    color: white;
    padding: 24px 32px;
    margin: -0.75in -0.75in 32px -0.75in;
  }}
  .cover-header h1 {{
    font-size: 28pt;
    margin: 0 0 4px 0;
    color: white;
  }}
  .cover-header .subtitle {{
    font-size: 11pt;
    color: rgba(255,255,255,0.85);
    margin: 0;
  }}
  .cover-header .meta {{
    font-size: 9pt;
    color: rgba(255,255,255,0.7);
    margin-top: 12px;
  }}
  h1 {{
    font-size: 18pt;
    color: {BRAND_DARK};
    border-bottom: 2px solid {BRAND_PURPLE};
    padding-bottom: 6px;
    margin-top: 28px;
  }}
  h2 {{
    font-size: 14pt;
    color: {BRAND_PURPLE};
    margin-top: 22px;
  }}
  h3 {{
    font-size: 12pt;
    color: {BRAND_DARK};
    margin-top: 16px;
  }}
  p {{ margin: 8px 0; }}
  ul, ol {{ margin: 8px 0; padding-left: 24px; }}
  li {{ margin-bottom: 4px; }}
  table {{
    width: 100%;
    border-collapse: collapse;
    margin: 12px 0;
  }}
  th, td {{
    border: 1px solid #d1d5db;
    padding: 6px 10px;
    text-align: left;
    font-size: 10pt;
  }}
  th {{
    background-color: #f3f4f6;
    font-weight: bold;
    color: {BRAND_DARK};
  }}
  .section {{
    page-break-inside: avoid;
  }}
</style>
</head>
<body>
  <div class="cover-header">
    <h1>OppGrid</h1>
    <p class="subtitle">{title}</p>
    <p class="meta">{report_type} &bull; Generated {generated_at}</p>
  </div>

  {content}

  <div id="page-footer" style="text-align: center; font-size: 8pt; color: #9ca3af;">
    OppGrid &mdash; AI-Powered Opportunity Intelligence &bull; oppgrid.com
  </div>
</body>
</html>"""


_HTML_TAG_RE = re.compile(r"<[a-zA-Z][^>]*>|</[a-zA-Z]+>", re.DOTALL)
_BORDER_ONLY_RE = re.compile(r"^[\s═─━╔╗╚╝║╠╣╦╩╪╫▀▄█▌▐░▒▓\-=_~*+|]+$")


def _ensure_html(content: str) -> str:
    """Convert plain-text report content to basic HTML if needed.

    Older reports stored in the database may contain plain ASCII text with
    box-drawing characters (═══, ───) rather than HTML.  xhtml2pdf cannot
    parse those characters cleanly, so we detect plain-text content and
    convert it before handing it to the PDF/DOCX generators.

    Detection uses a tag regex (not a bare `<` check) so angle brackets in
    plain text such as "<5%" or "&lt;10k" are not misidentified as HTML.
    Content that passes the regex is returned unchanged.

    Plain-text lines are HTML-escaped before wrapping so that any stray `<`,
    `>`, or `&` characters do not produce malformed markup.
    """
    if _HTML_TAG_RE.search(content):
        return content

    html_parts: list[str] = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if _BORDER_ONLY_RE.match(stripped):
            continue
        html_parts.append(f"<p>{html.escape(stripped)}</p>")
    return "\n".join(html_parts)


def generate_pdf(
    html_content: str,
    title: str = "OppGrid Report",
    report_type: str = "Report",
    generated_at: Optional[str] = None,
) -> bytes:
    """
    Convert HTML report content to a branded PDF.

    Args:
        html_content: The raw HTML content of the report
        title: Report title for the cover header
        report_type: e.g. "Problem Overview", "Deep Dive Analysis"
        generated_at: ISO date string; defaults to now

    Returns:
        PDF file as bytes
    """
    if not generated_at:
        generated_at = datetime.utcnow().strftime("%B %d, %Y")

    html_content = _ensure_html(html_content)
    full_html = _branded_html_wrapper(html_content, title, report_type, generated_at)

    buffer = io.BytesIO()
    pisa_status = pisa.CreatePDF(full_html, dest=buffer, encoding="utf-8")

    if pisa_status.err:
        raise RuntimeError(f"PDF generation failed with {pisa_status.err} errors")

    buffer.seek(0)
    return buffer.read()


def _strip_tags(html: str) -> str:
    """Remove HTML tags, returning plain text."""
    return re.sub(r"<[^>]+>", "", html).strip()


def _add_heading(doc: Document, text: str, level: int = 1):
    """Add a styled heading to the Word document."""
    heading = doc.add_heading(text, level=level)
    for run in heading.runs:
        if level == 1:
            run.font.color.rgb = BRAND_DARK_RGB
            run.font.size = Pt(18)
        elif level == 2:
            run.font.color.rgb = BRAND_PURPLE_RGB
            run.font.size = Pt(14)
        else:
            run.font.color.rgb = BRAND_DARK_RGB
            run.font.size = Pt(12)


def _add_paragraph(doc: Document, text: str, bold: bool = False):
    """Add a styled paragraph."""
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.size = Pt(11)
    run.font.color.rgb = BRAND_GRAY_RGB
    run.bold = bold
    p.paragraph_format.space_after = Pt(6)
    return p


def generate_docx(
    html_content: str,
    title: str = "OppGrid Report",
    report_type: str = "Report",
    generated_at: Optional[str] = None,
) -> bytes:
    """
    Convert HTML report content to a branded DOCX file.

    Parses the HTML structure and maps it to Word document elements
    with OppGrid branding (colors, fonts, header/footer).

    Args:
        html_content: The raw HTML content of the report
        title: Report title for the cover page
        report_type: e.g. "Problem Overview", "Deep Dive Analysis"
        generated_at: ISO date string; defaults to now

    Returns:
        DOCX file as bytes
    """
    if not generated_at:
        generated_at = datetime.utcnow().strftime("%B %d, %Y")

    html_content = _ensure_html(html_content)
    doc = Document()

    # Page margins
    for section in doc.sections:
        section.top_margin = Cm(2.5)
        section.bottom_margin = Cm(2.5)
        section.left_margin = Cm(2.5)
        section.right_margin = Cm(2.5)

    # Cover header
    header_para = doc.add_paragraph()
    header_para.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run = header_para.add_run("OppGrid")
    run.font.size = Pt(28)
    run.font.color.rgb = BRAND_PURPLE_RGB
    run.bold = True

    subtitle = doc.add_paragraph()
    run = subtitle.add_run("AI-Powered Opportunity Intelligence")
    run.font.size = Pt(11)
    run.font.color.rgb = BRAND_GRAY_RGB
    run.italic = True

    doc.add_paragraph()  # spacer

    # Title
    title_para = doc.add_paragraph()
    run = title_para.add_run(title)
    run.font.size = Pt(20)
    run.font.color.rgb = BRAND_DARK_RGB
    run.bold = True

    meta_para = doc.add_paragraph()
    run = meta_para.add_run(f"{report_type}  |  Generated {generated_at}")
    run.font.size = Pt(10)
    run.font.color.rgb = BRAND_GRAY_RGB

    # Divider
    divider = doc.add_paragraph()
    divider.paragraph_format.space_before = Pt(12)
    divider.paragraph_format.space_after = Pt(12)

    # Footer
    for section in doc.sections:
        footer = section.footer
        footer_para = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
        footer_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = footer_para.add_run("OppGrid — AI-Powered Opportunity Intelligence — oppgrid.com")
        run.font.size = Pt(8)
        run.font.color.rgb = BRAND_GRAY_RGB

    # Parse the HTML content
    soup = BeautifulSoup(html_content, "html.parser")

    for element in soup.children:
        _process_element(doc, element)

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.read()


def _process_element(doc: Document, element):
    """Recursively process an HTML element into Word document elements."""
    if isinstance(element, str):
        text = element.strip()
        if text:
            _add_paragraph(doc, text)
        return

    tag = element.name
    if tag is None:
        return

    if tag in ("h1",):
        _add_heading(doc, element.get_text(strip=True), level=1)
    elif tag in ("h2",):
        _add_heading(doc, element.get_text(strip=True), level=2)
    elif tag in ("h3", "h4", "h5", "h6"):
        _add_heading(doc, element.get_text(strip=True), level=3)
    elif tag == "p":
        text = element.get_text(strip=True)
        if text:
            p = doc.add_paragraph()
            _build_inline_runs(p, element)
            p.paragraph_format.space_after = Pt(6)
    elif tag in ("ul", "ol"):
        for li in element.find_all("li", recursive=False):
            text = li.get_text(strip=True)
            if text:
                p = doc.add_paragraph(style="List Bullet" if tag == "ul" else "List Number")
                run = p.add_run(text)
                run.font.size = Pt(11)
                run.font.color.rgb = BRAND_GRAY_RGB
    elif tag == "table":
        _process_table(doc, element)
    elif tag in ("div", "section", "article", "main", "span", "strong", "em", "b", "i"):
        for child in element.children:
            _process_element(doc, child)
    elif tag == "br":
        doc.add_paragraph()
    elif tag == "hr":
        divider = doc.add_paragraph()
        divider.paragraph_format.space_before = Pt(8)
        divider.paragraph_format.space_after = Pt(8)
    else:
        # Fallback: extract text from unknown tags
        text = element.get_text(strip=True)
        if text:
            _add_paragraph(doc, text)


def _build_inline_runs(paragraph, element):
    """Build runs for inline elements (bold, italic, etc.) within a paragraph."""
    for child in element.children:
        if isinstance(child, str):
            text = child
            if text:
                run = paragraph.add_run(text)
                run.font.size = Pt(11)
                run.font.color.rgb = BRAND_GRAY_RGB
        elif child.name in ("strong", "b"):
            run = paragraph.add_run(child.get_text())
            run.font.size = Pt(11)
            run.font.color.rgb = BRAND_DARK_RGB
            run.bold = True
        elif child.name in ("em", "i"):
            run = paragraph.add_run(child.get_text())
            run.font.size = Pt(11)
            run.font.color.rgb = BRAND_GRAY_RGB
            run.italic = True
        elif child.name == "a":
            run = paragraph.add_run(child.get_text())
            run.font.size = Pt(11)
            run.font.color.rgb = BRAND_PURPLE_RGB
            run.underline = True
        elif child.name == "br":
            paragraph.add_run("\n")
        else:
            run = paragraph.add_run(child.get_text())
            run.font.size = Pt(11)
            run.font.color.rgb = BRAND_GRAY_RGB


def _process_table(doc: Document, table_elem):
    """Convert an HTML table to a Word table."""
    rows_data = []
    header_row = None

    thead = table_elem.find("thead")
    if thead:
        tr = thead.find("tr")
        if tr:
            header_row = [th.get_text(strip=True) for th in tr.find_all(["th", "td"])]

    tbody = table_elem.find("tbody")
    body_rows = tbody.find_all("tr") if tbody else table_elem.find_all("tr")

    for tr in body_rows:
        cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
        if cells:
            # If no explicit thead, treat first row with <th> as header
            if not header_row and tr.find("th"):
                header_row = cells
            else:
                rows_data.append(cells)

    if not rows_data and not header_row:
        return

    num_cols = max(
        len(header_row) if header_row else 0,
        max((len(r) for r in rows_data), default=0),
    )
    if num_cols == 0:
        return

    num_rows = len(rows_data) + (1 if header_row else 0)
    table = doc.add_table(rows=num_rows, cols=num_cols)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"

    row_idx = 0
    if header_row:
        for col_idx, text in enumerate(header_row[:num_cols]):
            cell = table.cell(0, col_idx)
            cell.text = text
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.bold = True
                    run.font.size = Pt(10)
        row_idx = 1

    for data_row in rows_data:
        for col_idx, text in enumerate(data_row[:num_cols]):
            cell = table.cell(row_idx, col_idx)
            cell.text = text
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.font.size = Pt(10)
        row_idx += 1

    doc.add_paragraph()  # spacing after table
