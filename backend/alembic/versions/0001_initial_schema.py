"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-10-22

No earlier migrations exist for this project, so this single revision
creates the full schema as of Prompt 4 (users, timesheets, payroll_rules,
payslips - including payslip extraction fields - and verification_results).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("full_name", sa.String(150), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "timesheets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("break_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("shift_type", sa.String(40), nullable=False, server_default="normal"),
        sa.Column("hours_worked", sa.Numeric(6, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_timesheets_user_id", "timesheets", ["user_id"])

    op.create_table(
        "payroll_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("normal_rate", sa.Numeric(10, 2), nullable=False),
        sa.Column("overtime_rate", sa.Numeric(10, 2), nullable=False),
        sa.Column("saturday_rate", sa.Numeric(10, 2), nullable=False),
        sa.Column("sunday_rate", sa.Numeric(10, 2), nullable=False),
        sa.Column("public_holiday_rate", sa.Numeric(10, 2), nullable=False),
        sa.Column("overnight_rate", sa.Numeric(10, 2), nullable=False),
        sa.Column("early_morning_rate", sa.Numeric(10, 2), nullable=False),
        sa.Column("evening_rate", sa.Numeric(10, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_payroll_rules_user_id", "payroll_rules", ["user_id"])

    op.create_table(
        "payslips",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("file_hash", sa.String(64), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="UPLOADED"),
        sa.Column("used_ocr", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("employer_name", sa.String(255), nullable=True),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("pay_date", sa.Date(), nullable=True),
        sa.Column("gross_pay", sa.Numeric(12, 2), nullable=True),
        sa.Column("net_pay", sa.Numeric(12, 2), nullable=True),
        sa.Column("tax_deducted", sa.Numeric(12, 2), nullable=True),
        sa.Column("superannuation", sa.Numeric(12, 2), nullable=True),
        sa.Column("deductions", sa.Numeric(12, 2), nullable=True),
        sa.Column("ordinary_hours", sa.Numeric(6, 2), nullable=True),
        sa.Column("overtime_hours", sa.Numeric(6, 2), nullable=True),
        sa.Column("weekend_or_holiday_hours", sa.Numeric(6, 2), nullable=True),
        sa.Column("hourly_rate", sa.Numeric(10, 2), nullable=True),
        sa.Column("earnings_breakdown", sa.JSON(), nullable=True),
        sa.Column("extraction_warnings", sa.JSON(), nullable=True),
        sa.Column("extraction_errors", sa.JSON(), nullable=True),
        sa.Column("extracted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_payslips_user_id", "payslips", ["user_id"])
    op.create_index("ix_payslips_file_hash", "payslips", ["file_hash"])

    op.create_table(
        "verification_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("payslip_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("payslips.id", ondelete="CASCADE"), nullable=False),
        sa.Column("expected_pay", sa.Numeric(12, 2), nullable=False),
        sa.Column("actual_pay", sa.Numeric(12, 2), nullable=False),
        sa.Column("underpaid_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("overpaid_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("tax_deducted", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("deductions", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("status", sa.String(40), nullable=False, server_default="needs_review"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_verification_results_payslip_id", "verification_results", ["payslip_id"], unique=True)


def downgrade() -> None:
    op.drop_table("verification_results")
    op.drop_index("ix_payslips_file_hash", table_name="payslips")
    op.drop_index("ix_payslips_user_id", table_name="payslips")
    op.drop_table("payslips")
    op.drop_index("ix_payroll_rules_user_id", table_name="payroll_rules")
    op.drop_table("payroll_rules")
    op.drop_index("ix_timesheets_user_id", table_name="timesheets")
    op.drop_table("timesheets")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
