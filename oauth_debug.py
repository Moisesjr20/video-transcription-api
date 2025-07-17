#!/usr/bin/env python3
"""
Script de diagnóstico para problemas OAuth 400: invalid_request
============================================================

Este script ajuda a identificar e resolver problemas comuns do OAuth 2.0 do Google.
"""

import os
import json
import logging
from urllib.parse import urlparse, parse_qs

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_environment_variables():
    """Verifica se as variáveis de ambiente estão configuradas corretamente"""
    logger.info("🔍 Verificando variáveis de ambiente...")
    
    required_vars = [
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET", 
        "GOOGLE_REDIRECT_URI"
    ]
    
    issues = []
    
    for var in required_vars:
        value = os.environ.get(var)
        if not value:
            issues.append(f"❌ {var} não está definida")
        else:
            logger.info(f"✅ {var}: {'***' if 'SECRET' in var else value}")
    
    return issues

def validate_client_id_format(client_id):
    """Valida o formato do Client ID"""
    logger.info("🔍 Verificando formato do Client ID...")
    
    if not client_id:
        return ["❌ Client ID está vazio"]
    
    # Verificar se tem o formato correto do Google
    if not client_id.endswith('.apps.googleusercontent.com'):
        return ["❌ Client ID não tem formato válido (.apps.googleusercontent.com)"]
    
    # Verificar se tem pelo menos 50 caracteres (formato típico)
    if len(client_id) < 50:
        return ["❌ Client ID parece muito curto"]
    
    return []

def validate_redirect_uri(redirect_uri):
    """Valida a URI de redirecionamento"""
    logger.info("🔍 Verificando URI de redirecionamento...")
    
    if not redirect_uri:
        return ["❌ Redirect URI está vazia"]
    
    try:
        parsed = urlparse(redirect_uri)
        
        issues = []
        
        # Verificar se é HTTP/HTTPS
        if parsed.scheme not in ['http', 'https']:
            issues.append("❌ URI deve usar HTTP ou HTTPS")
        
        # Verificar se tem host
        if not parsed.netloc:
            issues.append("❌ URI deve ter um host válido")
        
        # Verificar se tem path
        if not parsed.path:
            issues.append("❌ URI deve ter um caminho")
        
        # Verificar se não tem fragment
        if parsed.fragment:
            issues.append("❌ URI não deve ter fragment (#)")
        
        return issues
        
    except Exception as e:
        return [f"❌ Erro ao analisar URI: {e}"]

def check_google_console_config():
    """Verifica se as configurações do Google Cloud Console estão corretas"""
    logger.info("🔍 Verificando configurações do Google Cloud Console...")
    
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    redirect_uri = os.environ.get("GOOGLE_REDIRECT_URI")
    
    if not client_id or not redirect_uri:
        return ["❌ Não é possível verificar sem Client ID e Redirect URI"]
    
    issues = []
    
    # Verificar se o Client ID parece ser do tipo correto
    if "apps.googleusercontent.com" not in client_id:
        issues.append("❌ Client ID não parece ser do Google Cloud Console")
    
    # Verificar se a URI de redirecionamento é válida
    uri_issues = validate_redirect_uri(redirect_uri)
    issues.extend(uri_issues)
    
    return issues

def check_oauth_flow_parameters():
    """Verifica os parâmetros do fluxo OAuth"""
    logger.info("🔍 Verificando parâmetros do fluxo OAuth...")
    
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google_config import GOOGLE_SCOPES
        
        client_id = os.environ.get("GOOGLE_CLIENT_ID")
        client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
        redirect_uri = os.environ.get("GOOGLE_REDIRECT_URI")
        
        if not all([client_id, client_secret, redirect_uri]):
            return ["❌ Variáveis de ambiente incompletas"]
        
        # Criar configuração do cliente
        client_config = {
            "installed": {
                "client_id": client_id,
                "project_id": "video-transcription-api",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_secret": client_secret,
                "redirect_uris": [redirect_uri]
            }
        }
        
        # Tentar criar o fluxo
        flow = InstalledAppFlow.from_client_config(client_config, GOOGLE_SCOPES)
        
        # Gerar URL de autorização
        auth_url, state = flow.authorization_url(
            access_type='offline',
            prompt='consent',
            include_granted_scopes='true'
        )
        
        logger.info("✅ Fluxo OAuth criado com sucesso")
        logger.info(f"✅ URL de autorização gerada: {auth_url[:100]}...")
        
        return []
        
    except Exception as e:
        return [f"❌ Erro no fluxo OAuth: {str(e)}"]

def analyze_auth_url(auth_url):
    """Analisa a URL de autorização para identificar problemas"""
    logger.info("🔍 Analisando URL de autorização...")
    
    try:
        parsed = urlparse(auth_url)
        params = parse_qs(parsed.query)
        
        issues = []
        
        # Verificar parâmetros obrigatórios
        required_params = ['response_type', 'client_id', 'scope', 'redirect_uri']
        for param in required_params:
            if param not in params:
                issues.append(f"❌ Parâmetro obrigatório ausente: {param}")
        
        # Verificar response_type
        if 'response_type' in params and params['response_type'] != ['code']:
            issues.append("❌ response_type deve ser 'code'")
        
        # Verificar scopes
        if 'scope' in params:
            scopes = params['scope'][0].split(' ')
            required_scopes = [
                'https://www.googleapis.com/auth/drive.readonly',
                'https://www.googleapis.com/auth/gmail.send',
                'https://www.googleapis.com/auth/gmail.compose'
            ]
            
            for scope in required_scopes:
                if scope not in scopes:
                    issues.append(f"❌ Scope obrigatório ausente: {scope}")
        
        return issues
        
    except Exception as e:
        return [f"❌ Erro ao analisar URL: {str(e)}"]

def main():
    """Executa todos os diagnósticos"""
    logger.info("🚀 Iniciando diagnóstico OAuth 400: invalid_request")
    logger.info("=" * 60)
    
    all_issues = []
    
    # 1. Verificar variáveis de ambiente
    logger.info("\n1️⃣ Verificando variáveis de ambiente...")
    env_issues = check_environment_variables()
    all_issues.extend(env_issues)
    
    # 2. Validar Client ID
    logger.info("\n2️⃣ Validando Client ID...")
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_issues = validate_client_id_format(client_id)
    all_issues.extend(client_issues)
    
    # 3. Validar Redirect URI
    logger.info("\n3️⃣ Validando Redirect URI...")
    redirect_uri = os.environ.get("GOOGLE_REDIRECT_URI")
    uri_issues = validate_redirect_uri(redirect_uri)
    all_issues.extend(uri_issues)
    
    # 4. Verificar configurações do Google Console
    logger.info("\n4️⃣ Verificando configurações do Google Cloud Console...")
    console_issues = check_google_console_config()
    all_issues.extend(console_issues)
    
    # 5. Testar fluxo OAuth
    logger.info("\n5️⃣ Testando fluxo OAuth...")
    flow_issues = check_oauth_flow_parameters()
    all_issues.extend(flow_issues)
    
    # Resumo
    logger.info("\n" + "=" * 60)
    logger.info("📊 RESUMO DO DIAGNÓSTICO")
    logger.info("=" * 60)
    
    if all_issues:
        logger.error(f"❌ Encontrados {len(all_issues)} problema(s):")
        for i, issue in enumerate(all_issues, 1):
            logger.error(f"   {i}. {issue}")
        
        logger.info("\n🔧 SOLUÇÕES RECOMENDADAS:")
        logger.info("1. Verifique se as variáveis de ambiente estão configuradas no Easypanel")
        logger.info("2. Confirme se o Client ID está correto no Google Cloud Console")
        logger.info("3. Verifique se a Redirect URI está autorizada no Google Cloud Console")
        logger.info("4. Certifique-se de que as APIs do Google Drive e Gmail estão habilitadas")
        logger.info("5. Limpe o cache do navegador e tente novamente")
        
    else:
        logger.info("✅ Nenhum problema encontrado na configuração!")
        logger.info("O erro 400 pode ser temporário. Tente novamente em alguns minutos.")
    
    logger.info("\n" + "=" * 60)

if __name__ == "__main__":
    main() 