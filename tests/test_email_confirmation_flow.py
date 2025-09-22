import os
import pytest

os.environ['PYTHONPATH'] = '.'

from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import Usuario, EmailConfirmation


@pytest.fixture
def client():
    return TestClient(app)


def find_confirmation_for_email(email):
    db = SessionLocal()
    try:
        user = db.query(Usuario).filter(Usuario.email == email).first()
        if not user:
            return None, None
        ec = db.query(EmailConfirmation).filter(EmailConfirmation.usuario_id == user.id).order_by(EmailConfirmation.criado_em.desc()).first()
        return user, ec
    finally:
        db.close()


def test_signup_and_confirm(client):
    email = 'pytest-confirm@example.com'

    # Ensure no leftover
    db = SessionLocal()
    try:
        old = db.query(Usuario).filter(Usuario.email == email).first()
        if old:
            db.delete(old)
            db.commit()
    finally:
        db.close()

    # Create user
    resp = client.post('/cadastro/cliente', json={
        'nome': 'PyTest',
        'email': email,
        'senha': 'testpass',
        'empresa': 'PyCo',
        'cnpj': '00.000.000/0000-00'
    })
    assert resp.status_code == 200

    user, ec = find_confirmation_for_email(email)
    assert user is not None
    assert ec is not None

    # Call confirmation endpoint
    resp2 = client.get(f'/confirm_email?token={ec.token}')
    assert resp2.status_code == 200

    # Verify DB
    db = SessionLocal()
    try:
        u = db.query(Usuario).filter(Usuario.email == email).first()
        assert u is not None
        assert u.email_confirmado == True
    finally:
        db.close()
