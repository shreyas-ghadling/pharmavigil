# Pharmavigil frontend

React 19 + TypeScript + Vite 8 + Tailwind CSS 4. The SPA in `frontend/` calls the same-origin FastAPI server in `app/api/`. Visual structure follows TailAdmin with Outfit typography and blue/white dashboard styling. License attribution: `frontend/TAILADMIN-LICENSE.md`.

Navigation: overview, adverse reports, inventory, safety monitoring, recalls, reports and exports. Doctor/patient and pharmacist roles have restricted menus; the API enforces those restrictions independently. All data comes from the existing MySQL and MongoDB services. Never send database credentials to the browser.

Run `npm run dev` inside `frontend/` and `python -m uvicorn app.api.server:app --reload` from the project root. Vite proxies `/api` to port 8000. Build and lint with `npm run build` and `npm run lint`. Pages and the chart are lazy-loaded. Anime.js handles drawer opening and respects reduced-motion preferences.

See README for test commands and VERCEL_DEPLOYMENT for the same-project release procedure.
