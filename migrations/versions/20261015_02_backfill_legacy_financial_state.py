"""backfill financial state from legacy transactions

Revision ID: 20261015_02
Revises: 20261015_01
"""
from decimal import Decimal

from alembic import op
import sqlalchemy as sa

revision = "20261015_02"
down_revision = "20261015_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("""
        UPDATE transactions SET
          transaction_kind = CASE
            WHEN transaction_type = 'income' AND status = 'open' THEN 'credit_sale'
            WHEN transaction_type = 'income' THEN 'cash_sale'
            WHEN status = 'open' THEN 'credit_purchase'
            ELSE 'cash_purchase' END,
          cash_effect = CASE
            WHEN status != 'paid' THEN 'none'
            WHEN transaction_type = 'income' THEN 'in' ELSE 'out' END,
          dre_effect = CASE
            WHEN transaction_type = 'income' THEN 'revenue'
            WHEN category = 'Fornecedores' THEN 'cost' ELSE 'expense' END
        WHERE transaction_kind = 'other'
    """))

    scenarios = bind.execute(sa.text("""
        SELECT s.id, c.opening_balance FROM scenarios s
        JOIN companies c ON c.id = s.company_id ORDER BY s.id
    """)).mappings()
    for scenario in scenarios:
        balance = Decimal(str(scenario["opening_balance"]))
        days = bind.execute(sa.text("""
            SELECT id FROM simulation_days WHERE scenario_id = :scenario_id ORDER BY simulation_date, id
        """), {"scenario_id": scenario["id"]}).mappings()
        for day in days:
            amounts = bind.execute(sa.text("""
                SELECT cash_effect, amount FROM transactions WHERE day_id = :day_id
            """), {"day_id": day["id"]}).mappings()
            delta = sum((Decimal(str(item["amount"])) if item["cash_effect"] == "in"
                         else -Decimal(str(item["amount"])) if item["cash_effect"] == "out"
                         else Decimal("0")) for item in amounts)
            closing = balance + delta
            bind.execute(sa.text("""
                UPDATE simulation_days SET opening_balance=:opening, closing_balance=:closing
                WHERE id=:day_id
            """), {"opening": balance, "closing": closing, "day_id": day["id"]})
            balance = closing

    bind.execute(sa.text("""
        INSERT INTO accounts_receivable
          (scenario_id, source_transaction_id, customer_name, description, original_amount,
           outstanding_amount, issue_date, due_date, status)
        SELECT d.scenario_id, t.id, t.counterparty, t.description, t.amount, t.amount,
               t.issue_date, t.due_date, 'open'
        FROM transactions t JOIN simulation_days d ON d.id=t.day_id
        WHERE t.transaction_type='income' AND t.status='open'
          AND NOT EXISTS (SELECT 1 FROM accounts_receivable a WHERE a.source_transaction_id=t.id)
    """))
    bind.execute(sa.text("""
        INSERT INTO accounts_payable
          (scenario_id, source_transaction_id, supplier_name, description, original_amount,
           outstanding_amount, issue_date, due_date, status)
        SELECT d.scenario_id, t.id, t.counterparty, t.description, t.amount, t.amount,
               t.issue_date, t.due_date, 'open'
        FROM transactions t JOIN simulation_days d ON d.id=t.day_id
        WHERE t.transaction_type='expense' AND t.status='open'
          AND NOT EXISTS (SELECT 1 FROM accounts_payable a WHERE a.source_transaction_id=t.id)
    """))


def downgrade() -> None:
    # Backfill preserves historical information and is intentionally not erased.
    pass
