from fastapi import APIRouter

from app.api import dashboard, payroll_calculation, payroll_rules, payslips, timesheets, verification

api_router = APIRouter()
api_router.include_router(dashboard.router)
api_router.include_router(timesheets.router)
api_router.include_router(payroll_rules.router)
api_router.include_router(payslips.router)
api_router.include_router(verification.router)
api_router.include_router(payroll_calculation.router)
