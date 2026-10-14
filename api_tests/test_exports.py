import csv
import io
from pathlib import Path
import pypdf
import pytest
from app.services.report_generator import report_generator


def rows(deliveries, audits, central=None):
    return list(csv.DictReader(io.StringIO(report_generator.generate_csv_quarantine_manifest(deliveries, audits, central))))


def test_export_keeps_central_only_recall_when_other_batches_have_deliveries():
    output = rows([{'batch_number': 'BCH-HOSP-1', 'hospital_name': 'One hospital', 'historically_distributed_units': 20}],
        [{'audit_id': 1, 'batch_number': 'BCH-HOSP-1', 'total_units_recalled': 20},
         {'audit_id': 2, 'batch_number': 'BCH-CENTRAL-1', 'total_units_recalled': 0}],
        [{'batch_number': 'BCH-CENTRAL-1', 'current_stock': 40, 'recall_status': 'RECALLED'}])
    assert len([r for r in output if r['record_type'] == 'RECALL_INITIATION']) == 2
    central = next(r for r in output if r['record_type'] == 'CENTRAL_BALANCE')
    assert central['recorded_central_balance'] == '40'


def test_batch_totals_are_not_repeated_for_each_hospital():
    output = rows([{'batch_number': 'BCH-X-1', 'historically_distributed_units': n} for n in (20, 30)],
        [{'batch_number': 'BCH-X-1', 'total_units_recalled': 50, 'affected_hospitals': 2}])
    assert sum(int(r['distributed_quantity_at_recall_initiation'] or 0) for r in output) == 50
    assert sum(int(r['historically_distributed_units'] or 0) for r in output) == 50
    deliveries = [r for r in output if r['record_type'] == 'HOSPITAL_DELIVERY']
    assert all(r['affected_hospitals'] == '' and r['distributed_quantity_at_recall_initiation'] == '' for r in deliveries)


def test_export_does_not_invent_missing_recall_or_central_stock_facts():
    output = rows([{'batch_number': 'BCH-OLD-1', 'affected_reason': 'EXPIRED',
        'hospital_name': 'Hospital', 'historically_distributed_units': 7}],
        [{'batch_number': 'BCH-OTHER-1', 'reason': 'Known reason', 'total_units_recalled': 0}])
    expired = next(r for r in output if r['record_type'] == 'HOSPITAL_DELIVERY')
    assert expired['reason'] == expired['recalled_by'] == expired['recall_stage'] == ''
    assert expired['recorded_central_balance'] == ''
    assert not any(r['record_type'] == 'CENTRAL_BALANCE' for r in output)
    audit = next(r for r in output if r['record_type'] == 'RECALL_INITIATION')
    assert audit['hospital_name'] == audit['historically_distributed_units'] == ''
    assert audit['distributed_quantity_at_recall_initiation'] == '0'


def test_pdf_includes_every_audit_full_reason_and_central_balance():
    reason = 'Long reason with <markup> & clinical detail. ' * 5 + 'COMPLETE-REASON-END'
    audits = [{'audit_id': n, 'batch_number': f'BCH-PDF-{n:04}', 'reason': reason,
        'recalled_by': 'Test officer', 'affected_hospitals': 0, 'total_units_recalled': 0,
        'stock_unit': 'tablet', 'recalled_at': '2026-10-14 10:00:00'} for n in range(12)]
    path = Path(report_generator.generate_pdf_recall_manifest([], audits, 'complete-export-test.pdf',
        [{'commercial_name': 'Central medicine', 'batch_number': 'BCH-PDF-0011', 'recall_status': 'RECALLED',
          'current_stock': 40, 'stock_unit': 'tablet', 'has_inferred_opening_balance': True}]))
    try:
        reader = pypdf.PdfReader(path)
        extracted = '\n'.join(p.extract_text() for p in reader.pages)
        assert len(reader.pages) > 1
        assert all(a['batch_number'] in extracted for a in audits)
        assert extracted.count('COMPLETE-REASON-END') == 12
        assert '<markup>' in extracted and '40 tablet' in extracted
        assert 'inferred legacy' in extracted
        assert all(float(p.mediabox.width) == 612 for p in reader.pages)
    finally:
        path.unlink(missing_ok=True)


def test_missing_pdf_library_does_not_return_text_disguised_as_pdf(monkeypatch):
    import importlib
    monkeypatch.setattr(importlib.import_module('app.services.report_generator'), 'HAS_REPORTLAB', False)
    with pytest.raises(RuntimeError, match='ReportLab'):
        report_generator.generate_pdf_recall_manifest([], [], 'no-library.pdf')
