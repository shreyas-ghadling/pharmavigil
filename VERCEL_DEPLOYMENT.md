# Vercel deployment

The existing `pharmavigil` project (Priority AI workspace) hosts React and FastAPI through `Dockerfile.vercel`. Keep the Container preset, repository-root directory, and Node 24 build stage. Do not set a static output directory in project settings: FastAPI serves the compiled SPA and `/api` at the same origin.

`vercel.json` pins the backend to Mumbai (`bom1`), close to the Atlas database. MySQL connections are reused through a lazy five-connection pool per application process. Closing a borrowed connection resets its session and returns it to the pool; transactions still commit or roll back before release. Brief pool contention waits up to ten seconds before returning a database-unavailable response.

## Backend environment variables

- MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE
- MONGO_URI, MONGO_DB_NAME, MONGO_ADVERSE_COLLECTION
- SESSION_SECRET: independently generated random secret, stored as Secret
- APP_ENV=production and APP_DEBUG=false

Database credentials remain exclusively on the backend. Supply variables to the deployment's environment and redeploy after changes. A preview deployment uses the preview environment variables; production values are not automatically available to previews.

Exports are generated under `/tmp/pharmavigil/exports`, downloaded immediately, and removed afterward. They are not durable storage. API startup never seeds or resets databases.

## Release checks

1. Run TypeScript/build, lint, API contract tests, and isolated integration tests.
2. Push the migration branch and build a preview in this same project.
3. Verify login for each role, inventory, safety signals/search, exports, mobile layouts, and direct-link refresh behavior.
4. Production database checks are read-only; write tests run against isolated databases.
5. Deploy the tested commit to production and verify the public URL.

## Original version

Pre-port repository commit: `6578e2b` (Pre-port backup commit).
Previous production deployment captured before migration: `dpl_3zaHWbHYeEAxch92XHTttHy6Fw8K`.
The user also retains a local backup. Restoring that source/deployment restores the Streamlit version; the active source no longer contains Streamlit.

## Seed account hash repair

The original SQL seed had placeholder hashes masked by Streamlit's embedded demo fallback. `scripts/repair_seed_accounts.py` replaces only hashes that exactly match the known pre-port placeholders, retaining the documented account passwords. Custom or already-valid hashes are left unchanged. The default target is the local `pharmavigil_test`; `--hosted` explicitly selects the ignored hosted credential file. This is a one-time migration, not a deployment startup step.
