"""
Monitor Automático do Google Drive
================================

Este módulo monitora uma pasta específica do Google Drive e processa
automaticamente novos vídeos encontrados.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
import requests

from google_config import get_drive_config, get_google_credentials, get_email_config
from gmail_service import GmailService
from drive_service import DriveService

logger = logging.getLogger(__name__)

class DriveMonitor:
    """Monitor automático para pasta do Google Drive"""
    
    def __init__(self):
        self.drive_config = get_drive_config()
        self.email_config = get_email_config()
        self.google_creds = get_google_credentials()
        
        # Serviços
        self.drive_service = DriveService()
        self.gmail_service = GmailService()
        
        # Estado do monitoramento
        self.processed_files = set()
        self.monitoring_active = False
        
        # Arquivo para persistir arquivos processados
        self.processed_file = Path("processed_files.json")
        self.load_processed_files()
    
    def load_processed_files(self):
        """Carrega lista de arquivos já processados"""
        try:
            if self.processed_file.exists():
                with open(self.processed_file, 'r') as f:
                    data = json.load(f)
                    self.processed_files = set(data.get('files', []))
                    logger.info(f"Carregados {len(self.processed_files)} arquivos processados")
        except Exception as e:
            logger.error(f"Erro ao carregar arquivos processados: {e}")
    
    def save_processed_files(self):
        """Salva lista de arquivos processados"""
        try:
            data = {
                'files': list(self.processed_files),
                'last_updated': datetime.now().isoformat()
            }
            with open(self.processed_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Erro ao salvar arquivos processados: {e}")
    
    async def check_new_videos(self) -> List[Dict[str, Any]]:
        """Verifica novos vídeos na pasta do Google Drive"""
        try:
            logger.info("🔍 Verificando novos vídeos na pasta do Google Drive...")
            
            # Listar arquivos na pasta
            files = await self.drive_service.list_folder_files(self.drive_config['folder_id'])
            
            new_videos = []
            for file in files:
                file_id = file['id']
                file_name = file['name']
                
                # Verificar se é vídeo
                if not self.is_video_file(file_name):
                    continue
                
                # Verificar se já foi processado
                if file_id in self.processed_files:
                    continue
                
                # Verificar tamanho do arquivo
                file_size_mb = int(file.get('size', 0)) / (1024 * 1024)
                if file_size_mb > self.drive_config['max_file_size']:
                    logger.warning(f"Arquivo {file_name} muito grande ({file_size_mb:.1f}MB), pulando...")
                    continue
                
                new_videos.append({
                    'id': file_id,
                    'name': file_name,
                    'size_mb': file_size_mb,
                    'created_time': file.get('createdTime'),
                    'web_view_link': file.get('webViewLink')
                })
            
            logger.info(f"📹 Encontrados {len(new_videos)} novos vídeos")
            return new_videos
            
        except Exception as e:
            logger.error(f"Erro ao verificar novos vídeos: {e}")
            return []
    
    def is_video_file(self, filename: str) -> bool:
        """Verifica se o arquivo é um vídeo"""
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm'}
        return Path(filename).suffix.lower() in video_extensions
    
    async def process_video(self, video_info: Dict[str, Any]):
        """Processa um vídeo encontrado"""
        try:
            file_id = video_info['id']
            file_name = video_info['name']
            
            logger.info(f"🎬 Processando vídeo: {file_name}")
            
            # Criar URL do Google Drive
            drive_url = f"https://drive.google.com/uc?id={file_id}&export=download"
            
            # Iniciar transcrição via API
            transcription_result = await self.start_transcription(drive_url, file_name)
            
            if transcription_result:
                # Enviar email com transcrição
                await self.send_transcription_email(video_info, transcription_result)
                
                # Marcar como processado
                self.processed_files.add(file_id)
                self.save_processed_files()
                
                logger.info(f"✅ Vídeo {file_name} processado com sucesso")
            else:
                logger.error(f"❌ Falha ao processar vídeo {file_name}")
                
        except Exception as e:
            logger.error(f"Erro ao processar vídeo {video_info.get('name', 'unknown')}: {e}")
    
    async def start_transcription(self, drive_url: str, filename: str) -> Optional[Dict[str, Any]]:
        """Inicia transcrição via API"""
        try:
            # Preparar payload para API
            payload = {
                "google_drive_url": drive_url,
                "filename": filename,
                "language": "pt",
                "extract_subtitles": True,
                "max_segment_minutes": 10
            }
            
            # Fazer requisição para API
            response = requests.post(
                "http://localhost:8000/transcribe",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                task_id = result['task_id']
                
                # Aguardar conclusão da transcrição
                return await self.wait_for_transcription(task_id)
            else:
                logger.error(f"Erro na API: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao iniciar transcrição: {e}")
            return None
    
    async def wait_for_transcription(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Aguarda conclusão da transcrição"""
        max_wait_time = 3600  # 1 hora máximo
        check_interval = 30  # Verificar a cada 30 segundos
        
        start_time = datetime.now()
        
        while (datetime.now() - start_time).seconds < max_wait_time:
            try:
                response = requests.get(f"http://localhost:8000/status/{task_id}")
                
                if response.status_code == 200:
                    status = response.json()
                    
                    if status['status'] == 'sucesso':
                        logger.info(f"🎉 Transcrição {task_id} concluída")
                        return status
                    elif status['status'] == 'erro':
                        logger.error(f"❌ Erro na transcrição {task_id}: {status.get('message', 'Unknown error')}")
                        return None
                    else:
                        # Ainda processando
                        progress = status.get('progress', 0) * 100
                        logger.info(f"⏳ Transcrição {task_id}: {progress:.1f}% - {status.get('message', '')}")
                
                await asyncio.sleep(check_interval)
                
            except Exception as e:
                logger.error(f"Erro ao verificar status da transcrição: {e}")
                await asyncio.sleep(check_interval)
        
        logger.error(f"Timeout na transcrição {task_id}")
        return None
    
    async def send_transcription_email(self, video_info: Dict[str, Any], transcription_result: Dict[str, Any]):
        """Envia email com transcrição"""
        try:
            # Preparar dados do email
            email_data = {
                'filename': video_info['name'],
                'date': datetime.now().strftime('%d/%m/%Y %H:%M'),
                'duration': 'N/A',  # Pode ser extraído do vídeo se necessário
                'size_mb': f"{video_info['size_mb']:.1f}",
                'transcription': transcription_result.get('transcription', 'Transcrição não disponível'),
                'task_id': transcription_result.get('task_id', 'N/A')
            }
            
            # Enviar email
            await self.gmail_service.send_transcription_email(
                to_email=self.email_config['destination_email'],
                subject=f"{self.email_config['subject_prefix']} {video_info['name']}",
                email_data=email_data
            )
            
            logger.info(f"📧 Email enviado para {self.email_config['destination_email']}")
            
        except Exception as e:
            logger.error(f"Erro ao enviar email: {e}")
    
    async def start_monitoring(self):
        """Inicia o monitoramento automático"""
        logger.info("🚀 Iniciando monitoramento automático do Google Drive")
        self.monitoring_active = True
        
        while self.monitoring_active:
            try:
                # Verificar novos vídeos
                new_videos = await self.check_new_videos()
                
                # Processar cada vídeo encontrado
                for video in new_videos:
                    await self.process_video(video)
                
                # Aguardar próximo ciclo
                await asyncio.sleep(self.drive_config['monitor_interval'])
                
            except Exception as e:
                logger.error(f"Erro no monitoramento: {e}")
                await asyncio.sleep(60)  # Aguardar 1 minuto em caso de erro
    
    def stop_monitoring(self):
        """Para o monitoramento"""
        logger.info("🛑 Parando monitoramento automático")
        self.monitoring_active = False

# Instância global do monitor
drive_monitor = DriveMonitor() 