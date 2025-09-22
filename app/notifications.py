from typing import Dict, List
import json
from datetime import datetime
from fastapi import WebSocket

class NotificationManager:
    def __init__(self):
        self.user_connections: Dict[int, List[WebSocket]] = {}
    
    async def connect_user(self, user_id: int, websocket: WebSocket):
        """Conectar usuário para receber notificações"""
        await websocket.accept()
        
        if user_id not in self.user_connections:
            self.user_connections[user_id] = []
        
        self.user_connections[user_id].append(websocket)
    
    def disconnect_user(self, user_id: int, websocket: WebSocket):
        """Desconectar usuário"""
        if user_id in self.user_connections:
            self.user_connections[user_id].remove(websocket)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
    
    async def notify_user(self, user_id: int, notification: dict):
        """Enviar notificação para usuário específico"""
        if user_id in self.user_connections:
            message = json.dumps({
                "type": "notification",
                "timestamp": datetime.utcnow().isoformat(),
                **notification
            })
            
            disconnected = []
            for websocket in self.user_connections[user_id]:
                try:
                    await websocket.send_text(message)
                except:
                    disconnected.append(websocket)
            
            # Remover conexões mortas
            for ws in disconnected:
                self.user_connections[user_id].remove(ws)
    
    async def notify_session_users(self, analyst_id: int, client_id: int, notification: dict):
        """Notificar usuários de uma sessão"""
        await self.notify_user(analyst_id, notification)
        await self.notify_user(client_id, notification)

notification_manager = NotificationManager()
