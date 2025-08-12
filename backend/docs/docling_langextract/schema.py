# schema.py
from pydantic import BaseModel, Field
from typing import Optional, List

class FeeTerms(BaseModel):
    management_fee: Optional[str] = None
    carry: Optional[str] = None
    hurdle_rate: Optional[str] = None
    catch_up: Optional[str] = None

class FundEntity(BaseModel):
    fund_name: Optional[str] = None
    vintage_year: Optional[int] = None
    gp_name: Optional[str] = None
    domicile: Optional[str] = None
    strategy: Optional[str] = None

class KeyContacts(BaseModel):
    name: Optional[str] = None
    title: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

class Investment(BaseModel):
    investment_name: Optional[str] = None
    investment_type: Optional[str] = None
    industry: Optional[str] = None
    country: Optional[str] = None
    currency: Optional[str] = None
    # ISO date string "YYYY-MM-DD" when available
    investment_date: Optional[str] = None
    investment_cost: Optional[float] = None
    fair_value: Optional[float] = None
    # Percentage ownership, numeric value only
    ownership: Optional[float] = None
    number_of_shares: Optional[float] = None
    # Multiple on invested capital
    moic: Optional[float] = None

class FundDocExtraction(BaseModel):
    fund: FundEntity = Field(default_factory=FundEntity)
    investment: Investment = Field(default_factory=Investment)
    fees: FeeTerms = Field(default_factory=FeeTerms)
    contacts: List[KeyContacts] = Field(default_factory=list)
    # keep traceability anchors if you want
    source_anchors: Optional[List[str]] = None
