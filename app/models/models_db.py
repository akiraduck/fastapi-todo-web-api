from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class Currency(Base):
    """Модель валютной пары в БД"""
    
    __tablename__ = "currencies"
    
    id = Column(Integer, primary_key=True, index=True)
    base = Column(String(3), nullable=False, index=True)
    target = Column(String(3), nullable=False, index=True)
    current_rate = Column(Float, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    def __repr__(self):
        return f"<Currency {self.base}/{self.target} = {self.current_rate}>"
