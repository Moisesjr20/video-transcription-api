"""
Serviço do Google Drive
======================

Este módulo fornece funcionalidades para interagir com a API do Google Drive.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pickle
import os

from google_config import get_google_credentials, GOOGLE_SCOPES

logger = logging.getLogger(__name__)

class DriveService:
    """Serviço para interagir com Google Drive API"""
    
    def __init__(self):
        self.creds = None
        self.service = None
        self.token_file = 'token.pickle'
        self.credentials_file = 'credentials.json'
        
        # Configurações
        self.google_creds = get_google_credentials()
        
        # Inicializar serviço
        self.initialize_service()
    
    def initialize_service(self):
        """Inicializa o serviço do Google Drive"""
        try:
            # Carregar credenciais
            self.creds = self.get_credentials()
            
            if self.creds and self.creds.valid:
                # Construir serviço
                self.service = build('drive', 'v3', credentials=self.creds)
                logger.info("✅ Serviço do Google Drive inicializado com sucesso")
            else:
                logger.error("❌ Falha ao inicializar serviço do Google Drive")
                
        except Exception as e:
            logger.error(f"Erro ao inicializar serviço do Google Drive: {e}")
    
    def get_credentials(self) -> Optional[Credentials]:
        """Obtém credenciais do Google Drive"""
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
            logger.error(f"Erro ao obter credenciais: {e}")
            return None
    
    def create_credentials_file(self):
        """Cria arquivo de credenciais temporário"""
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
                
            logger.info("📄 Arquivo de credenciais criado")
            
        except Exception as e:
            logger.error(f"Erro ao criar arquivo de credenciais: {e}")
    
    async def list_folder_files(self, folder_id: str) -> List[Dict[str, Any]]:
        """Lista arquivos em uma pasta do Google Drive"""
        try:
            if not self.service:
                logger.error("Serviço do Google Drive não inicializado")
                return []
            
            # Parâmetros da consulta
            query = f"'{folder_id}' in parents and trashed=false"
            
            # Fazer requisição
            results = self.service.files().list(
                q=query,
                pageSize=100,
                fields="nextPageToken, files(id, name, size, createdTime, webViewLink, mimeType)"
            ).execute()
            
            files = results.get('files', [])
            logger.info(f"📁 Encontrados {len(files)} arquivos na pasta")
            
            return files
            
        except HttpError as error:
            logger.error(f"Erro HTTP do Google Drive: {error}")
            return []
        except Exception as e:
            logger.error(f"Erro ao listar arquivos: {e}")
            return []
    
    async def get_file_info(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Obtém informações detalhadas de um arquivo"""
        try:
            if not self.service:
                return None
            
            file_info = self.service.files().get(
                fileId=file_id,
                fields="id, name, size, createdTime, modifiedTime, webViewLink, mimeType"
            ).execute()
            
            return file_info
            
        except HttpError as error:
            logger.error(f"Erro ao obter informações do arquivo {file_id}: {error}")
            return None
        except Exception as e:
            logger.error(f"Erro ao obter informações do arquivo: {e}")
            return None
    
    async def check_folder_exists(self, folder_id: str) -> bool:
        """Verifica se uma pasta existe"""
        try:
            if not self.service:
                return False
            
            folder_info = self.service.files().get(
                fileId=folder_id,
                fields="id, name, mimeType"
            ).execute()
            
            return folder_info.get('mimeType') == 'application/vnd.google-apps.folder'
            
        except HttpError as error:
            logger.error(f"Erro ao verificar pasta {folder_id}: {error}")
            return False
        except Exception as e:
            logger.error(f"Erro ao verificar pasta: {e}")
            return False
    
    def get_file_download_url(self, file_id: str) -> str:
        """Gera URL de download para um arquivo"""
        return f"https://drive.google.com/uc?id={file_id}&export=download"
    
    async def test_connection(self) -> bool:
        """Testa conexão com Google Drive"""
        try:
            if not self.service:
                return False
            
            # Tentar listar arquivos (limite 1)
            results = self.service.files().list(
                pageSize=1,
                fields="files(id, name)"
            ).execute()
            
            logger.info("✅ Conexão com Google Drive testada com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao testar conexão com Google Drive: {e}")
            return False 