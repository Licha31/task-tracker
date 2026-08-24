# Task Tracker

Simple internal tracker for weekly Payroll and Sales Tax work.

## Stack

- Frontend: React + TypeScript + Vite
- Backend: Python + FastAPI
- Database: SQLite
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
- Payroll profiles
  - SUI ID
  - SIT ID
  - Principal owner
  - Frequency: Weekly, Biweekly, Semi-monthly, Monthly
  - Payroll platform
  - Next process date
  - Next pay date
  - Configurable Semi-monthly pay days
- Sales Tax profiles
  - Frequency: Monthly or Quarterly
  - Next due date
- Automatic task generation from client profiles
- U.S. weekends and federal holidays considered for Payroll business-day calculations

## Project structure

```text
backend/   FastAPI API, scheduling logic, SQL access and SQLite DB
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

- `ADMIN_PASSWORD`: the Admin password, validated only by FastAPI.
- `ADMIN_SESSION_SECRET`: a long random value used to sign the 12-hour Admin session.
- `ENVIRONMENT`: set to `production` on Railway so the session cookie uses `Secure`.
- `FRONTEND_ORIGINS`: comma-separated frontend origins allowed by CORS.
- `ADMIN_COOKIE_SAMESITE`: defaults to `lax`. Use `none` with `ENVIRONMENT=production` only when the frontend and backend are deployed on different sites.

Frontend variable:

- `VITE_API_URL`: full backend API URL, including `/api`.

The Admin session is stored in a signed, HttpOnly cookie. Guest access is read-only; client CRUD and task status changes require an authenticated Admin session.
