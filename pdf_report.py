import os
import json
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT

def generate_pdf_report(scan, farmer):
    """Generate a styled PDF disease report."""
    import tempfile
    from flask import current_app

    upload_dir = os.path.join(current_app.root_path, 'static', 'reports')
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"report_{scan.id}_{farmer.id}.pdf"
    filepath = os.path.join(upload_dir, filename)

    doc = SimpleDocTemplate(filepath, pagesize=A4,
                            rightMargin=0.75*inch, leftMargin=0.75*inch,
                            topMargin=0.75*inch, bottomMargin=0.75*inch)
    elements = []
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle('Title', parent=styles['Title'],
                                  fontSize=20, textColor=colors.HexColor('#1a6b2f'),
                                  spaceAfter=6, alignment=TA_CENTER)
    subtitle_style = ParagraphStyle('Subtitle', parent=styles['Normal'],
                                     fontSize=11, textColor=colors.HexColor('#4a4a4a'),
                                     spaceAfter=4, alignment=TA_CENTER)
    section_style = ParagraphStyle('Section', parent=styles['Heading2'],
                                    fontSize=13, textColor=colors.HexColor('#1a6b2f'),
                                    spaceBefore=14, spaceAfter=4)
    body_style = ParagraphStyle('Body', parent=styles['Normal'],
                                 fontSize=10, textColor=colors.HexColor('#333333'),
                                 spaceAfter=4, leading=16)

    # Header
    elements.append(Paragraph("🌾 Early Detection of Millet Diseases", title_style))
    elements.append(Paragraph("AI-Powered Disease Detection Report", subtitle_style))
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#1a6b2f')))
    elements.append(Spacer(1, 12))

    # Report Info Table
    report_time = scan.scanned_at.strftime("%d %B %Y, %I:%M %p") if scan.scanned_at else "N/A"
    info_data = [
        ['Report ID', f"RPT-{scan.id:04d}", 'Date', report_time],
        ['Farmer Name', farmer.name, 'Location', farmer.location or 'N/A'],
        ['Crop Type', farmer.crop_type or 'Pearl Millet', 'Status', scan.status.capitalize()],
    ]
    info_table = Table(info_data, colWidths=[1.2*inch, 2.2*inch, 1.2*inch, 2.2*inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#e8f5e9')),
        ('BACKGROUND', (2,0), (2,-1), colors.HexColor('#e8f5e9')),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME', (2,0), (2,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#c8e6c9')),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 14))

    # Disease Detection Result
    elements.append(Paragraph("Disease Detection Result", section_style))
    severity_color = {'High': '#d32f2f', 'Medium': '#f57c00', 'Low': '#388e3c', 'None': '#1976d2'}.get(scan.severity, '#333333')
    result_data = [
        ['Disease Detected', scan.disease_name or 'N/A'],
        ['Confidence Score', f"{scan.confidence:.1f}%" if scan.confidence else 'N/A'],
        ['Severity Level', scan.severity or 'N/A'],
    ]
    result_table = Table(result_data, colWidths=[2.0*inch, 4.8*inch])
    result_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#1a6b2f')),
        ('TEXTCOLOR', (0,0), (0,-1), colors.white),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#c8e6c9')),
        ('PADDING', (0,0), (-1,-1), 8),
        ('BACKGROUND', (1,2), (1,2), colors.HexColor('#fff3e0')),
    ]))
    elements.append(result_table)
    elements.append(Spacer(1, 10))

    def add_section(title, content):
        if content:
            elements.append(Paragraph(title, section_style))
            elements.append(Paragraph(content, body_style))

    add_section("Description", scan.disease_description)
    add_section("Symptoms Observed", scan.symptoms)
    add_section("Recommended Treatment", scan.treatment)
    add_section("Recommended Chemicals", scan.chemicals)
    add_section("Fertilizer Recommendations", scan.fertilizers)
    add_section("Prevention Measures", scan.prevention)

    if scan.dos_donts:
        elements.append(Paragraph("Do's and Don'ts", section_style))
        parts = scan.dos_donts.split('|||')
        if len(parts) == 2:
            dos_text = "✅ " + "<br/>✅ ".join(parts[0].replace("Do's: ","").split("; "))
            donts_text = "❌ " + "<br/>❌ ".join(parts[1].replace("Don'ts: ","").split("; "))
            dos_donts_data = [["Do's", "Don'ts"], [Paragraph(dos_text, body_style), Paragraph(donts_text, body_style)]]
            dd_table = Table(dos_donts_data, colWidths=[3.4*inch, 3.4*inch])
            dd_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1a6b2f')),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,-1), 9),
                ('GRID', (0,0), (-1,-1), 0.3, colors.HexColor('#c8e6c9')),
                ('PADDING', (0,0), (-1,-1), 8),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ]))
            elements.append(dd_table)
        else:
            elements.append(Paragraph(scan.dos_donts, body_style))

    if scan.expert_notes:
        elements.append(Paragraph("Expert Verification Notes", section_style))
        elements.append(Paragraph(scan.expert_notes, body_style))

    elements.append(Spacer(1, 20))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#1a6b2f')))
    elements.append(Spacer(1, 6))
    footer_style = ParagraphStyle('Footer', parent=styles['Normal'],
                                   fontSize=8, textColor=colors.grey, alignment=TA_CENTER)
    elements.append(Paragraph(
        "This report was generated by the Early Detection of Millet Diseases AI System. "
        "Consult a qualified agronomist for field-level treatment decisions.",
        footer_style))

    doc.build(elements)
    return filename
