# Pharmavigil

Pharmavigil is a medicine inventory and adverse drug reaction reporting system developed for the Database Concepts for Data Science course. It connects medicine batches, hospital distribution records, patient reports, and batch recalls in one application.

MySQL stores structured records such as medicines, batches, users, and hospital dispatches. MongoDB stores adverse reaction reports with patient details, symptoms, and clinical notes. The project demonstrates relational queries, transactions, stored procedures, document storage, and aggregation pipelines through a working web application.

**Website:** [pharmavigil.vercel.app](https://pharmavigil.vercel.app/)

## Features

- Record adverse reactions with medicine, batch, patient, and symptom details.
- View medicine stock, import batches from CSV, and record hospital dispatches.
- Identify safety signals using report frequency and severity.
- Search clinical notes and review reported symptoms.
- Recall batches, trace affected hospitals, and maintain a recall audit.
- Download safety reports as PDF and quarantine records as CSV.

## User roles

| Role | Access |
| --- | --- |
| Doctor / Patient | Submit adverse reaction reports. |
| Pharmacist | Manage inventory, record dispatches, and download permitted exports. |
| Safety Officer | Access all sections, review safety signals, and manage recalls. |

The API checks permissions for each request. Accounts are stored in MySQL, passwords are hashed, and signed cookies maintain login sessions.

## Technology stack

| Component | Technology |
| --- | --- |
| Frontend | React 19, TypeScript, Vite 8 |
| Styling | Tailwind CSS 4 |
| Charts, icons, and animations | Recharts, Lucide React, Anime.js |
| Backend | Python, FastAPI |
| Databases | MySQL, MongoDB |
| Reports | ReportLab, CSV |
| Hosting | Vercel |

React communicates with FastAPI through `/api` routes. The backend handles authentication, validation, database operations, and report generation. Database credentials are used only by the backend.

## Local setup

### Requirements

- Python 3.14 and Node.js 24, matching the deployment environment.
- MySQL 8.0 or later.
- A running MongoDB instance or an Atlas connection.
- Git and npm.

The commands below use PowerShell.

### 1. Install dependencies

```powershell
git clone https://github.com/shreyas-ghadling/pharmavigil.git
cd pharmavigil
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
npm --prefix frontend install
```

### 2. Configure the environment

From the project root:

```powershell
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Open `.env`, enter the MySQL and MongoDB connection details, and use the generated value for `SESSION_SECRET`. Keep `APP_ENV=development` for local use. The database names default to `pharmavigil_db`.

Keep `.env` private. Do not put database credentials in frontend configuration.

### 3. Prepare the databases

For a new local MySQL database, open the MySQL client from the project root:

```powershell
mysql -u root -p
```

Load the schema, stored procedures, and sample records:

```sql
SOURCE sql_scripts/schema.sql;
SOURCE sql_scripts/stored_procedures.sql;
SOURCE sql_scripts/seed_data.sql;
EXIT;
```

Create MongoDB indexes and load the sample reports:

```powershell
python -m app.database.setup_mongo
python -m app.database.seed_mongo
```

These setup scripts replace existing tables or reports. Run them only against a new local database. Skip this step when connecting to databases that are already configured.

### 4. Start the application

Start the backend from the project root:

```powershell
python -m uvicorn app.api.server:app --reload --host 127.0.0.1 --port 8000
```

In a second terminal, start the frontend:

```powershell
cd frontend
npm run dev
```

Open [localhost:5173](http://127.0.0.1:5173). Vite forwards API requests to the backend on port 8000.

To check the production build locally, run `npm run build` inside `frontend`, keep the backend running, and open [localhost:8000](http://127.0.0.1:8000).

## Testing

Run the backend tests from the project root with the virtual environment active:

```powershell
python -m pytest api_tests -q
python -m pytest tests -q
```

API tests use mocked database access. Integration tests require local MySQL and MongoDB and create a separate `pharmavigil_test` database. They stop if database isolation cannot be established.

Check the frontend:

```powershell
npm --prefix frontend run lint
npm --prefix frontend run build
```

## Deployment

Vercel uses `Dockerfile.vercel` to build React and run FastAPI in one container. The backend serves both the compiled frontend and the API. `vercel.json` sets the backend region to Mumbai (`bom1`).

Use the Container preset with the repository root as the root directory. Add the database variables from `.env.example`, a random `SESSION_SECRET`, `APP_ENV=production`, and `APP_DEBUG=false` to Vercel's environment variables. Redeploy after changing them.

Both databases must be running for the full application to work. MySQL is also required for login and account verification.

## Project structure

```text
app/
  api/          API routes and authentication
  database/     Database clients, indexes, and sample data
  models/       Data models and validation
  services/     Inventory, safety, recall, and reporting logic
  utils/        Password utilities and custom exceptions
frontend/
  src/          Pages, components, styles, and API client
sql_scripts/    MySQL schema, stored procedures, and sample data
data/           Sample CSV files
api_tests/      API tests
tests/          Database and validation tests
scripts/        Local maintenance utilities
```

## Credits

The interface is based on the TailAdmin dashboard template. Its MIT license is included in [frontend/TAILADMIN-LICENSE.md](frontend/TAILADMIN-LICENSE.md).
