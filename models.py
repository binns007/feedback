from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class SalesCustomer(Base):
    __tablename__ = 'sales_customers'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone_number = Column(String, nullable=False) 
    vehicle_name = Column(String, nullable=False)
    purchase_date = Column(DateTime, nullable=False)
    additional_notes = Column(String, nullable=True)

    feedback = relationship("Feedback", back_populates="customer")

class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey('sales_customers.id')) 
    rating = Column(Float)
    comments = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    customer = relationship("SalesCustomer", back_populates="feedback")
