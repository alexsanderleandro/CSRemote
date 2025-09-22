# ==========================================
# WEBSOCKET PARA SINALIZAÇÃO WEBRTC
# ==========================================

# app/webrtc.py
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List
import json
import logging

logger = logging.getLogger(__name__)

class WebRTCManager:
    def __init__(self):
        self.active_connections: Dict[int, Dict[str, WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, session_id: int, user_type: str):
        """Conectar WebSocket para sinalização WebRTC"""
        await websocket.accept()
        
        if session_id not in self.active_connections:
            self.active_connections[session_id] = {}
        
        self.active_connections[session_id][user_type] = websocket
        logger.info(f"WebRTC connection established: session={session_id}, type={user_type}")
    
    def disconnect(self, session_id: int, user_type: str):
        """Desconectar WebSocket"""
        if session_id in self.active_connections:
            if user_type in self.active_connections[session_id]:
                del self.active_connections[session_id][user_type]
            
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
    
    async def relay_signal(self, session_id: int, from_type: str, message: dict):
        """Retransmitir sinal WebRTC entre analista e cliente"""
        if session_id not in self.active_connections:
            return
        
        # Determinar destinatário
        to_type = "cliente" if from_type == "analista" else "analista"
        
        if to_type in self.active_connections[session_id]:
            try:
                await self.active_connections[session_id][to_type].send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error relaying WebRTC signal: {e}")

webrtc_manager = WebRTCManager()
