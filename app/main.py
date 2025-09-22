from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, UploadFile, Response
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
from fastapi.responses import HTMLResponse
from fastapi import Request
from sqlalchemy.orm import Session
from datetime import timedelta, datetime
from typing import List, Dict
import json

from .database import get_db, create_tables
from .models import Usuario, SessaoRemota, MensagemChat
from .schemas import (
    UsuarioCreate, Usuario as UsuarioSchema, Token, CodigoAcesso,
    IniciarSessao, MensagemChatCreate, UsuarioCriarAnalista
)
from .auth import (
    authenticate_user, create_access_token, get_password_hash,
    ACCESS_TOKEN_EXPIRE_MINUTES, is_valid_analyst_email
)
from .access_codes import create_temporary_code, validate_access_code, mark_code_as_used
from .email_utils import send_confirmation_email
from .dependencies import get_current_user, get_current_analyst, get_current_admin, get_current_client, get_current_user_from_request
from .webrtc import webrtc_manager
from .file_manager import file_manager

app = FastAPI(title="CSRemote", description="Sistema de Suporte Remoto", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especificar domínios
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Templates e arquivos estáticos
BASE_DIR = Path(__file__).resolve().parent.parent
# Use absolute paths to avoid issues when the reloader changes working directory
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Criar tabelas na inicialização
@app.on_event("startup")
async def startup_event():
    create_tables()

# ==========================================
# WEBSOCKET MANAGER PARA CHAT
# ==========================================

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, session_id: int):
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append(websocket)

    def disconnect(self, websocket: WebSocket, session_id: int):
        if session_id in self.active_connections:
            self.active_connections[session_id].remove(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]

    async def send_message_to_session(self, message: str, session_id: int):
        if session_id in self.active_connections:
            for connection in self.active_connections[session_id]:
                try:
                    await connection.send_text(message)
                except:
                    pass

manager = ConnectionManager()

# ==========================================
# ROTAS DE AUTENTICAÇÃO
# ==========================================

@app.post("/token", response_model=Token)
async def login(response: Response, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    # Set HttpOnly cookie for server-side auth; also return JSON for API clients
    response.set_cookie(key="token", value=access_token, httponly=True, samesite="lax", path="/")
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/cadastro/cliente", response_model=UsuarioSchema)
async def cadastrar_cliente(usuario: UsuarioCreate, db: Session = Depends(get_db)):
    # Verificar se email já existe
    db_user = db.query(Usuario).filter(Usuario.email == usuario.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Criar novo cliente
    hashed_password = get_password_hash(usuario.senha)
    db_user = Usuario(
        nome=usuario.nome,
        email=usuario.email,
        senha_hash=hashed_password,
        tipo_usuario="cliente",
        empresa=usuario.empresa,
        cnpj=usuario.cnpj
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    # Enviar email de confirmação (assíncrono no próximo passo; aqui chamamos diretamente)
    try:
        send_confirmation_email(db_user.id)
    except Exception:
        pass
    return db_user


@app.get('/confirm_email', response_class=HTMLResponse)
async def confirm_email(request: Request):
    token = request.query_params.get('token')
    db = next(get_db())
    try:
        conf = db.query(__import__('app.models', fromlist=['EmailConfirmation']).EmailConfirmation).filter_by(token=token).first()
        if not conf:
            return templates.TemplateResponse('confirmado.html', {'request': request, 'success': False, 'message': 'Token inválido.'})
        if conf.expira_em < datetime.utcnow():
            return templates.TemplateResponse('confirmado.html', {'request': request, 'success': False, 'message': 'Token expirado.'})
        conf.confirmado = True
        # Marcar usuário como email_confirmado
        usuario = db.query(__import__('app.models', fromlist=['Usuario']).Usuario).filter_by(id=conf.usuario_id).first()
        if usuario:
            usuario.email_confirmado = True
        db.commit()
        return templates.TemplateResponse('confirmado.html', {'request': request, 'success': True, 'message': 'E-mail confirmado com sucesso.'})
    finally:
        db.close()

@app.post("/admin/criar-analista", response_model=UsuarioSchema)
async def criar_analista(
    analista: UsuarioCriarAnalista,
    current_admin: Usuario = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    # Verificar se email é válido para analista
    if not is_valid_analyst_email(analista.email):
        raise HTTPException(status_code=400, detail="Invalid email domain for analyst")
    
    # Verificar se email já existe
    db_user = db.query(Usuario).filter(Usuario.email == analista.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Criar analista com senha temporária
    temp_password = "TempPass123!"  # Deve ser alterada no primeiro login
    hashed_password = get_password_hash(temp_password)
    
    db_user = Usuario(
        nome=analista.nome,
        email=analista.email,
        senha_hash=hashed_password,
        tipo_usuario="analista",
        administrador=analista.administrador,
        empresa=analista.empresa,
        cnpj=analista.cnpj
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# ==========================================
# ROTAS DE CÓDIGO DE ACESSO
# ==========================================

@app.post("/cliente/gerar-codigo", response_model=CodigoAcesso)
async def gerar_codigo_acesso(
    current_client: Usuario = Depends(get_current_client),
    db: Session = Depends(get_db)
):
    code_data = create_temporary_code(current_client.id)
    return CodigoAcesso(codigo=code_data["codigo"], expira_em=code_data["expira_em"])

@app.post("/analista/iniciar-sessao")
async def iniciar_sessao_remota(
    sessao_data: IniciarSessao,
    current_analyst: Usuario = Depends(get_current_analyst),
    db: Session = Depends(get_db)
):
    # Validar código de acesso
    cliente_id = validate_access_code(sessao_data.codigo_acesso)
    if not cliente_id:
        raise HTTPException(status_code=400, detail="Invalid or expired access code")
    
    # Buscar cliente
    cliente = db.query(Usuario).filter(Usuario.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Marcar código como usado
    mark_code_as_used(sessao_data.codigo_acesso)
    
    # Criar sessão remota
    db_sessao = SessaoRemota(
        analista_id=current_analyst.id,
        cliente_id=cliente.id,
        codigo_acesso=sessao_data.codigo_acesso,
        maquina_cliente="Unknown"  # Será atualizado via WebRTC
    )
    db.add(db_sessao)
    db.commit()
    db.refresh(db_sessao)
    
    return {
        "sessao_id": db_sessao.id,
        "cliente": {
            "id": cliente.id,
            "nome": cliente.nome,
            "empresa": cliente.empresa
        },
        "message": "Remote session started successfully"
    }

@app.post("/sessao/{sessao_id}/encerrar")
async def encerrar_sessao(
    sessao_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Buscar sessão
    sessao = db.query(SessaoRemota).filter(SessaoRemota.id == sessao_id).first()
    if not sessao:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Verificar permissão (analista ou cliente da sessão)
    if current_user.id not in [sessao.analista_id, sessao.cliente_id]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Encerrar sessão
    sessao.termino = datetime.utcnow()
    db.commit()
    
    return {"message": "Session ended successfully"}

# ==========================================
# WEBSOCKET PARA CHAT
# ==========================================

@app.websocket("/ws/chat/{sessao_id}")
async def websocket_chat(
    websocket: WebSocket,
    sessao_id: int,
    db: Session = Depends(get_db)
):
    # Verificar se sessão existe
    sessao = db.query(SessaoRemota).filter(SessaoRemota.id == sessao_id).first()
    if not sessao:
        await websocket.close(code=4004)
        return
    
    await manager.connect(websocket, sessao_id)
    
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Verificar se usuário pertence à sessão
            usuario_id = message_data.get("usuario_id")
            if usuario_id not in [sessao.analista_id, sessao.cliente_id]:
                continue
            
            # Salvar mensagem no banco
            db_mensagem = MensagemChat(
                sessao_id=sessao_id,
                usuario_id=usuario_id,
                mensagem=message_data.get("mensagem", "")
            )
            db.add(db_mensagem)
            db.commit()
            db.refresh(db_mensagem)
            
            # Buscar dados do usuário para enviar com a mensagem
            usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
            
            # Broadcast para todos os conectados na sessão
            response_data = {
                "id": db_mensagem.id,
                "usuario_id": usuario.id,
                "usuario_nome": usuario.nome,
                "mensagem": db_mensagem.mensagem,
                "timestamp": db_mensagem.timestamp.isoformat()
            }
            
            await manager.send_message_to_session(json.dumps(response_data), sessao_id)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, sessao_id)

# ==========================================
# ROTAS ADMINISTRATIVAS
# ==========================================

@app.get("/admin/usuarios", response_model=List[UsuarioSchema])
async def listar_usuarios(
    current_admin: Usuario = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    return db.query(Usuario).all()

@app.get("/admin/sessoes")
async def relatorio_sessoes(
    current_admin: Usuario = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    sessoes = db.query(SessaoRemota).all()
    relatorio = []
    
    for sessao in sessoes:
        duracao = None
        if sessao.termino:
            duracao = (sessao.termino - sessao.inicio).total_seconds()
        
        relatorio.append({
            "id": sessao.id,
            "analista": sessao.analista.nome,
            "cliente": sessao.cliente.nome,
            "inicio": sessao.inicio,
            "termino": sessao.termino,
            "duracao_segundos": duracao,
            "trafego_bytes": sessao.trafego_bytes
        })
    
    return relatorio

@app.post("/admin/resetar-senha/{usuario_id}")
async def resetar_senha_usuario(
    usuario_id: int,
    current_admin: Usuario = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Nova senha temporária
    nova_senha = "TempPass123!"
    usuario.senha_hash = get_password_hash(nova_senha)
    db.commit()
    
    return {"message": f"Password reset for user {usuario.nome}", "temporary_password": nova_senha}

# ==========================================
# ROTAS DE INFORMAÇÕES
# ==========================================

@app.get("/me", response_model=UsuarioSchema)
async def get_user_info(current_user: Usuario = Depends(get_current_user)):
    return current_user

@app.get("/sessoes/minhas")
async def minhas_sessoes(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.tipo_usuario == "analista":
        sessoes = db.query(SessaoRemota).filter(SessaoRemota.analista_id == current_user.id).all()
    else:
        sessoes = db.query(SessaoRemota).filter(SessaoRemota.cliente_id == current_user.id).all()
    
    return [
        {
            "id": sessao.id,
            "analista": sessao.analista.nome,
            "cliente": sessao.cliente.nome,
            "inicio": sessao.inicio,
            "termino": sessao.termino,
            "codigo_acesso": sessao.codigo_acesso if current_user.tipo_usuario == "analista" else None
        }
        for sessao in sessoes
    ]

# ==========================================
# ROTA PARA ARQUIVOS WEBRTC/FRONTEND
# ==========================================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, current_user: Usuario = Depends(get_current_user_from_request)):
    # Render server-side different dashboards to avoid exposing analyst UI to clients
    ctx = {"request": request, "user": current_user}
    if current_user.tipo_usuario == 'analista':
        return templates.TemplateResponse("dashboard_analista.html", ctx)
    else:
        return templates.TemplateResponse("dashboard_cliente.html", ctx)


@app.get("/cadastro", response_class=HTMLResponse)
async def cadastro_page(request: Request):
    return templates.TemplateResponse("cadastro.html", {"request": request})

@app.get("/sessao/{sessao_id}", response_class=HTMLResponse)
async def sessao_page(request: Request, sessao_id: int):
    return templates.TemplateResponse("sessao.html", {"request": request, "sessao_id": sessao_id})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

@app.websocket("/ws/signaling/{sessao_id}")
async def websocket_signaling(
    websocket: WebSocket,
    sessao_id: int,
    db: Session = Depends(get_db)
):
    """WebSocket para sinalização WebRTC"""
    # Verificar se sessão existe
    sessao = db.query(SessaoRemota).filter(SessaoRemota.id == sessao_id).first()
    if not sessao:
        await websocket.close(code=4004)
        return
    
    # Determinar tipo de usuário (seria melhor obter do token, mas para simplicidade...)
    user_type = "cliente"  # Será determinado pela primeira mensagem
    
    try:
        await webrtc_manager.connect(websocket, sessao_id, user_type)
        
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Primeira mensagem define o tipo
            if "user_type" in message:
                # Atualizar tipo se necessário
                if user_type != message["user_type"]:
                    webrtc_manager.disconnect(sessao_id, user_type)
                    user_type = message["user_type"]
                    await webrtc_manager.connect(websocket, sessao_id, user_type)
                continue
            
            # Retransmitir sinais WebRTC
            await webrtc_manager.relay_signal(sessao_id, user_type, message)
            
    except WebSocketDisconnect:
        webrtc_manager.disconnect(sessao_id, user_type)

@app.post("/sessao/{sessao_id}/upload")
async def upload_file(
    sessao_id: int,
    file: UploadFile,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload de arquivo durante sessão"""
    # Verificar se usuário pertence à sessão
    sessao = db.query(SessaoRemota).filter(SessaoRemota.id == sessao_id).first()
    if not sessao or current_user.id not in [sessao.analista_id, sessao.cliente_id]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        file_info = await file_manager.save_file(file, sessao_id)
        return {
            "message": "File uploaded successfully",
            "file": file_info
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sessao/{sessao_id}/download/{file_id}")
async def download_file(
    sessao_id: int,
    file_id: str,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download de arquivo da sessão"""
    # Verificar permissões
    sessao = db.query(SessaoRemota).filter(SessaoRemota.id == sessao_id).first()
    if not sessao or current_user.id not in [sessao.analista_id, sessao.cliente_id]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return await file_manager.get_file(sessao_id, file_id)

@app.get("/sessao/{sessao_id}/files")
async def list_session_files(
    sessao_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Listar arquivos da sessão"""
    sessao = db.query(SessaoRemota).filter(SessaoRemota.id == sessao_id).first()
    if not sessao or current_user.id not in [sessao.analista_id, sessao.cliente_id]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    files = file_manager.list_session_files(sessao_id)
    return {"files": files}