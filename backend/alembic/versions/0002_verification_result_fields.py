"""verification result fields for LangGraph workflow

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-22

Replaces the old mock-only verification_results columns (expected_pay, actual_pay,
underpaid_amount, overpaid_amount, tax_deducted, notes) with the richer shape the
Prompt 5 LangGraph verification workflow persists: separate gross/net expected vs
actual, signed differences, the tolerance used, a JSON calculation breakdown, a
structured explanation, and accumulated warnings/errors. No production data depends
on the old shape - it was only ever populated by a mock service.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_verification_results_payslip_id", table_name="verification_results")
    op.drop_table("verification_results")

    op.create_table(
        "verification_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("payslip_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("payslips.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("pay_period_start", sa.Date(), nullable=True),
        sa.Column("pay_period_end", sa.Date(), nullable=True),
        sa.Column("expected_gross_pay", sa.Numeric(12, 2), nullable=True),
        sa.Column("actual_gross_pay", sa.Numeric(12, 2), nullable=True),
        sa.Column("expected_net_pay", sa.Numeric(12, 2), nullable=True),
        sa.Column("actual_net_pay", sa.Numeric(12, 2), nullable=True),
        sa.Column("gross_difference", sa.Numeric(12, 2), nullable=True),
        sa.Column("net_difference", sa.Numeric(12, 2), nullable=True),
        sa.Column("tolerance", sa.Numeric(12, 2), nullable=True),
        sa.Column("estimated_tax", sa.Numeric(12, 2), nullable=True),
        sa.Column("estimated_super", sa.Numeric(12, 2), nullable=True),
        sa.Column("deductions", sa.Numeric(12, 2), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="NEEDS_REVIEW"),
        sa.Column("calculation_breakdown", sa.JSON(), nullable=True),
        sa.Column("explanation_summary", sa.Text(), nullable=True),
        sa.Column("explanation_evidence", sa.JSON(), nullable=True),
        sa.Column("explanation_uncertainties", sa.JSON(), nullable=True),
        sa.Column("explanation_next_steps", sa.JSON(), nullable=True),
        sa.Column("warnings", sa.JSON(), nullable=True),
        sa.Column("errors", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_verification_results_payslip_id", "verification_results", ["payslip_id"], unique=True)
    op.create_index("ix_verification_results_user_id", "verification_results", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_verification_results_user_id", table_name="verification_results")
    op.drop_index("ix_verification_results_payslip_id", table_name="verification_results")
    op.drop_table("verification_results")

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
