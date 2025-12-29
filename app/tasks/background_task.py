import asyncio
import httpx
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal
from app.services.currency_service import CurrencyService
from app.models.models_db import Currency
from app.models.schemas import CurrencyCreate
from app.services.nats_service import get_nats_service
from app.ws.ws_manager import manager
from app.app_config import settings

logger = logging.getLogger(__name__)

target_currencies = ["EUR", "GBP", "JPY", "CNY", "INR", "CAD", "AUD", "CZK", "EGP", "RUB"]

class TaskStatus:    
    def __init__(self):
        self.status = "pending"
        self.last_run: Optional[datetime] = None
        self.next_run: Optional[datetime] = None
        self.total_runs = 0
        self.last_error: Optional[str] = None


task_status = TaskStatus()
background_task: Optional[asyncio.Task] = None
force_run_event = asyncio.Event()


async def fetch_exchange_rates() -> dict:
    try:
        currencies_str = ",".join(target_currencies)
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            url = f"https://api.frankfurter.app/latest"
            params = {
                "from": "USD",
                "to": currencies_str
            }
            
            logger.info(f"Запрос курсов: USD -> {currencies_str}")
            response = await client.get(url, params=params)
            
            logger.info(f"Статус ответа: {response.status_code}")
            
            response.raise_for_status()
            
            data = response.json()
            rates = data.get("rates", {})
            
            logger.info(f"Получено {len(rates)} курсов валют")
            logger.debug(f"Курсы: {rates}")
            
            return rates
    except httpx.RequestError as e:
        logger.error(f"HTTP request error: {e}")
        raise
    except Exception as e:
        logger.error(f"Ошибка подлавливания валют: {e}")
        raise


async def update_currencies_in_db(rates: dict):
    async with AsyncSessionLocal() as session:
        try:
            for target in target_currencies:
                if target not in rates:
                    continue
                
                rate = rates[target]
                
                existing = await CurrencyService.get_by_pair(
                    session, "USD", target
                )
                
                if existing:
                    if existing.current_rate != rate:
                        existing.current_rate = rate
                        await session.commit()
                        await session.refresh(existing)
                        
                        try:
                            nats = get_nats_service()
                            await nats.publish_currency_updated({
                                "id": existing.id,
                                "base": existing.base,
                                "target": existing.target,
                                "current_rate": existing.current_rate,
                                "last_updated": existing.last_updated.isoformat()
                            })
                        except Exception as e:
                            logger.error(f"Failed to publish NATS event: {e}")
                        
                        await manager.broadcast({
                            "event_type": "updated",
                            "data": {
                                "id": existing.id,
                                "base": existing.base,
                                "target": existing.target,
                                "current_rate": existing.current_rate,
                                "last_updated": existing.last_updated.isoformat()
                            },
                            "timestamp": datetime.utcnow().isoformat()
                        })
                else:
                    new_currency = await CurrencyService.create(
                        session,
                        CurrencyCreate(
                            base="USD",
                            target=target,
                            current_rate=rate
                        )
                    )
                    
                    if new_currency:
                        try:
                            nats = get_nats_service()
                            await nats.publish_currency_created({
                                "id": new_currency.id,
                                "base": new_currency.base,
                                "target": new_currency.target,
                                "current_rate": new_currency.current_rate,
                                "last_updated": new_currency.last_updated.isoformat()
                            })
                        except Exception as e:
                            logger.error(f"Failed to publish NATS event: {e}")
                        
                        await manager.broadcast({
                            "event_type": "created",
                            "data": {
                                "id": new_currency.id,
                                "base": new_currency.base,
                                "target": new_currency.target,
                                "current_rate": new_currency.current_rate,
                                "last_updated": new_currency.last_updated.isoformat()
                            },
                            "timestamp": datetime.utcnow().isoformat()
                        })
            
            logger.info("Database updated successfully")
        
        except Exception as e:
            logger.error(f"Error updating currencies: {e}")
            task_status.last_error = str(e)
            raise


async def background_task_worker():
    logger.info("Фоновая задача запускается")
    
    while True:
        try:
            try:
                await asyncio.wait_for(
                    force_run_event.wait(),
                    timeout=settings.BACKGROUND_TASK_INTERVAL
                )
                force_run_event.clear()
                logger.info("Запуск фоновой задачи вручную")
            except asyncio.TimeoutError:
                pass
            
            task_status.status = "running"
            task_status.last_run = datetime.utcnow()
            task_status.total_runs += 1
            
            logger.info(f"Фоновая задача: (#{task_status.total_runs})")
            
            rates = await fetch_exchange_rates()
            
            await update_currencies_in_db(rates)
            
            task_status.status = "completed"
            task_status.last_error = None
            
            try:
                nats = get_nats_service()
                await nats.publish_task_completed({
                    "total_runs": task_status.total_runs,
                    "timestamp": datetime.utcnow().isoformat(),
                    "currencies_updated": len(rates)
                })
            except Exception as e:
                logger.error(f"Задача провалена: {e}")
            
            logger.info("Фоновая задача успешно выполнена")
        
        except asyncio.CancelledError:
            logger.info("Отмена фоновой задачи")
            break
        except Exception as e:
            logger.error(f"Ошибка выполнения ФЗ: {e}")
            task_status.status = "failed"
            task_status.last_error = str(e)


async def start_background_task():
    global background_task
    
    if background_task and not background_task.done():
        logger.warning("ФЗ уже запущена")
        return
    
    background_task = asyncio.create_task(background_task_worker())
    logger.info("ФЗ запущена")


async def stop_background_task():
    global background_task
    
    if background_task:
        background_task.cancel()
        try:
            await background_task
        except asyncio.CancelledError:
            pass
        logger.info("ФЗ остановлена")


async def trigger_manual_run():
    force_run_event.set()


def get_task_status() -> dict:
    return {
        "status": task_status.status,
        "last_run": task_status.last_run.isoformat() if task_status.last_run else None,
        "next_run": task_status.next_run.isoformat() if task_status.next_run else None,
        "total_runs": task_status.total_runs,
        "last_error": task_status.last_error
    }
