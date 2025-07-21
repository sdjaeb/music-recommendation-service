from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class FinancialTransaction(BaseModel):
    transaction_id: str = Field(..., example="FT-20231026-001")
    timestamp: datetime = Field(..., example="2023-10-26T14:30:00Z")
    account_id: str = Field(..., example="ACC-001")
    amount: float = Field(..., gt=0, example=150.75)
    currency: str = Field(..., max_length=3, example="USD")
    transaction_type: str = Field(..., example="debit")
    merchant_id: Optional[str] = Field(None, example="MER-XYZ")
    category: Optional[str] = Field(None, example="groceries")

class InsuranceClaim(BaseModel):
    claim_id: str = Field(..., example="IC-20231026-001")
    timestamp: datetime = Field(..., example="2023-10-26T15:00:00Z")
    policy_number: str = Field(..., example="POL-987654")
    claim_amount: float = Field(..., gt=0, example=1000.00)
    claim_type: str = Field(..., example="auto")
    claim_status: str = Field(..., example="submitted")
    customer_id: str = Field(..., example="CUST-ABC")
    incident_date: datetime = Field(..., example="2023-09-15T08:00:00Z")

class SportsEvent(BaseModel):
    event_id: str = Field(..., example="SE-20231026-001")
    timestamp: datetime = Field(..., example="2023-10-26T18:00:00Z")
    sport: str = Field(..., example="soccer")
    team_a: str = Field(..., example="Team Alpha")
    team_b: str = Field(..., example="Team Beta")
    score_a: Optional[int] = Field(None, example=2)
    score_b: Optional[int] = Field(None, example=1)
    location: Optional[str] = Field(None, example="Stadium XYZ")
    status: str = Field(..., example="finished")

class MusicEvent(BaseModel):
    event_id: str = Field(..., example="ME-20240719-001")
    user_id: int = Field(..., example=123)
    track_id: int = Field(..., example=101)
    event_type: str = Field(..., example="play") # e.g., 'play', 'skip', 'like'
    timestamp: datetime = Field(..., example="2024-07-19T22:45:00Z")