"""Retention/deletion policy for uploaded payslips.

Payslips contain sensitive personal and financial information, so they
should not be kept indefinitely. PAYGUARD_PAYSLIP_RETENTION_DAYS (default
365) defines how long a payslip record and its stored PDF are kept before
purge_expired_payslips removes them.

This stage does not wire up a scheduler - there is no background task
runner in the project yet. Run this periodically (e.g. a daily cron/
scheduled task calling this function) once one exists; see backend/README.md.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.models.payslip import Payslip
from app.services.payslip_storage import delete_payslip_file


def purge_expired_payslips(db: Session) -> int:
    """Delete payslip records (and their files) older than the retention window.
    Returns the number of payslips purged."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.payslip_retention_days)
    expired = db.query(Payslip).filter(Payslip.created_at < cutoff).all()
    for payslip in expired:
        delete_payslip_file(payslip.file_path)
        db.delete(payslip)
    db.commit()
    return len(expired)
