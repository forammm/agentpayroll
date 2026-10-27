# Payguide (PayGuard AI)

A full-stack payroll verification app: React/TypeScript/Vite/Tailwind frontend, FastAPI/PostgreSQL backend, a LangGraph workflow that orchestrates a deterministic payroll calculator and an LLM explanation step.

As of Prompt 6, the frontend is connected to the real backend end-to-end - timesheets, payroll rules, payslip upload/extraction, verification, and the dashboard all read and write real data. See `backend/README.md` for backend setup, migrations, and the LangGraph workflow; this file covers the frontend.

## Run locally

```bash
npm install
cp .env.example .env   # defaults already point at http://localhost:8000/api/v1
npm run dev
```

The backend must be running (see `backend/README.md`) and its CORS `PAYGUARD_FRONTEND_ORIGIN` must match wherever Vite is actually serving from (`http://localhost:5173` by default - note some environments bind Vite to the IPv6 loopback `::1` rather than `127.0.0.1`; use `localhost` if `127.0.0.1` doesn't connect).

## Testing

```bash
npm test
```

Runs the Vitest suite (`src/lib/api.test.ts`, `src/App.test.tsx`) with jsdom and React Testing Library - the central API client's request/error handling, and component-level coverage of the Upload, Dashboard, and Timesheets pages with the backend mocked. Also run:

```bash
npm run lint
npx tsc -b
```

## Known gap: no authentication

There is no login or session system anywhere in this app. Every API call is attributed to a single fixed demo user id (see `backend/scripts/seed_demo_user.py` and `src/lib/api.ts`'s `DEMO_USER_ID`). The backend does enforce per-record ownership checks wherever a request references another id (a timesheet, payslip, or verification result by its own id) - so one `user_id` cannot read or modify another's records - but nothing stops a client from simply claiming a different `user_id`, since there is no credential proving who is actually calling. **This is a production-readiness gap, not a secured multi-tenant system** - treat it as such before deploying anywhere a second real user might show up. `src/lib/api.ts` already has a single place (`authHeaders()`) where a bearer token would be attached once real auth exists.

## Backend

The FastAPI/PostgreSQL backend lives in [`backend/`](backend/README.md): payroll calculation engine, payslip PDF extraction (with OCR fallback), and the LangGraph verification workflow (deterministic calculation + LLM-generated explanation).
