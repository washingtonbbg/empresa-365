from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    trade_name: Mapped[str] = mapped_column(String(150))
    educational_id: Mapped[str] = mapped_column(String(30), unique=True)
    business_type: Mapped[str] = mapped_column(String(100))
    city: Mapped[str] = mapped_column(String(100))
    state: Mapped[str] = mapped_column(String(2))
    opening_balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    scenarios: Mapped[list[Scenario]] = relationship(back_populates="company", cascade="all, delete-orphan")


class Scenario(Base):
    __tablename__ = "scenarios"
    __table_args__ = (UniqueConstraint("company_id", "name", "version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"))
    name: Mapped[str] = mapped_column(String(150))
    period_type: Mapped[str] = mapped_column(String(10))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    seed: Mapped[int] = mapped_column(default=365)
    version: Mapped[int] = mapped_column(default=1)
    difficulty: Mapped[str] = mapped_column(String(20), default="basic")
    status: Mapped[str] = mapped_column(String(20), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    company: Mapped[Company] = relationship(back_populates="scenarios")
    days: Mapped[list[SimulationDay]] = relationship(back_populates="scenario", cascade="all, delete-orphan")


class SimulationDay(Base):
    __tablename__ = "simulation_days"
    __table_args__ = (UniqueConstraint("scenario_id", "simulation_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenarios.id"))
    simulation_date: Mapped[date] = mapped_column(Date)
    opening_balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"))
    closing_balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"))
    status: Mapped[str] = mapped_column(String(20), default="draft")
    generator_version: Mapped[str] = mapped_column(String(20), default="1.0")
    generation_hash: Mapped[str] = mapped_column(String(64), default="")
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    summary: Mapped[str] = mapped_column(Text)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    scenario: Mapped[Scenario] = relationship(back_populates="days")
    transactions: Mapped[list[Transaction]] = relationship(back_populates="day", cascade="all, delete-orphan")


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    day_id: Mapped[int] = mapped_column(ForeignKey("simulation_days.id"))
    transaction_type: Mapped[str] = mapped_column(String(10))
    transaction_kind: Mapped[str] = mapped_column(String(40), default="other")
    cash_effect: Mapped[str] = mapped_column(String(10), default="none")
    dre_effect: Mapped[str] = mapped_column(String(20), default="none")
    category: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(String(255))
    counterparty: Mapped[str] = mapped_column(String(150))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    issue_date: Mapped[date] = mapped_column(Date)
    due_date: Mapped[date] = mapped_column(Date)
    payment_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20))
    payment_method: Mapped[str | None] = mapped_column(String(50), nullable=True)

    day: Mapped[SimulationDay] = relationship(back_populates="transactions")
    documents: Mapped[list[Document]] = relationship(back_populates="transaction", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"))
    document_type: Mapped[str] = mapped_column(String(30))
    educational_number: Mapped[str] = mapped_column(String(50), unique=True)
    file_path: Mapped[str] = mapped_column(String(500))
    mime_type: Mapped[str] = mapped_column(String(80), default="text/html")
    disclaimer: Mapped[str] = mapped_column(String(100), default="SIMULAÇÃO EDUCACIONAL")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    transaction: Mapped[Transaction] = relationship(back_populates="documents")


class AccountReceivable(Base):
    __tablename__ = "accounts_receivable"

    id: Mapped[int] = mapped_column(primary_key=True)
    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenarios.id"), index=True)
    source_transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"), unique=True)
    customer_name: Mapped[str] = mapped_column(String(150))
    description: Mapped[str] = mapped_column(String(255))
    original_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    outstanding_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    issue_date: Mapped[date] = mapped_column(Date)
    due_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="open")
    settled_date: Mapped[date | None] = mapped_column(Date, nullable=True)


class AccountPayable(Base):
    __tablename__ = "accounts_payable"

    id: Mapped[int] = mapped_column(primary_key=True)
    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenarios.id"), index=True)
    source_transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"), unique=True)
    supplier_name: Mapped[str] = mapped_column(String(150))
    description: Mapped[str] = mapped_column(String(255))
    original_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    outstanding_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    issue_date: Mapped[date] = mapped_column(Date)
    due_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="open")
    settled_date: Mapped[date | None] = mapped_column(Date, nullable=True)
