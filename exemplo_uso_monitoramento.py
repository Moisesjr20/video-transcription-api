#!/usr/bin/env python3
"""
Exemplo de Uso do Monitoramento Automático
==========================================

Este script demonstra como usar a nova funcionalidade de monitoramento
automático de pastas do Google Drive.
"""

import requests
import json
import time
from datetime import datetime

# Configuração da API
API_BASE_URL = "http://localhost:8000"

def test_api_health():
    """Testa se a API está funcionando"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=10)
        if response.status_code == 200:
            print("✅ API está funcionando")
            return True
        else:
            print(f"❌ API retornou status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Erro ao conectar com API: {e}")
        return False

def test_google_connection():
    """Testa conexão com Google APIs"""
    try:
        response = requests.get(f"{API_BASE_URL}/google/test-connection", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print("🔍 Status das conexões Google:")
            print(f"   Drive: {data['drive_connection']}")
            print(f"   Gmail: {data['gmail_connection']}")
            
            if data.get('drive_user_email'):
                print(f"   Email Drive: {data['drive_user_email']}")
            if data.get('gmail_user_email'):
                print(f"   Email Gmail: {data['gmail_user_email']}")
            
            return data['drive_connection'] == "✅ OK" and data['gmail_connection'] == "✅ OK"
        else:
            print(f"❌ Erro no teste: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Erro ao testar conexão: {e}")
        return False

def start_monitoring():
    """Inicia o monitoramento automático"""
    try:
        response = requests.post(f"{API_BASE_URL}/monitor/start", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"🚀 {data['message']}")
            print(f"📁 Pasta monitorada: {data['details']['folder_id']}")
            print(f"⏰ Intervalo: {data['details']['check_interval']} segundos")
            print(f"📧 Email destino: {data['details']['destination_email']}")
            return True
        else:
            print(f"❌ Erro ao iniciar: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Erro ao iniciar monitoramento: {e}")
        return False

def check_monitor_status():
    """Verifica status do monitoramento"""
    try:
        response = requests.get(f"{API_BASE_URL}/monitor/status", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print("📊 Status do Monitoramento:")
            print(f"   Ativo: {'✅ Sim' if data['active'] else '❌ Não'}")
            print(f"   Arquivos processados: {data['processed_files_count']}")
            if data.get('next_check_in_seconds'):
                print(f"   Próxima verificação em: {data['next_check_in_seconds']} segundos")
            return data
        else:
            print(f"❌ Erro ao obter status: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Erro ao verificar status: {e}")
        return None

def check_new_videos():
    """Força verificação de novos vídeos"""
    try:
        response = requests.post(f"{API_BASE_URL}/monitor/check-now", timeout=30)
        if response.status_code == 200:
            data = response.json()
            print(f"🔍 {data['message']}")
            if data.get('new_videos'):
                print("📹 Novos vídeos encontrados:")
                for video in data['new_videos']:
                    print(f"   - {video['name']} ({video['size_mb']:.1f}MB)")
            return True
        else:
            print(f"❌ Erro na verificação: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Erro na verificação manual: {e}")
        return False

def send_test_email(email):
    """Envia email de teste"""
    try:
        payload = {"email": email}
        response = requests.post(f"{API_BASE_URL}/google/send-test-email", json=payload, timeout=30)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ {data['message']}")
            return True
        else:
            print(f"❌ Erro ao enviar email: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Erro ao enviar email de teste: {e}")
        return False

def monitor_continuously():
    """Monitora continuamente o status"""
    print("🔄 Iniciando monitoramento contínuo...")
    print("Pressione Ctrl+C para parar")
    
    try:
        while True:
            status = check_monitor_status()
            if status and status['active']:
                print(f"⏰ {datetime.now().strftime('%H:%M:%S')} - Monitoramento ativo")
                print(f"   Arquivos processados: {status['processed_files_count']}")
            else:
                print(f"⏰ {datetime.now().strftime('%H:%M:%S')} - Monitoramento inativo")
            
            time.sleep(60)  # Verificar a cada minuto
            
    except KeyboardInterrupt:
        print("\n🛑 Monitoramento interrompido pelo usuário")

def main():
    """Função principal"""
    print("=" * 60)
    print("🎬 EXEMPLO DE USO - MONITORAMENTO AUTOMÁTICO")
    print("=" * 60)
    
    # 1. Testar API
    print("\n1️⃣ Testando API...")
    if not test_api_health():
        print("❌ API não está disponível")
        return
    
    # 2. Testar Google APIs
    print("\n2️⃣ Testando Google APIs...")
    if not test_google_connection():
        print("❌ Google APIs não estão configuradas")
        print("Execute primeiro: python setup_google_auth.py")
        return
    
    # 3. Menu de opções
    while True:
        print("\n" + "=" * 40)
        print("📋 MENU DE OPÇÕES")
        print("=" * 40)
        print("1. Iniciar monitoramento automático")
        print("2. Verificar status do monitoramento")
        print("3. Verificar novos vídeos agora")
        print("4. Enviar email de teste")
        print("5. Monitoramento contínuo")
        print("6. Sair")
        
        choice = input("\nEscolha uma opção (1-6): ").strip()
        
        if choice == "1":
            start_monitoring()
            
        elif choice == "2":
            check_monitor_status()
            
        elif choice == "3":
            check_new_videos()
            
        elif choice == "4":
            email = input("📧 Digite o email para teste: ").strip()
            if email:
                send_test_email(email)
            else:
                print("❌ Email não fornecido")
                
        elif choice == "5":
            monitor_continuously()
            
        elif choice == "6":
            print("👋 Saindo...")
            break
            
        else:
            print("❌ Opção inválida")

if __name__ == "__main__":
    main() 