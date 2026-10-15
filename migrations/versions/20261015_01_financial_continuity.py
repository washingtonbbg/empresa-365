"""financial continuity, versioning and accounts

Revision ID: 20261015_01
Revises: None
"""
from alembic import op
import sqlalchemy as sa

revision = "20261015_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "companies" not in inspector.get_table_names():
        from app.core.database import Base
        from app import models  # noqa: F401
        Base.metadata.create_all(bind)
        return

    scenario_columns = {c["name"] for c in inspector.get_columns("scenarios")}
    with op.batch_alter_table("scenarios") as batch:
        if "version" not in scenario_columns:
            batch.add_column(sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
        if "difficulty" not in scenario_columns:
            batch.add_column(sa.Column("difficulty", sa.String(20), nullable=False, server_default="basic"))
        unique_names = {item.get("name") for item in inspector.get_unique_constraints("scenarios")}
        if "uq_scenario_company_name_version" not in unique_names:
            batch.create_unique_constraint("uq_scenario_company_name_version", ["company_id", "name", "version"])

    day_columns = {c["name"] for c in inspector.get_columns("simulation_days")}
    with op.batch_alter_table("simulation_days") as batch:
        additions = {
            "opening_balance": sa.Column("opening_balance", sa.Numeric(14, 2), nullable=False, server_default="0"),
            "closing_balance": sa.Column("closing_balance", sa.Numeric(14, 2), nullable=False, server_default="0"),
            "status": sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
            "generator_version": sa.Column("generator_version", sa.String(20), nullable=False, server_default="1.0"),
            "generation_hash": sa.Column("generation_hash", sa.String(64), nullable=False, server_default=""),
            "published_at": sa.Column("published_at", sa.DateTime(), nullable=True),
        }
        for name, column in additions.items():
            if name not in day_columns:
                batch.add_column(column)

    transaction_columns = {c["name"] for c in inspector.get_columns("transactions")}
    with op.batch_alter_table("transactions") as batch:
        additions = {
            "transaction_kind": sa.Column("transaction_kind", sa.String(40), nullable=False, server_default="other"),
            "cash_effect": sa.Column("cash_effect", sa.String(10), nullable=False, server_default="none"),
            "dre_effect": sa.Column("dre_effect", sa.String(20), nullable=False, server_default="none"),
        }
        for name, column in additions.items():
            if name not in transaction_columns:
                batch.add_column(column)

    metadata = sa.MetaData()
    metadata.reflect(bind=bind)
    if "accounts_receivable" not in inspector.get_table_names():
        op.create_table("accounts_receivable",
            sa.Column("id", sa.Integer(), primary_key=True), sa.Column("scenario_id", sa.Integer(), sa.ForeignKey("scenarios.id"), nullable=False),
            sa.Column("source_transaction_id", sa.Integer(), sa.ForeignKey("transactions.id"), nullable=False, unique=True),
            sa.Column("customer_name", sa.String(150), nullable=False), sa.Column("description", sa.String(255), nullable=False),
            sa.Column("original_amount", sa.Numeric(14, 2), nullable=False), sa.Column("outstanding_amount", sa.Numeric(14, 2), nullable=False),
            sa.Column("issue_date", sa.Date(), nullable=False), sa.Column("due_date", sa.Date(), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="open"), sa.Column("settled_date", sa.Date(), nullable=True))
        op.create_index("ix_accounts_receivable_scenario_id", "accounts_receivable", ["scenario_id"])
    if "accounts_payable" not in inspector.get_table_names():
        op.create_table("accounts_payable",
            sa.Column("id", sa.Integer(), primary_key=True), sa.Column("scenario_id", sa.Integer(), sa.ForeignKey("scenarios.id"), nullable=False),
            sa.Column("source_transaction_id", sa.Integer(), sa.ForeignKey("transactions.id"), nullable=False, unique=True),
            sa.Column("supplier_name", sa.String(150), nullable=False), sa.Column("description", sa.String(255), nullable=False),
            sa.Column("original_amount", sa.Numeric(14, 2), nullable=False), sa.Column("outstanding_amount", sa.Numeric(14, 2), nullable=False),
            sa.Column("issue_date", sa.Date(), nullable=False), sa.Column("due_date", sa.Date(), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="open"), sa.Column("settled_date", sa.Date(), nullable=True))
        op.create_index("ix_accounts_payable_scenario_id", "accounts_payable", ["scenario_id"])


def downgrade() -> None:
    op.drop_table("accounts_payable")
    op.drop_table("accounts_receivable")
    with op.batch_alter_table("transactions") as batch:
        batch.drop_column("dre_effect"); batch.drop_column("cash_effect"); batch.drop_column("transaction_kind")
    with op.batch_alter_table("simulation_days") as batch:
        for name in ("published_at", "generation_hash", "generator_version", "status", "closing_balance", "opening_balance"):
            batch.drop_column(name)
    with op.batch_alter_table("scenarios") as batch:
        batch.drop_constraint("uq_scenario_company_name_version", type_="unique")
        batch.drop_column("difficulty"); batch.drop_column("version")
