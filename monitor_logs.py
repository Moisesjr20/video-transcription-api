#!/usr/bin/env python3
"""
Script para monitorar logs em tempo real
"""

import time
import requests
import json
from datetime import datetime

def monitor_health():
    """Monitorar health check continuamente"""
    print("🏥 Monitorando health check...")
    while True:
        try:
            response = requests.get("http://localhost:8000/health")
            timestamp = datetime.now().strftime("%H:%M:%S")
            if response.status_code == 200:
                data = response.json()
                print(f"[{timestamp}] ✅ Health OK | Active tasks: {data.get('active_tasks', 0)}")
            else:
                print(f"[{timestamp}] ❌ Health falhou: {response.status_code}")
        except Exception as e:
            print(f"[{timestamp}] ❌ Erro: {e}")
        
        time.sleep(5)  # Verificar a cada 5 segundos

def test_endpoints():
    """Testar endpoints básicos"""
    print("🧪 Testando endpoints...")
    
    # Health check
    try:
        response = requests.get("http://localhost:8000/health")
        print(f"🏥 Health: {response.status_code}")
        if response.status_code == 200:
            print("✅ Health OK")
        else:
            print("❌ Health falhou")
    except Exception as e:
        print(f"❌ Health erro: {e}")
    
    # Ping
    try:
        response = requests.get("http://localhost:8000/ping")
        print(f"🏓 Ping: {response.status_code}")
        if response.status_code == 200:
            print("✅ Ping OK")
        else:
            print("❌ Ping falhou")
    except Exception as e:
        print(f"❌ Ping erro: {e}")
    
    # Root
    try:
        response = requests.get("http://localhost:8000/")
        print(f"🏠 Root: {response.status_code}")
        if response.status_code == 200:
            print("✅ Root OK")
        else:
            print("❌ Root falhou")
    except Exception as e:
        print(f"❌ Root erro: {e}")

def test_transcription():
    """Testar transcrição"""
    print("\n🎬 Testando transcrição...")
    
    payload = {
        "url": "https://www.soundjay.com/misc/sounds/bell-ringing-05.wav",
        "filename": "test_audio.wav",
        "language": "pt"
    }
    
    try:
        response = requests.post("http://localhost:8000/transcribe", json=payload)
        print(f"📤 Transcribe request: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            task_id = data.get('task_id')
            print(f"✅ Transcrição iniciada | Task ID: {task_id}")
            
            # Monitorar status
            print(f"📊 Monitorando status da tarefa {task_id}...")
            for i in range(10):  # Verificar por 20 segundos
                time.sleep(2)
                try:
                    status_response = requests.get(f"http://localhost:8000/status/{task_id}")
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        status = status_data.get('status', 'unknown')
                        progress = status_data.get('progress', 0)
                        message = status_data.get('message', '')
                        
                        print(f"📈 [{i+1}/10] Status: {status} | Progresso: {progress:.1%} | {message}")
                        
                        if status == 'sucesso':
                            print("✅ Transcrição concluída!")
                            print(f"📝 Texto: {status_data.get('transcription', '')[:100]}...")
                            return True
                        elif status == 'erro':
                            print(f"❌ Transcrição falhou: {message}")
                            return False
                    else:
                        print(f"❌ Erro ao obter status: {status_response.status_code}")
                except Exception as e:
                    print(f"❌ Erro ao monitorar: {e}")
            
            print("⏰ Timeout - não foi possível concluir em 20 segundos")
            return False
            
        else:
            print(f"❌ Falha na requisição: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Erro na transcrição: {e}")
        return False

def main():
    """Função principal"""
    print("🔍 MONITOR DE LOGS - TRANSCRITOR API")
    print("=" * 50)
    
    # Testar se o servidor está rodando
    print("🔍 Verificando se o servidor está rodando...")
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ Servidor está rodando!")
        else:
            print("❌ Servidor não está respondendo corretamente")
            return
    except Exception as e:
        print(f"❌ Servidor não está rodando: {e}")
        print("💡 Execute: python -m uvicorn app:app --host 0.0.0.0 --port 8000")
        return
    
    # Testar endpoints
    test_endpoints()
    
    # Perguntar se quer testar transcrição
    try:
        response = input("\n🤔 Deseja testar uma transcrição? (s/n): ")
        if response.lower() in ['s', 'sim', 'y', 'yes']:
            test_transcription()
    except KeyboardInterrupt:
        print("\n👋 Teste interrompido pelo usuário")
    
    # Perguntar se quer monitorar continuamente
    try:
        response = input("\n🤔 Deseja monitorar health check continuamente? (s/n): ")
        if response.lower() in ['s', 'sim', 'y', 'yes']:
            monitor_health()
    except KeyboardInterrupt:
        print("\n👋 Monitoramento interrompido pelo usuário")
    
    print("\n✅ Monitoramento concluído!")

if __name__ == "__main__":
    main() 