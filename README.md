# 💊 Pharmavigil: Drug Adverse Reaction & Medicine Safety Tracking System

[![Course](https://img.shields.io/badge/Course-DCDS%20Lab-blue.svg)](#)
[![Python](https://img.shields.io/badge/Python-3.10%2B-green.svg)](#)
[![SQL](https://img.shields.io/badge/Database-MySQL%208.0-orange.svg)](#)
[![NoSQL](https://img.shields.io/badge/NoSQL-MongoDB%206.0%2B-green.svg)](#)
[![Framework](https://img.shields.io/badge/UI-Streamlit-red.svg)](#)

Pharmavigil is an end-to-end Pharmacovigilance and Medicine Safety Tracking System engineered for the **Database Concepts for Data Science (DCDS)** curriculum. It bridges an **ACID-compliant MySQL** relational database for physical pharmaceutical supply chains with a high-throughput **MongoDB** document store for polymorphic adverse event telemetry.

---

## 🚀 Quick Start Guide (Windows PowerShell)

All commands below are formatted to run natively in **Windows PowerShell** from the project root.

### 1. Prerequisites
- Python 3.10+ (active virtual environment at `C:\venvs\pharmavigil` or standard venv)
- MySQL Server 8.0+ running on port `3306`
- MongoDB Community Server (6.0+) running on port `27017`

### 2. Environment Configuration (.env)
Copy the configuration template:
```powershell
Copy-Item .env.example .env
```
Ensure `.env` contains your local database credentials (e.g. `MYSQL_PASSWORD`, `MYSQL_HOST=localhost`, `MONGO_URI=mongodb://localhost:27017/`).

---

## 🗄️ Database Initialization

### A. Initialize MySQL Database (Execute in Order)

> [!NOTE]
> Windows PowerShell does not support `<` shell redirection syntax. Use `mysql -e "source ..."` or execute in **MySQL Workbench**.

**Option 1: Windows PowerShell (Using mysql CLI)**
```powershell
# Adjust path to mysql.exe if different on your system
$MYSQL = "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe"

# 1. Create normalized tables, keys, and CHECK constraints
& $MYSQL -u root -p -e "source sql_scripts/schema.sql"

# 2. Create atomic sp_recall_batch stored procedure
& $MYSQL -u root -p -e "source sql_scripts/stored_procedures.sql"

# 3. Populate realistic presentation seed data
& $MYSQL -u root -p -e "source sql_scripts/seed_data.sql"
```

**Option 2: MySQL Workbench**
1. Open MySQL Workbench and connect to your local MySQL instance.
2. Open and execute `sql_scripts/schema.sql`.
3. Open and execute `sql_scripts/stored_procedures.sql`.
4. Open and execute `sql_scripts/seed_data.sql`.

---

### B. Initialize MongoDB Collections & Indexes

Run the following commands using Python from the project root:

```powershell
# 1. Setup collections and specialized indexes (Text search on notes, batch index)
python -m app.database.setup_mongo

# 2. Seed exactly 22 clinical adverse reaction documents with risk clusters
python -m app.database.seed_mongo
```

---

### C. One-Command Reset for Demo Presentation

To reset both databases to a pristine demonstration state at any time:

```powershell
python scripts/reset_demo.py
```

This reloads the MySQL relational schema, procedures, and seed data, completely empties `recall_audit` (resetting IDs), and reseeds MongoDB with exactly 22 clinical adverse reports.

---

## 🖥️ Running the Application

Launch the Streamlit multi-portal web dashboard:

```powershell
python -m streamlit run app/ui/app.py
```

Open your browser at: **[http://localhost:8501](http://localhost:8501)**

---

## 🔑 Demo Logins & Role-Based Access Control

Role authorization is strictly enforced on the server side:

| Role | Username | Password | Accessible Portal(s) |
| :--- | :--- | :--- | :--- |
| **Doctor / Patient** | `doctor_smith` | `doctor123` | **Portal 1:** Doctor & Patient Reporting Portal only |
| **Hospital Pharmacist** | `pharmacist_jane` | `pharmacist123` | **Portal 2:** Hospital Pharmacist Inventory Portal only |
| **Safety Officer / Admin** | `admin_officer` | `admin123` | **All 3 Portals:** Doctor, Pharmacist, and Safety Officer Admin Center |

*(Quick-login buttons are also provided on the login page for rapid presentation demo).*

---

## 🧪 Running Automated Tests

Run the Pytest test suite from the project root:

```powershell
python -m pytest tests/ -v
```

### Test Coverage Highlights:
- **`tests/test_validation.py`**:
  - Pydantic input boundaries (severity $1 - 5$, age $0 - 120$, batch format regex `BCH-XXX-XXXX`).
  - Domain OOP models (`Medicine`, `Batch`, `SafetyAuditor`) and custom exceptions (`ExpiredBatchDispenseError`, `RecalledBatchOperationError`).
  - **Server-Side Validation**: Rejection of mismatched batches (`BatchMedicineMismatchError`).
  - **Fail-Closed Verification**: Rejection when MySQL is unreachable or batch does not exist.
  - **Server-Side RBAC**: Authorization checks enforcing strict portal isolation for Doctor, Pharmacist, and Admin roles.
- **`tests/test_sql_operations.py`**:
  - In-memory SQLite mock testing for CTE high-risk inventory tracing.
  - Live MySQL execution of stored procedure `sp_recall_batch(IN, IN, IN, OUT, OUT)` verifying audit logging.
- **`tests/test_mongo_pipeline.py`**:
  - Live MongoDB 6-Stage Signal Detection Aggregation Pipeline (`$match` $\to$ `$unwind` $\to$ `$group` $\to$ `$match` $\to$ `$project` $\to$ `$sort`).
  - Native MongoDB Full-Text Search on doctor clinical notes (`$text: {$search: ...}`).

---

## 📁 Project Architecture

```
DCDS Project/
├── .streamlit/
│   └── config.toml                   # Light dashboard theme configuration
├── app/
│   ├── config.py                     # Environment variables & DB settings
│   ├── database/
│   │   ├── mysql_client.py           # Parameterized MySQL client & procedure runner
│   │   ├── mongo_client.py           # PyMongo driver connection manager
│   │   ├── setup_mongo.py            # MongoDB index setup script
│   │   └── seed_mongo.py             # Seeds 22 adverse reports into MongoDB
│   ├── models/
│   │   ├── medicine.py               # Domain OOP classes: Medicine, Batch, SafetyAuditor
│   │   └── schemas.py                # Pydantic validation schemas
│   ├── services/
│   │   ├── sql_service.py            # Relational queries, CTE quarantine tracing, recall caller
│   │   ├── mongo_service.py          # Document ingest, 6-stage aggregation pipeline, text search
│   │   └── report_generator.py       # CSV bulk intake and PDF/CSV Safety Audit Manifest export
│   ├── utils/
│   │   ├── auth.py                   # Bcrypt password hashing & server-side RBAC guards
│   │   └── exceptions.py             # Domain exceptions
│   └── ui/
│       ├── app.py                    # Streamlit main entrypoint & auth router
│       ├── page_patient.py           # Portal 1: Doctor/Patient adverse event reporting
│       ├── page_inventory.py         # Portal 2: Pharmacist live stock, alarms, CSV intake, dispatch
│       └── page_admin.py             # Portal 3: Safety Officer alarms, recalls, CTE table, PDF export
├── data/
│   ├── sample_batches.csv            # Sample CSV for pharmacist batch intake
│   └── exports/                      # Target directory for generated PDF/CSV audit reports
├── scripts/
│   └── reset_demo.py                 # One-command reset for MySQL and MongoDB demo state
├── sql_scripts/
│   ├── schema.sql                    # 7 normalized MySQL tables, PKs, FKs, CHECK constraints
│   ├── stored_procedures.sql         # sp_recall_batch transactional stored procedure
│   └── seed_data.sql                 # Supply chain seed data & bcrypt hashed user records
├── tests/
│   ├── conftest.py                   # Pytest fixtures & isolated test database setup
│   ├── test_validation.py            # Input validation, fail-closed & RBAC tests
│   ├── test_sql_operations.py        # SQLite mock & live MySQL stored procedure tests
│   └── test_mongo_pipeline.py        # MongoDB aggregation pipeline & text search tests
├── .env.example                      # Configuration template
├── .gitignore                        # Git ignore rules
├── requirements.txt                  # Python dependencies
├── PROJECT_PLAN.md                   # Project implementation plan & architecture rubric
└── PHARMAVIGIL_PROJECT_GUIDE.md      # Full engineering specification & viva FAQ
```
