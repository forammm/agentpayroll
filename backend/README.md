# PayGuard AI backend

FastAPI foundation for payroll verification. Payslip extraction, AI, and LangGraph execution are intentionally placeholders.

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

## Database migrations

Create the PostgreSQL database configured in `.env`, then run:

```powershell
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```
