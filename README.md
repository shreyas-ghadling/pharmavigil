# Pharmavigil

Medicine inventory and pharmacovigilance workspace, built with React 19, TypeScript, Vite 8, Tailwind CSS 4, Anime.js, and FastAPI. MySQL stores medicines, batches, hospital distribution, users, and recall audits; MongoDB stores adverse reports and supports signal detection and clinical-note search.

## Workspace

- Overview: summaries and shortcuts for the signed-in role.
- Adverse reports: medication, patient details, symptoms, and review before submission.
- Inventory: batch search, shipment CSV import, and hospital dispatch.
- Safety monitoring: risk signals, filters, chart, and clinical search.
- Recalls: confirmation, affected hospital stock, and audit history.
- Reports and exports: safety audit PDF and quarantine CSV.

Doctor/patient accounts can report reactions. Pharmacists manage inventory. Safety officers can access every section. Authentication verifies MySQL password hashes; role permissions and clinical validation are enforced by the API. There is no passwordless demo-login fallback.

## Local development (PowerShell)

Activate the existing virtual environment and install backend dependencies:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Configure the backend-only `.env` using `.env.example`. Generate a random session secret:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Set `SESSION_SECRET` to that value and use `APP_ENV=development` locally. Database secrets must never be placed in frontend environment variables.

Start the API from the project root:

```powershell
python -m uvicorn app.api.server:app --reload --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173. Vite proxies `/api` to port 8000. To test the production frontend locally, run `npm run build` and open http://127.0.0.1:8000; FastAPI serves `frontend/dist` and supports SPA deep links.

## Verification

```powershell
python -m pytest api_tests -q
python -m pytest tests -q
cd frontend
npm run lint
npm run build
```

API contract tests mock database access. Integration tests initialize only `pharmavigil_test` and stop if isolation cannot be established. Never run reset or seeding scripts against hosted data as part of deployment.

## Deployment

The existing Vercel project uses `Dockerfile.vercel`: a Node build stage compiles React, then a Python stage serves assets and the same-origin FastAPI API. See `VERCEL_DEPLOYMENT.md` for environment variables and rollback information.

The Streamlit UI and configuration have been removed. The pre-port Git commit and the user's local backup retain the original version.

## Layout

- `frontend/src`: React pages, shared components, API client, styles, and types.
- `app/api`: HTTP endpoints and signed-cookie sessions.
- `app/services`, `app/models`, `app/database`: shared business rules and persistence.
- `sql_scripts`: schema, stored procedure, and seed data for explicit database setup.
- `tests`, `api_tests`: database integration and API contract coverage.

TailAdmin supplied the visual reference. Its MIT attribution is retained in `frontend/TAILADMIN-LICENSE.md`. Project-local skills, design-reference files, install metadata, and local credentials are ignored by Git.
