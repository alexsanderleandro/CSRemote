from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./csremote.db")

# Configuração especial para SQLite
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL, 
        connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    # Cria tabelas novas (não altera colunas existentes em tabelas já criadas)
    Base.metadata.create_all(bind=engine)

    # Ajuste simples de esquema para dev: adicionar coluna email_confirmado em usuarios se não existir
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            # If Alembic has been used (alembic_version table exists), skip runtime ALTERs
            tbls = [r[0] for r in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()]
            if 'alembic_version' in tbls:
                return

            # Use exec_driver_sql/text para statements driver-specific (PRAGMA/ALTER)
            res = conn.execute(text("PRAGMA table_info(usuarios)"))
            cols = [row[1] for row in res.fetchall()]
            if 'email_confirmado' not in cols:
                # ALTER TABLE is supported by SQLite to add a new column
                conn.exec_driver_sql("ALTER TABLE usuarios ADD COLUMN email_confirmado BOOLEAN DEFAULT 0")
    except Exception:
        # Não bloquear inicialização em caso de erro; em produção use alembic
        pass