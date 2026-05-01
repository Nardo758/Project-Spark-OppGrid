"""
Base Report Generator - Foundation for PDF report generation
Uses ReportLab for professional PDF creation with branding, layouts, and styling
"""

import io
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle, StyleSheet1
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, black, white, grey, lightgrey
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    PageBreak,
    Image,
    KeepTogether,
)
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.pdfgen import canvas
from reportlab.lib import colors

logger = logging.getLogger(__name__)


class BrandingConfig:
    """OppGrid branding configuration"""

    PRIMARY_COLOR = HexColor("#0066CC")  # OppGrid blue
    SECONDARY_COLOR = HexColor("#FF6B35")  # OppGrid orange
    ACCENT_COLOR = HexColor("#2D9CDB")  # Accent blue
    TEXT_COLOR = HexColor("#1A1A1A")
    LIGHT_BG = HexColor("#F5F7FA")
    BORDER_COLOR = HexColor("#E0E0E0")
    RISK_HIGH = HexColor("#DC3545")  # Red
    RISK_MEDIUM = HexColor("#FFC107")  # Yellow/Amber
    RISK_LOW = HexColor("#28A745")  # Green
    
    FONT_FAMILY = "Helvetica"
    FONT_TITLE = f"{FONT_FAMILY}-Bold"
    FONT_BOLD = f"{FONT_FAMILY}-Bold"
    FONT_NORMAL = FONT_FAMILY
    FONT_ITALIC = f"{FONT_FAMILY}-Oblique"


def get_styles() -> StyleSheet1:
    """Get custom stylesheet with OppGrid branding"""
    styles = getSampleStyleSheet()
    
    # Heading styles
    styles.add(ParagraphStyle(
        name='CustomHeading1',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=BrandingConfig.PRIMARY_COLOR,
        spaceAfter=12,
        fontName=BrandingConfig.FONT_TITLE,
        keepWithNext=True,
    ))
    
    styles.add(ParagraphStyle(
        name='CustomHeading2',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=BrandingConfig.PRIMARY_COLOR,
        spaceAfter=10,
        fontName=BrandingConfig.FONT_BOLD,
        keepWithNext=True,
    ))
    
    styles.add(ParagraphStyle(
        name='CustomHeading3',
        parent=styles['Heading3'],
        fontSize=13,
        textColor=BrandingConfig.TEXT_COLOR,
        spaceAfter=8,
        fontName=BrandingConfig.FONT_BOLD,
        keepWithNext=True,
    ))
    
    # Body text
    styles.add(ParagraphStyle(
        name='CustomBody',
        parent=styles['BodyText'],
        fontSize=11,
        textColor=BrandingConfig.TEXT_COLOR,
        spaceAfter=6,
        leading=15,
        fontName=BrandingConfig.FONT_NORMAL,
    ))
    
    # Small text
    styles.add(ParagraphStyle(
        name='CustomSmall',
        parent=styles['Normal'],
        fontSize=9,
        textColor=grey,
        spaceAfter=4,
        fontName=BrandingConfig.FONT_NORMAL,
    ))
    
    return styles


class ReportGenerator(ABC):
    """
    Abstract base class for PDF report generation
    Handles common report structure, branding, and styling
    """

    def __init__(
        self,
        title: str,
        request_id: str,
        page_size: str = "letter",
        include_toc: bool = False,
    ):
        """
        Initialize report generator
        
        Args:
            title: Report title
            request_id: Unique request identifier for traceability
            page_size: 'letter' or 'landscape'
            include_toc: Whether to include table of contents
        """
        self.title = title
        self.request_id = request_id
        self.include_toc = include_toc
        self.styles = get_styles()
        self.page_size = landscape(letter) if page_size == "landscape" else letter
        self.elements = []
        self.timestamp = datetime.utcnow()
        
    def _add_header(self) -> None:
        """Add OppGrid branded header to report"""
        header_data = [
            [
                Paragraph(
                    f"<font color='{BrandingConfig.PRIMARY_COLOR.hexval()}' size=28><b>OppGrid</b></font>",
                    self.styles['Normal'],
                ),
                Paragraph(
                    f"<font color='{BrandingConfig.TEXT_COLOR.hexval()}' size=14><b>{self.title}</b></font>",
                    self.styles['Normal'],
                ),
            ]
        ]
        
        header_table = Table(header_data, colWidths=[2*inch, 4.5*inch])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (-1, -1), BrandingConfig.LIGHT_BG),
            ('LINEBELOW', (0, 0), (-1, -1), 2, BrandingConfig.PRIMARY_COLOR),
        ]))
        
        self.elements.append(header_table)
        self.elements.append(Spacer(1, 0.2*inch))
    
    def _add_footer(self) -> None:
        """Add footer with timestamp and request ID"""
        footer_text = f"""
        <font size=8 color='{grey.hexval()}'>
        Report ID: {self.request_id} | Generated: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}
        <br/>
        This report contains proprietary analysis. For OppGrid users only.
        </font>
        """
        self.elements.append(Spacer(1, 0.2*inch))
        self.elements.append(Paragraph(footer_text, self.styles['CustomSmall']))
    
    def _add_executive_summary(
        self,
        summary_text: str,
        key_findings: List[str],
        metrics: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Add executive summary section
        
        Args:
            summary_text: Main summary paragraph
            key_findings: List of key findings
            metrics: Optional metrics dictionary to display
        """
        self.elements.append(Paragraph("Executive Summary", self.styles['CustomHeading2']))
        self.elements.append(Paragraph(summary_text, self.styles['CustomBody']))
        self.elements.append(Spacer(1, 0.1*inch))
        
        # Key findings
        self.elements.append(Paragraph("Key Findings", self.styles['CustomHeading3']))
        findings_list = "<br/>".join([f"• {finding}" for finding in key_findings])
        self.elements.append(Paragraph(findings_list, self.styles['CustomBody']))
        
        # Metrics if provided
        if metrics:
            self.elements.append(Spacer(1, 0.1*inch))
            self._add_metrics_grid(metrics)
        
        self.elements.append(Spacer(1, 0.2*inch))
    
    def _add_metrics_grid(self, metrics: Dict[str, Any]) -> None:
        """Add a grid of metrics with colored backgrounds"""
        metric_data = []
        
        # Create 2-column layout
        items = list(metrics.items())
        for i in range(0, len(items), 2):
            row = []
            for j in range(2):
                if i + j < len(items):
                    key, value = items[i + j]
                    metric_text = f"<b>{key}</b><br/><font size=14>{value}</font>"
                    row.append(Paragraph(metric_text, self.styles['CustomBody']))
                else:
                    row.append(Paragraph("", self.styles['CustomBody']))
            metric_data.append(row)
        
        metric_table = Table(metric_data, colWidths=[3.25*inch, 3.25*inch])
        metric_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), BrandingConfig.LIGHT_BG),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 12),
            ('BORDER', (0, 0), (-1, -1), 1, BrandingConfig.BORDER_COLOR),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ]))
        
        self.elements.append(metric_table)
    
    def _add_comparison_table(
        self,
        headers: List[str],
        rows: List[List[Any]],
        title: Optional[str] = None,
    ) -> None:
        """
        Add comparison table to report
        
        Args:
            headers: Column headers
            rows: List of row data
            title: Optional table title
        """
        if title:
            self.elements.append(Paragraph(title, self.styles['CustomHeading2']))
        
        # Build table data
        table_data = [headers] + rows
        
        table = Table(
            table_data,
            colWidths=[6.5*inch / len(headers)] * len(headers),
        )
        
        table.setStyle(TableStyle([
            # Header styling
            ('BACKGROUND', (0, 0), (-1, 0), BrandingConfig.PRIMARY_COLOR),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), BrandingConfig.FONT_BOLD),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            
            # Body styling
            ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 1), (-1, -1), 'TOP'),
            ('FONTNAME', (0, 1), (-1, -1), BrandingConfig.FONT_NORMAL),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('PADDING', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, BrandingConfig.BORDER_COLOR),
            
            # Alternating row colors
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, BrandingConfig.LIGHT_BG]),
        ]))
        
        self.elements.append(table)
        self.elements.append(Spacer(1, 0.2*inch))
    
    def _add_risk_indicator(
        self,
        title: str,
        risk_level: str,
        description: str,
    ) -> None:
        """
        Add color-coded risk indicator
        
        Args:
            title: Risk factor title
            risk_level: 'low', 'medium', or 'high'
            description: Risk description
        """
        risk_colors = {
            'low': BrandingConfig.RISK_LOW,
            'medium': BrandingConfig.RISK_MEDIUM,
            'high': BrandingConfig.RISK_HIGH,
        }
        
        color = risk_colors.get(risk_level.lower(), BrandingConfig.BORDER_COLOR)
        
        data = [[
            Paragraph(
                f"<b>{title}</b><br/><font size=9>{risk_level.upper()}</font>",
                self.styles['CustomBody'],
            ),
            Paragraph(description, self.styles['CustomBody']),
        ]]
        
        table = Table(data, colWidths=[1.5*inch, 5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), color),
            ('TEXTCOLOR', (0, 0), (0, 0), white),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('PADDING', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (0, 0), 'CENTER'),
            ('BORDER', (0, 0), (-1, -1), 1, BrandingConfig.BORDER_COLOR),
        ]))
        
        self.elements.append(table)
        self.elements.append(Spacer(1, 0.1*inch))
    
    def _add_page_break(self) -> None:
        """Add page break"""
        self.elements.append(PageBreak())
    
    @abstractmethod
    def build(self) -> bytes:
        """
        Build and return PDF bytes
        Must be implemented by subclasses
        
        Returns:
            PDF content as bytes
        """
        pass
    
    def generate(self) -> bytes:
        """
        Generate complete PDF document
        
        Returns:
            PDF content as bytes
        """
        # Add header
        self._add_header()
        
        # Build document-specific content
        self.build()
        
        # Add footer
        self._add_footer()
        
        # Generate PDF
        pdf_buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            pdf_buffer,
            pagesize=self.page_size,
            topMargin=0.5*inch,
            bottomMargin=0.5*inch,
            leftMargin=0.5*inch,
            rightMargin=0.5*inch,
        )
        
        doc.build(self.elements)
        pdf_buffer.seek(0)
        return pdf_buffer.getvalue()
