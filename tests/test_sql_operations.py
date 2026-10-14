import io
import sqlite3
import pytest
import pypdf

from app.config import config
from app.database.mysql_client import mysql_client
from app.services.sql_service import sql_service
from app.services.report_generator import report_generator
from app.utils.exceptions import (
    ExpiredBatchDispenseError,
    RecalledBatchOperationError
)


def is_mysql_available() -> bool:
    """Helper to detect if MySQL is currently reachable and sp_recall_batch exists."""
    try:
        row = mysql_client.execute_one(
            "SELECT ROUTINE_NAME FROM information_schema.ROUTINES WHERE ROUTINE_SCHEMA = %s AND ROUTINE_NAME = 'sp_recall_batch';",
            (mysql_client.database,)
        )
        return bool(row)
    except Exception:
        return False


class TestSQLiteMockOperations:
    """Mock testing of normalized tables and CTE query logic in SQLite."""

    @pytest.fixture
    def mock_db(self):
        conn = sqlite3.connect(":memory:")
        cursor = conn.cursor()

        # Create normalized schema in SQLite
        cursor.executescript("""
            CREATE TABLE manufacturers (
                manufacturer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT NOT NULL,
                license_number TEXT NOT NULL UNIQUE,
                country TEXT NOT NULL,
                contact_email TEXT NOT NULL
            );

            CREATE TABLE medicines (
                medicine_id INTEGER PRIMARY KEY AUTOINCREMENT,
                commercial_name TEXT NOT NULL,
                generic_name TEXT NOT NULL,
                dosage_form TEXT NOT NULL,
                strength TEXT NOT NULL,
                manufacturer_id INTEGER NOT NULL REFERENCES manufacturers(manufacturer_id)
            );

            CREATE TABLE batches (
                batch_number TEXT PRIMARY KEY,
                medicine_id INTEGER NOT NULL REFERENCES medicines(medicine_id),
                manufacturing_date TEXT NOT NULL,
                expiry_date TEXT NOT NULL,
                total_units_produced INTEGER NOT NULL CHECK (total_units_produced > 0),
                recall_status TEXT NOT NULL DEFAULT 'ACTIVE'
            );

            CREATE TABLE hospitals (
                hospital_id INTEGER PRIMARY KEY AUTOINCREMENT,
                hospital_name TEXT NOT NULL,
                city TEXT NOT NULL,
                state TEXT NOT NULL,
                contact_phone TEXT NOT NULL
            );

            CREATE TABLE batch_distribution (
                distribution_id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_number TEXT NOT NULL REFERENCES batches(batch_number),
                hospital_id INTEGER NOT NULL REFERENCES hospitals(hospital_id),
                quantity_delivered INTEGER NOT NULL CHECK (quantity_delivered > 0),
                dispatch_date TEXT NOT NULL
            );

            -- Seed minimal mock records
            INSERT INTO manufacturers VALUES (1, 'Apex Pharma', 'LIC-APX-9901', 'Germany', 'info@apex.de');
            INSERT INTO medicines VALUES (101, 'Cardiomax', 'Amlodipine', 'Tablet', '50mg', 1);
            INSERT INTO batches VALUES ('BCH-PCM-9042', 101, '2025-01-10', '2027-01-10', 50000, 'RECALLED');
            INSERT INTO hospitals VALUES (1, 'St. Jude Hospital', 'Metropolis', 'NY', '+1-212-555-0199');
            INSERT INTO batch_distribution VALUES (1, 'BCH-PCM-9042', 1, 12000, '2025-01-15');
        """)
        conn.commit()
        yield conn
        conn.close()

    def test_mock_cte_quarantine_trace(self, mock_db):
        """Verifies Section 6.2 Common Table Expression (CTE) query execution in SQLite."""
        cursor = mock_db.cursor()
        cte_query = """
            WITH FlaggedBatches AS (
                SELECT batch_number, medicine_id, expiry_date
                FROM batches
                WHERE recall_status = 'RECALLED'
            )
            SELECT 
                h.hospital_name,
                h.city,
                m.commercial_name,
                fb.batch_number,
                SUM(bd.quantity_delivered) AS total_quarantine_units
            FROM FlaggedBatches fb
            JOIN batch_distribution bd ON fb.batch_number = bd.batch_number
            JOIN hospitals h ON bd.hospital_id = h.hospital_id
            JOIN medicines m ON fb.medicine_id = m.medicine_id
            GROUP BY h.hospital_name, h.city, m.commercial_name, fb.batch_number
            HAVING SUM(bd.quantity_delivered) > 0;
        """
        cursor.execute(cte_query)
        rows = cursor.fetchall()
        assert len(rows) == 1
        assert rows[0][0] == "St. Jude Hospital"
        assert rows[0][3] == "BCH-PCM-9042"
        assert rows[0][4] == 12000


class TestRealMySQLOperations:
    """Integration test suite executing transactional stored procedures and business rules against MySQL."""

    @pytest.mark.skipif(not is_mysql_available(), reason="MySQL database server is not reachable")
    def test_sp_recall_batch_live(self):
        """Executes the real sp_recall_batch stored procedure against MySQL."""
        batch_number = "BCH-PCM-9042"
        reason = "Automated Pytest Emergency Recall Verification"

        orig_row = mysql_client.execute_one(
            "SELECT recall_status FROM batches WHERE batch_number = %s;",
            (batch_number,)
        )
        orig_status = orig_row["recall_status"] if orig_row else "ACTIVE"

        try:
            # Clean audit row for test
            mysql_client.execute_update(
                "DELETE FROM recall_audit WHERE batch_number = %s AND recalled_by = 'PYTEST_RUNNER';",
                (batch_number,)
            )

            result = sql_service.execute_emergency_recall(
                batch_number=batch_number,
                reason=reason,
                recalled_by="PYTEST_RUNNER"
            )

            assert result["batch_number"] == batch_number
            assert result["status"] == "RECALLED"
            assert result["affected_hospitals"] >= 1
            assert result["total_units_recalled"] > 0

            # Verify audit row in recall_audit table
            audits = sql_service.get_recall_audits()
            assert any(a["batch_number"] == batch_number and a["recalled_by"] == "PYTEST_RUNNER" for a in audits)
        finally:
            # Restore batch status
            mysql_client.execute_update(
                "UPDATE batches SET recall_status = %s WHERE batch_number = %s;",
                (orig_status, batch_number)
            )
            mysql_client.execute_update(
                "DELETE FROM recall_audit WHERE recalled_by = 'PYTEST_RUNNER';"
            )

    @pytest.mark.skipif(not is_mysql_available(), reason="MySQL database server is not reachable")
    def test_dispatch_expired_batch_raises_error(self):
        """Business rule: dispatching an EXPIRED batch raises ExpiredBatchDispenseError."""
        # BCH-GLU-5502 is seeded as expired in seed_data.sql
        with pytest.raises(ExpiredBatchDispenseError) as exc_info:
            sql_service.dispatch_batch_to_hospital(
                batch_number="BCH-GLU-5502",
                hospital_id=1,
                quantity=100
            )
        assert "BCH-GLU-5502" in str(exc_info.value)

    @pytest.mark.skipif(not is_mysql_available(), reason="MySQL database server is not reachable")
    def test_dispatch_recalled_batch_raises_error(self):
        """Business rule: dispatching a RECALLED batch raises RecalledBatchOperationError."""
        batch_number = "BCH-DER-8801"
        try:
            mysql_client.execute_update(
                "UPDATE batches SET recall_status = 'RECALLED' WHERE batch_number = %s;",
                (batch_number,)
            )
            with pytest.raises(RecalledBatchOperationError) as exc_info:
                sql_service.dispatch_batch_to_hospital(
                    batch_number=batch_number,
                    hospital_id=1,
                    quantity=50
                )
            assert "RECALLED" in str(exc_info.value)
        finally:
            mysql_client.execute_update(
                "UPDATE batches SET recall_status = 'ACTIVE' WHERE batch_number = %s;",
                (batch_number,)
            )

    @pytest.mark.skipif(not is_mysql_available(), reason="MySQL database server is not reachable")
    def test_recalling_recalled_batch_refused_no_duplicate_audit(self):
        """Business rule: recalling an already RECALLED batch is refused cleanly with no duplicate recall_audit row."""
        batch_number = "BCH-DER-8801"
        try:
            # Ensure batch is initially active and clean
            mysql_client.execute_update(
                "UPDATE batches SET recall_status = 'ACTIVE' WHERE batch_number = %s;",
                (batch_number,)
            )
            mysql_client.execute_update(
                "DELETE FROM recall_audit WHERE batch_number = %s;",
                (batch_number,)
            )

            # First recall: should succeed
            res1 = sql_service.execute_emergency_recall(
                batch_number=batch_number,
                reason="Initial Regulatory Recall",
                recalled_by="OFFICER_A"
            )
            assert res1["status"] == "RECALLED"

            count_after_first = mysql_client.execute_one(
                "SELECT COUNT(*) as cnt FROM recall_audit WHERE batch_number = %s;",
                (batch_number,)
            )["cnt"]
            assert count_after_first == 1

            # Second recall attempt on already RECALLED batch: must raise RecalledBatchOperationError
            with pytest.raises(RecalledBatchOperationError) as exc_info:
                sql_service.execute_emergency_recall(
                    batch_number=batch_number,
                    reason="Second Duplicate Recall Attempt",
                    recalled_by="OFFICER_B"
                )
            assert "already RECALLED" in str(exc_info.value)

            # Audit log must NOT contain duplicate row
            count_after_second = mysql_client.execute_one(
                "SELECT COUNT(*) as cnt FROM recall_audit WHERE batch_number = %s;",
                (batch_number,)
            )["cnt"]
            assert count_after_second == 1

        finally:
            mysql_client.execute_update(
                "UPDATE batches SET recall_status = 'ACTIVE' WHERE batch_number = %s;",
                (batch_number,)
            )
            mysql_client.execute_update(
                "DELETE FROM recall_audit WHERE batch_number = %s;",
                (batch_number,)
            )

    @pytest.mark.skipif(not is_mysql_available(), reason="MySQL database server is not reachable")
    def test_csv_intake_rejects_bad_rows_and_rolls_back(self):
        """
        Business rule: CSV intake rejects bad rows
        (negative quantity, expiry before manufacture, duplicate batch number)
        and rolls back the whole file.
        """
        # Case A: Negative quantity in one row
        bad_csv_negative = """batch_number,medicine_id,manufacturing_date,expiry_date,total_units_produced,recall_status
BCH-VAL-0001,101,2026-01-01,2028-01-01,5000,ACTIVE
BCH-BAD-0002,101,2026-01-01,2028-01-01,-1000,ACTIVE
"""
        count, errors = report_generator.ingest_batches_from_csv(io.StringIO(bad_csv_negative))
        assert count == 0
        assert len(errors) > 0
        # Check that valid row was rolled back and not inserted
        check_inserted = mysql_client.execute_one("SELECT * FROM batches WHERE batch_number = 'BCH-VAL-0001';")
        assert check_inserted is None

        # Case B: Expiry before manufacture
        bad_csv_dates = """batch_number,medicine_id,manufacturing_date,expiry_date,total_units_produced,recall_status
BCH-VAL-0003,101,2026-05-01,2025-05-01,5000,ACTIVE
"""
        count, errors = report_generator.ingest_batches_from_csv(io.StringIO(bad_csv_dates))
        assert count == 0
        assert len(errors) > 0

        # Case C: Duplicate batch number within the CSV file
        bad_csv_duplicate_in_file = """batch_number,medicine_id,manufacturing_date,expiry_date,total_units_produced,recall_status
BCH-DUP-0001,101,2026-01-01,2028-01-01,5000,ACTIVE
BCH-DUP-0001,102,2026-01-01,2028-01-01,4000,ACTIVE
"""
        count, errors = report_generator.ingest_batches_from_csv(io.StringIO(bad_csv_duplicate_in_file))
        assert count == 0
        assert any("Duplicate batch number" in e for e in errors)
        check_dup = mysql_client.execute_one("SELECT * FROM batches WHERE batch_number = 'BCH-DUP-0001';")
        assert check_dup is None

        # Case D: Duplicate batch number already existing in database
        bad_csv_existing_db = """batch_number,medicine_id,manufacturing_date,expiry_date,total_units_produced,recall_status
BCH-PCM-9042,101,2026-01-01,2028-01-01,5000,ACTIVE
"""
        count, errors = report_generator.ingest_batches_from_csv(io.StringIO(bad_csv_existing_db))
        assert count == 0
        assert any("already exists in database" in e for e in errors)

    @pytest.mark.skipif(not is_mysql_available(), reason="MySQL database server is not reachable")
    def test_exports_pdf_and_csv_contain_real_data(self):
        """
        Exports verification:
        Ensures that PDF and CSV manifests contain real data after a recall
        (batch, reason, hospitals, units).
        """
        test_batch = "BCH-PCM-9042"
        test_reason = "Acute Clinical Signal Hazard Detection"

        try:
            # 1. Trigger recall in test database
            sql_service.execute_emergency_recall(
                batch_number=test_batch,
                reason=test_reason,
                recalled_by="EXPORT_TEST_OFFICER"
            )

            # 2. Gather quarantine records & recall audit data
            quarantine_data = sql_service.get_high_risk_quarantine_trace()
            recall_audits = sql_service.get_recall_audits()

            # 3. Test CSV manifest output
            csv_output = report_generator.generate_csv_quarantine_manifest(
                quarantine_data=quarantine_data,
                recall_audits=recall_audits
            )
            assert test_batch in csv_output
            assert test_reason in csv_output
            assert "hospital_name" in csv_output
            assert "historically_distributed_units" in csv_output

            # 4. Test PDF manifest output
            pdf_path = report_generator.generate_pdf_recall_manifest(
                quarantine_data=quarantine_data,
                recall_audits=recall_audits,
                output_filename="test_safety_manifest.pdf"
            )
            assert pdf_path is not None

            # Read back generated PDF text via pypdf
            reader = pypdf.PdfReader(pdf_path)
            extracted_text = "".join(page.extract_text() for page in reader.pages)

            # Verify presence of real data fields in PDF
            assert test_batch in extracted_text
            assert "Acute Clinical Signal" in extracted_text
            assert "EXPORT_TEST_OFFICER" in ''.join(extracted_text.split())
            assert "Historical Affected-Batch Deliveries" in extracted_text

        finally:
            # Clean up
            mysql_client.execute_update(
                "UPDATE batches SET recall_status = 'ACTIVE' WHERE batch_number = %s;",
                (test_batch,)
            )
            mysql_client.execute_update(
                "DELETE FROM recall_audit WHERE batch_number = %s;",
                (test_batch,)
            )

