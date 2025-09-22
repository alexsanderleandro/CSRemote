from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class UsuarioBase(BaseModel):
    nome: str
    email: str  # Usando str em vez de EmailStr temporariamente
    empresa: Optional[str] = None
    cnpj: Optional[str] = None

class UsuarioCreate(UsuarioBase):
    senha: str

class UsuarioCriarAnalista(UsuarioBase):
    tipo_usuario: str = "analista"
    administrador: bool = False

class Usuario(UsuarioBase):
    id: int
    tipo_usuario: str
    administrador: bool
    criado_em: datetime
    atualizado_em: datetime
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class CodigoAcesso(BaseModel):
    codigo: str
    expira_em: datetime

class IniciarSessao(BaseModel):
    codigo_acesso: str

class MensagemChatCreate(BaseModel):
    mensagem: str

class MensagemChat(BaseModel):
    id: int
    usuario_id: int
    mensagem: str
    timestamp: datetime
    usuario: Usuario
    
    class Config:
        from_attributes = True

class SessaoRemota(BaseModel):
    id: int
    analista_id: int
    cliente_id: int
    codigo_acesso: str
    maquina_cliente: Optional[str]
    inicio: datetime
    termino: Optional[datetime]
    trafego_bytes: int
    analista: Usuario
    cliente: Usuario
    
    class Config:
        from_attributes = True
