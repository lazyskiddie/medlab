import uuid
from datetime import datetime
from pathlib import Path
from django.conf import settings

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


def generate_pdf_report(analysis_result) -> str | None:
    if not REPORTLAB_AVAILABLE:
        return None

    output_dir = Path(settings.REPORTS_OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f'report_{uuid.uuid4().hex}.pdf'
    filepath = output_dir / filename
    rel_path = f'output_reports/{filename}'

    report  = analysis_result.report
    patient = report.uploaded_by
    flags   = analysis_result.flagged_items
    doc     = SimpleDocTemplate(str(filepath), pagesize=A4,
                                 topMargin=2*cm, bottomMargin=2*cm,
                                 leftMargin=2*cm, rightMargin=2*cm)
    styles  = getSampleStyleSheet()
    title_style   = ParagraphStyle('title',   parent=styles['Title'],    fontSize=18, spaceAfter=6)
    heading_style = ParagraphStyle('heading', parent=styles['Heading2'],  fontSize=13, spaceAfter=4)
    normal_style  = styles['Normal']

    sev_color = {'normal': colors.HexColor('#1D9E75'), 'mild': colors.HexColor('#BA7517'),
                 'moderate': colors.HexColor('#D85A30'), 'severe': colors.HexColor('#E24B4A')
                 }.get(analysis_result.severity, colors.black)

    story = []
    story.append(Paragraph('MedLab — Lab Report Analysis', title_style))
    story.append(HRFlowable(width='100%', thickness=1, color=colors.HexColor('#D3D1C7')))
    story.append(Spacer(1, 0.4*cm))

    meta_table = Table([
        ['Patient',   patient.get_full_name() or patient.username],
        ['Report ID', str(report.id)],
        ['Date',      datetime.now().strftime('%d %B %Y, %H:%M')],
        ['Severity',  analysis_result.severity.upper()],
    ], colWidths=[4*cm, 12*cm])
    meta_table.setStyle(TableStyle([
        ('FONTNAME',  (0,0),(-1,-1), 'Helvetica'),
        ('FONTSIZE',  (0,0),(-1,-1), 10),
        ('FONTNAME',  (0,0),(0,-1),  'Helvetica-Bold'),
        ('TEXTCOLOR', (1,3),(1,3),   sev_color),
        ('FONTNAME',  (1,3),(1,3),   'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0),(-1,-1), 4),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 0.6*cm))

    if analysis_result.summary:
        story.append(Paragraph('Analysis Summary', heading_style))
        story.append(Paragraph(analysis_result.summary, normal_style))
        story.append(Spacer(1, 0.6*cm))

    if analysis_result.conditions_detected:
        story.append(Paragraph('Conditions Detected', heading_style))
        for c in analysis_result.conditions_detected:
            story.append(Paragraph(f"• <b>{c['name']}</b> — {c.get('confidence','n/a')}", normal_style))
        story.append(Spacer(1, 0.6*cm))

    if flags:
        story.append(Paragraph('Test Results', heading_style))
        rows = [['Test', 'Value', 'Unit', 'Reference', 'Status']]
        for f in flags:
            rows.append([f['test'], str(f['value']), f['unit'],
                         f"{f['low']} – {f['high']}",
                         f['status'].upper() + (' ⚠' if f['is_critical'] else '')])
        tbl = Table(rows, colWidths=[5*cm, 2.5*cm, 2.5*cm, 3.5*cm, 2.5*cm])
        cmds = [
            ('BACKGROUND',    (0,0),(-1,0),  colors.HexColor('#3C3489')),
            ('TEXTCOLOR',     (0,0),(-1,0),  colors.white),
            ('FONTNAME',      (0,0),(-1,0),  'Helvetica-Bold'),
            ('FONTSIZE',      (0,0),(-1,-1), 9),
            ('ROWBACKGROUNDS',(0,1),(-1,-1), [colors.HexColor('#F1EFE8'), colors.white]),
            ('GRID',          (0,0),(-1,-1), 0.4, colors.HexColor('#D3D1C7')),
            ('TOPPADDING',    (0,0),(-1,-1), 5),
            ('BOTTOMPADDING', (0,0),(-1,-1), 5),
        ]
        for i, f in enumerate(flags, 1):
            bg = colors.HexColor('#FCEBEB' if f['is_critical'] else
                                 '#FAEEDA' if f['status']=='high' else
                                 '#E6F1FB' if f['status']=='low' else '#EAF3DE')
            cmds.append(('BACKGROUND', (4,i),(4,i), bg))
        tbl.setStyle(TableStyle(cmds))
        story.append(tbl)

    story.append(Spacer(1, 0.6*cm))
    story.append(HRFlowable(width='100%', thickness=0.5, color=colors.HexColor('#D3D1C7')))
    story.append(Paragraph(
        'This report is for informational purposes only and does not constitute medical advice. '
        'Always consult a qualified healthcare professional.',
        ParagraphStyle('disc', parent=normal_style, fontSize=8,
                       textColor=colors.HexColor('#888780')),
    ))
    doc.build(story)
    return rel_path