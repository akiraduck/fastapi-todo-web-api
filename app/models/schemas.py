from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class CurrencyBase(BaseModel):
    base: str = Field(..., min_length=3, max_length=3, description="Базовая валюта (ISO 4217)")
    target: str = Field(..., min_length=3, max_length=3, description="Целевая валюта (ISO 4217)")
    current_rate: float = Field(..., gt=0, description="Текущий курс")


class CurrencyCreate(CurrencyBase):
    pass


class CurrencyUpdate(BaseModel):
    base: Optional[str] = Field(None, min_length=3, max_length=3)
    target: Optional[str] = Field(None, min_length=3, max_length=3)
    current_rate: Optional[float] = Field(None, gt=0)


class CurrencyResponse(CurrencyBase):
    id: int
    last_updated: datetime
    is_active: bool
    
    class Config:
        from_attributes = True


class TaskStatus(BaseModel):
    status: str = Field(..., description="Статус задачи: pending, running, completed, failed")
    last_run: Optional[datetime] = Field(None, description="Время последнего запуска")
    next_run: Optional[datetime] = Field(None, description="Время следующего запуска")
    total_runs: int = Field(0, description="Всего запусков")
    last_error: Optional[str] = Field(None, description="Последняя ошибка")


class WebSocketMessage(BaseModel):
    event_type: str = Field(..., description="Тип события: created, updated, deleted, task_completed")
    data: dict = Field(..., description="Данные события")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Время события")
