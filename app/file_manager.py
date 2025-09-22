from fastapi import UploadFile, HTTPException
from fastapi.responses import FileResponse
import os
import uuid
import aiofiles
from typing import List
import mimetypes
from pathlib import Path

class FileManager:
    def __init__(self, upload_dir: str = "uploads"):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(exist_ok=True)
        
        # Tipos de arquivo permitidos
        self.allowed_extensions = {
            '.txt', '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
            '.jpg', '.jpeg', '.png', '.gif', '.zip', '.rar', '.7z'
        }
        
        # Tamanho máximo: 100MB
        self.max_file_size = 100 * 1024 * 1024
    
    async def save_file(self, file: UploadFile, session_id: int) -> dict:
        """Salvar arquivo enviado"""
        # Validar extensão
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in self.allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"File type not allowed: {file_ext}"
            )
        
        # Validar tamanho
        content = await file.read()
        if len(content) > self.max_file_size:
            raise HTTPException(
                status_code=400,
                detail="File too large (max 100MB)"
            )
        
        # Gerar nome único
        file_id = str(uuid.uuid4())
        safe_filename = f"{file_id}_{file.filename}"
        session_dir = self.upload_dir / str(session_id)
        session_dir.mkdir(exist_ok=True)
        
        file_path = session_dir / safe_filename
        
        # Salvar arquivo
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        
        return {
            "file_id": file_id,
            "filename": file.filename,
            "size": len(content),
            "path": str(file_path),
            "mime_type": mimetypes.guess_type(file.filename)[0]
        }
    
    async def get_file(self, session_id: int, file_id: str):
        """Recuperar arquivo por ID"""
        session_dir = self.upload_dir / str(session_id)
        
        # Encontrar arquivo pelo ID
        for file_path in session_dir.glob(f"{file_id}_*"):
            if file_path.is_file():
                original_name = file_path.name[37:]  # Remove UUID + _
                return FileResponse(
                    path=str(file_path),
                    filename=original_name,
                    media_type='application/octet-stream'
                )
        
        raise HTTPException(status_code=404, detail="File not found")
    
    def list_session_files(self, session_id: int) -> List[dict]:
        """Listar arquivos de uma sessão"""
        session_dir = self.upload_dir / str(session_id)
        files = []
        
        if session_dir.exists():
            for file_path in session_dir.glob("*"):
                if file_path.is_file():
                    parts = file_path.name.split('_', 1)
                    if len(parts) == 2:
                        file_id, original_name = parts
                        files.append({
                            "file_id": file_id,
                            "filename": original_name,
                            "size": file_path.stat().st_size,
                            "uploaded_at": file_path.stat().st_mtime
                        })
        
        return files

file_manager = FileManager()