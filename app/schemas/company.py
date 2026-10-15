from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CompanyCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    trade_name: str = Field(min_length=2, max_length=150)
    educational_id: str = Field(pattern=r"^EDU-[A-Z0-9-]{3,20}$")
    business_type: str
    city: str
    state: str = Field(min_length=2, max_length=2)
    opening_balance: Decimal = Field(default=Decimal("10000.00"), ge=0)


class CompanyRead(CompanyCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)

