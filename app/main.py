from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import logging
from contextlib import asynccontextmanager
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

from app.app_config import settings
from app.db.database import init_db, close_db
from app.services.nats_service import init_nats, close_nats
from app.tasks.background_task import start_background_task, stop_background_task
from app.ws.ws_manager import manager
from app.api.routes import router as api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Запускаем приложение...")
    
    await init_db()
    
    try:
        await init_nats(settings.NATS_URL)
    except Exception as e:
        logger.warning(f"Соединение NUTS профукано: {e}. Сегодня без него.")
    
    await start_background_task()
    
    logger.info("Приложение запущено")
    
    yield
    
    logger.info("Завершение работы...")
    
    await stop_background_task()
    await close_nats()
    await close_db()
    
    logger.info("Приложение выключено")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Асинхронный Backend: REST API + WebSocket + NATS + Фоновая задача",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

@app.websocket("/ws/currencies")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)

    await manager.send_personal(websocket, {
        "event_type": "connected",
        "data": {
            "message": "Connected to currency updates",
            "timestamp": datetime.utcnow().isoformat()
        }
    })
    
    try:
        while True:
            data = await websocket.receive_text()
            logger.debug(f"Получено от клиента: {data}")
            
            await manager.send_personal(websocket, {
                "event_type": "pong",
                "data": {"message": "pong"}
            })
    
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
        logger.info("WebSocket отключен")
    except Exception as e:
        logger.error(f"WebSocket ошибка: {e}")
        await manager.disconnect(websocket)


@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "websocket": "ws://localhost:8000/ws/currencies"
    }


@app.get("/ready")
async def readiness():
    return {"status": "ready"}


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
