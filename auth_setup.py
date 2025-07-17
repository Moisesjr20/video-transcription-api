#!/usr/bin/env python3
"""
Script de Configuração de Autenticação OAuth
============================================

Este script configura a autenticação OAuth do Google de forma persistente.
Execute uma vez e as credenciais ficarão salvas permanentemente.
"""

import os
import json
import pickle
import logging
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configurações
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.compose"
]

def get_environment_config():
    """Obtém configurações das variáveis de ambiente"""
    config = {
        "client_id": os.environ.get("GOOGLE_CLIENT_ID"),
        "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET"),
        "redirect_uri": os.environ.get("GOOGLE_REDIRECT_URI")
    }
    
    # Verificar se todas as variáveis estão configuradas
    missing_vars = [key for key, value in config.items() if not value]
    if missing_vars:
        logger.error(f"❌ Variáveis de ambiente faltando: {missing_vars}")
        logger.error("Configure as seguintes variáveis no Easypanel:")
        logger.error("GOOGLE_CLIENT_ID=1051222617815-jmdb2igpmhu4vhuhn92advr20qacj9vt.apps.googleusercontent.com")
        logger.error("GOOGLE_CLIENT_SECRET=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")
        logger.error("GOOGLE_REDIRECT_URI=https://transcritor-transcritor.whhc5g.easypanel.host/auth/callback")
        return None
    
    logger.info("✅ Todas as variáveis de ambiente estão configuradas")
    return config

def create_oauth_flow(config):
    """Cria o fluxo OAuth"""
    try:
        flow = InstalledAppFlow.from_client_config(
            {
                "installed": {
                    "client_id": config["client_id"],
                    "project_id": "video-transcription-api",
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_secret": config["client_secret"],
                    "redirect_uris": [config["redirect_uri"]]
                }
            },
            GOOGLE_SCOPES
        )
        
        logger.info("✅ Fluxo OAuth criado com sucesso")
        return flow
    except Exception as e:
        logger.error(f"❌ Erro ao criar fluxo OAuth: {e}")
        return None

def save_credentials(credentials):
    """Salva as credenciais em formato JSON"""
    try:
        creds_data = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }
        
        with open('token.json', 'w') as f:
            json.dump(creds_data, f, indent=2)
        
        logger.info("✅ Credenciais salvas em token.json")
        return True
    except Exception as e:
        logger.error(f"❌ Erro ao salvar credenciais: {e}")
        return False

def test_credentials():
    """Testa se as credenciais estão funcionando"""
    try:
        if not os.path.exists('token.json'):
            logger.error("❌ Arquivo token.json não encontrado")
            return False
        
        with open('token.json', 'r') as f:
            creds_data = json.load(f)
        
        credentials = Credentials(
            token=creds_data['token'],
            refresh_token=creds_data['refresh_token'],
            token_uri=creds_data['token_uri'],
            client_id=creds_data['client_id'],
            client_secret=creds_data['client_secret'],
            scopes=creds_data['scopes']
        )
        
        # Verificar se precisa renovar
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
            save_credentials(credentials)
        
        logger.info("✅ Credenciais testadas e válidas")
        return True
    except Exception as e:
        logger.error(f"❌ Erro ao testar credenciais: {e}")
        return False

def main():
    """Função principal"""
    logger.info("🚀 Iniciando configuração de autenticação OAuth")
    logger.info("=" * 50)
    
    # 1. Verificar configurações
    config = get_environment_config()
    if not config:
        return False
    
    # 2. Verificar se já existe autenticação
    if os.path.exists('token.json'):
        logger.info("📋 Arquivo token.json encontrado")
        if test_credentials():
            logger.info("✅ Autenticação já configurada e funcionando!")
            return True
        else:
            logger.info("⚠️ Credenciais expiradas, será necessário reautenticar")
    
    # 3. Criar fluxo OAuth
    flow = create_oauth_flow(config)
    if not flow:
        return False
    
    # 4. Gerar URL de autenticação
    auth_url, _ = flow.authorization_url(
        access_type='offline',
        prompt='consent',
        include_granted_scopes='true'
    )
    
    logger.info("🔗 URL de autenticação gerada:")
    logger.info(f"   {auth_url}")
    logger.info("")
    logger.info("📋 Instruções:")
    logger.info("1. Acesse a URL acima no navegador")
    logger.info("2. Faça login com sua conta Google")
    logger.info("3. Autorize o acesso ao Drive e Gmail")
    logger.info("4. Copie o código de autorização")
    logger.info("5. Execute: python auth_setup.py --code SEU_CODIGO")
    
    return True

def complete_auth(auth_code):
    """Completa a autenticação com o código recebido"""
    try:
        config = get_environment_config()
        if not config:
            return False
        
        flow = create_oauth_flow(config)
        if not flow:
            return False
        
        # Trocar código por tokens
        flow.fetch_token(code=auth_code)
        credentials = flow.credentials
        
        # Salvar credenciais
        if save_credentials(credentials):
            logger.info("🎉 Autenticação OAuth concluída com sucesso!")
            logger.info("✅ As credenciais foram salvas e estão prontas para uso")
            return True
        else:
            return False
            
    except Exception as e:
        logger.error(f"❌ Erro ao completar autenticação: {e}")
        return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--code":
        if len(sys.argv) < 3:
            logger.error("❌ Código de autorização não fornecido")
            logger.error("Uso: python auth_setup.py --code SEU_CODIGO")
            sys.exit(1)
        
        auth_code = sys.argv[2]
        if complete_auth(auth_code):
            sys.exit(0)
        else:
            sys.exit(1)
    else:
        if main():
            sys.exit(0)
        else:
            sys.exit(1) 