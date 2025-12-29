from fastapi import WebSocket
import json
import logging
from typing import Set, Dict
from datetime import datetime

logger = logging.getLogger(__name__)


class ConnectionManager:    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.client_data: Dict[WebSocket, dict] = {}
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        self.client_data[websocket] = {"connected_at": datetime.utcnow()}
        logger.info(f"Клиент подключен. Всего: {len(self.active_connections)}")
    
    async def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        self.client_data.pop(websocket, None)
        logger.info(f"Клиент отключился. Всего: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        disconnected = set()
        
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Ошибка отправки сообщения: {e}")
                disconnected.add(connection)
        
        for connection in disconnected:
            await self.disconnect(connection)
    
    async def send_personal(self, websocket: WebSocket, message: dict):
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Ошибка отправки ЛС: {e}")
            await self.disconnect(websocket)
    
    def get_connection_count(self) -> int:
        return len(self.active_connections)


manager = ConnectionManager()
