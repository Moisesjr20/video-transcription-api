"""
Serviço do Gmail
================

Este módulo fornece funcionalidades para enviar emails via Gmail API.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import base64
import pickle
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from google_config import get_google_credentials, get_email_config, GOOGLE_SCOPES

logger = logging.getLogger(__name__)

class GmailService:
    """Serviço para enviar emails via Gmail API"""
    
    def __init__(self):
        self.creds = None
        self.service = None
        self.token_file = 'gmail_token.pickle'
        self.credentials_file = 'gmail_credentials.json'
        
        # Configurações
        self.google_creds = get_google_credentials()
        self.email_config = get_email_config()
        
        # Inicializar serviço
        self.initialize_service()
    
    def initialize_service(self):
        """Inicializa o serviço do Gmail"""
        try:
            # Carregar credenciais
            self.creds = self.get_credentials()
            
            if self.creds and self.creds.valid:
                # Construir serviço
                self.service = build('gmail', 'v1', credentials=self.creds)
                logger.info("✅ Serviço do Gmail inicializado com sucesso")
            else:
                logger.error("❌ Falha ao inicializar serviço do Gmail")
                
        except Exception as e:
            logger.error(f"Erro ao inicializar serviço do Gmail: {e}")
    
    def get_credentials(self) -> Optional[Credentials]:
        """Obtém credenciais do Gmail"""
        try:
            # Verificar se já temos token salvo
            if os.path.exists(self.token_file):
                with open(self.token_file, 'rb') as token:
                    self.creds = pickle.load(token)
            
            # Se não há credenciais válidas, fazer autenticação
            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    self.creds.refresh(Request())
                else:
                    # Criar arquivo de credenciais temporário
                    self.create_credentials_file()
                    
                    # Fazer fluxo de autenticação
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, 
                        GOOGLE_SCOPES
                    )
                    self.creds = flow.run_local_server(port=0)
                
                # Salvar credenciais para próximo uso
                with open(self.token_file, 'wb') as token:
                    pickle.dump(self.creds, token)
            
            return self.creds
            
        except Exception as e:
            logger.error(f"Erro ao obter credenciais do Gmail: {e}")
            return None
    
    def create_credentials_file(self):
        """Cria arquivo de credenciais temporário para Gmail"""
        try:
            credentials_data = {
                "installed": {
                    "client_id": self.google_creds['client_id'],
                    "project_id": "video-transcription-api",
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_secret": self.google_creds['client_secret'],
                    "redirect_uris": [self.google_creds['redirect_uri']]
                }
            }
            
            import json
            with open(self.credentials_file, 'w') as f:
                json.dump(credentials_data, f)
                
            logger.info("📄 Arquivo de credenciais do Gmail criado")
            
        except Exception as e:
            logger.error(f"Erro ao criar arquivo de credenciais do Gmail: {e}")
    
    def create_message(self, to_email: str, subject: str, html_content: str) -> Dict[str, Any]:
        """Cria mensagem de email"""
        try:
            message = MIMEMultipart('alternative')
            message['to'] = to_email
            message['subject'] = subject
            
            # Adicionar conteúdo HTML
            html_part = MIMEText(html_content, 'html')
            message.attach(html_part)
            
            # Codificar mensagem
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            return {'raw': raw_message}
            
        except Exception as e:
            logger.error(f"Erro ao criar mensagem: {e}")
            return None
    
    async def send_transcription_email(self, to_email: str, subject: str, email_data: Dict[str, Any]):
        """Envia email com transcrição"""
        try:
            if not self.service:
                logger.error("Serviço do Gmail não inicializado")
                return False
            
            # Preparar conteúdo HTML
            html_content = self.email_config['template'].format(
                filename=email_data.get('filename', 'Arquivo desconhecido'),
                date=email_data.get('date', 'Data desconhecida'),
                duration=email_data.get('duration', 'Duração desconhecida'),
                size_mb=email_data.get('size_mb', 'Tamanho desconhecido'),
                transcription=email_data.get('transcription', 'Transcrição não disponível'),
                task_id=email_data.get('task_id', 'N/A')
            )
            
            # Criar mensagem
            message = self.create_message(to_email, subject, html_content)
            
            if not message:
                logger.error("Falha ao criar mensagem")
                return False
            
            # Enviar email
            sent_message = self.service.users().messages().send(
                userId='me',
                body=message
            ).execute()
            
            logger.info(f"📧 Email enviado com sucesso: {sent_message.get('id')}")
            return True
            
        except HttpError as error:
            logger.error(f"Erro HTTP do Gmail: {error}")
            return False
        except Exception as e:
            logger.error(f"Erro ao enviar email: {e}")
            return False
    
    async def send_simple_email(self, to_email: str, subject: str, body: str) -> bool:
        """Envia email simples"""
        try:
            if not self.service:
                return False
            
            # Criar mensagem simples
            message = MIMEText(body)
            message['to'] = to_email
            message['subject'] = subject
            
            # Codificar e enviar
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            sent_message = self.service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            logger.info(f"📧 Email simples enviado: {sent_message.get('id')}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao enviar email simples: {e}")
            return False
    
    async def test_connection(self) -> bool:
        """Testa conexão com Gmail"""
        try:
            if not self.service:
                return False
            
            # Tentar obter perfil do usuário
            profile = self.service.users().getProfile(userId='me').execute()
            
            logger.info(f"✅ Conexão com Gmail testada - Email: {profile.get('emailAddress')}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao testar conexão com Gmail: {e}")
            return False
    
    def get_user_email(self) -> Optional[str]:
        """Obtém email do usuário autenticado"""
        try:
            if not self.service:
                return None
            
            profile = self.service.users().getProfile(userId='me').execute()
            return profile.get('emailAddress')
            
        except Exception as e:
            logger.error(f"Erro ao obter email do usuário: {e}")
            return None 