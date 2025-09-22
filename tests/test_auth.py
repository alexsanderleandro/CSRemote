import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import get_db, Base
from app.models import Usuario
from app.auth import get_password_hash

# Banco de teste em memória
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture
def client():
    Base.metadata.create_all(bind=engine)
    yield TestClient(app)
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def test_user(client):
    db = TestingSessionLocal()
    user = Usuario(
        nome="Test User",
        email="test@example.com",
        senha_hash=get_password_hash("testpass"),
        tipo_usuario="cliente",
        administrador=False
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user

def test_register_client(client):
    response = client.post("/cadastro/cliente", json={
        "nome": "Test Client",
        "email": "client@test.com",
        "empresa": "Test Corp",
        "senha": "password123"
    })
    assert response.status_code == 200
    assert response.json()["email"] == "client@test.com"

def test_login_success(client, test_user):
    response = client.post("/token", data={
        "username": "test@example.com",
        "password": "testpass"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_login_failure(client):
    response = client.post("/token", data={
        "username": "wrong@email.com",
        "password": "wrongpass"
    })
    assert response.status_code == 401

# tests/test_sessions.py
def test_generate_access_code(client, test_user):
    # Login first
    login_response = client.post("/token", data={
        "username": "test@example.com",
        "password": "testpass"
    })
    token = login_response.json()["access_token"]
    
    # Generate access code
    response = client.post(
        "/cliente/gerar-codigo",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert "codigo" in response.json()
    assert len(response.json()["codigo"]) == 10