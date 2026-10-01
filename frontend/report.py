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
             p('STRUCTURED-LSB / AUTHORITATIVE CURRENT SCAN ASSESSMENT'), Spacer(1, 16),
             p('Final verdict: ' + result['verdict'], 'Heading2'),
             p('Artifact: ' + snapshot['upload']['filename']), p('SHA256: ' + artifact['sha256']),
             p('Scan ID: ' + snapshot['scan_id']), p('Generated: ' + snapshot['generated_at'])]
    runtime = result.get('canonical', {})
    risk = runtime.get('risk_results', {})
    ml = runtime.get('ml_results', {})
    p2 = runtime.get('p2_evidence', {})
    story += [p('Authoritative assessment', 'Heading2'),
              p('Decision source: ' + result.get('decision_source', 'withheld')),
              p('PASS means no evidence exceeded the configured criteria within the tested scope; it does not guarantee safety.'),
              p('Generation: ' + runtime.get('generation_commit', 'unavailable'))]
    detector = result.get('structured_stego')
    if detector:
        story += [p(f"Observed S_FULL: {detector['score']:.12g} | Frozen threshold: {detector['threshold']:.16g}"),
                  p('Dominant signal: ' + detector['dominant_signal']), p('Detector: ' + detector['detector_version'])]
    else:
        story.append(p('Required authoritative detector evidence unavailable. No other score substitutes for it.'))
    story += [p('Static evidence / advisory explainability', 'Heading2'),
              p('Analyzed layers: ' + str(runtime.get('features', {}).get('layer_count', 'unavailable'))),
              p('D6 statistical outlier (diagnostic, not payload localization): ' + runtime.get('dashboard_results', {}).get('highest_risk_layer', 'unavailable')),
              p('Advisory LightGBM output: ' + str(ml.get('p_tamper', 'unavailable'))),
              p('LightGBM / TreeSHAP is not authoritative for the final assessment.'),
              p('Classifier: ' + ml.get('model_version', 'unavailable')),
              p('SHAP explained layer: ' + runtime.get('explanation', {}).get('explained_layer', 'unavailable'))]
    for name, number in ml.get('shap_attributions', {}).items():
        story.append(p(f'TreeSHAP {name}: {number:+.9g}'))
    story += [p('Supporting behavioral evidence', 'Heading2')]
    for name, number in p2.get('behavior', {}).items(): story.append(p(f'{name}: {number}'))
    story.append(p('Trigger verification: unavailable; not implemented.'))
    if result.get('error'): story.append(p('Execution issue: ' + result['error']['message']))
    structured = result.get('structured_stego')
    if structured:
        story += [p('Authoritative structured-LSB evidence: ' + structured['verdict'], 'Heading2'),
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
        story += [p('Structured-LSB unavailable / not applicable', 'Heading2'), p(result.get('structured_status', {}).get('reason', 'No structured evidence produced.'))]
    story += [p('Scope, assurance and limitations', 'Heading2')]
    story += [p(text) for text in snapshot['limitations']]
    if risk:
        story += [p('Historical MRS diagnostic - excluded from final decision', 'Heading2'),
                  p(f"Experimental MRS: {risk['mrs_score']} / historical verdict: {risk['verdict']}. This is NOT the final assessment."),
                  p(p2.get('boundary_rule', ''))]
        for item in p2.get('contributions', []):
            story.append(p(f"{item['source']}: score={item['score']}, contribution={item['contribution']}, status={item['status']}"))
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
