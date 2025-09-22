from app.database import SessionLocal, create_tables
from app.models import Usuario
from app.auth import get_password_hash


def create_or_update_admin(email: str, password: str, nome: str = "Administrador"):
    create_tables()
    db = SessionLocal()
    try:
        user = db.query(Usuario).filter(Usuario.email == email).first()
        if user:
            print(f"Atualizando usuário existente: {email}")
            user.nome = nome
            user.senha_hash = get_password_hash(password)
            user.tipo_usuario = "analista"
            user.administrador = True
        else:
            print(f"Criando novo usuário administrador: {email}")
            user = Usuario(
                nome=nome,
                email=email,
                senha_hash=get_password_hash(password),
                tipo_usuario="analista",
                administrador=True
            )
            db.add(user)
        db.commit()
        print("Operação concluída com sucesso.")
    finally:
        db.close()


if __name__ == "__main__":
    create_or_update_admin("alex@ceosoftware.com.br", "123", nome="Alex")
