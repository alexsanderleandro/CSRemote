from enum import Enum
from typing import Dict, Set

class Permission(Enum):
    VIEW_SCREEN = "view_screen"
    CONTROL_MOUSE = "control_mouse"
    CONTROL_KEYBOARD = "control_keyboard"
    TRANSFER_FILES = "transfer_files"
    RECORD_SESSION = "record_session"
    ADMIN_PANEL = "admin_panel"

class PermissionManager:
    def __init__(self):
        # Configurações padrão de permissões
        self.default_permissions: Dict[str, Set[Permission]] = {
            "cliente": {
                Permission.VIEW_SCREEN,
                Permission.TRANSFER_FILES
            },
            "analista": {
                Permission.VIEW_SCREEN,
                Permission.CONTROL_MOUSE,
                Permission.CONTROL_KEYBOARD,
                Permission.TRANSFER_FILES,
                Permission.RECORD_SESSION
            },
            "admin": {
                Permission.VIEW_SCREEN,
                Permission.CONTROL_MOUSE,
                Permission.CONTROL_KEYBOARD,
                Permission.TRANSFER_FILES,
                Permission.RECORD_SESSION,
                Permission.ADMIN_PANEL
            }
        }
        
        # Permissões específicas por sessão
        self.session_permissions: Dict[int, Dict[int, Set[Permission]]] = {}
    
    def get_user_permissions(self, user_type: str, is_admin: bool = False) -> Set[Permission]:
        """Obter permissões base do usuário"""
        if is_admin:
            return self.default_permissions["admin"]
        return self.default_permissions.get(user_type, set())
    
    def set_session_permission(self, session_id: int, user_id: int, permission: Permission, granted: bool):
        """Conceder/revogar permissão específica para sessão"""
        if session_id not in self.session_permissions:
            self.session_permissions[session_id] = {}
        
        if user_id not in self.session_permissions[session_id]:
            self.session_permissions[session_id][user_id] = set()
        
        if granted:
            self.session_permissions[session_id][user_id].add(permission)
        else:
            self.session_permissions[session_id][user_id].discard(permission)
    
    def has_permission(self, user_type: str, user_id: int, session_id: int, 
                      permission: Permission, is_admin: bool = False) -> bool:
        """Verificar se usuário tem permissão específica"""
        # Permissões base
        base_permissions = self.get_user_permissions(user_type, is_admin)
        
        # Permissões específicas da sessão
        session_perms = self.session_permissions.get(session_id, {}).get(user_id, set())
        
        return permission in base_permissions or permission in session_perms

permission_manager = PermissionManager()