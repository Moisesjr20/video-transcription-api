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
            # Primeiro, tentar carregar do token.json (novo formato)
            if os.path.exists('token.json'):
                with open('token.json', 'r') as f:
                    creds_data = json.load(f)
                
                self.creds = Credentials(
                    token=creds_data['token'],
                    refresh_token=creds_data['refresh_token'],
                    token_uri=creds_data['token_uri'],
                    client_id=creds_data['client_id'],
                    client_secret=creds_data['client_secret'],
                    scopes=creds_data['scopes']
                )
                
                # Verificar se precisa renovar
                if self.creds.expired and self.creds.refresh_token:
                    self.creds.refresh(Request())
                    
                    # Salvar credenciais atualizadas
                    creds_data = {
                        'token': self.creds.token,
                        'refresh_token': self.creds.refresh_token,
                        'token_uri': self.creds.token_uri,
                        'client_id': self.creds.client_id,
                        'client_secret': self.creds.client_secret,
                        'scopes': self.creds.scopes
                    }
                    
                    with open('token.json', 'w') as f:
                        json.dump(creds_data, f)
                
                return self.creds
            
            # Fallback para o formato antigo (pickle)
            elif os.path.exists(self.token_file):
                with open(self.token_file, 'rb') as token:
                    self.creds = pickle.load(token)
                
                if self.creds and self.creds.valid:
                    return self.creds
            
            # Se não há credenciais válidas, retornar None
            logger.warning("❌ Nenhuma credencial válida encontrada para Gmail. Execute a autenticação OAuth primeiro.")
            return None
            
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
    
    async def send_html_email(self, to_email: str, subject: str, html_content: str) -> bool:
        """Envia email HTML"""
        try:
            if not self.service:
                logger.error("Serviço do Gmail não inicializado")
                return False
            
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
            
            logger.info(f"📧 Email HTML enviado com sucesso: {sent_message.get('id')}")
            return True
            
        except HttpError as error:
            logger.error(f"Erro HTTP do Gmail: {error}")
            return False
        except Exception as e:
            logger.error(f"Erro ao enviar email HTML: {e}")
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
    
    async def send_test_email(self, to_email: str) -> bool:
        """Envia email de teste"""
        try:
            subject = "🧪 Teste - Transcritor Automático"
            html_content = """
            <html>
            <head>
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; }
                    .header { background-color: #4285f4; color: white; padding: 15px; border-radius: 5px; }
                    .content { margin: 20px 0; }
                    .footer { color: #666; font-size: 12px; margin-top: 20px; }
                </style>
            </head>
            <body>
                <div class="header">
                    <h2>🧪 Teste de Email</h2>
                </div>
                
                <div class="content">
                    <h3>✅ Configuração do Gmail Funcionando!</h3>
                    <p>Este é um email de teste do <strong>Transcritor Automático</strong>.</p>
                    <p>Se você recebeu este email, significa que:</p>
                    <ul>
                        <li>✅ A autenticação OAuth está funcionando</li>
                        <li>✅ O Gmail API está configurado corretamente</li>
                        <li>✅ O sistema pode enviar emails automaticamente</li>
                    </ul>
                </div>
                
                <div class="footer">
                    <p>Este email foi enviado automaticamente pelo sistema de transcrição.</p>
                    <p>Data: {date}</p>
                </div>
            </body>
            </html>
            """.format(date=datetime.now().strftime("%d/%m/%Y %H:%M"))
            
            return await self.send_html_email(to_email, subject, html_content)
            
        except Exception as e:
            logger.error(f"Erro ao enviar email de teste: {e}")
            return False 