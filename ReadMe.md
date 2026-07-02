# Payguide

Frontend prototype for a payroll verification SaaS application, built with React, TypeScript, Vite, Tailwind CSS, and React Router.

## Run locally

```bash
npm install
npm run dev
```

All data is mocked. No backend or document processing is connected yet.

## Backend

The FastAPI/PostgreSQL backend foundation lives in [`backend/`](backend/README.md). Its payslip and verification endpoints currently return mock data; PDF extraction, AI, and LangGraph execution are intentionally deferred.
