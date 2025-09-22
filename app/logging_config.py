import logging
import sys
from datetime import datetime
import os

def setup_logging():
    """Configurar sistema de logs"""
    
    # Criar diretório de logs
    os.makedirs("logs", exist_ok=True)
    
    # Configurar formato
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Handler para arquivo
    file_handler = logging.FileHandler(
        f"logs/csremote_{datetime.now().strftime('%Y%m%d')}.log"
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    
    # Handler para console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    
    # Configurar logger raiz
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Logger específico para WebRTC
    webrtc_logger = logging.getLogger("webrtc")
    webrtc_logger.setLevel(logging.DEBUG)
    
    return root_logger