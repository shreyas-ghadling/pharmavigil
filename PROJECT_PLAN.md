# Pharmavigil: Project Architecture & Execution Plan

**Course:** Database Concepts for Data Science Lab (DCDS Lab)  
**Academic Department:** Artificial Intelligence & Machine Learning (AIML)  
**Evaluation:** End Semester Examination (ESE) Project (10 Marks / 40% Weightage)  
**Primary Tech Stack:** Python 3.10+, MySQL 8.0+, MongoDB 6.0+, Streamlit, Pydantic, Pytest

---

## 1. Executive Summary & Problem Formulation
When pharmaceutical products enter the consumer market, rare adverse drug reactions (ADRs) and manufacturing lot defects manifest across large patient cohorts. Regulatory bodies require strict transactional tracking of licensed manufacturers, drug formulations, batch numbers, and hospital stock distribution (ACID relational data). Simultaneously, patient-reported adverse reactions and clinical symptoms are irregular, multi-symptomatic, and polymorphic (unstructured document data).

**Pharmavigil** bridges this gap: it unites an ACID-compliant **MySQL** relational core for pharmaceutical supply chains with a high-throughput **MongoDB** document store for adverse event telemetry. The platform computes real-time signal detection, severity aggregations, and automates emergency batch recall procedures across healthcare networks.

---

## 2. Evaluation Rubric & Scoring Mapping (10 / 10 Marks)

| Criterion | Marks | Deliverable in Pharmavigil | Technical Evidence |
| :--- | :---: | :--- | :--- |
| **1. Application Design & Functionality** | **2.0** | Interactive 3-Portal Streamlit Web Application | Doctor/Patient Reporting Portal, Hospital Pharmacist Inventory Portal, Safety Officer Admin Control Center |
| **2. Python Programming Implementation** | **2.0** | Object-Oriented Design, File I/O & Custom Exceptions | Classes (`Medicine`, `Batch`, `SafetyAuditor`), CSV bulk batch intake, PDF/CSV report generation, 4 domain exceptions |
| **3. SQL & NoSQL Database Integration** | **2.0** | Hybrid Dual-Database Architecture | MySQL relational schema (7 normalized tables) + MongoDB `adverse_reports` polymorphic collection |
| **4. Advanced Database Querying** | **2.0** | Complex SQL Operations & MongoDB Aggregations | Multi-table JOINs, CTE distribution tracing, SQL Stored Procedure (`sp_recall_batch`), 6-stage MongoDB Aggregation Pipeline, Text Indexing |
| **5. Code Quality, UI & Documentation** | **1.0** | PEP 8 Modular Architecture & Streamlit UI | Clean separation into `database/`, `models/`, `services/`, `ui/`, `utils/`, type hints, docstrings, comprehensive README |
| **6. Testing, Validation & Security** | **1.0** | Input Validation, Defensive Queries & Pytest Suite | Pydantic schema validation, parameterized SQL queries, password hashing (`bcrypt`), automated test suite in `tests/` |

---

## 3. Directory Layout

```
DCDS Project/
├── app/
│   ├── config.py
│   ├── database/
│   │   ├── mysql_client.py
│   │   ├── mongo_client.py
│   │   ├── setup_mongo.py
│   │   └── seed_mongo.py
│   ├── models/
│   │   ├── medicine.py
│   │   └── schemas.py
│   ├── services/
│   │   ├── sql_service.py
│   │   ├── mongo_service.py
│   │   └── report_generator.py
│   ├── utils/
│   │   ├── exceptions.py
│   │   └── auth.py
│   └── ui/
│       ├── app.py
│       ├── page_patient.py
│       ├── page_inventory.py
│       └── page_admin.py
├── sql_scripts/
│   ├── schema.sql
│   ├── stored_procedures.sql
│   └── seed_data.sql
├── data/
│   ├── sample_batches.csv
│   └── exports/
├── tests/
│   ├── test_validation.py
│   ├── test_sql_operations.py
│   └── test_mongo_pipeline.py
├── requirements.txt
├── .env.example
├── PROJECT_PLAN.md
├── PHARMAVIGIL_PROJECT_GUIDE.md
└── README.md
```
