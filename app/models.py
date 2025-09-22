from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, BigInteger, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Usuario(Base):
    __tablename__ = "usuarios"
    
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    senha_hash = Column(String(255), nullable=False)
    tipo_usuario = Column(String(20), nullable=False)  # "analista" ou "cliente"
    administrador = Column(Boolean, default=False)
    empresa = Column(String(200))
    cnpj = Column(String(18))
    email_confirmado = Column(Boolean, default=False)
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    sessoes_como_analista = relationship("SessaoRemota", foreign_keys="SessaoRemota.analista_id", back_populates="analista")
    sessoes_como_cliente = relationship("SessaoRemota", foreign_keys="SessaoRemota.cliente_id", back_populates="cliente")
    mensagens = relationship("MensagemChat", back_populates="usuario")

class SessaoRemota(Base):
    __tablename__ = "sessoes_remotas"
    
    id = Column(Integer, primary_key=True, index=True)
    analista_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    cliente_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    codigo_acesso = Column(String(10), nullable=False, index=True)
    maquina_cliente = Column(String(255))
    inicio = Column(DateTime, default=datetime.utcnow)
    termino = Column(DateTime, nullable=True)
    trafego_bytes = Column(BigInteger, default=0)
    
    # Relacionamentos
    analista = relationship("Usuario", foreign_keys=[analista_id], back_populates="sessoes_como_analista")
    cliente = relationship("Usuario", foreign_keys=[cliente_id], back_populates="sessoes_como_cliente")
    mensagens = relationship("MensagemChat", back_populates="sessao")

class MensagemChat(Base):
    __tablename__ = "mensagens_chat"
    
    id = Column(Integer, primary_key=True, index=True)
    sessao_id = Column(Integer, ForeignKey("sessoes_remotas.id"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    mensagem = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    sessao = relationship("SessaoRemota", back_populates="mensagens")
    usuario = relationship("Usuario", back_populates="mensagens")


class EmailConfirmation(Base):
    __tablename__ = "email_confirmations"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    token = Column(String(128), unique=True, index=True, nullable=False)
    criado_em = Column(DateTime, default=datetime.utcnow)
    expira_em = Column(DateTime, nullable=False)
    confirmado = Column(Boolean, default=False)

    usuario = relationship("Usuario")