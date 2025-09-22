import os
import uuid
from datetime import datetime, timedelta
from typing import Optional

from .database import SessionLocal
from .models import EmailConfirmation, Usuario

try:
    import boto3
except Exception:
    boto3 = None

DEFAULT_EXPIRATION_MINUTES = int(os.getenv('EMAIL_CONFIRMATION_EXPIRATION_MINUTES', '60'))

def generate_confirmation_token() -> str:
    return uuid.uuid4().hex

def create_email_confirmation(usuario_id: int) -> str:
    db = SessionLocal()
    try:
        token = generate_confirmation_token()
        expira_em = datetime.utcnow() + timedelta(minutes=DEFAULT_EXPIRATION_MINUTES)
        conf = EmailConfirmation(usuario_id=usuario_id, token=token, expira_em=expira_em)
        db.add(conf)
        db.commit()
        return token
    finally:
        db.close()

def send_email(to_email: str, subject: str, body: str):
    """Enviar email: primeiro tenta AWS SES se configurado, senão loga no console."""
    # Tentar SES se boto3 disponível e AWS credenciais configuradas
    if boto3 and os.getenv('AWS_ACCESS_KEY_ID') and os.getenv('AWS_SECRET_ACCESS_KEY'):
        try:
            client = boto3.client('ses', region_name=os.getenv('AWS_REGION', 'us-east-1'))
            resp = client.send_email(
                Source=os.getenv('EMAIL_FROM', 'no-reply@example.com'),
                Destination={'ToAddresses': [to_email]},
                Message={
                    'Subject': {'Data': subject},
                    'Body': {'Html': {'Data': body}}
                }
            )
            return resp
        except Exception as e:
            print('SES send failed, falling back to console:', e)

    # Fallback: console
    print('--- EMAIL SEND (console) ---')
    print('To:', to_email)
    print('Subject:', subject)
    print('Body:', body)
    print('--- END EMAIL ---')

def send_confirmation_email(usuario_id: int):
    db = SessionLocal()
    try:
        usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
        if not usuario:
            return
        token = create_email_confirmation(usuario_id)
        confirm_url = f"{os.getenv('APP_BASE_URL','http://127.0.0.1:8000')}/confirm_email?token={token}"
        subject = 'Confirme seu e-mail - CSRemote'
        body = f"<p>Olá {usuario.nome},</p><p>Clique no link abaixo para confirmar seu e-mail:</p><p><a href=\"{confirm_url}\">Confirmar e-mail</a></p>"
        send_email(usuario.email, subject, body)
    finally:
        db.close()
