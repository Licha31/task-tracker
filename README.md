# Task Tracker

Task Tracker runs on one computer at <http://127.0.0.1:8000>. One FastAPI process serves the built React interface and `/api/*`, with `backend/payroll_tracker.db` as the live SQLite database. Daily use needs no Node process, PostgreSQL server, Docker, Railway connection, or internet access. Admin and Guest access work as before.

## First setup

These commands use Linux or WSL from the repository root. Install Python 3.14+, [uv](https://docs.astral.sh/uv/), and Node.js/npm. Node is needed to build the interface, not to run the app each day.

```bash
git clone <your-repository-url>
cd task-tracker
cp backend/.env.example backend/.env
```

Edit `backend/.env` and set a private `ADMIN_PASSWORD` and long random `ADMIN_SESSION_SECRET`. Keep `ENVIRONMENT=development` for the local HTTP cookie. The file is gitignored. Leave `DATABASE_URL` unset; the app uses `backend/payroll_tracker.db` regardless of the launch directory.

```bash
cd backend
uv sync
uv run alembic upgrade head
cd ../frontend
npm install
npm run build
cd ..
```

The Alembic command creates or upgrades the SQLite schema. Application startup never runs migrations. For an existing production database, use the one-time import below instead of initializing an empty live database. Do not delete an existing `backend/payroll_tracker.db`.

## Daily use

From the repository root:

```bash
bash scripts/start-local.sh
```

The launcher loads `backend/.env`, uses the local SQLite database, binds to `127.0.0.1:8000`, and attempts to open a browser. If browser opening fails, visit <http://127.0.0.1:8000>. Stop the server with Ctrl+C. Pass `--no-browser` to skip browser launch. On Windows with a native Python/uv installation, `powershell -ExecutionPolicy Bypass -File scripts/start-local.ps1` offers the same flow. WSL users can use the shell script.

`backend/payroll_tracker.db` is the application's real data. Keep it and its backups safe. The server only listens on this computer by default.

## Development and updates

For frontend development, run `npm run dev` in `frontend/` and set `VITE_API_URL=http://127.0.0.1:8000/api` in `frontend/.env` if needed. Run the backend separately with `uv run uvicorn app.main:app --reload --host 127.0.0.1` from `backend/`, with `backend/.env` loaded into that shell. The normal built frontend defaults to same-origin `/api`; the PDF download uses the same setting. CORS remains available for the separate Vite development server. Admin sessions use a signed, HttpOnly, SameSite=lax cookie over local HTTP.

Checks:

```bash
cd backend
uv sync
uv run pytest
uv run ruff check .
uv run alembic upgrade head
cd ../frontend
npm install
npm test
npm run build
npm audit
```

After changing frontend code, run `npm run build` again and restart FastAPI. Daily startup does not install packages, build the frontend, or migrate the database.

To update source, stop the app, back up the database, run `git pull`, `uv sync` in `backend/`, `npm install` in `frontend/` if the lockfile changed, `npm run build` in `frontend/`, and `uv run alembic upgrade head` in `backend/`. Then restart the app. Keep the existing database.

## SQLite backup and restore

Stop the app before copying the SQLite file. From the repository root:

```bash
bash scripts/backup-db.sh
```

The script creates a unique `backups/task-tracker-YYYY-MM-DD-HHMMSS.db` file, checks that the source exists, and prints the backup path. `backups/` is gitignored. No automatic schedule or retention is configured.

To restore, stop the app, rename `backend/payroll_tracker.db` to a safety filename, copy the selected backup to `backend/payroll_tracker.db`, then start the app and verify Clients, Weekly, Calendar, and a previously changed status. Keep the safety copy until verification passes.

## One-time PostgreSQL to SQLite import

The importer reads the PostgreSQL source in a read-only, repeatable-read transaction. It builds a separate SQLite file with the existing Alembic revisions, imports companies, schedules, registrations, legacy profiles, and tasks with their IDs, then compares every copied row and runs `PRAGMA foreign_key_check`. It also validates task sources, company ownership, statuses, and relationships. It never writes to PostgreSQL or copies its `alembic_version` row. Stop the app before replacing an existing local database.

Only for the one-time migration, install the optional PostgreSQL driver:

```bash
cd backend
uv sync --extra migration
export SOURCE_DATABASE_URL='postgresql://user:password@host/database'
uv run --extra migration python -m tools.migrate_postgres_to_sqlite
unset SOURCE_DATABASE_URL
```

Supply the source URL privately at execution time, never in a committed file. The command refuses an existing target. Add `--overwrite` only when intentionally replacing it; the importer first writes and verifies a timestamped backup of the existing SQLite file. The imported file is installed only after validation succeeds. The default target is `backend/payroll_tracker.db`; `--target /path/to/file.db` is available for a rehearsal. The source must already use the current application schema. Do not run this command against the live Railway database until the manual checklist below is ready. After migration, `uv sync` without the extra removes the optional PostgreSQL runtime dependency.

## Railway decommission checklist

Railway is not changed by this repository or by the importer. Perform these steps manually:

1. Ensure the latest code is committed and pushed to GitHub.
2. Create a final `pg_dump` backup from Railway PostgreSQL.
3. Store the dump somewhere safe.
4. Stop the Task Tracker app temporarily if necessary to avoid writes during final migration. Reads can generate tasks, so prevent those too.
5. Run the PostgreSQL to SQLite migration utility with the explicit source URL.
6. Confirm migration validation passes.
7. Compare source and target row counts for every copied table.
8. Start the self-hosted application.
9. Verify Admin login.
10. Verify Clients and client editing.
11. Verify Weekly.
12. Verify Calendar.
13. Verify multiple Payroll schedules.
14. Verify multiple Sales Tax jurisdictions.
15. Change one task status.
16. Restart the local application.
17. Confirm the changed status persisted.
18. Generate a monthly PDF.
19. Verify the PDF contents.
20. Create the first SQLite backup.
21. Use the local application for a short validation period.
22. Only after all checks pass, manually stop or delete the Railway frontend, backend, and PostgreSQL services.
23. Keep the final PostgreSQL dump for disaster recovery.
