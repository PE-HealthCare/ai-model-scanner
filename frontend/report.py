"""PDF rendering of the same finalized snapshot exported as JSON."""
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle


def pdf_export(snapshot: dict) -> bytes:
    stream = BytesIO()
    styles = getSampleStyleSheet()
    for name in ('Normal', 'BodyText'):
        styles[name].fontSize = 9
        styles[name].leading = 11
        styles[name].wordWrap = 'CJK'
    styles['Title'].alignment = TA_LEFT
    styles['BodyText'].spaceBefore = 4
    styles['Heading1'].fontSize = 17
    styles['Heading1'].leading = 21
    styles['Heading2'].fontSize = 12
    styles['Heading2'].leading = 15
    styles['Heading2'].spaceBefore = 9
    styles['Heading2'].spaceAfter = 6
    p = lambda text, style='BodyText': Paragraph(escape(str(text)), styles[style])
    result = snapshot['backend']
    artifact = result['artifact']
    doc = SimpleDocTemplate(stream, pagesize=(595, 842), rightMargin=42, leftMargin=42, topMargin=42, bottomMargin=42)
    story = [p('SIGTENSOR', 'Title'), p('From evidence to assessment.', 'Heading1'),
             p('STRUCTURED LSB SECURITY ASSESSMENT'), Spacer(1, 16),
             p('Final verdict: ' + result['verdict'], 'Heading2'),
             p('Artifact: ' + snapshot['upload']['filename']), p('SHA256: ' + artifact['sha256']),
             p('Scan ID: ' + snapshot['scan_id']), p('Generated: ' + snapshot['generated_at'])]
    structured = result.get('structured_stego')
    if structured:
        story += [p('Intake and detector evidence', 'Heading2'),
                  p(f"Trusted architecture: {artifact['architecture']} / {artifact['input_domain']} / {artifact['dtype']}"),
                  p(f"Score: {structured['score']:.12g} | Threshold: {structured['threshold']:.16g}"),
                  p('Dominant signal: ' + structured['dominant_signal'])]
        data = [[p('Evidence / feature'), p('Observed value'), p('Role')]]
        for evidence in snapshot['evidence']:
            data.append([p(evidence['id'] + ' / ' + evidence['feature']), p(format(evidence['value'], '.12g')),
                         p('Diagnostic only' if evidence['diagnostic_only'] else 'Scored')])
        table = Table(data, colWidths=[285, 126, 100], repeatRows=1, hAlign='LEFT')
        table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ededed')),
                                  ('LINEBELOW', (0, 0), (-1, -1), .4, colors.HexColor('#c1c1c1')),
                                  ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('BOTTOMPADDING', (0, 0), (-1, -1), 6)]))
        story += [Spacer(1, 12), table, p('Normalized signals', 'Heading2')]
        story += [p(f'{key}: {value:.12g}') for key, value in structured['z_scores'].items()]
        story += [p('Detector: ' + structured['detector_version']), p('Reference hash: ' + structured['reference_hash'])]
    else:
        story += [p('Assessment withheld', 'Heading2'), p(result['error']['message'])]
    story += [p('Scope, assurance and limitations', 'Heading2')]
    story += [p(text) for text in snapshot['limitations']]
    story += [p('Evidence integrity', 'Heading2'), p('Contract: ' + snapshot['contract_version']),
              p('Evidence SHA256: ' + snapshot['evidence_sha256']),
              p('Hash covers canonical JSON excluding the evidence_sha256 field. It is an integrity digest, not a digital signature.')]
    def footer(canvas, document):
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#474747'))
        canvas.drawString(42, 24, 'SIGTENSOR / ' + snapshot['scan_id'][:8])
        canvas.drawRightString(553, 24, str(document.page))
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return stream.getvalue()
