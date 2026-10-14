"""
SQL Business Logic Service for Pharmavigil
Coordinates relational operations, multi-table JOINs, CTE quarantine tracking,
and stored procedure calls against MySQL.
"""

from datetime import date
from typing import List, Dict, Any, Optional, Tuple
from app.database.mysql_client import mysql_client
from app.models.medicine import Batch
from app.utils.exceptions import (
    ExpiredBatchDispenseError,
    RecalledBatchOperationError,
    DatabaseConnectionError
)


class SQLService:
    """Encapsulates all relational queries and transactions."""

    def get_all_medicines(self) -> List[Dict[str, Any]]:
        """Retrieves all registered medicines with manufacturer names."""
        query = """
            SELECT 
                m.medicine_id,
                m.commercial_name,
                m.generic_name,
                m.dosage_form,
                m.strength,
                m.stock_unit,
                m.manufacturer_id,
                mf.company_name AS manufacturer_name
            FROM medicines m
            JOIN manufacturers mf ON m.manufacturer_id = mf.manufacturer_id
            ORDER BY m.commercial_name ASC;
        """
        return mysql_client.execute_query(query)

    def get_batches(self, medicine_id: Optional[int] = None, only_active: bool = False) -> List[Dict[str, Any]]:
        """Fetches batches with optional medicine filter and status filter."""
        base_query = """
            SELECT 
                b.batch_number,
                b.medicine_id,
                m.commercial_name,
                m.stock_unit,
                b.manufacturing_date,
                b.expiry_date,
                b.total_units_produced,
                CASE 
                    WHEN b.recall_status = 'RECALLED' THEN 'RECALLED'
                    WHEN b.recall_status = 'EXPIRED' OR b.expiry_date < CURDATE() THEN 'EXPIRED'
                    ELSE b.recall_status 
                END AS recall_status,
                DATEDIFF(b.expiry_date, CURDATE()) AS days_left
            FROM batches b
            JOIN medicines m ON b.medicine_id = m.medicine_id
        """
        conditions = []
        params = []

        if medicine_id:
            conditions.append("b.medicine_id = %s")
            params.append(medicine_id)
        if only_active:
            conditions.append("b.recall_status = 'ACTIVE' AND b.expiry_date >= CURDATE() AND b.manufacturing_date <= CURDATE()")

        if conditions:
            base_query += " WHERE " + " AND ".join(conditions)

        base_query += " ORDER BY b.expiry_date ASC;"
        return mysql_client.execute_query(base_query, tuple(params))

    def get_batch_by_number(self, batch_number: str) -> Optional[Dict[str, Any]]:
        """Retrieves full details for a single batch."""
        query = """
            SELECT 
                b.batch_number,
                b.medicine_id,
                m.commercial_name,
                m.stock_unit,
                b.manufacturing_date,
                b.expiry_date,
                b.total_units_produced,
                CASE 
                    WHEN b.recall_status = 'RECALLED' THEN 'RECALLED'
                    WHEN b.recall_status = 'EXPIRED' OR b.expiry_date < CURDATE() THEN 'EXPIRED'
                    ELSE b.recall_status 
                END AS recall_status,
                DATEDIFF(b.expiry_date, CURDATE()) AS days_left
            FROM batches b
            JOIN medicines m ON b.medicine_id = m.medicine_id
            WHERE b.batch_number = %s;
        """
        return mysql_client.execute_one(query, (batch_number,))

    def get_hospitals(self) -> List[Dict[str, Any]]:
        """Retrieves list of registered partner hospitals."""
        query = "SELECT hospital_id, hospital_name, city, state, contact_phone FROM hospitals ORDER BY hospital_name ASC;"
        return mysql_client.execute_query(query)

    def get_inventory_stock_overview(self) -> List[Dict[str, Any]]:
        """
        Multi-table SQL JOIN Query:
        Combines batches, medicines, manufacturers, and aggregated distribution counts.
        """
        query = """
            SELECT 
                b.batch_number,
                m.commercial_name,
                m.generic_name,
                m.dosage_form,
                m.strength,
                mf.company_name AS manufacturer_name,
                m.stock_unit,
                b.manufacturing_date,
                b.expiry_date,
                b.total_units_produced,
                CASE 
                    WHEN b.recall_status = 'RECALLED' THEN 'RECALLED'
                    WHEN b.recall_status = 'EXPIRED' OR b.expiry_date < CURDATE() THEN 'EXPIRED'
                    ELSE b.recall_status 
                END AS recall_status,
                DATEDIFF(b.expiry_date, CURDATE()) AS days_left,
                COALESCE(SUM(bd.quantity_delivered), 0) AS total_distributed_units,
                COUNT(bd.distribution_id) AS distribution_count,
                COALESCE(sr.received, 0) AS total_received_units,
                COALESCE(sr.inferred, 0) AS has_inferred_opening_balance,
                (COALESCE(sr.received, 0) - COALESCE(SUM(bd.quantity_delivered), 0)) AS current_stock
            FROM batches b
            JOIN medicines m ON b.medicine_id = m.medicine_id
            JOIN manufacturers mf ON m.manufacturer_id = mf.manufacturer_id
            LEFT JOIN batch_distribution bd ON b.batch_number = bd.batch_number
            LEFT JOIN (SELECT batch_number, SUM(quantity_received) AS received,
                       MAX(source_type='LEGACY_OPENING') AS inferred FROM stock_receipts GROUP BY batch_number) sr
                ON sr.batch_number=b.batch_number
            GROUP BY 
                b.batch_number, m.commercial_name, m.generic_name, 
                m.dosage_form, m.strength, mf.company_name, 
                b.manufacturing_date, b.expiry_date, 
                b.total_units_produced, b.recall_status, sr.received, sr.inferred, m.stock_unit
            ORDER BY b.expiry_date ASC;
        """
        return mysql_client.execute_query(query)

    def insert_batch(
        self,
        batch_number: str,
        medicine_id: int,
        manufacturing_date: str,
        expiry_date: str,
        total_units_produced: int,
        recall_status: str = "ACTIVE"
    ) -> int:
        """Inserts a new batch record into MySQL."""
        query = """
            INSERT INTO batches (
                batch_number, medicine_id, manufacturing_date, expiry_date, 
                total_units_produced, recall_status
            ) VALUES (%s, %s, %s, %s, %s, %s);
        """
        return mysql_client.execute_update(
            query,
            (batch_number, medicine_id, manufacturing_date, expiry_date, total_units_produced, recall_status)
        )

    def dispatch_batch_to_hospital(
        self,
        batch_number: str,
        hospital_id: int,
        quantity: int,
        dispatch_date: Optional[str] = None
    ) -> int:
        """
        Validates batch status before recording distribution.
        Raises ExpiredBatchDispenseError or RecalledBatchOperationError if invalid.
        """
        dispatched_on = date.fromisoformat(dispatch_date) if dispatch_date else date.today()
        if dispatched_on > date.today():
            raise ValueError("The selected batch dispatch date cannot be in the future.")
        # Serialize stock changes on the batch row so concurrent dispatches cannot oversell.
        with mysql_client.get_cursor(dictionary=True) as cursor:
            cursor.execute("SELECT * FROM batches WHERE batch_number = %s FOR UPDATE", (batch_number,))
            batch_info = cursor.fetchone()
            if not batch_info:
                raise ValueError("The selected batch does not exist.")
            mfg = batch_info["manufacturing_date"]
            exp = batch_info["expiry_date"]
            domain_batch = Batch(
                batch_number=batch_number,
                medicine_id=batch_info["medicine_id"],
                manufacturing_date=date.fromisoformat(mfg) if isinstance(mfg, str) else mfg,
                expiry_date=date.fromisoformat(exp) if isinstance(exp, str) else exp,
                total_units_produced=batch_info["total_units_produced"],
                recall_status=batch_info["recall_status"],
            )
            domain_batch.validate_for_dispensing()
            if dispatched_on < domain_batch.manufacturing_date or dispatched_on > domain_batch.expiry_date:
                raise ValueError("The selected batch dispatch date must be between its manufacturing and expiry dates.")
            cursor.execute("SELECT stock_unit FROM medicines WHERE medicine_id=%s", (batch_info["medicine_id"],))
            if cursor.fetchone()["stock_unit"] == "unspecified":
                raise ValueError("The selected batch has no defined inventory unit.")
            cursor.execute("SELECT COALESCE(SUM(quantity_delivered), 0) AS distributed FROM batch_distribution WHERE batch_number = %s", (batch_number,))
            distributed = cursor.fetchone()["distributed"]
            cursor.execute("SELECT COALESCE(SUM(quantity_received),0) AS received FROM stock_receipts WHERE batch_number=%s", (batch_number,))
            available = cursor.fetchone()["received"] - distributed
            if quantity < 1 or quantity > available:
                raise ValueError(f"Only {available} units are available for dispatch.")
            # A backdated dispatch must not make any recorded daily balance negative.
            cursor.execute("SELECT receipt_date AS event_date, quantity_received AS delta FROM stock_receipts WHERE batch_number=%s", (batch_number,))
            events = cursor.fetchall()
            cursor.execute("SELECT dispatch_date AS event_date, -quantity_delivered AS delta FROM batch_distribution WHERE batch_number=%s", (batch_number,))
            events += cursor.fetchall()
            daily = {dispatched_on: -quantity}
            for event in events:
                daily[event["event_date"]] = daily.get(event["event_date"], 0) + event["delta"]
            balance = 0
            for day in sorted(daily):
                balance += daily[day]
                if balance < 0:
                    raise ValueError("The selected batch has insufficient recorded stock for that dispatch date.")
            cursor.execute(
                "INSERT INTO batch_distribution (batch_number, hospital_id, quantity_delivered, dispatch_date) VALUES (%s, %s, %s, %s)",
                (batch_number, hospital_id, quantity, dispatched_on),
            )
            return cursor.rowcount

    def receive_stock(self, batch_number, quantity, receipt_date, reference, recorded_by):
        received_on = date.fromisoformat(receipt_date)
        with mysql_client.get_cursor(dictionary=True) as cursor:
            cursor.execute("SELECT * FROM batches WHERE batch_number=%s FOR UPDATE", (batch_number,))
            batch = cursor.fetchone()
            if not batch:
                raise ValueError("The selected batch does not exist.")
            cursor.execute("SELECT stock_unit FROM medicines WHERE medicine_id=%s", (batch["medicine_id"],))
            if cursor.fetchone()["stock_unit"] == "unspecified":
                raise ValueError("The selected batch has no defined inventory unit.")
            if received_on > date.today() or received_on < batch["manufacturing_date"] or received_on > batch["expiry_date"]:
                raise ValueError("The selected batch receipt date must be between manufacture and expiry, and cannot be in the future.")
            cursor.execute("SELECT * FROM stock_receipts WHERE batch_number=%s AND reference=%s", (batch_number, reference))
            existing = cursor.fetchone()
            if existing:
                if existing["quantity_received"] == quantity and existing["receipt_date"] == received_on:
                    return {"message": "This receipt is already recorded."}
                raise ValueError("The selected batch receipt reference is already used for a different receipt.")
            cursor.execute("SELECT COALESCE(SUM(quantity_received),0) AS received FROM stock_receipts WHERE batch_number=%s", (batch_number,))
            remaining = batch["total_units_produced"] - cursor.fetchone()["received"]
            if quantity < 1 or quantity > remaining:
                raise ValueError(f"Only {remaining} additional units can be received for this production batch.")
            cursor.execute("INSERT INTO stock_receipts (batch_number,quantity_received,receipt_date,reference,source_type,recorded_by) VALUES (%s,%s,%s,%s,'RECEIPT',%s)",
                           (batch_number, quantity, received_on, reference, recorded_by))
            return {"message": "Receipt recorded."}

    def execute_emergency_recall(
        self,
        batch_number: str,
        reason: str,
        recalled_by: str = "SAFETY_OFFICER_ADMIN"
    ) -> Dict[str, Any]:
        """
        Invokes the real MySQL Stored Procedure 'sp_recall_batch' with IN and OUT parameters.
        Rejects recall if the batch is already RECALLED to prevent duplicate audit rows.
        Returns execution statistics.
        """
        batch_info = self.get_batch_by_number(batch_number)
        if not batch_info:
            raise ValueError(f"Batch recall failed: Specified batch number '{batch_number}' does not exist in the database.")
        if batch_info.get("recall_status") == "RECALLED":
            raise RecalledBatchOperationError(
                batch_number=batch_number,
                recall_status="RECALLED",
                message=f"Batch recall refused: Specified batch '{batch_number}' is already RECALLED."
            )

        in_out_args = (batch_number, reason, recalled_by, 0, 0)
        result_args = mysql_client.call_stored_procedure("sp_recall_batch", in_out_args)
        
        # result_args maps to (batch_number, reason, recalled_by, affected_hospitals, total_units_recalled)
        affected_hospitals = result_args[3] if len(result_args) > 3 else 0
        total_units_recalled = result_args[4] if len(result_args) > 4 else 0

        return {
            "batch_number": batch_number,
            "status": "RECALLED",
            "reason": reason,
            "recalled_by": recalled_by,
            "affected_hospitals": affected_hospitals,
            "total_units_recalled": total_units_recalled
            ,"distributed_quantity_at_initiation": total_units_recalled,
            "recall_stage": "INITIATED"
        }

    def get_high_risk_quarantine_trace(self) -> List[Dict[str, Any]]:
        """
        Executes Section 6.2 Advanced Analytical Query:
        Uses Common Table Expressions (CTE) and multi-table JOIN with GROUP BY ... HAVING
        to pinpoint hospitals holding active stock of recalled batches.
        """
        query = """
            WITH FlaggedBatches AS (
                SELECT batch_number, medicine_id, expiry_date,
                       CASE WHEN recall_status='RECALLED' THEN 'RECALLED' ELSE 'EXPIRED' END AS affected_reason
                FROM batches
                WHERE recall_status = 'RECALLED' OR recall_status = 'EXPIRED' OR expiry_date < CURDATE()
            )
            SELECT 
                h.hospital_name,
                h.hospital_id,
                h.city,
                h.contact_phone,
                m.commercial_name,
                m.stock_unit,
                fb.batch_number,
                fb.affected_reason,
                SUM(bd.quantity_delivered) AS total_quarantine_units,
                SUM(bd.quantity_delivered) AS historically_distributed_units
            FROM FlaggedBatches fb
            JOIN batch_distribution bd ON fb.batch_number = bd.batch_number
            JOIN hospitals h ON bd.hospital_id = h.hospital_id
            JOIN medicines m ON fb.medicine_id = m.medicine_id
            GROUP BY h.hospital_id, h.hospital_name, h.city, h.contact_phone, m.commercial_name, m.stock_unit, fb.batch_number, fb.affected_reason
            HAVING SUM(bd.quantity_delivered) > 0
            ORDER BY total_quarantine_units DESC;
        """
        return mysql_client.execute_query(query)

    def get_recall_audits(self) -> List[Dict[str, Any]]:
        """Retrieves chronological audit log of all emergency recalls."""
        query = """
            SELECT 
                audit_id,
                batch_number,
                reason,
                recalled_by,
                affected_hospitals,
                total_units_recalled,
                total_units_recalled AS distributed_quantity_at_initiation,
                'INITIATED' AS recall_stage,
                recalled_at
            FROM recall_audit
            ORDER BY recalled_at DESC;
        """
        return mysql_client.execute_query(query)


# Singleton SQL service instance
sql_service = SQLService()
