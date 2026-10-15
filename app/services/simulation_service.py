import hashlib
import random
from calendar import monthrange
from datetime import date
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import AccountPayable, AccountReceivable, Document, Scenario, SimulationDay, Transaction
from app.services.document_generator import generate_document
from app.services.transaction_generator import GeneratedTransaction, generate_transactions

GENERATOR_VERSION = "2.0"


def scenario_end(start: date, period_type: str) -> date:
    if period_type == "monthly":
        return date(start.year, start.month, monthrange(start.year, start.month)[1])
    return date(start.year, 12, 31)


def _generation_hash(scenario: Scenario, simulation_date: date) -> str:
    raw = f"{scenario.id}:{scenario.seed}:{scenario.version}:{GENERATOR_VERSION}:{simulation_date.isoformat()}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _last_day(db: Session, scenario_id: int) -> SimulationDay | None:
    return db.scalar(select(SimulationDay).where(SimulationDay.scenario_id == scenario_id)
                     .order_by(SimulationDay.simulation_date.desc()).limit(1))


def _add_documents(db: Session, transaction: Transaction, scenario: Scenario, origin_type: str) -> None:
    types = [origin_type]
    if transaction.status == "paid" and origin_type != "comprovante":
        types.append("comprovante")
    for document_type in types:
        number, path = generate_document(transaction, scenario.company, document_type)
        db.add(Document(transaction_id=transaction.id, document_type=document_type,
                        educational_number=number, file_path=path))


def _create_account(db: Session, scenario_id: int, transaction: Transaction) -> None:
    common = dict(scenario_id=scenario_id, source_transaction_id=transaction.id,
                  description=transaction.description, original_amount=transaction.amount,
                  outstanding_amount=transaction.amount, issue_date=transaction.issue_date,
                  due_date=transaction.due_date, status="open")
    if transaction.transaction_type == "income":
        db.add(AccountReceivable(customer_name=transaction.counterparty, **common))
    else:
        db.add(AccountPayable(supplier_name=transaction.counterparty, **common))


def _settle_due_accounts(db: Session, scenario: Scenario, simulation_date: date, limit: int) -> list[tuple[GeneratedTransaction, object]]:
    if limit <= 0:
        return []
    rng = random.Random(scenario.seed + scenario.version * 2_000_003 + simulation_date.toordinal())
    receivables = list(db.scalars(select(AccountReceivable).where(
        AccountReceivable.scenario_id == scenario.id, AccountReceivable.status.in_(["open", "overdue"]),
        AccountReceivable.due_date <= simulation_date).order_by(AccountReceivable.due_date, AccountReceivable.id)))
    payables = list(db.scalars(select(AccountPayable).where(
        AccountPayable.scenario_id == scenario.id, AccountPayable.status.in_(["open", "overdue"]),
        AccountPayable.due_date <= simulation_date).order_by(AccountPayable.due_date, AccountPayable.id)))
    candidates: list[tuple[str, object]] = [("receivable", a) for a in receivables] + [("payable", a) for a in payables]
    candidates.sort(key=lambda item: (item[1].due_date, item[1].id, item[0]))
    for _, account in candidates:
        if account.due_date < simulation_date and account.status == "open":
            account.status = "overdue"
    settled = []
    for account_type, account in candidates:
        if len(settled) >= limit:
            break
        if rng.random() >= 0.75:
            continue
        is_receivable = account_type == "receivable"
        counterparty = account.customer_name if is_receivable else account.supplier_name
        settled.append((GeneratedTransaction(
            transaction_type="income" if is_receivable else "expense",
            transaction_kind="customer_receipt" if is_receivable else "supplier_payment",
            cash_effect="in" if is_receivable else "out", dre_effect="none",
            category="Recebimentos" if is_receivable else "Fornecedores",
            description=f"Baixa de título: {account.description}", counterparty=counterparty,
            amount=account.outstanding_amount, issue_date=simulation_date, due_date=account.due_date,
            payment_date=simulation_date, status="paid", payment_method="transferência simulada",
            document_type="comprovante",
        ), account))
    return settled


def create_simulated_day(db: Session, scenario: Scenario, simulation_date: date, count: int | None) -> SimulationDay:
    if not scenario.start_date <= simulation_date <= scenario.end_date:
        raise HTTPException(422, "A data deve estar dentro do período do cenário.")
    existing = db.scalar(select(SimulationDay).where(
        SimulationDay.scenario_id == scenario.id, SimulationDay.simulation_date == simulation_date))
    if existing:
        raise HTTPException(409, "Este dia já foi gerado para o cenário.")

    previous_day = _last_day(db, scenario.id)
    if previous_day and simulation_date < previous_day.simulation_date:
        raise HTTPException(409, "Não é permitido gerar um dia anterior ao último dia do cenário.")
    opening_balance = previous_day.closing_balance if previous_day else scenario.company.opening_balance
    target_count = count or random.Random(
        scenario.seed + simulation_date.toordinal() + scenario.version * 1_000_003
    ).randint(3, 8)
    settlements = _settle_due_accounts(db, scenario, simulation_date, max(0, target_count - 3))
    specs = [item[0] for item in settlements]
    specs.extend(generate_transactions(simulation_date, scenario.seed, target_count - len(specs), scenario.version))
    cash_delta = sum((s.amount if s.cash_effect == "in" else -s.amount if s.cash_effect == "out" else Decimal("0")) for s in specs)
    day = SimulationDay(scenario_id=scenario.id, simulation_date=simulation_date,
                        opening_balance=opening_balance, closing_balance=opening_balance + cash_delta,
                        status="draft", generator_version=GENERATOR_VERSION,
                        generation_hash=_generation_hash(scenario, simulation_date),
                        summary=f"Rotina simulada com {len(specs)} movimentações administrativas e financeiras.")
    db.add(day)
    db.flush()

    settlement_accounts = {index: account for index, (_, account) in enumerate(settlements)}
    for index, spec in enumerate(specs):
        values = spec.__dict__.copy()
        document_type = values.pop("document_type")
        transaction = Transaction(day_id=day.id, **values)
        db.add(transaction)
        db.flush()
        _add_documents(db, transaction, scenario, document_type)
        if index in settlement_accounts:
            account = settlement_accounts[index]
            account.outstanding_amount = Decimal("0.00")
            account.status = "paid"
            account.settled_date = simulation_date
        elif transaction.status == "open":
            _create_account(db, scenario.id, transaction)
    db.commit()
    return db.scalar(select(SimulationDay).options(
        selectinload(SimulationDay.transactions).selectinload(Transaction.documents)
    ).where(SimulationDay.id == day.id))
