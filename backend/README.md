# PayGuard AI backend

FastAPI foundation for payroll verification, with payslip extraction (Prompt 4), a LangGraph verification workflow (Prompt 5), and full frontend integration (Prompt 6) - timesheet/payroll-rule CRUD, a real dashboard, and verification history.

## Setup

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

API docs: `http://127.0.0.1:8000/docs`

## Payroll calculation

The deterministic payroll calculator is exposed at:

```http
POST /api/v1/calculate-payroll
```

Request body:

```json
{ "timesheet_id": "00000000-0000-0000-0000-000000000000" }
```

Payroll rules must include normal, overtime, Saturday, Sunday, public holiday, overnight, early morning, and evening rates. The calculator does not use AI, LangGraph, OCR, or payslip extraction.

## Database migrations

Create the PostgreSQL database configured in `.env`, then run:

```powershell
alembic upgrade head
```

Two migrations exist: `0001_initial_schema.py` (every table as of Prompt 4, including the
payslip extraction fields - there was no prior migration history) and
`0002_verification_result_fields.py` (replaces the old mock-only `verification_results`
columns with the richer shape the Prompt 5 workflow persists). For future schema changes,
generate a new revision the usual way: `alembic revision --autogenerate -m "..."`.

## Payslip upload & extraction (Prompt 4)

```http
POST /api/v1/payslips/upload?user_id=<uuid>   (multipart/form-data, field name "file")
GET  /api/v1/payslips/{payslip_id}
```

A PDF is validated (type, magic bytes, size limit, corruption, encryption) and saved privately
under `PAYGUARD_UPLOAD_DIR` (default `storage/payslips/<user_id>/<payslip_id>.pdf` - never the
original filename, so there is no path traversal surface). Text-based PDFs are read directly
with PyMuPDF; scanned/image-only PDFs fall back to OCR via `pytesseract` **only if** a
Tesseract binary is actually installed on the host - otherwise the payslip is marked `FAILED`
with a clear message instead of silently failing or inventing data. Extracted fields are
parsed heuristically (regex label-matching, tolerant of a few currency/date formats and
multiple label wordings per field - see `app/services/payslip_field_parser.py`), validated for
consistency (`app/services/payslip_validation_service.py`), and stored with one of:
`UPLOADED`, `PROCESSING`, `EXTRACTED`, `NEEDS_REVIEW`, `FAILED`.

This stage only extracts and validates structured data - it does not calculate payroll or
decide under/overpayment (that remains `app/services/payroll_calculator.py` and the
verification service) and does not invoke an LLM.

**OCR on Windows/local dev:** `pytesseract` is a thin Python wrapper and needs the actual
[Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) binary on `PATH` to do anything;
without it, scanned payslips are reported as `FAILED` rather than crashing.

**Privacy & retention:** only the fields needed for verification are extracted and stored (no
bank details, addresses, or government ID numbers are retained, and raw extracted text is never
saved - just the structured fields). `app/services/payslip_retention_service.py` deletes
payslip records and files older than `PAYGUARD_PAYSLIP_RETENTION_DAYS` (default 365) when
called; there is no background scheduler in the project yet, so run it periodically yourself
(e.g. a daily cron/scheduled task) once one exists.

**Local demo user:** there is still no authentication, so every call needs an explicit
`user_id` that already exists in the `users` table. Run once after migrating:

```powershell
python scripts/seed_demo_user.py
```

This creates the fixed demo user the frontend defaults to (see `src/lib/payslipApi.ts`).

## LangGraph verification workflow (Prompt 5)

```http
POST /api/v1/verification/run      body: { "user_id": "<uuid>", "payslip_id": "<uuid>" }
GET  /api/v1/verification/{payslip_id}?user_id=<uuid>
```

`POST /run` executes `app.langgraph_app.graph.run_verification`, a 9-node LangGraph pipeline
that connects services already built in Prompts 2-4 - it contains no payroll formulas or
calculation logic of its own:

1. **validate_payslip** - reuses `app.services.payslip_validation_service.validate_extracted_fields`
   (built in Prompt 4) to check the already-extracted payslip data.
2. **minimize_pii** - builds an allowlisted, payroll-only view of the data; this is the only
   thing ever passed to the LLM in step 8.
3. **load_timesheet** - loads `Timesheet` rows for the payslip's pay period (scoped to the
   requesting user by the SQL filter itself - no cross-user mixing is possible), and reuses
   the calculator's own `validate_shift_time_range`/`validate_no_shift_overlaps`.
4. **load_payroll_rules** - reuses `app.services.payroll_rule_service.get_latest_rule` and
   `validate_required_rates`; never invents a rate that isn't on file.
5. **calculate_expected_pay** - calls `app.services.payroll_calculator.calculate_payroll_summary`
   directly, the same deterministic engine `/calculate-payroll` uses.
6. **compare_pay** - gross vs. gross, net vs. net, never mixed; computes signed differences
   against `PAYGUARD_VERIFICATION_TOLERANCE` (default $1.00).
7. **classify_result** - the only place the final status is decided: `MATCH` / `UNDERPAID` /
   `OVERPAID` / `NEEDS_REVIEW`, by explicit rule, not by the LLM. Any hard error from steps 1,
   3, 4, or 5 short-circuits straight here and forces `NEEDS_REVIEW`, skipping every later
   step - an underpayment conclusion is never reached when evidence is missing. Gross and net
   disagreeing on direction is also `NEEDS_REVIEW`, not an automatic violation.
8. **generate_explanation** - the one LLM call (`app.langgraph_app.tools.llm_client`), asking
   Claude to turn the already-decided numbers into plain English. Always runs, even for
   `NEEDS_REVIEW`. If the LLM is disabled, times out, errors, refuses, or returns something
   that fails schema validation, this step falls back to a deterministic template built only
   from the structured result - verification itself never fails because of this step.
9. **save_result** - persists via `app.services.verification_service.persist_verification_result`
   (re-running for the same payslip updates the existing row rather than duplicating it).

**LLM configuration:** set `ANTHROPIC_API_KEY` (read directly by the `anthropic` SDK - get one
at https://console.anthropic.com/). `PAYGUARD_LLM_MODEL` (default `claude-opus-5`),
`PAYGUARD_LLM_MAX_TOKENS`, `PAYGUARD_LLM_TIMEOUT_SECONDS`, and `PAYGUARD_LLM_ENABLED` (set to
`false` to always use the deterministic fallback explanation, e.g. for offline/cost-free runs)
are all in `.env.example`. **Without a key, verification still works end-to-end** - every
number and the classification are unaffected, only the explanation text falls back to a plain
template.

**Prompt injection:** the explanation call is given no tools and requests no code/SQL
execution, so there is nothing for an injected instruction to hijack even if one succeeded.
The model only ever sees the minimized payload from step 2 - never raw extracted PDF text
(Prompt 4 never retains that at all). The one quasi-freeform string that reaches the prompt,
`employer_name`, is explicitly labelled as untrusted data in the system prompt, and the
response schema (`VerificationExplanation`) has no field through which the model could alter
a number or the classification even if it tried.

**Access control:** there is still no authentication, so `user_id` is taken at face value on
every call - but the service layer independently verifies that the given `user_id` actually
owns the given `payslip_id` before doing anything else, returning 403 rather than leaking
another user's data. This is the enforcement point to swap for real auth later.

## Full-stack integration (Prompt 6)

Endpoints added/completed this stage, all consumed by the real frontend (`src/lib/api.ts`) - none of this duplicates the payroll calculator or LangGraph workflow, it only exposes and aggregates what they already produce:

```http
GET    /api/v1/timesheets/{id}            retrieve one timesheet
PUT    /api/v1/timesheets/{id}            update (body: full TimesheetCreate shape; ownership-checked by user_id)
DELETE /api/v1/timesheets/{id}?user_id=   delete (ownership-checked)
GET    /api/v1/dashboard/{user_id}        real aggregation: latest verification, hours logged in that
                                           period, and history - replaces the Prompt 2 mock
GET    /api/v1/verification?user_id=      verification history for a user, newest first
```

`GET /payroll-rules/{user_id}` and `POST /payroll-rules` were already enough for "create and update": the
model keeps payroll rules as a small version history (every `POST` records a new current rule set, and
`GET` always returns the latest), so the frontend's "Save rates" button just calls `POST` again - no
separate update endpoint was needed.

**Security review for this stage:**
- **CORS** is already scoped to a single configured origin (`PAYGUARD_FRONTEND_ORIGIN`), not a wildcard.
- **Cross-user access**: every mutation or lookup keyed by a secondary id (a timesheet, payslip, or
  verification result - not directly by `user_id`) independently verifies that id belongs to the caller's
  `user_id` and returns 403 otherwise, rather than trusting the id alone. Plain `user_id`-scoped reads
  (timesheet list, payroll rule, dashboard, verification history) need no separate check since the
  `user_id` filter itself is the only key.
- **No authentication exists.** `user_id` is taken at face value on every request - nothing cryptographically
  proves who is calling. The ownership checks above stop one claimed `user_id` from reading or modifying
  data under a *different* `user_id`, but they do not stop a client from simply claiming any `user_id` it
  wants. This is documented here as a **production-readiness gap**, not something this stage claims to
  have solved.
- **Error responses** never include stack traces or raw document content - see `app/api/verification.py`'s
  catch-all, which logs full detail server-side and returns a generic message to the client.
- **Secrets**: `ANTHROPIC_API_KEY` stays in the environment (see Prompt 5 section below), never logged or
  returned in any response.

## Testing

```powershell
pip install -r requirements-dev.txt
pytest
```

Tests run against an in-memory SQLite database (no Postgres required) using synthetic PDFs
built on the fly with PyMuPDF/Pillow (`tests/pdf_factory.py`) - no real payslips are used or
stored anywhere in this repo. Payslip extraction tests (Prompt 4) cover: text-based extraction
across more than one payslip layout, scanned PDFs without OCR available, corrupted/encrypted/
non-PDF uploads, oversized uploads, missing/inconsistent fields, duplicate-upload detection,
and API/DB persistence.

OCR itself (actually recognising text in an image) is not exercised in CI/tests since it
requires the Tesseract binary; the scanned-PDF tests instead confirm the code degrades to a
clear `FAILED` status with a warning when OCR is unavailable, which is the state of this dev
environment.

Verification workflow tests (Prompt 5) are split three ways:

- `tests/test_verification_graph.py` - the graph itself, with the LLM call mocked out via a
  `FakeExplanationClient` (see `tests/conftest.py`). Covers matching/underpaid/overpaid
  results, missing timesheets, missing payroll rules, failed extraction, overlapping shifts,
  gross/net disagreement routing to `NEEDS_REVIEW`, LLM failure fallback, DB persistence
  (including re-run updating rather than duplicating), cross-user access denial, and a prompt
  injection scenario proving an "obedient" fake model still cannot alter the deterministic
  result.
- `tests/test_llm_client.py` - the LLM wrapper's own request/response handling (successful
  parse, refusal, schema-validation failure, SDK errors, and a non-SDK `TypeError` such as the
  one raised for missing credentials) with the underlying `anthropic` client mocked - no
  network call, no API key needed.
- `tests/test_verification_api.py` - the real HTTP endpoints via FastAPI's `TestClient`,
  including the **real** `AnthropicExplanationClient` (not mocked) - since no
  `ANTHROPIC_API_KEY` is set in this environment, these genuinely exercise the documented
  fallback behavior end-to-end, plus 404/403/422 error responses, and the verification history
  endpoint (newest-first ordering, scoping).

Full-stack integration tests (Prompt 6):

- `tests/test_timesheets_api.py` - the timesheet CRUD endpoints: create/list/get/update/delete,
  a validation rejection (equal start/end time), and cross-user 403s on update/delete.
- `tests/test_dashboard_api.py` - the real dashboard aggregation: empty state for a brand-new
  user (nothing fabricated), reflecting a real verification's numbers, and history scoping
  (one user's verifications never leak into another's dashboard).
- `tests/test_end_to_end.py` - the full Prompt 6 definition-of-done flow through the real HTTP
  API in one test: create a timesheet, configure payroll rules, upload a synthetic payslip,
  confirm extraction, run verification, confirm it's independently retrievable, and confirm it
  shows up on the dashboard. This is a backend-only end-to-end test - no browser automation is
  available in this environment, so it exercises every HTTP boundary the frontend calls, but not
  the rendered UI; see the frontend's own test suite (`npm test` at the repo root) for
  component-level coverage of the UI layer, and the final report for how the UI itself was
  verified.

## Frontend tests

The frontend's own Vitest suite (`src/lib/api.test.ts`, `src/App.test.tsx`) lives at the repo
root - run `npm test` there. It covers the central API client's error/timeout handling and
component-level behavior for the Upload, Dashboard, and Timesheets pages with the backend
mocked (`vi.mock('./lib/api', ...)`).
