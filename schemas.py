from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class SalesCustomerCreate(BaseModel):
    name: str
    phone_number: str
    vehicle_name: str
    purchase_date: datetime
    additional_notes: Optional[str] = None

class FeedbackResponse(BaseModel):
    id: int
    customer_id: int
    rating: float
    comments: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
