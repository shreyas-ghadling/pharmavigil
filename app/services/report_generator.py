"""
File Handling and Automated Reporting Service for Pharmavigil
Manages CSV bulk batch ingestion with atomic transactions, CSV exports,
and professional PDF Safety Audit Recall Manifest generation.
"""

import csv
import io
import os
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

from app.config import config
from app.database.mysql_client import mysql_client
from app.models.schemas import BatchIntakeSchema

# Attempt ReportLab or FPDF2 for PDF manifest generation
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
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
                'affected_hospitals': audit.get('affected_hospitals'),
                'distributed_quantity_at_recall_initiation': audit.get('distributed_quantity_at_initiation', audit.get('total_units_recalled')),
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
        self,
        quarantine_data: List[Dict[str, Any]],
        recall_audits: List[Dict[str, Any]],
        output_filename: str = "Safety_Audit_Recall_Manifest.pdf"
    ) -> str:
        """
        Builds a formal PDF Regulatory Safety Audit Recall Manifest.
        Saves to the configured exports directory and returns the absolute filepath.
        """
        output_path = config.exports_dir / output_filename

        if HAS_REPORTLAB:
            doc = SimpleDocTemplate(
                str(output_path),
                pagesize=letter,
                rightMargin=36,
                leftMargin=36,
                topMargin=36,
                bottomMargin=36
            )
            styles = getSampleStyleSheet()
            story = []

            # Document Title
            title_style = ParagraphStyle(
                "DocTitle",
                parent=styles["Heading1"],
                fontSize=20,
                leading=24,
                textColor=colors.HexColor("#1A365D"),
                spaceAfter=8
            )
            story.append(Paragraph("PHARMAVIGIL SAFETY AUDIT & RECALL MANIFEST", title_style))
            
            sub_style = ParagraphStyle(
                "SubTitle",
                parent=styles["Normal"],
                fontSize=10,
                textColor=colors.HexColor("#4A5568"),
                spaceAfter=14
            )
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
            story.append(Paragraph(f"Generated by: Safety Officer & Admin Control Center | Timestamp: {timestamp}", sub_style))
            story.append(Spacer(1, 12))

            # Section 1: Emergency Batch Recall Audits
            story.append(Paragraph("1. Batch Recall Initiations", styles["Heading2"]))
            story.append(Paragraph("Quantities reflect historical deliveries at initiation, not confirmed recovery. Hospital notification, returns, disposal, and recall completion are not recorded by this manifest.", styles["Normal"]))
            if recall_audits:
                audit_table_data = [["Audit ID", "Batch No", "Reason", "Recalled By", "Hospitals", "Units"]]
                for a in recall_audits[:8]:
                    audit_table_data.append([
                        str(a.get("audit_id", "")),
                        str(a.get("batch_number", "")),
                        str(a.get("reason", ""))[:28],
                        str(a.get("recalled_by", "")),
                        str(a.get("affected_hospitals", 0)),
                        str(a.get("total_units_recalled", 0))
                    ])
                t_audit = Table(audit_table_data, colWidths=[55, 95, 180, 110, 50, 50])
                t_audit.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2B6CB0")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#F7FAFC"), colors.white])
                ]))
                story.append(t_audit)
            else:
                story.append(Paragraph("No batch recalls logged in audit history.", styles["Normal"]))

            story.append(Spacer(1, 16))

            # Section 2: Quarantined Stock Distribution (CTE Tracing)
            story.append(Paragraph("2. Historical Affected-Batch Deliveries", styles["Heading2"]))
            story.append(Paragraph("Delivered quantities do not establish stock remaining, quarantined, or recovered at hospitals.", styles["Normal"]))
            if quarantine_data:
                q_table_data = [["Hospital", "City", "Contact Phone", "Medicine", "Batch", "Delivered Quantity"]]
                for q in quarantine_data:
                    q_table_data.append([
                        str(q.get("hospital_name", "")),
                        str(q.get("city", "")),
                        str(q.get("contact_phone", "")),
                        str(q.get("commercial_name", "")),
                        str(q.get("batch_number", "")),
                        f"{q.get('historically_distributed_units', q.get('total_quarantine_units', 0))} {q.get('stock_unit', 'unspecified')}"
                    ])
                t_q = Table(q_table_data, colWidths=[120, 70, 90, 85, 95, 80])
                t_q.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#C53030")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#FED7D7")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#FFF5F5"), colors.white])
                ]))
                story.append(t_q)
            else:
                story.append(Paragraph("No hospital delivery records match the affected-batch criteria.", styles["Normal"]))

            doc.build(story)
        else:
            # Fallback simple text-based manifest file if reportlab is absent
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("PHARMAVIGIL SAFETY AUDIT & RECALL MANIFEST\n")
                f.write("=" * 60 + "\n\n")
                f.write(self.generate_csv_quarantine_manifest(quarantine_data))

        return str(output_path)


# Singleton instance
report_generator = ReportGenerator()
