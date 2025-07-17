#!/usr/bin/env python3
"""
Script de Configuração do Google Auth
====================================

Este script ajuda a configurar a autenticação com Google APIs
para o monitoramento automático de pastas do Google Drive.
"""

import asyncio
import logging
import requests
import json
from pathlib import Path

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_api_connection():
    """Testa se a API está rodando"""
    try:
        response = requests.get("http://localhost:8000/health", timeout=10)
        if response.status_code == 200:
            logger.info("✅ API está rodando")
            return True
        else:
            logger.error("❌ API não está respondendo corretamente")
            return False
    except Exception as e:
        logger.error(f"❌ Não foi possível conectar à API: {e}")
        return False

def get_google_auth_url():
    """Obtém URL de autenticação do Google"""
    try:
        response = requests.get("http://localhost:8000/google/auth-url", timeout=10)
        if response.status_code == 200:
            data = response.json()
            auth_url = data['auth_url']
            logger.info("🔗 URL de autenticação gerada com sucesso")
            logger.info(f"📋 Acesse esta URL para autorizar: {auth_url}")
            return auth_url
        else:
            logger.error(f"❌ Erro ao gerar URL: {response.text}")
            return None
    except Exception as e:
        logger.error(f"❌ Erro ao obter URL de autenticação: {e}")
        return None

def test_google_connection():
    """Testa conexão com Google APIs"""
    try:
        response = requests.get("http://localhost:8000/google/test-connection", timeout=10)
        if response.status_code == 200:
            data = response.json()
            logger.info("🔍 Teste de conexão com Google APIs:")
            logger.info(f"   Drive: {data['drive_connection']}")
            logger.info(f"   Gmail: {data['gmail_connection']}")
            
            if data.get('drive_user_email'):
                logger.info(f"   Email Drive: {data['drive_user_email']}")
            if data.get('gmail_user_email'):
                logger.info(f"   Email Gmail: {data['gmail_user_email']}")
            
            return data['drive_connection'] == "✅ OK" and data['gmail_connection'] == "✅ OK"
        else:
            logger.error(f"❌ Erro no teste: {response.text}")
            return False
    except Exception as e:
        logger.error(f"❌ Erro ao testar conexão: {e}")
        return False

def send_test_email(email):
    """Envia email de teste"""
    try:
        payload = {"email": email}
        response = requests.post("http://localhost:8000/google/send-test-email", json=payload, timeout=30)
        if response.status_code == 200:
            data = response.json()
            logger.info(f"✅ {data['message']}")
            return True
        else:
            logger.error(f"❌ Erro ao enviar email: {response.text}")
            return False
    except Exception as e:
        logger.error(f"❌ Erro ao enviar email de teste: {e}")
        return False

def start_monitoring():
    """Inicia o monitoramento automático"""
    try:
        response = requests.post("http://localhost:8000/monitor/start", timeout=10)
        if response.status_code == 200:
            data = response.json()
            logger.info(f"🚀 {data['message']}")
            logger.info(f"📁 Pasta monitorada: {data['details']['folder_id']}")
            logger.info(f"⏰ Intervalo de verificação: {data['details']['check_interval']} segundos")
            logger.info(f"📧 Email de destino: {data['details']['destination_email']}")
            return True
        else:
            logger.error(f"❌ Erro ao iniciar monitoramento: {response.text}")
            return False
    except Exception as e:
        logger.error(f"❌ Erro ao iniciar monitoramento: {e}")
        return False

def check_monitor_status():
    """Verifica status do monitoramento"""
    try:
        response = requests.get("http://localhost:8000/monitor/status", timeout=10)
        if response.status_code == 200:
            data = response.json()
            logger.info("📊 Status do Monitoramento:")
            logger.info(f"   Ativo: {'✅ Sim' if data['active'] else '❌ Não'}")
            logger.info(f"   Arquivos processados: {data['processed_files_count']}")
            if data.get('next_check_in_seconds'):
                logger.info(f"   Próxima verificação em: {data['next_check_in_seconds']} segundos")
            return data
        else:
            logger.error(f"❌ Erro ao obter status: {response.text}")
            return None
    except Exception as e:
        logger.error(f"❌ Erro ao verificar status: {e}")
        return None

def check_new_videos():
    """Força verificação de novos vídeos"""
    try:
        response = requests.post("http://localhost:8000/monitor/check-now", timeout=30)
        if response.status_code == 200:
            data = response.json()
            logger.info(f"🔍 {data['message']}")
            if data.get('new_videos'):
                logger.info("📹 Novos vídeos encontrados:")
                for video in data['new_videos']:
                    logger.info(f"   - {video['name']} ({video['size_mb']:.1f}MB)")
            return True
        else:
            logger.error(f"❌ Erro na verificação: {response.text}")
            return False
    except Exception as e:
        logger.error(f"❌ Erro na verificação manual: {e}")
        return False

def main():
    """Função principal do script"""
    logger.info("=" * 60)
    logger.info("🔧 CONFIGURAÇÃO DO MONITORAMENTO AUTOMÁTICO")
    logger.info("=" * 60)
    
    # 1. Testar conexão com API
    logger.info("\n1️⃣ Testando conexão com API...")
    if not test_api_connection():
        logger.error("❌ API não está disponível. Certifique-se de que está rodando em http://localhost:8000")
        return
    
    # 2. Testar conexão com Google
    logger.info("\n2️⃣ Testando conexão com Google APIs...")
    if not test_google_connection():
        logger.info("\n🔐 Configuração de autenticação necessária...")
        auth_url = get_google_auth_url()
        if auth_url:
            logger.info("\n📋 INSTRUÇÕES:")
            logger.info("1. Acesse a URL de autenticação acima")
            logger.info("2. Faça login com sua conta Google")
            logger.info("3. Autorize o acesso ao Drive e Gmail")
            logger.info("4. Copie o código de autorização")
            logger.info("5. Execute este script novamente após a autenticação")
            
            input("\n⏳ Pressione Enter após completar a autenticação...")
            
            # Testar novamente após autenticação
            if test_google_connection():
                logger.info("✅ Autenticação configurada com sucesso!")
            else:
                logger.error("❌ Falha na autenticação. Tente novamente.")
                return
        else:
            logger.error("❌ Não foi possível gerar URL de autenticação")
            return
    else:
        logger.info("✅ Conexão com Google APIs OK!")
    
    # 3. Testar envio de email
    logger.info("\n3️⃣ Testando envio de email...")
    test_email = input("📧 Digite seu email para teste: ").strip()
    if test_email:
        if send_test_email(test_email):
            logger.info("✅ Email de teste enviado com sucesso!")
        else:
            logger.error("❌ Falha no envio de email de teste")
            return
    else:
        logger.info("⏭️ Pulando teste de email...")
    
    # 4. Iniciar monitoramento
    logger.info("\n4️⃣ Iniciando monitoramento automático...")
    if start_monitoring():
        logger.info("✅ Monitoramento iniciado com sucesso!")
        
        # Verificar status
        status = check_monitor_status()
        if status:
            logger.info("📊 Monitoramento ativo e funcionando!")
        
        # Verificar vídeos existentes
        logger.info("\n5️⃣ Verificando vídeos existentes...")
        check_new_videos()
        
    else:
        logger.error("❌ Falha ao iniciar monitoramento")
        return
    
    logger.info("\n" + "=" * 60)
    logger.info("🎉 CONFIGURAÇÃO CONCLUÍDA COM SUCESSO!")
    logger.info("=" * 60)
    logger.info("📋 RESUMO:")
    logger.info("✅ API conectada")
    logger.info("✅ Google APIs autenticadas")
    logger.info("✅ Email configurado")
    logger.info("✅ Monitoramento ativo")
    logger.info("\n📝 PRÓXIMOS PASSOS:")
    logger.info("1. Adicione vídeos à pasta do Google Drive")
    logger.info("2. A API detectará automaticamente novos vídeos")
    logger.info("3. Transcrições serão enviadas por email")
    logger.info("\n🔗 Endpoints úteis:")
    logger.info("   - GET /monitor/status - Status do monitoramento")
    logger.info("   - POST /monitor/check-now - Verificar vídeos agora")
    logger.info("   - POST /monitor/stop - Parar monitoramento")

if __name__ == "__main__":
    main() 