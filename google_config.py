"""
Configuração para Google APIs
============================

Este arquivo contém as configurações para integração com Google Drive e Gmail.
"""

import os
from typing import Dict, Any

# Configurações do Google OAuth2
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "1051222617815-jmdb2igpmhu4vhuhn92advr20qacj9vt.apps.googleusercontent.com")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "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")

# URL de redirecionamento autorizado (será configurada via variável de ambiente)
GOOGLE_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/callback")

# ID da pasta do Google Drive para monitorar
GOOGLE_DRIVE_FOLDER_ID = os.environ.get("GOOGLE_DRIVE_FOLDER_ID", "14BFqXqjV1MsQIkafQ8oWPPvKASnQLiQG")

# Email de destino para envio das transcrições
DESTINATION_EMAIL = os.environ.get("DESTINATION_EMAIL", "seu-email@gmail.com")  # Altere para seu email real

# Configurações do Gmail
GMAIL_SENDER_NAME = "API de Transcrição"

# Escopos necessários para as APIs
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.compose"
]

# Configurações de monitoramento
MONITOR_INTERVAL_SECONDS = 300  # Verificar a cada 5 minutos
MAX_FILE_SIZE_MB = 500  # Tamanho máximo de arquivo para processar

# Configurações de email
EMAIL_SUBJECT_PREFIX = "[TRANSCRIÇÃO]"
EMAIL_TEMPLATE = """
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #4285f4; color: white; padding: 15px; border-radius: 5px; }}
        .content {{ margin: 20px 0; }}
        .transcription {{ background-color: #f8f9fa; padding: 15px; border-left: 4px solid #4285f4; }}
        .footer {{ color: #666; font-size: 12px; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="header">
        <h2>🎬 Transcrição Automática Concluída</h2>
    </div>
    
    <div class="content">
        <h3>📁 Arquivo: {filename}</h3>
        <p><strong>📅 Data:</strong> {date}</p>
        <p><strong>⏱️ Duração:</strong> {duration}</p>
        <p><strong>📏 Tamanho:</strong> {size_mb} MB</p>
    </div>
    
    <div class="transcription">
        <h4>📝 Transcrição:</h4>
        <p>{transcription}</p>
    </div>
    
    <div class="footer">
        <p>Esta transcrição foi gerada automaticamente pela API de Transcrição de Vídeos.</p>
        <p>Task ID: {task_id}</p>
    </div>
</body>
</html>
"""

def get_google_credentials() -> Dict[str, Any]:
    """Retorna as configurações do Google OAuth2"""
    return {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "scopes": GOOGLE_SCOPES
    }

def get_drive_config() -> Dict[str, Any]:
    """Retorna as configurações do Google Drive"""
    return {
        "folder_id": GOOGLE_DRIVE_FOLDER_ID,
        "monitor_interval": MONITOR_INTERVAL_SECONDS,
        "max_file_size": MAX_FILE_SIZE_MB
    }

def get_email_config() -> Dict[str, Any]:
    """Retorna as configurações de email"""
    return {
        "destination_email": DESTINATION_EMAIL,
        "sender_name": GMAIL_SENDER_NAME,
        "subject_prefix": EMAIL_SUBJECT_PREFIX,
        "template": EMAIL_TEMPLATE
    } 