import asyncio
import json
import logging
from nats.aio.client import Client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    nc = Client()
    
    try:
        await nc.connect("nats://localhost:4222")
        logger.info("Подключено к NATS")
        
        async def on_currency_created(msg):
            data = json.loads(msg.data.decode())
            logger.info(f"✅ СОЗДАНА валюта: {data}")
        
        async def on_currency_updated(msg):
            data = json.loads(msg.data.decode())
            logger.info(f"📈 ОБНОВЛЕНА валюта: {data}")
        
        async def on_currency_deleted(msg):
            data = json.loads(msg.data.decode())
            logger.info(f"❌ УДАЛЕНА валюта: {data}")
        
        async def on_task_completed(msg):
            data = json.loads(msg.data.decode())
            logger.info(f"⚡ ЗАДАЧА ЗАВЕРШЕНА: {data}")
        
        await nc.subscribe("currency.created", cb=on_currency_created)
        await nc.subscribe("currency.updated", cb=on_currency_updated)
        await nc.subscribe("currency.deleted", cb=on_currency_deleted)
        await nc.subscribe("task.completed", cb=on_task_completed)
        
        logger.info("Подписан на все уведомления изменения валют")
        logger.info("Ожидаем сообщения... (Ctrl+C для выхода)")
        
        while True:
            await asyncio.sleep(1)
    
    except KeyboardInterrupt:
        logger.info("Выключение...")
    except Exception as e:
        logger.error(f"Ошибка: {e}")
    finally:
        await nc.close()
        logger.info("Отключено от NATS")


if __name__ == "__main__":
    asyncio.run(main())
