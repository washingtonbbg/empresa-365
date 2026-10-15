from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class ScenarioCreate(BaseModel):
    company_id: int
    name: str = Field(min_length=3, max_length=150)
    period_type: str = Field(pattern=r"^(monthly|annual)$")
    start_date: date
    seed: int = Field(default=365, ge=1, le=2_147_483_647)
    version: int = Field(default=1, ge=1)
    difficulty: str = Field(default="basic", pattern=r"^(basic|intermediate|advanced)$")


class ScenarioRead(BaseModel):
    id: int
    company_id: int
    name: str
    period_type: str
    start_date: date
    end_date: date
    seed: int
    version: int
    difficulty: str
    status: str
    model_config = ConfigDict(from_attributes=True)


class DayGenerateRequest(BaseModel):
    simulation_date: date
    transaction_count: int | None = Field(default=None, ge=3, le=8)


class PrimaveraDayRequest(BaseModel):
    date: date
    transaction_count: int | None = Field(default=None, ge=3, le=8)
    seed: int = Field(default=365, ge=1, le=2_147_483_647)


class DocumentRead(BaseModel):
    id: int
    document_type: str
    educational_number: str
    file_path: str
    disclaimer: str
    model_config = ConfigDict(from_attributes=True)


class TransactionRead(BaseModel):
    id: int
    transaction_type: str
    transaction_kind: str
    cash_effect: str
    dre_effect: str
    category: str
    description: str
    counterparty: str
    amount: float
    issue_date: date
    due_date: date
    payment_date: date | None
    status: str
    payment_method: str | None
    documents: list[DocumentRead]
    model_config = ConfigDict(from_attributes=True)


class DayRead(BaseModel):
    id: int
    scenario_id: int
    simulation_date: date
    opening_balance: float
    closing_balance: float
    status: str
    generator_version: str
    generation_hash: str
    summary: str
    transactions: list[TransactionRead]
    model_config = ConfigDict(from_attributes=True)


class AccountRead(BaseModel):
    id: int
    scenario_id: int
    source_transaction_id: int
    description: str
    original_amount: float
    outstanding_amount: float
    issue_date: date
    due_date: date
    status: str
    settled_date: date | None
    counterparty: str
