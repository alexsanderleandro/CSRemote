import random
import string
from datetime import datetime, timedelta
from typing import Dict, Optional

# Storage em memória para códigos temporários
# Em produção, considere usar Redis ou banco de dados
access_codes_storage: Dict[str, dict] = {}

def generate_access_code() -> str:
    """Gera código alfanumérico de 10 caracteres"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

def create_temporary_code(cliente_id: int) -> dict:
    """Cria código temporário para cliente"""
    codigo = generate_access_code()
    expira_em = datetime.utcnow() + timedelta(minutes=10)
    
    # Remove códigos expirados do cliente
    remove_expired_codes_for_user(cliente_id)
    
    access_codes_storage[codigo] = {
        "cliente_id": cliente_id,
        "expira_em": expira_em,
        "usado": False
    }
    
    return {
        "codigo": codigo,
        "expira_em": expira_em
    }

def validate_access_code(codigo: str) -> Optional[int]:
    """Valida código de acesso e retorna cliente_id se válido"""
    if codigo not in access_codes_storage:
        return None
    
    code_data = access_codes_storage[codigo]
    
    # Verifica se não expirou
    if datetime.utcnow() > code_data["expira_em"]:
        del access_codes_storage[codigo]
        return None
    
    # Verifica se não foi usado
    if code_data["usado"]:
        return None
    
    return code_data["cliente_id"]

def mark_code_as_used(codigo: str):
    """Marca código como usado"""
    if codigo in access_codes_storage:
        access_codes_storage[codigo]["usado"] = True

def remove_expired_codes_for_user(cliente_id: int):
    """Remove códigos expirados de um usuário específico"""
    current_time = datetime.utcnow()
    codes_to_remove = []
    
    for codigo, data in access_codes_storage.items():
        if data["cliente_id"] == cliente_id and current_time > data["expira_em"]:
            codes_to_remove.append(codigo)
    
    for codigo in codes_to_remove:
        del access_codes_storage[codigo]