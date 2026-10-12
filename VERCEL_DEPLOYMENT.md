# Vercel deployment compatibility check

This repository includes `Dockerfile.vercel` for an initial Streamlit hosting
check using Vercel's beta container runtime. This path has not yet been tested
on Vercel. A successful build alone does not verify Streamlit sessions.

## Repository access

For an organization-owned repository, Vercel's GitHub import requires an
organization owner or member with repository access. An outside collaborator
cannot import it through that integration. The Hobby plan cannot deploy a
private organization repository through Git integration.

## Initial hosting check

1. Ensure the container files and the missing `Optional` import fix are present
   in the Git branch selected for deployment.
2. In Vercel, select **Add New > Project** and import the repository. Keep the
   project root at the repository root. Vercel detects `Dockerfile.vercel`.
   Do not configure a static output directory or use `streamlit run` as a build
   command; the container starts the server.
3. Deploy without database credentials first to check hosting. The app's demo
   login fallback can display the portals, but database operations will fail
   until hosted databases are configured. The local `.env` is not included.
4. Check `/_stcore/health`, load the actual page, use the demo logins, navigate
   portals, refresh, and test session behavior after idle time or reconnection.
   Check runtime logs for WebSocket failures and session resets.

## Hosted databases and full verification

Add environment variables in Vercel for the intended deployment environment:

- `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE`
- `MONGO_URI`, `MONGO_DB_NAME`, `MONGO_ADVERSE_COLLECTION`
- `APP_ENV=production`, `APP_DEBUG=false`, and a new random `APP_SECRET_KEY`

Use hosted database addresses, not `localhost`. Configure provider-required
TLS and network access, and verify connectivity before initializing data.
The MySQL SQL scripts currently use `pharmavigil_db` explicitly; align this
with the hosted database name before executing them. Initialization is an
explicit setup step, not a container startup action.

After database setup, redeploy to load environment variables and verify:

- MySQL-backed logins and all three role-specific portals.
- Adverse report submission and MongoDB search/safety signals.
- Inventory display, CSV intake, dispatch, and the recall procedure.
- PDF and CSV downloads.

Exports use `/tmp/pharmavigil/exports` in the container. They are temporary
files for immediate download, not durable cloud storage. Login includes
hardcoded demo-account fallback, so this deployment configuration is intended
for the project demo; authentication needs separate hardening before real use.

## Local container check (requires Docker)

```powershell
docker build -f Dockerfile.vercel -t pharmavigil-vercel .
docker run --rm -p 8502:80 pharmavigil-vercel
```

Open `http://localhost:8502`. This checks the container UI without connecting
to the databases on the Windows host. Use hosted database variables for full
container verification.

## References

- https://vercel.com/docs/functions/runtimes/container
- https://vercel.com/docs/functions/websockets
- https://vercel.com/docs/git/vercel-for-github
- https://vercel.com/docs/git
