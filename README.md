# Pharmavigil

Pharmavigil is a web application for tracking medicine inventory, reporting suspected adverse drug reactions, and managing batch recalls. It was developed for the Database Concepts for Data Science course to demonstrate how relational and document databases can work together in one project.

The application connects two parts of medicine safety: where a medicine batch has been distributed and what reactions have been reported after its use. Doctors and patients submit reports, pharmacists manage stock and hospital dispatches, and safety officers review report patterns and handle recalls.

**Hosted application:** [pharmavigil.vercel.app](https://pharmavigil.vercel.app/)

## What the application does

### Adverse reaction reporting

Doctors, patients, and pharmacists can submit a report through a guided form. Each report includes the medicine and batch, patient age and gender, existing conditions, observed symptoms, onset, reaction intensity, serious outcomes, and clinical notes. Users can add symptoms and conditions outside the suggested lists, record unknown onset, and report delayed reactions. Clinical fields start blank. Users review their entries before submitting and receive a report ID after submission. The authenticated submitting account is recorded separately from the declared reporting source.

Reports can include active, expired, recalled, or investigated batches. If the batch number is unknown, users can record that explicitly. When a batch is supplied, the backend checks that it exists and belongs to the selected medicine. It also validates patient details, symptoms, and severity scores before saving the report in MongoDB.

### Medicine inventory and hospital distribution

The inventory page lists medicine batches with manufacturer details, manufacturing and expiry dates, batch status, quantities distributed, and stock remaining. Users can search the records and identify expired or recalled batches.

Pharmacists can record a dispatch by selecting a batch, hospital, quantity, and dispatch date. The system checks stock availability and rejects dispatches from recalled or expired batches. Dispatches use database transactions and row locking to prevent simultaneous requests from allocating more stock than is available.

### Batch import from CSV

Pharmacists can download a sample CSV and use it to import several batches at once. The import checks required fields, dates, quantities, medicine references, and duplicate batch numbers.

If any row is invalid, the entire import is rejected. This prevents a file from being partly saved and makes it easier to correct errors before trying again.

### Safety monitoring and clinical search

Safety officers can review reported medicine and symptom combinations. The system groups adverse reports and calculates report-entry counts, average intensity, reported serious outcomes, and a review-priority score. Legacy symptom flags remain distinguishable from structured serious outcomes.

The score is calculated as **report-entry count × average intensity**. It is a project heuristic for prioritizing review, not a measure of incidence, probability of harm, or causality. Project thresholds assign urgent review at 12 or above, prioritized review at 6 or above, and routine review below 6. Recommendations call for investigation; the score cannot determine that a batch should be recalled or that a medicine is safe.

Officers can filter by minimum average intensity and report-entry count. These filters apply after aggregation, so counts and averages include lower-intensity reports across the available history. Charts and tables show the results, while clinical-note search helps locate reports containing relevant observations.

### Batch recalls and stock tracing

Safety officers can select a batch, enter a recall reason, and confirm the action. A MySQL stored procedure updates the batch status and creates an audit record containing the reason, officer name, and timestamp.

Distribution records identify hospitals that received the batch and the quantities delivered. The recall section also shows stock associated with recalled or expired batches so affected records can be reviewed. Recalled batches are blocked from further dispatch.

### Dashboard and exports

The dashboard changes according to the signed-in user's role. Inventory users see stock on hand, registered batches, batches expiring within 30 days, and distribution totals. Safety officers also see detected safety signals and recall information. Doctors and patients get a shortcut to submit a reaction report.

Safety officers can download a PDF safety audit and a CSV quarantine manifest. These exports include recall and affected-stock records. Pharmacists can download the sample CSV used for batch intake.

## User roles

| Role | Main responsibilities |
| --- | --- |
| Doctor / Patient | Submit suspected adverse reaction reports. |
| Pharmacist | Submit suspected reaction reports, review inventory, import batches, and record hospital dispatches. |
| Safety Officer | Review safety signals, search reports, manage recalls, and download audit reports. |

Accounts are stored in MySQL with hashed passwords. Signed cookies maintain login sessions, and the backend checks role permissions before allowing an operation.

## Database design

| Database | Records stored | Main operations |
| --- | --- | --- |
| MySQL | Users, manufacturers, medicines, batches, hospitals, distributions, and recall audits | Table joins, stock calculations, transactions, foreign-key checks, and a recall stored procedure |
| MongoDB | Adverse reaction reports, patient details, symptom lists, and clinical notes | Document validation, symptom aggregation, severity calculations, and indexed text search |

MySQL keeps the relationships between medicines, batches, and hospitals consistent. MongoDB allows reports to contain different symptom lists and clinical observations. The backend links the two databases by verifying medicine and batch references before accepting a report.

## Technology stack

| Component | Technology |
| --- | --- |
| Frontend | React 19, TypeScript, Vite 8 |
| Styling | Tailwind CSS 4 |
| Charts, icons, and animations | Recharts, Lucide React, Anime.js |
| Backend | Python, FastAPI |
| Databases | MySQL, MongoDB |
| Hosting | Vercel |

The React frontend sends requests to FastAPI through `/api` routes. FastAPI handles authentication, validation, database access, and exports. Database credentials stay on the backend.

## Hosting

The application is deployed on Vercel. `Dockerfile.vercel` builds the frontend and runs the backend in one container, which serves both the website and API. The backend runs in Mumbai, as configured in `vercel.json`.

MySQL is hosted on Aiven and MongoDB on Atlas. Both services must be available for the full application to work. Login and account verification also depend on MySQL.

## Development and testing

The repository includes the frontend, backend, database setup scripts, sample data, and tests. Local development uses Python 3.14 and Node.js 24. Install backend dependencies from `requirements.txt` and frontend dependencies from `frontend/package.json`, then configure a private `.env` using `.env.example` and a randomly generated `SESSION_SECRET`.

Start FastAPI on port 8000 with `python -m uvicorn app.api.server:app --reload`. Run `npm run dev` inside `frontend` to open the frontend on port 5173.

API tests run with `python -m pytest api_tests -q`. Integration tests run with `python -m pytest tests -q` and require local MySQL and MongoDB. They use a separate `pharmavigil_test` database. Frontend checks are available through `npm run lint` and `npm run build` inside `frontend`.

## Credits

The interface is based on the TailAdmin dashboard template. Its MIT license is included in [frontend/TAILADMIN-LICENSE.md](frontend/TAILADMIN-LICENSE.md).
