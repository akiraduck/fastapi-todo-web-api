from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.db.database import get_db
from app.models.schemas import CurrencyResponse, CurrencyCreate, CurrencyUpdate, TaskStatus
from app.services.currency_service import CurrencyService
from app.services.nats_service import get_nats_service
from app.tasks.background_task import (
    get_task_status,
    trigger_manual_run
)
from app.ws.ws_manager import manager
from datetime import datetime

router = APIRouter(prefix="/api", tags=["currencies"])


@router.get("/currencies", response_model=List[CurrencyResponse])
async def get_currencies(session: AsyncSession = Depends(get_db)):
    currencies = await CurrencyService.get_all(session)
    return currencies


@router.get("/currencies/{currency_id}", response_model=CurrencyResponse)
async def get_currency(currency_id: int, session: AsyncSession = Depends(get_db)):
    currency = await CurrencyService.get_by_id(session, currency_id)
    
    if not currency:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Currency not found"
        )
    
    return currency


@router.post("/currencies", response_model=CurrencyResponse, status_code=status.HTTP_201_CREATED)
async def create_currency(
    currency: CurrencyCreate,
    session: AsyncSession = Depends(get_db)
):
    db_currency = await CurrencyService.create(session, currency)
    
    if not db_currency:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create currency"
        )
    
    try:
        nats = get_nats_service()
        await nats.publish_currency_created({
            "id": db_currency.id,
            "base": db_currency.base,
            "target": db_currency.target,
            "current_rate": db_currency.current_rate,
            "last_updated": db_currency.last_updated.isoformat()
        })
    except Exception as e:
        print(f"Ошибка публикации NATS: {e}")
    
    await manager.broadcast({
        "event_type": "created",
        "data": {
            "id": db_currency.id,
            "base": db_currency.base,
            "target": db_currency.target,
            "current_rate": db_currency.current_rate,
            "last_updated": db_currency.last_updated.isoformat()
        },
        "timestamp": datetime.utcnow().isoformat()
    })
    
    return db_currency


@router.patch("/currencies/{currency_id}", response_model=CurrencyResponse)
async def update_currency(
    currency_id: int,
    currency_update: CurrencyUpdate,
    session: AsyncSession = Depends(get_db)
):
    db_currency = await CurrencyService.update(session, currency_id, currency_update)
    
    if not db_currency:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Currency not found"
        )
    
    try:
        nats = get_nats_service()
        await nats.publish_currency_updated({
            "id": db_currency.id,
            "base": db_currency.base,
            "target": db_currency.target,
            "current_rate": db_currency.current_rate,
            "last_updated": db_currency.last_updated.isoformat()
        })
    except Exception as e:
        print(f"Ошибка публикации NATS: {e}")
    
    await manager.broadcast({
        "event_type": "updated",
        "data": {
            "id": db_currency.id,
            "base": db_currency.base,
            "target": db_currency.target,
            "current_rate": db_currency.current_rate,
            "last_updated": db_currency.last_updated.isoformat()
        },
        "timestamp": datetime.utcnow().isoformat()
    })
    
    return db_currency


@router.delete("/currencies/{currency_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_currency(currency_id: int, session: AsyncSession = Depends(get_db)):
    result = await CurrencyService.delete(session, currency_id)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Currency not found"
        )
    
    try:
        nats = get_nats_service()
        await nats.publish_currency_deleted(currency_id)
    except Exception as e:
        print(f"Ошибка публикации NATS: {e}")
    
    await manager.broadcast({
        "event_type": "deleted",
        "data": {"id": currency_id},
        "timestamp": datetime.utcnow().isoformat()
    })
    
    return None


@router.post("/tasks/run")
async def run_background_task():
    try:
        await trigger_manual_run()
        return {
            "status": "triggered",
            "message": "Background task triggered successfully"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger task: {str(e)}"
        )


@router.get("/tasks/status", response_model=TaskStatus)
async def get_task_status_endpoint():
    return get_task_status()


@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "websocket_connections": manager.get_connection_count()
    }
