# Pharmavigil: Drug Adverse Reaction & Medicine Safety Tracking System
## Comprehensive Engineering Specification & Academic Project Guide

- **Course:** Database Concepts for Data Science Lab (DCDS Lab)
- **Department:** Artificial Intelligence & Machine Learning (AIML)
- **Evaluation:** End Semester Examination (ESE) Project (10 Marks / 40% Weightage)
- **Primary Tech Stack:** Python 3.10+, MySQL, MongoDB, Streamlit, Pydantic, Pytest

---

## 1. Dual-Database Architectural Rationale (Viva Goldmine)

### Why not store everything in a single SQL or NoSQL database?

- **Relational SQL Database (MySQL):**
  Pharmaceutical regulation mandates strict ACID compliance. A batch must link to a valid manufacturer, expiration dates must be enforced, distribution counts cannot become negative, and foreign keys prevent orphaned records.
- **NoSQL MongoDB Database:**
  Adverse drug reports vary widely between patients:
  - *Patient A:* Age 28, 1 symptom (Nausea), no notes.
  - *Patient B:* Age 64, 4 symptoms (Arrhythmia, Hypotension, Dizziness, Dyspnea), lab findings, free-text doctor observations.
  Altering an SQL schema every time a new clinical observation metric is introduced violates normalization; MongoDB document collections accommodate polymorphic JSON natively.

---

## 2. Advanced Database Querying & Operations

### 2.1 SQL Stored Procedure: Atomic Emergency Batch Recall (`sp_recall_batch`)
Atomically updates the batch status, logs the recall audit, and identifies affected stock distribution:
```sql
DELIMITER //
CREATE PROCEDURE sp_recall_batch(
    IN p_batch_number VARCHAR(50),
    IN p_reason VARCHAR(255),
    IN p_recalled_by VARCHAR(100),
    OUT p_affected_hospitals INT,
    OUT p_total_units_recalled INT
)
BEGIN
    DECLARE v_batch_exists INT DEFAULT 0;
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    SELECT COUNT(*) INTO v_batch_exists FROM batches WHERE batch_number = p_batch_number;
    IF v_batch_exists = 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Batch does not exist';
    END IF;

    START TRANSACTION;
        UPDATE batches SET recall_status = 'RECALLED' WHERE batch_number = p_batch_number;

        SELECT COUNT(DISTINCT hospital_id), COALESCE(SUM(quantity_delivered), 0)
        INTO p_affected_hospitals, p_total_units_recalled
        FROM batch_distribution WHERE batch_number = p_batch_number;

        INSERT INTO recall_audit (batch_number, reason, recalled_by, affected_hospitals, total_units_recalled, recalled_at)
        VALUES (p_batch_number, p_reason, p_recalled_by, p_affected_hospitals, p_total_units_recalled, NOW());
    COMMIT;
END //
DELIMITER ;
```

### 2.2 SQL Advanced Analytical Query: High-Risk Inventory Tracing (CTE)
Uses Common Table Expressions (CTE) and multi-table JOIN with GROUP BY ... HAVING to pinpoint hospitals holding active stock of flagged batches:
```sql
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
HAVING SUM(bd.quantity_delivered) > 0
ORDER BY total_quarantine_units DESC;
```

### 2.3 MongoDB Multi-Stage Aggregation Pipeline: Safety Signal Detection
Unwinds polymorphic symptom arrays to calculate symptom frequency and average severity per medicine:
```python
pipeline = [
    # Stage 1: Match recent reports with significant severity
    {"$match": {"severity_score": {"$gte": 3}}},

    # Stage 2: Deconstruct symptoms array for granular aggregation
    {"$unwind": "$symptoms"},

    # Stage 3: Group by drug and symptom to compute frequencies
    {
        "$group": {
            "_id": {
                "medicine_name": "$medicine_name",
                "symptom": "$symptoms.name"
            },
            "incident_count": {"$sum": 1},
            "avg_severity": {"$avg": "$severity_score"},
            "critical_cases": {
                "$sum": {"$cond": ["$symptoms.is_critical", 1, 0]}
            }
        }
    },

    # Stage 4: Filter out low-frequency noise (Signal Detection threshold)
    {"$match": {"incident_count": {"$gte": 2}}},

    # Stage 5: Format output projection and calculate signal risk score
    {
        "$project": {
            "_id": 0,
            "medicine": "$_id.medicine_name",
            "symptom": "$_id.symptom",
            "incident_count": 1,
            "avg_severity": {"$round": ["$avg_severity", 2]},
            "critical_cases": 1,
            "signal_risk_score": {"$multiply": ["$incident_count", "$avg_severity"]}
        }
    },

    # Stage 6: Rank by calculated safety risk
    {"$sort": {"signal_risk_score": -1}}
]
```

### 2.4 MongoDB Text Search Index
Enables clinical keyword retrieval across doctor notes without needing external NLP libraries:
```python
# Create Text Index
db.adverse_reports.create_index([("clinical_notes", "text")])

# Fast keyword retrieval
results = db.adverse_reports.find(
    {"$text": {"$search": "anaphylaxis seizure arrhythmia"}},
    {"score": {"$meta": "textScore"}}
).sort([("score", {"$meta": "textScore"})])
```

---

## 3. Viva & Evaluation FAQ (How to Defend Your Project)

1. **Q: Why did you use both SQL and NoSQL instead of putting everything in SQL?**
   - *A:* "Pharmaceutical inventory and distribution must adhere to strict regulatory compliance, relational integrity, and ACID guarantees (foreign keys, non-null expiration dates, non-negative stock counts). However, patient adverse event telemetry is inherently polymorphic and semi-structured—symptom count varies, severity metrics differ, and clinical observations are unstandardized. Using MongoDB for telemetry avoids continuous schema migrations in SQL while preserving transactional guarantees in MySQL for physical batch inventory."

2. **Q: How did you implement advanced database concepts in SQL?**
   - *A:* "We implemented atomic stored procedures (`sp_recall_batch`) to transition batch statuses, calculate affected distribution, and insert audit records within an isolated transaction. Additionally, we utilized Common Table Expressions (CTEs) and multi-table JOINs with `GROUP BY ... HAVING` to locate quarantined units across distributed hospital networks."

3. **Q: How did you implement advanced database concepts in MongoDB?**
   - *A:* "We built a multi-stage aggregation pipeline utilizing `$match`, `$unwind`, `$group`, `$project`, and `$sort` to execute pharmacovigilance signal detection across nested symptom documents. Furthermore, we built a native MongoDB Text Index across doctor clinical notes for keyword retrieval."

4. **Q: How did you handle doctor clinical notes without complex AI?**
   - *A:* "Clinical notes are stored in MongoDB document strings. While standard symptom reporting uses structured inputs for predictable querying, doctor free-text notes are indexed using MongoDB's native full-text search engine (`$text` index), allowing instant clinical keyword search without unnecessary NLP overhead."

5. **Q: How did you ensure security and validation?**
   - *A:* "All SQL interactions utilize parameterized queries via Python DB-API to eliminate SQL injection risks. All incoming adverse reports are validated at the application boundary via Pydantic schemas, checking bounded ranges on severity scores (1 to 5) and patient age (0 to 120). User authentication enforces bcrypt password hashing."
