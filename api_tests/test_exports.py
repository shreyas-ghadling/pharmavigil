import csv
import io
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
