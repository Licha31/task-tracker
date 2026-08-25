# Task Tracker

Simple internal tracker for weekly Payroll and Sales Tax work.

## Stack

- Frontend: React + TypeScript + Vite
- Backend: Python + FastAPI
- Database: SQLite for local development; PostgreSQL for production
- Database access: explicit SQL through SQLAlchemy sessions

The project follows a SQL-first learning approach: understand the SQL operation first, then see how Python executes it.

## Current MVP

- Weekly Tracker
  - Current week by default
  - Previous / next week navigation
  - All / Payroll / Sales Tax filters
  - Pending / In Progress / Completed status
  - Status changes persist in SQLite
- Client CRUD
  - List clients
  - Add client
  - Edit client
  - Delete client
- Payroll Schedules (zero or many per company)
  - User-defined label
  - Jurisdiction
  - SUI ID
  - SIT ID
  - Principal owner
  - Frequency: Weekly, Biweekly, Semi-monthly, Monthly
  - Payroll platform
  - Next process date
  - Next pay date
  - Configurable Semi-monthly pay days
- Sales Tax Registrations (zero or many per company)
  - Jurisdiction
  - Frequency: Monthly or Quarterly
  - Next due date
- Automatic task generation from client profiles
- U.S. weekends and federal holidays considered for Payroll business-day calculations

## Project structure

```text
backend/   FastAPI API, scheduling logic, SQL access and database configuration
frontend/  React + TypeScript UI
```

## Run locally

Open two PowerShell terminals from the project root.

Copy the example environment files and set local values. Keep real secrets out of source control.

### Backend

```powershell
cd .\backend
Copy-Item .env.example .env
$env:ADMIN_PASSWORD = "your-local-admin-password"
$env:ADMIN_SESSION_SECRET = "a-long-random-local-secret"
uv sync
uv run uvicorn app.main:app --reload
```

API: `http://localhost:8000`

Docs: `http://localhost:8000/docs`

The backend reads `DATABASE_URL`. When it is unset outside production it defaults to
`sqlite:///./payroll_tracker.db`, so the existing `backend/payroll_tracker.db` remains the local
development database when the backend is started from `backend/`. You may explicitly set another
SQLite or PostgreSQL URL when needed.

Create or update a local schema explicitly before starting the API:

```powershell
uv run alembic upgrade head
```

Application startup does not create or migrate database objects.

### Frontend

```powershell
cd .\frontend
Copy-Item .env.example .env
npm install
npm run dev
```

Frontend: `http://localhost:5173`

Use `localhost` for both local services. Mixing `localhost` and `127.0.0.1` makes the browser treat the session cookie as cross-site, so authenticated API requests will not carry it with the default `SameSite=lax` setting.

## Deployment configuration

Backend variables:

- `DATABASE_URL`: required in production. Set this to Railway's PostgreSQL connection string. Both
  `postgres://` and `postgresql://` URLs are normalized to SQLAlchemy's psycopg 3 driver.
- `ADMIN_PASSWORD`: the Admin password, validated only by FastAPI.
- `ADMIN_SESSION_SECRET`: a long random value used to sign the 12-hour Admin session.
- `ENVIRONMENT`: set to `production` on Railway so the session cookie uses `Secure`.
- `FRONTEND_ORIGINS`: comma-separated frontend origins allowed by CORS.
- `ADMIN_COOKIE_SAMESITE`: defaults to `lax`. Use `none` with `ENVIRONMENT=production` only when the frontend and backend are deployed on different sites.

Production does not use or require a local database file. Schema changes are managed explicitly
with Alembic and are never run automatically by application startup.

Frontend variable:

- `VITE_API_URL`: full backend API URL, including `/api`.

The Admin session is stored in a signed, HttpOnly cookie. Guest access is read-only; client CRUD and task status changes require an authenticated Admin session.

## First production migration procedure

The existing Railway database predates Alembic. Do not run these commands until the live schema
and a restorable backup have been reviewed.

1. Put the application into a maintenance window and stop all old application instances. Task
   reads generate rows, so read traffic must also be stopped.
2. Create a Railway PostgreSQL backup and verify that it can be restored.
3. Record row counts for `companies`, `payroll_profiles`, `sales_tax_profiles`, and `tasks`.
4. Verify the live tables contain every column represented by revision `20260824_01`, including
   both semi-monthly columns. Verify the two legacy task indexes are present with these definitions:
   - `uq_tasks_payroll_occurrence` on company/type/process date for Payroll rows.
   - `uq_tasks_sales_tax_occurrence` on company/type/due date for Sales Tax rows.
5. Verify these preconditions return zero:

   ```sql
   SELECT COUNT(*)
   FROM tasks AS t
   LEFT JOIN payroll_profiles AS p ON p.company_id = t.company_id
   WHERE t.task_type = 'payroll' AND p.id IS NULL;

   SELECT COUNT(*)
   FROM tasks AS t
   LEFT JOIN sales_tax_profiles AS s ON s.company_id = t.company_id
   WHERE t.task_type = 'sales_tax' AND s.id IS NULL;
   ```

6. From `backend/`, with the reviewed Railway `DATABASE_URL` set manually, mark the verified
   legacy schema and inspect the planned revision state:

   ```powershell
   uv run alembic stamp 20260824_01
   uv run alembic current
   uv run alembic heads
   ```

7. Run the additive migration manually:

   ```powershell
   uv run alembic upgrade 20260824_02
   ```

   The migration aborts if any existing Payroll or Sales Tax task cannot be associated with its
   one legacy profile. It copies legacy IDs, writes `UNSET` jurisdictions, backfills task source
   IDs, validates the copy, replaces task occurrence indexes, and resets both PostgreSQL sequences.
8. Re-run the recorded counts and confirm that every Payroll/Sales Tax task has exactly its matching
   source ID and that the source belongs to the same company.
9. Deploy the new application and smoke-test Admin client editing plus Guest/Admin Weekly and
   Calendar views. Resolve every visible `UNSET` jurisdiction through Admin editing.

Do not include `alembic upgrade` in the Railway start command for this first migration.

## Migration rollback

Before the new application accepts configuration writes, the additive revision can be rolled back:

```powershell
uv run alembic downgrade 20260824_01
```

The downgrade validates that copied configurations still exactly match the frozen legacy rows and
that no same-company/date duplicates exist. It refuses to run if edits, archives, or additional
configurations cannot be represented without loss.

After the new schema accepts writes, do not downgrade or deploy the legacy application. Use a
forward fix. Restoring the pre-migration backup is the disaster-recovery option only when losing
all post-backup writes has been explicitly accepted.
