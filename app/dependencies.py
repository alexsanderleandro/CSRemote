from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from .database import get_db
from .auth import verify_token, get_user_by_email
from .models import Usuario

security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token_data = verify_token(credentials.credentials, credentials_exception)
    user = get_user_by_email(db, email=token_data.email)
    if user is None:
        raise credentials_exception
    return user


def get_current_user_from_request(request: Request, db: Session = Depends(get_db)):
    """Try to get token from cookie 'token' first, then fallback to Authorization header bearer."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = request.cookies.get('token')
    if not token:
        # Fallback to Authorization header
        auth = request.headers.get('Authorization')
        if not auth or not auth.lower().startswith('bearer '):
            raise credentials_exception
        token = auth.split(' ', 1)[1]

    token_data = verify_token(token, credentials_exception)
    user = get_user_by_email(db, email=token_data.email)
    if user is None:
        raise credentials_exception
    return user

def get_current_analyst(current_user: Usuario = Depends(get_current_user)):
    if current_user.tipo_usuario != "analista":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Analyst required."
        )
    return current_user

def get_current_admin(current_user: Usuario = Depends(get_current_user)):
    if current_user.tipo_usuario != "analista" or not current_user.administrador:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Administrator required."
        )
    return current_user

def get_current_client(current_user: Usuario = Depends(get_current_user)):
    if current_user.tipo_usuario != "cliente":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Client required."
        )
    return current_user
