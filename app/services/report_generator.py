"""
File Handling and Automated Reporting Service for Pharmavigil
Manages CSV bulk batch ingestion with atomic transactions, CSV exports,
and professional PDF Safety Audit Recall Manifest generation.
"""

import csv
import io
import os
from datetime import datetime, date, timezone
from xml.sax.saxutils import escape
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

from app.config import config
from app.database.mysql_client import mysql_client
from app.models.schemas import BatchIntakeSchema

# Attempt ReportLab or FPDF2 for PDF manifest generation
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


class ReportGenerator:
    """Handles CSV parsing, transaction batch loading, and PDF audit generation."""

    def ingest_batches_from_csv(self, file_content_or_path) -> Tuple[int, List[str]]:
        """
        Parses CSV data, validates records with BatchIntakeSchema,
        checks for duplicate batch numbers (within file and in database),
        and atomically commits valid batches into MySQL.
        If any row is invalid or duplicate, rejects the entire file and commits nothing.
        Returns (success_count, list_of_error_messages).
        """
        if isinstance(file_content_or_path, (str, Path)):
            with open(file_content_or_path, mode="r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        else:
            # File-like object (e.g. from Streamlit st.file_uploader)
            content = file_content_or_path.read()
            if isinstance(content, bytes):
                content = content.decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(content))
            rows = list(reader)

        if not rows:
            return 0, ["CSV file is empty or could not be parsed."]

        valid_records: List[BatchIntakeSchema] = []
        errors: List[str] = []
        seen_in_file = set()

        for idx, row in enumerate(rows, start=1):
            try:
                # Clean whitespace
                cleaned_row = {k.strip(): v.strip() for k, v in row.items() if k}
                b_num = cleaned_row.get("batch_number", "")

                # Check duplicate within file
                if b_num in seen_in_file:
                    errors.append(f"Row {idx} rejected: Duplicate batch number '{b_num}' found in CSV file.")
                    continue
                seen_in_file.add(b_num)

                # Check duplicate in database
                existing = mysql_client.execute_one(
                    "SELECT batch_number FROM batches WHERE batch_number = %s;",
                    (b_num,)
                )
                if existing:
                    errors.append(f"Row {idx} rejected: Batch number '{b_num}' already exists in database.")
                    continue

                validated = BatchIntakeSchema(
                    batch_number=b_num,
                    medicine_id=int(cleaned_row["medicine_id"]),
                    manufacturing_date=date.fromisoformat(cleaned_row["manufacturing_date"]),
                    expiry_date=date.fromisoformat(cleaned_row["expiry_date"]),
                    total_units_produced=int(cleaned_row["total_units_produced"]),
                    recall_status=cleaned_row.get("recall_status", "ACTIVE").upper()
                )
                valid_records.append(validated)
            except Exception as e:
                errors.append(f"Row {idx} rejected: {str(e)}")

        # Strict business rule: if ANY row fails, reject the whole file and insert 0 rows
        if errors or not valid_records:
            return 0, errors

        # Atomic insertion into MySQL
        conn = mysql_client.get_connection()
        cursor = conn.cursor()
        inserted_count = 0
        try:
            insert_query = """
                INSERT INTO batches (
                    batch_number, medicine_id, manufacturing_date, expiry_date, 
                    total_units_produced, recall_status
                ) VALUES (%s, %s, %s, %s, %s, %s);
            """
            for record in valid_records:
                cursor.execute(
                    insert_query,
                    (
                        record.batch_number,
                        record.medicine_id,
                        str(record.manufacturing_date),
                        str(record.expiry_date),
                        record.total_units_produced,
                        record.recall_status
                    )
                )
                inserted_count += 1
            conn.commit()
        except Exception as e:
            conn.rollback()
            errors.append(f"Transaction Rollback: Database error during bulk insert: {str(e)}")
            return 0, errors
        finally:
            cursor.close()
            conn.close()

        return inserted_count, errors

    def generate_csv_quarantine_manifest(
        self, quarantine_data: List[Dict[str, Any]],
        recall_audits: Optional[List[Dict[str, Any]]] = None,
        central_stock: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Export recall initiations, historical deliveries, and recorded central balances."""
        output = io.StringIO()
        fields = ['record_type', 'audit_id', 'recalled_at', 'batch_number', 'commercial_name',
                  'affected_reason', 'recall_stage', 'reason', 'recalled_by', 'affected_hospitals',
                  'distributed_quantity_at_recall_initiation', 'hospital_id', 'hospital_name',
                  'city', 'contact_phone', 'historically_distributed_units', 'recorded_central_balance',
                  'stock_unit', 'includes_inferred_opening_balance']
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        audits = recall_audits or []
        audit_map = {}
        for audit in audits:
            audit_map.setdefault(audit.get('batch_number'), audit)
            writer.writerow({
                'record_type': 'RECALL_INITIATION', 'audit_id': audit.get('audit_id'),
                'recalled_at': audit.get('recalled_at'), 'batch_number': audit.get('batch_number'),
                'commercial_name': audit.get('commercial_name'), 'affected_reason': 'RECALLED',
                'recall_stage': audit.get('recall_stage', 'INITIATED'), 'reason': audit.get('reason'),
                'recalled_by': audit.get('recalled_by'), 'affected_hospitals': audit.get('affected_hospitals'),
                'distributed_quantity_at_recall_initiation': audit.get('distributed_quantity_at_initiation', audit.get('total_units_recalled')),
                'stock_unit': audit.get('stock_unit')})
        for row in quarantine_data:
            audit = audit_map.get(row.get('batch_number'), {})
            writer.writerow({
                'record_type': 'HOSPITAL_DELIVERY', 'batch_number': row.get('batch_number'),
                'commercial_name': row.get('commercial_name'), 'affected_reason': row.get('affected_reason'),
                'reason': audit.get('reason'), 'recalled_by': audit.get('recalled_by'),
                'hospital_id': row.get('hospital_id'), 'hospital_name': row.get('hospital_name'),
                'city': row.get('city'), 'contact_phone': row.get('contact_phone'),
                'historically_distributed_units': row.get('historically_distributed_units', row.get('total_quarantine_units')),
                'stock_unit': row.get('stock_unit')})
        for row in central_stock or []:
            writer.writerow({
                'record_type': 'CENTRAL_BALANCE', 'batch_number': row.get('batch_number'),
                'commercial_name': row.get('commercial_name'), 'affected_reason': row.get('recall_status'),
                'recorded_central_balance': row.get('current_stock'), 'stock_unit': row.get('stock_unit'),
                'includes_inferred_opening_balance': row.get('has_inferred_opening_balance')})
        return output.getvalue()

    def generate_pdf_recall_manifest(
        self, quarantine_data: List[Dict[str, Any]], recall_audits: List[Dict[str, Any]],
        output_filename: str = "Safety_Audit_Recall_Manifest.pdf",
        central_stock: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Paginated manifest with full records, wrapped text, and explicit quantity meanings."""
        if not HAS_REPORTLAB:
            raise RuntimeError('PDF generation requires ReportLab.')
        output_path = config.exports_dir / output_filename
        doc = SimpleDocTemplate(str(output_path), pagesize=letter,
                                rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=40)
        styles = getSampleStyleSheet()
        cell_style = ParagraphStyle('ManifestCell', parent=styles['Normal'], fontSize=8, leading=10)
        header_style = ParagraphStyle('ManifestHeader', parent=cell_style, textColor=colors.white)
        section_intro = ParagraphStyle('SectionIntro', parent=styles['Normal'], spaceAfter=6)

        def section(title, description):
            story.append(KeepTogether([Paragraph(title, styles['Heading2']), Paragraph(description, section_intro)]))
        story = [Paragraph('PHARMAVIGIL SAFETY AUDIT &amp; RECALL MANIFEST', styles['Heading1']),
                 Paragraph('Generated: ' + datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'), styles['Normal']),
                 Paragraph('Blank CSV cells and "Not recorded" PDF values indicate missing or inapplicable fields. Recorded zero quantities remain zero. Quantities use each medicine stock unit; do not add unlike units.', styles['Normal']), Spacer(1, 12)]

        def text(value):
            return 'Not recorded' if value is None or value == '' else str(value)

        def table(headers, rows, widths):
            data = [[Paragraph(escape(h), header_style) for h in headers]]
            data.extend([[Paragraph(escape(text(v)), cell_style) for v in row] for row in rows])
            grid = Table(data, colWidths=widths, repeatRows=1, splitInRow=1, hAlign='LEFT')
            grid.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2B6CB0')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#CBD5E0')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#F7FAFC'), colors.white]),
                ('LEFTPADDING', (0, 0), (-1, -1), 5), ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 6)]))
            story.append(grid)

        section('1. Batch Recall Initiations', 'Historical deliveries at initiation do not confirm recovery. Hospital notification, returns, disposal, and recall completion are not recorded here.')
        if recall_audits:
            table(['Audit', 'Batch', 'Full recall reason', 'Recorded by', 'Hospitals', 'Delivered at initiation', 'Initiated at'],
                  [[a.get('audit_id'), a.get('batch_number'), a.get('reason'), a.get('recalled_by'),
                    a.get('affected_hospitals'),
                    text(a.get('distributed_quantity_at_initiation', a.get('total_units_recalled'))) + ' ' + text(a.get('stock_unit')),
                    a.get('recalled_at')] for a in recall_audits], [30, 85, 135, 80, 50, 80, 80])
        else:
            story.append(Paragraph('No batch recalls logged in audit history.', styles['Normal']))
        story.append(Spacer(1, 16))
        section('2. Historical Affected-Batch Deliveries', 'Delivered quantities do not establish stock remaining, quarantined, or recovered at hospitals.')
        if quarantine_data:
            table(['Hospital / city', 'Contact phone', 'Medicine / batch', 'Reason flagged', 'Historical deliveries'],
                  [[text(q.get('hospital_name')) + ' / ' + text(q.get('city')), q.get('contact_phone'),
                    text(q.get('commercial_name')) + ' / ' + text(q.get('batch_number')), q.get('affected_reason'),
                    text(q.get('historically_distributed_units', q.get('total_quarantine_units'))) + ' ' + text(q.get('stock_unit'))]
                   for q in quarantine_data], [125, 90, 170, 65, 90])
        else:
            story.append(Paragraph('No hospital delivery records match the affected-batch criteria.', styles['Normal']))
        story.append(Spacer(1, 16))
        section('3. Affected Central Balances', 'Current recorded ledger balances, not verified physical counts or recovered stock. Legacy opening balances are identified where inferred.')
        if central_stock:
            table(['Medicine / batch', 'Reason flagged', 'Recorded central balance', 'Opening balance basis'],
                  [[text(c.get('commercial_name')) + ' / ' + text(c.get('batch_number')), c.get('recall_status'),
                    text(c.get('current_stock')) + ' ' + text(c.get('stock_unit')),
                    'Includes inferred legacy opening balance' if c.get('has_inferred_opening_balance') else 'Receipt ledger']
                   for c in central_stock], [190, 70, 115, 165])
        else:
            story.append(Paragraph('No affected central balances supplied.', styles['Normal']))

        def footer(canvas, document):
            canvas.saveState()
            canvas.setFont('Helvetica', 8)
            canvas.drawRightString(576, 22, 'Page ' + str(document.page))
            canvas.restoreState()
        doc.build(story, onFirstPage=footer, onLaterPages=footer)
        return str(output_path)


# Singleton instance
report_generator = ReportGenerator()
