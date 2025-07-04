#!/usr/bin/env python3
"""
Exemplo de uso da API de Transcrição de Vídeo
==============================================

Este arquivo demonstra como usar a API melhorada para transcrição de vídeos
com processamento assíncrono.
"""

import requests
import time
import json
from typing import Dict, Any

# Configuração da API
API_BASE_URL = "http://localhost:8000"  # Altere para sua URL

def fazer_upload_video(url_video: str) -> Dict[str, Any]:
    """
    Faz upload de um vídeo para transcrição
    
    Args:
        url_video: URL do vídeo para transcrever
        
    Returns:
        Resposta da API com task_id e status
    """
    print(f"📤 Fazendo upload do vídeo: {url_video}")
    
    payload = {
        "url": url_video,
        "extract_subtitles": True,
        "max_segment_minutes": 10,
        "language": "pt"  # Português
    }
    
    response = requests.post(f"{API_BASE_URL}/transcribe", json=payload)
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Upload concluído com sucesso!")
        print(f"📋 Task ID: {result['task_id']}")
        print(f"💬 Mensagem: {result['message']}")
        print(f"🔗 URL para verificar status: {result['check_status_url']}")
        return result
    else:
        print(f"❌ Erro no upload: {response.status_code}")
        print(f"Resposta: {response.text}")
        return {}

def verificar_status(task_id: str) -> Dict[str, Any]:
    """
    Verifica o status da transcrição
    
    Args:
        task_id: ID da tarefa de transcrição
        
    Returns:
        Status atual da transcrição
    """
    response = requests.get(f"{API_BASE_URL}/status/{task_id}")
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ Erro ao verificar status: {response.status_code}")
        return {}

def aguardar_transcricao(task_id: str) -> Dict[str, Any]:
    """
    Aguarda a conclusão da transcrição, mostrando progresso
    
    Args:
        task_id: ID da tarefa de transcrição
        
    Returns:
        Resultado final da transcrição
    """
    print(f"\n🕐 Aguardando transcrição (Task ID: {task_id})")
    print("=" * 60)
    
    while True:
        status = verificar_status(task_id)
        
        if not status:
            print("❌ Erro ao verificar status")
            break
        
        # Mostrar progresso
        progress = status.get('progress', 0) * 100
        status_text = status.get('status', 'unknown')
        message = status.get('message', 'Processando...')
        
        print(f"📊 Status: {status_text}")
        print(f"📈 Progresso: {progress:.1f}%")
        print(f"💬 Mensagem: {message}")
        
        # Mostrar informações do arquivo se disponível
        if status.get('file_info'):
            file_info = status['file_info']
            print(f"📁 Arquivo: {file_info.get('filename', 'N/A')}")
            print(f"📏 Tamanho: {file_info.get('size_mb', 'N/A')} MB")
            print(f"⏱️ Tempo estimado: {file_info.get('estimated_time', 'N/A')}")
        
        print("-" * 60)
        
        # Verificar se terminou
        if status_text == 'sucesso':
            print("🎉 Transcrição concluída com sucesso!")
            return status
        elif status_text == 'erro':
            print("❌ Erro na transcrição!")
            return status
        
        # Aguardar antes da próxima verificação
        time.sleep(5)  # Verificar a cada 5 segundos
    
    return {}

def baixar_transcricao(filename: str) -> str:
    """
    Baixa o arquivo de transcrição
    
    Args:
        filename: Nome do arquivo de transcrição
        
    Returns:
        Conteúdo da transcrição
    """
    response = requests.get(f"{API_BASE_URL}/download/{filename}")
    
    if response.status_code == 200:
        return response.text
    else:
        print(f"❌ Erro ao baixar transcrição: {response.status_code}")
        return ""

def exemplo_completo():
    """
    Exemplo completo de uso da API
    """
    print("🚀 Exemplo de uso da API de Transcrição de Vídeo")
    print("=" * 60)
    
    # 1. Fazer upload do vídeo
    url_video = input("🔗 Digite a URL do vídeo para transcrever: ")
    
    if not url_video:
        print("❌ URL não fornecida")
        return
    
    # Iniciar transcrição
    resultado_upload = fazer_upload_video(url_video)
    
    if not resultado_upload:
        print("❌ Falha no upload")
        return
    
    task_id = resultado_upload['task_id']
    
    # 2. Aguardar conclusão
    resultado_final = aguardar_transcricao(task_id)
    
    if not resultado_final:
        print("❌ Falha na transcrição")
        return
    
    # 3. Mostrar resultado
    if resultado_final.get('status') == 'sucesso':
        print("\n📝 TRANSCRIÇÃO CONCLUÍDA!")
        print("=" * 60)
        
        transcricao = resultado_final.get('transcription', '')
        if transcricao:
            print("📄 Conteúdo da transcrição:")
            print("-" * 40)
            # Mostrar apenas os primeiros 500 caracteres
            if len(transcricao) > 500:
                print(transcricao[:500] + "...")
                print(f"\n(Transcrição completa tem {len(transcricao)} caracteres)")
            else:
                print(transcricao)
        
        # Opção de baixar arquivo completo
        if resultado_final.get('filename'):
            salvar = input("\n💾 Deseja salvar a transcrição em arquivo? (s/n): ")
            if salvar.lower() == 's':
                transcricao_completa = baixar_transcricao(resultado_final['filename'])
                if transcricao_completa:
                    nome_arquivo = f"transcricao_{task_id}.txt"
                    with open(nome_arquivo, 'w', encoding='utf-8') as f:
                        f.write(transcricao_completa)
                    print(f"✅ Transcrição salva em: {nome_arquivo}")
    
    print("\n🎯 Processo concluído!")

if __name__ == "__main__":
    exemplo_completo()