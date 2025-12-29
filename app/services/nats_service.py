from nats.aio.client import Client
import logging
import json
from typing import Callable, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class NATSService:
    def __init__(self, nats_url: str):
        self.nats_url = nats_url
        self.nc: Optional[Client] = None
    
    async def connect(self):
        try:
            self.nc = Client()
            await self.nc.connect(self.nats_url)
            logger.info(f"Подключено к NATS: {self.nats_url}")
        except Exception as e:
            logger.error(f"Ошибка подключения к NATS: {e}")
            raise
    
    async def disconnect(self):
        if self.nc:
            try:
                await self.nc.close()
                logger.info("Отключено от NATS")
            except Exception as e:
                logger.error(f"Ошибка отключения от NATS: {e}")
    
    async def publish(self, subject: str, message: dict):
        if not self.nc:
            logger.warning("NATS не подключен")
            return
        
        try:
            payload = json.dumps(message).encode()
            await self.nc.publish(subject, payload)
            logger.debug(f"Опубликовано в {subject}: {message}")
        except Exception as e:
            logger.error(f"Ошибка публикации: {e}")
    
    async def subscribe(self, subject: str, callback: Callable):
        if not self.nc:
            logger.warning("NATS не подключен, лол")
            return
        
        async def message_handler(msg):
            try:
                data = json.loads(msg.data.decode())
                await callback(data)
            except json.JSONDecodeError:
                logger.error(f"JSON инвалид: {msg.data}")
            except Exception as e:
                logger.error(f"Ошибка управление ошибка: {e}")
        
        try:
            await self.nc.subscribe(subject, cb=message_handler)
            logger.info(f"Подписан на {subject}")
        except Exception as e:
            logger.error(f"Ошибка подписки: {e}")
    
    async def publish_currency_created(self, currency_data: dict):
        await self.publish("currency.created", {
            "event": "currency_created",
            "timestamp": datetime.utcnow().isoformat(),
            "data": currency_data
        })
    
    async def publish_currency_updated(self, currency_data: dict):
        await self.publish("currency.updated", {
            "event": "currency_updated",
            "timestamp": datetime.utcnow().isoformat(),
            "data": currency_data
        })
    
    async def publish_currency_deleted(self, currency_id: int):
        await self.publish("currency.deleted", {
            "event": "currency_deleted",
            "timestamp": datetime.utcnow().isoformat(),
            "currency_id": currency_id
        })
    
    async def publish_task_completed(self, task_data: dict):
        await self.publish("task.completed", {
            "event": "task_completed",
            "timestamp": datetime.utcnow().isoformat(),
            "data": task_data
        })

nats_service: Optional[NATSService] = None


async def init_nats(nats_url: str):
    global nats_service
    nats_service = NATSService(nats_url)
    await nats_service.connect()


async def close_nats():
    global nats_service
    if nats_service:
        await nats_service.disconnect()


def get_nats_service() -> NATSService:
    if not nats_service:
        raise RuntimeError("NATS сервис не инициализирован")
    return nats_service
