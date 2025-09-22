from fastapi import Request
from sqlalchemy.orm import Session
from datetime import datetime
import json

class AuditLogger:
    def __init__(self, db: Session):
        self.db = db
    
    def log_action(self, user_id: int, action: str, details: dict = None):
        """Registrar ação para auditoria"""
        # Em produção, salvar em tabela separada de auditoria
        print(f"AUDIT: User {user_id} - {action} - {json.dumps(details, default=str)}")
    
    def log_session_event(self, session_id: int, event_type: str, user_id: int, details: dict = None):
        """Registrar evento de sessão"""
        self.log_action(user_id, f"SESSION_{event_type}", {
            "session_id": session_id,
            "details": details
        })
    
    def log_file_transfer(self, session_id: int, user_id: int, filename: str, action: str):
        """Registrar transferência de arquivo"""
        self.log_action(user_id, f"FILE_{action}", {
            "session_id": session_id,
            "filename": filename
        })