from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import uuid
import requests
import tempfile
import shutil
from pathlib import Path
import asyncio
from typing import Optional, List
import logging
from datetime import datetime
import re
import json

# Imports para monitoramento automático
from drive_monitor import drive_monitor
from drive_service import DriveService
from gmail_service import GmailService

# Imports para processamento de vídeo
import moviepy.editor as mp
from moviepy.video.io.VideoFileClip import VideoFileClip
import whisper
import gdown

# Imports para OAuth
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import pickle
import json

# Configuração de logging mais detalhada
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Log de informações do sistema
logger.info("=" * 50)
logger.info("INICIANDO API DE TRANSCRIÇÃO DE VÍDEO")
logger.info("=" * 50)
logger.info(f"Python version: {os.sys.version}")
logger.info(f"Working directory: {os.getcwd()}")
logger.info(f"Build date: {os.environ.get('BUILD_DATE', 'Unknown')}")

app = FastAPI(
    title="Video Transcription API",
    description="API para transcrição de vídeos com suporte a Google Drive, divisão automática, extração de legendas e monitoramento automático",
    version="1.3.3"
)

# Diretórios de trabalho
TEMP_DIR = Path("temp")
DOWNLOADS_DIR = Path("downloads")
TRANSCRIPTIONS_DIR = Path("transcriptions")
TASKS_DIR = Path("tasks")

# Criar diretórios se não existirem
for directory in [TEMP_DIR, DOWNLOADS_DIR, TRANSCRIPTIONS_DIR, TASKS_DIR]:
    directory.mkdir(exist_ok=True)

# Criar diretório static se não existir
STATIC_DIR = Path("static")
STATIC_DIR.mkdir(exist_ok=True)

# Montar arquivos estáticos
app.mount("/static", StaticFiles(directory="static"), name="static")

# Carregar modelo Whisper (será carregado na primeira execução)
whisper_model = None

def load_whisper_model():
    global whisper_model
    if whisper_model is None:
        logger.info("Carregando modelo Whisper...")
        whisper_model = whisper.load_model("base")
        logger.info("Modelo Whisper carregado com sucesso!")
    return whisper_model

class VideoTranscriptionRequest(BaseModel):
    url: Optional[str] = None
    google_drive_url: Optional[str] = None
    base64_data: Optional[str] = None
    filename: Optional[str] = None
    extract_subtitles: bool = True
    max_segment_minutes: int = 10
    language: Optional[str] = None  # pt, en, es, etc.

class TranscriptionResponse(BaseModel):
    task_id: str
    status: str
    message: str
    upload_status: str
    estimated_time: Optional[str] = None
    check_status_url: Optional[str] = None

class TranscriptionStatus(BaseModel):
    task_id: str
    status: str  # upload_concluido, em_progresso, sucesso, erro
    progress: float
    message: str
    transcription: Optional[str] = None
    segments: Optional[List[dict]] = None
    filename: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None
    file_info: Optional[dict] = None

# Storage para tarefas em andamento
transcription_tasks = {}

def save_task_to_file(task_id: str, task_data: dict):
    """Salva o status da tarefa em arquivo para persistência"""
    try:
        task_file = TASKS_DIR / f"{task_id}.json"
        with open(task_file, 'w', encoding='utf-8') as f:
            json.dump(task_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Erro ao salvar tarefa {task_id}: {e}")

def load_task_from_file(task_id: str) -> Optional[dict]:
    """Carrega o status da tarefa do arquivo"""
    try:
        task_file = TASKS_DIR / f"{task_id}.json"
        if task_file.exists():
            with open(task_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Erro ao carregar tarefa {task_id}: {e}")
    return None

def load_all_tasks():
    """Carrega todas as tarefas salvas na inicialização"""
    try:
        for task_file in TASKS_DIR.glob("*.json"):
            task_id = task_file.stem
            task_data = load_task_from_file(task_id)
            if task_data:
                transcription_tasks[task_id] = task_data
                logger.info(f"Tarefa {task_id} carregada: {task_data['status']}")
    except Exception as e:
        logger.error(f"Erro ao carregar tarefas: {e}")

def get_file_size_mb(file_path: Path) -> float:
    """Retorna o tamanho do arquivo em MB"""
    return file_path.stat().st_size / (1024 * 1024)

def estimate_transcription_time(file_size_mb: float) -> str:
    """Estima o tempo de transcrição baseado no tamanho do arquivo"""
    # Estimativa: ~1 minuto para cada 10MB
    estimated_minutes = max(1, int(file_size_mb / 10))
    if estimated_minutes < 60:
        return f"{estimated_minutes} minutos"
    else:
        hours = estimated_minutes // 60
        minutes = estimated_minutes % 60
        return f"{hours}h {minutes}min"

def extract_google_drive_id(url: str) -> str:
    """Extrai o ID do Google Drive da URL de compartilhamento"""
    patterns = [
        r'drive\.google\.com/file/d/([a-zA-Z0-9-_]+)',
        r'drive\.google\.com/open\?id=([a-zA-Z0-9-_]+)',
        r'drive\.google\.com/uc\?id=([a-zA-Z0-9-_]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    raise ValueError("URL do Google Drive inválida")

def download_from_google_drive(file_id: str, destination: Path) -> Path:
    """Baixa arquivo do Google Drive usando a biblioteca gdown para robustez."""
    url = f'https://drive.google.com/uc?id={file_id}'
    logger.info(f"📥 Iniciando download do Google Drive com gdown: {url}")
    output_path = str(destination)
    gdown.download(url, output_path, quiet=False, fuzzy=True)
    
    if not destination.exists() or destination.stat().st_size == 0:
        raise Exception(f"Falha no download com gdown. O arquivo de destino não foi criado ou está vazio: {destination}")
        
    logger.info(f"✅ Download via gdown concluído. Arquivo salvo em: {destination}")
    return destination

def extract_subtitles_from_video(video_path: Path) -> Optional[str]:
    """Extrai legendas do vídeo se disponíveis"""
    try:
        video = VideoFileClip(str(video_path))
        
        # Verificar se há streams de legendas
        if hasattr(video, 'audio') and video.audio is not None:
            # Tentar extrair legendas usando ffmpeg
            subtitle_path = video_path.with_suffix('.srt')
            
            # Comando ffmpeg para extrair legendas
            import subprocess
            cmd = [
                'ffmpeg', '-i', str(video_path),
                '-map', '0:s:0',  # Primeiro stream de legendas
                '-c:s', 'srt',
                str(subtitle_path),
                '-y'  # Sobrescrever se existir
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0 and subtitle_path.exists():
                with open(subtitle_path, 'r', encoding='utf-8') as f:
                    subtitles = f.read()
                subtitle_path.unlink()  # Remover arquivo temporário
                return subtitles
            
    except Exception as e:
        logger.warning(f"Erro ao extrair legendas: {e}")
    
    return None

def split_video_by_duration(video_path: Path, max_minutes: int = 10) -> List[Path]:
    """Divide o vídeo em segmentos de duração máxima especificada"""
    video = VideoFileClip(str(video_path))
    duration = video.duration
    max_duration = max_minutes * 60  # Converter para segundos
    
    segments = []
    
    if duration <= max_duration:
        # Vídeo já é curto o suficiente
        segments.append(video_path)
    else:
        # Dividir em segmentos
        num_segments = int(duration / max_duration) + 1
        segment_duration = duration / num_segments
        
        for i in range(num_segments):
            start_time = i * segment_duration
            end_time = min((i + 1) * segment_duration, duration)
            
            segment_path = video_path.parent / f"{video_path.stem}_segment_{i+1:03d}{video_path.suffix}"
            
            segment_video = video.subclip(start_time, end_time)
            segment_video.write_videofile(str(segment_path), verbose=False, logger=None)
            segment_video.close()
            
            segments.append(segment_path)
    
    video.close()
    return segments

def transcribe_audio_segment(audio_path: Path, model, language: Optional[str] = None) -> dict:
    """Transcreve um segmento de áudio usando Whisper"""
    try:
        result = model.transcribe(
            str(audio_path),
            language=language,
            verbose=False
        )
        
        return {
            "text": result["text"].strip(),
            "segments": result.get("segments", []),
            "language": result.get("language", "unknown")
        }
    except Exception as e:
        logger.error(f"Erro na transcrição: {e}")
        return {
            "text": "",
            "segments": [],
            "language": "unknown",
            "error": str(e)
        }

async def process_video_transcription(task_id: str, request: VideoTranscriptionRequest):
    """Processa a transcrição do vídeo de forma assíncrona"""
    try:
        # Fase 1: Upload e preparação
        transcription_tasks[task_id]["status"] = "upload_concluido"
        transcription_tasks[task_id]["progress"] = 0.1
        transcription_tasks[task_id]["message"] = "✅ Upload concluído! Iniciando preparação do vídeo..."
        save_task_to_file(task_id, transcription_tasks[task_id])
        
        # Determinar origem do vídeo
        temp_video_path = None
        
        if request.google_drive_url:
            file_id = extract_google_drive_id(request.google_drive_url)
            filename = request.filename or f"video_{task_id}.mp4"
            temp_video_path = TEMP_DIR / filename
            download_from_google_drive(file_id, temp_video_path)
            
        elif request.url:
            filename = request.filename or f"video_{task_id}.mp4"
            temp_video_path = TEMP_DIR / filename
            response = requests.get(request.url, stream=True)
            response.raise_for_status()
            
            with open(temp_video_path, 'wb') as f:
                shutil.copyfileobj(response.raw, f)
                
        elif request.base64_data:
            import base64
            filename = request.filename or f"video_{task_id}.mp4"
            temp_video_path = TEMP_DIR / filename
            
            # Remover prefixo data: se presente
            if request.base64_data.startswith('data:'):
                base64_data = request.base64_data.split(',')[1]
            else:
                base64_data = request.base64_data
                
            with open(temp_video_path, 'wb') as f:
                f.write(base64.b64decode(base64_data))
        
        # Informações do arquivo
        if temp_video_path and temp_video_path.exists():
            file_size_mb = get_file_size_mb(temp_video_path)
            estimated_time = estimate_transcription_time(file_size_mb)
            
            transcription_tasks[task_id]["file_info"] = {
                "filename": temp_video_path.name,
                "size_mb": round(file_size_mb, 2),
                "estimated_time": estimated_time
            }
        else:
            raise Exception("Erro: Arquivo de vídeo não foi criado corretamente")
        
        # Fase 2: Processamento iniciado
        transcription_tasks[task_id]["status"] = "em_progresso"
        transcription_tasks[task_id]["progress"] = 0.2
        file_size_info = f"({round(file_size_mb, 1)}MB)" if 'file_size_mb' in locals() else ""
        transcription_tasks[task_id]["message"] = f"🎬 Arquivo recebido {file_size_info}. Verificando legendas..."
        save_task_to_file(task_id, transcription_tasks[task_id])
        
        # Extrair legendas se solicitado
        subtitles_text = None
        if request.extract_subtitles:
            subtitles_text = extract_subtitles_from_video(temp_video_path)
            if subtitles_text:
                logger.info("Legendas encontradas no vídeo")
        
        transcription_tasks[task_id]["progress"] = 0.3
        transcription_tasks[task_id]["message"] = "📏 Analisando duração do vídeo..."
        save_task_to_file(task_id, transcription_tasks[task_id])
        
        # Dividir vídeo se necessário
        max_minutes = request.max_segment_minutes or 10
        video_segments = split_video_by_duration(temp_video_path, max_minutes)
        
        transcription_tasks[task_id]["progress"] = 0.4
        transcription_tasks[task_id]["message"] = f"✂️ Vídeo dividido em {len(video_segments)} segmento(s). Convertendo para áudio..."
        save_task_to_file(task_id, transcription_tasks[task_id])
        
        # Converter segmentos para áudio
        audio_segments = []
        for i, video_segment in enumerate(video_segments):
            audio_path = video_segment.with_suffix('.wav')
            
            video_clip = VideoFileClip(str(video_segment))
            audio_clip = video_clip.audio
            audio_clip.write_audiofile(str(audio_path), verbose=False, logger=None)
            audio_clip.close()
            video_clip.close()
            
            audio_segments.append(audio_path)
            
            # Limpar segmento de vídeo se não for o original
            if video_segment != temp_video_path:
                video_segment.unlink()
        
        transcription_tasks[task_id]["progress"] = 0.5
        transcription_tasks[task_id]["message"] = "🤖 Carregando modelo de transcrição..."
        save_task_to_file(task_id, transcription_tasks[task_id])
        
        # Carregar modelo Whisper
        model = load_whisper_model()
        
        transcription_tasks[task_id]["progress"] = 0.6
        transcription_tasks[task_id]["message"] = "🎙️ Iniciando transcrição com inteligência artificial..."
        save_task_to_file(task_id, transcription_tasks[task_id])
        
        # Transcrever cada segmento
        all_transcriptions = []
        all_segments_data = []
        
        for i, audio_path in enumerate(audio_segments):
            transcription_tasks[task_id]["message"] = f"🎯 Transcrevendo segmento {i+1}/{len(audio_segments)}..."
            transcription_tasks[task_id]["progress"] = 0.6 + (0.3 * (i / len(audio_segments)))
            save_task_to_file(task_id, transcription_tasks[task_id])
            
            transcription_result = transcribe_audio_segment(
                audio_path, 
                model, 
                request.language
            )
            
            all_transcriptions.append(transcription_result["text"])
            all_segments_data.extend(transcription_result["segments"])
            
            # Limpar arquivo de áudio
            audio_path.unlink()
        
        # Unir todas as transcrições
        final_transcription = "\n\n".join(all_transcriptions)
        
        # Se havia legendas, adicionar ao resultado
        result_text = final_transcription
        if subtitles_text:
            result_text = f"=== LEGENDAS EXTRAÍDAS ===\n{subtitles_text}\n\n=== TRANSCRIÇÃO DE ÁUDIO ===\n{final_transcription}"
        
        transcription_tasks[task_id]["progress"] = 0.9
        transcription_tasks[task_id]["message"] = "💾 Salvando transcrição..."
        save_task_to_file(task_id, transcription_tasks[task_id])
        
        # Salvar transcrição final
        transcription_filename = f"transcription_{task_id}.txt"
        transcription_path = TRANSCRIPTIONS_DIR / transcription_filename
        
        with open(transcription_path, 'w', encoding='utf-8') as f:
            f.write(result_text)
        
        # Atualizar status final
        transcription_tasks[task_id].update({
            "status": "sucesso",
            "progress": 1.0,
            "message": "🎉 Transcrição concluída com sucesso!",
            "transcription": result_text,
            "segments": all_segments_data,
            "filename": transcription_filename,
            "completed_at": datetime.now().isoformat()
        })
        save_task_to_file(task_id, transcription_tasks[task_id])
        
        # Limpar arquivo de vídeo temporário
        if temp_video_path and temp_video_path.exists():
            temp_video_path.unlink()
            
        logger.info(f"Transcrição {task_id} concluída com sucesso")
        
    except Exception as e:
        logger.error(f"Erro na transcrição {task_id}: {e}")
        transcription_tasks[task_id].update({
            "status": "erro",
            "message": f"❌ Erro: {str(e)}",
            "progress": 0.0,
            "completed_at": datetime.now().isoformat()
        })
        save_task_to_file(task_id, transcription_tasks[task_id])

@app.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_video(request: VideoTranscriptionRequest, background_tasks: BackgroundTasks):
    """Inicia o processo de transcrição de vídeo"""
    
    # Validar entrada
    if not any([request.url, request.google_drive_url, request.base64_data]):
        raise HTTPException(
            status_code=400, 
            detail="É necessário fornecer url, google_drive_url ou base64_data"
        )
    
    # Gerar ID da tarefa
    task_id = str(uuid.uuid4())
    
    # Inicializar status da tarefa
    transcription_tasks[task_id] = {
        "status": "upload_concluido",
        "progress": 0.0,
        "message": "✅ Upload realizado com sucesso! Transcrição será iniciada em instantes...",
        "created_at": datetime.now().isoformat(),
        "transcription": None,
        "segments": None,
        "filename": None,
        "completed_at": None,
        "file_info": None
    }
    
    # Salvar tarefa
    save_task_to_file(task_id, transcription_tasks[task_id])
    
    # Adicionar tarefa ao background
    background_tasks.add_task(process_video_transcription, task_id, request)
    
    return TranscriptionResponse(
        task_id=task_id,
        status="upload_concluido",
        upload_status="sucesso",
        message="🎉 Upload concluído com sucesso! Sua transcrição está sendo processada.",
        estimated_time="A transcrição será iniciada em alguns segundos",
        check_status_url=f"/status/{task_id}"
    )

@app.get("/status/{task_id}", response_model=TranscriptionStatus)
async def get_transcription_status(task_id: str):
    """Obtém o status de uma transcrição"""
    
    # Tentar carregar da memória ou arquivo
    task_data = transcription_tasks.get(task_id)
    if not task_data:
        task_data = load_task_from_file(task_id)
        if task_data:
            transcription_tasks[task_id] = task_data
    
    if not task_data:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    
    return TranscriptionStatus(
        task_id=task_id,
        status=task_data["status"],
        progress=task_data["progress"],
        message=task_data["message"],
        transcription=task_data.get("transcription"),
        segments=task_data.get("segments"),
        filename=task_data.get("filename"),
        created_at=task_data["created_at"],
        completed_at=task_data.get("completed_at"),
        file_info=task_data.get("file_info")
    )

@app.get("/download/{filename}")
async def download_transcription(filename: str):
    """Download do arquivo de transcrição"""
    
    file_path = TRANSCRIPTIONS_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type='text/plain; charset=utf-8'
    )

@app.get("/tasks")
async def list_tasks():
    """Lista todas as tarefas de transcrição"""
    return {
        "tasks": [
            {
                "task_id": task_id,
                "status": data["status"],
                "progress": data["progress"],
                "created_at": data["created_at"],
                "message": data["message"]
            }
            for task_id, data in transcription_tasks.items()
        ]
    }

@app.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    """Remove uma tarefa da lista"""
    
    if task_id not in transcription_tasks:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    
    # Remover arquivos associados se existirem
    task_data = transcription_tasks[task_id]
    if task_data.get("filename"):
        file_path = TRANSCRIPTIONS_DIR / task_data["filename"]
        if file_path.exists():
            file_path.unlink()
    
    del transcription_tasks[task_id]
    
    return {"message": "Tarefa removida com sucesso"}

@app.get("/")
async def root():
    """Endpoint raiz - Interface web ou informações da API"""
    return HTMLResponse(content=open("static/index.html").read(), media_type="text/html")

@app.get("/api")
async def api_info():
    """Endpoint com informações da API"""
    return {
        "message": "Video Transcription API",
        "version": "1.3.0",
        "description": "API para transcrição de vídeos com processamento assíncrono, status em tempo real e monitoramento automático",
        "build_date": os.environ.get('BUILD_DATE', 'Unknown'),
        "status_meanings": {
            "upload_concluido": "Arquivo recebido, transcrição será iniciada",
            "em_progresso": "Transcrição em andamento",
            "sucesso": "Transcrição concluída com sucesso",
            "erro": "Erro durante o processamento"
        },
        "endpoints": [
            "POST /transcribe - Iniciar transcrição (resposta imediata)",
            "GET /status/{task_id} - Verificar status da transcrição",
            "GET /download/{filename} - Download da transcrição",
            "GET /tasks - Listar todas as tarefas",
            "DELETE /tasks/{task_id} - Remover tarefa",
            "POST /monitor/start - Iniciar monitoramento automático",
            "POST /monitor/stop - Parar monitoramento automático",
            "GET /monitor/status - Status do monitoramento",
            "GET /google/test-connection - Testar conexões Google"
        ]
    }

@app.get("/health")
async def health_check():
    """Health check da API com informações detalhadas"""
    import psutil
    import platform
    
    try:
        # Informações do sistema
        memory_info = psutil.virtual_memory()
        disk_info = psutil.disk_usage('/')
        
        health_data = {
                    "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.3.3",
            "build_date": os.environ.get('BUILD_DATE', 'Unknown'),
            "whisper_loaded": whisper_model is not None,
            "system_info": {
                "platform": platform.system(),
                "python_version": platform.python_version(),
                "memory_usage_percent": memory_info.percent,
                "disk_usage_percent": disk_info.percent,
                "available_memory_gb": round(memory_info.available / (1024**3), 2)
            },
            "directories": {
                "temp_exists": TEMP_DIR.exists(),
                "downloads_exists": DOWNLOADS_DIR.exists(),
                "transcriptions_exists": TRANSCRIPTIONS_DIR.exists()
            }
        }
        
        logger.info(f"Health check OK - Memory: {memory_info.percent}%, Disk: {disk_info.percent}%")
        return health_data
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
                    "status": "unhealthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.3.3",
            "error": str(e)
        }

# Carregar tarefas salvas na inicialização
load_all_tasks()

# ============================================================================
# NOVAS ROTAS PARA MONITORAMENTO AUTOMÁTICO
# ============================================================================

class MonitorStatus(BaseModel):
    active: bool
    last_check: Optional[str] = None
    processed_files_count: int
    next_check_in_seconds: Optional[int] = None

class GoogleAuthRequest(BaseModel):
    email: str

@app.post("/monitor/start")
async def start_automated_monitoring():
    """Inicia o monitoramento automático do Google Drive"""
    try:
        # Iniciar monitoramento em background
        asyncio.create_task(drive_monitor.start_monitoring())
        
        return {
            "status": "success",
            "message": "🚀 Monitoramento automático iniciado com sucesso!",
            "details": {
                "folder_id": drive_monitor.drive_config['folder_id'],
                "check_interval": drive_monitor.drive_config['monitor_interval'],
                "destination_email": drive_monitor.email_config['destination_email']
            }
        }
    except Exception as e:
        logger.error(f"Erro ao iniciar monitoramento: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao iniciar monitoramento: {str(e)}")

@app.post("/monitor/stop")
async def stop_automated_monitoring():
    """Para o monitoramento automático"""
    try:
        drive_monitor.stop_monitoring()
        
        return {
            "status": "success",
            "message": "🛑 Monitoramento automático parado com sucesso!"
        }
    except Exception as e:
        logger.error(f"Erro ao parar monitoramento: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao parar monitoramento: {str(e)}")

@app.get("/monitor/status", response_model=MonitorStatus)
async def get_monitor_status():
    """Obtém o status do monitoramento automático"""
    try:
        return MonitorStatus(
            active=drive_monitor.monitoring_active,
            last_check=None,  # Pode ser implementado para rastrear último check
            processed_files_count=len(drive_monitor.processed_files),
            next_check_in_seconds=drive_monitor.drive_config['monitor_interval'] if drive_monitor.monitoring_active else None
        )
    except Exception as e:
        logger.error(f"Erro ao obter status do monitoramento: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao obter status: {str(e)}")

@app.post("/monitor/check-now")
async def check_new_videos_now():
    """Força uma verificação imediata de novos vídeos"""
    try:
        new_videos = await drive_monitor.check_new_videos()
        
        return {
            "status": "success",
            "message": f"🔍 Verificação concluída - {len(new_videos)} novos vídeos encontrados",
            "new_videos": new_videos
        }
    except Exception as e:
        logger.error(f"Erro na verificação manual: {e}")
        raise HTTPException(status_code=500, detail=f"Erro na verificação: {str(e)}")

@app.get("/google/auth-url")
async def get_google_auth_url():
    """Gera URL de autenticação do Google"""
    try:
        from google_config import get_google_credentials, GOOGLE_SCOPES
        
        # Debug: verificar configurações
        logger.info("🔍 Verificando configurações OAuth...")
        
        creds = get_google_credentials()
        logger.info(f"Client ID configurado: {'Sim' if creds['client_id'] else 'Não'}")
        logger.info(f"Client Secret configurado: {'Sim' if creds['client_secret'] else 'Não'}")
        logger.info(f"Redirect URI: {creds['redirect_uri']}")
        
        # Verificar se as credenciais estão configuradas
        if not creds['client_id'] or not creds['client_secret']:
            raise Exception("Credenciais do Google não configuradas. Configure GOOGLE_CLIENT_ID e GOOGLE_CLIENT_SECRET no Easypanel.")
        
        # Criar fluxo de autenticação
        flow = InstalledAppFlow.from_client_config(
            {
                "installed": {
                    "client_id": creds['client_id'],
                    "project_id": "video-transcription-api",
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_secret": creds['client_secret'],
                    "redirect_uris": [creds['redirect_uri']]
                }
            },
            GOOGLE_SCOPES
        )
        
        # Salvar o fluxo para usar no callback
        with open('oauth_flow.pickle', 'wb') as f:
            pickle.dump(flow, f)
        
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            prompt='consent',
            include_granted_scopes='true'
        )
        
        logger.info("✅ URL de autenticação gerada com sucesso")
        
        return {
            "auth_url": auth_url,
            "message": "Acesse esta URL para autorizar o acesso ao Google Drive e Gmail"
        }
    except Exception as e:
        logger.error(f"Erro ao gerar URL de autenticação: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao gerar URL: {str(e)}")

@app.get("/auth/callback")
async def oauth_callback(code: str = None, error: str = None):
    """Endpoint de callback para OAuth2"""
    try:
        if error:
            logger.error(f"Erro no OAuth: {error}")
            return HTMLResponse(f"""
            <html>
            <head><title>Erro de Autenticação</title></head>
            <body>
                <h1>❌ Erro de Autenticação</h1>
                <p>Erro: {error}</p>
                <p><a href="/">Voltar ao início</a></p>
            </body>
            </html>
            """)
        
        if not code:
            return HTMLResponse("""
            <html>
            <head><title>Erro de Autenticação</title></head>
            <body>
                <h1>❌ Código de autorização não recebido</h1>
                <p><a href="/">Voltar ao início</a></p>
            </body>
            </html>
            """)
        
        # Carregar o fluxo salvo
        try:
            with open('oauth_flow.pickle', 'rb') as f:
                flow = pickle.load(f)
        except FileNotFoundError:
            return HTMLResponse("""
            <html>
            <head><title>Erro de Autenticação</title></head>
            <body>
                <h1>❌ Sessão de autenticação expirada</h1>
                <p>Por favor, inicie o processo de autenticação novamente.</p>
                <p><a href="/">Voltar ao início</a></p>
            </body>
            </html>
            """)
        
        # Trocar o código por tokens
        flow.fetch_token(code=code)
        
        # Salvar as credenciais
        credentials = flow.credentials
        creds_data = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }
        
        with open('token.json', 'w') as f:
            json.dump(creds_data, f)
        
        # Limpar o arquivo de fluxo
        try:
            os.remove('oauth_flow.pickle')
        except:
            pass
        
        logger.info("✅ Autenticação OAuth concluída com sucesso!")
        
        return HTMLResponse(f"""
        <html>
        <head>
            <title>Autenticação Concluída</title>
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; margin-top: 50px; }}
                .success {{ color: #28a745; }}
                .info {{ color: #17a2b8; }}
            </style>
        </head>
        <body>
            <h1 class="success">✅ Autenticação Concluída!</h1>
            <p class="info">As credenciais do Google foram configuradas com sucesso.</p>
            <p>Você pode fechar esta janela e voltar à interface principal.</p>
            <p><a href="/">Voltar ao início</a></p>
        </body>
        </html>
        """)
        
    except Exception as e:
        logger.error(f"Erro no callback OAuth: {e}")
        return HTMLResponse(f"""
        <html>
        <head><title>Erro de Autenticação</title></head>
        <body>
            <h1>❌ Erro durante a autenticação</h1>
            <p>Erro: {str(e)}</p>
            <p><a href="/">Voltar ao início</a></p>
        </body>
        </html>
        """)

@app.get("/google/test-connection")
async def test_google_connection():
    """Testa conexão com Google APIs"""
    try:
        drive_service = DriveService()
        gmail_service = GmailService()
        
        drive_ok = await drive_service.test_connection()
        gmail_ok = await gmail_service.test_connection()
        
        return {
            "drive_connection": "✅ OK" if drive_ok else "❌ FALHA",
            "gmail_connection": "✅ OK" if gmail_ok else "❌ FALHA",
            "drive_user_email": drive_service.get_user_email() if drive_ok else None,
            "gmail_user_email": gmail_service.get_user_email() if gmail_ok else None
        }
    except Exception as e:
        logger.error(f"Erro ao testar conexões Google: {e}")
        raise HTTPException(status_code=500, detail=f"Erro nos testes: {str(e)}")

@app.get("/google/debug-config")
async def debug_google_config():
    """Debug: verifica configurações do Google"""
    try:
        from google_config import get_google_credentials
        
        creds = get_google_credentials()
        
        return {
            "client_id_configured": bool(creds['client_id']),
            "client_secret_configured": bool(creds['client_secret']),
            "redirect_uri": creds['redirect_uri'],
            "client_id_preview": creds['client_id'][:10] + "..." if creds['client_id'] else "Não configurado",
            "client_secret_preview": creds['client_secret'][:10] + "..." if creds['client_secret'] else "Não configurado",
            "environment_vars": {
                "GOOGLE_CLIENT_ID": os.environ.get("GOOGLE_CLIENT_ID", "Não configurado"),
                "GOOGLE_CLIENT_SECRET": os.environ.get("GOOGLE_CLIENT_SECRET", "Não configurado"),
                "GOOGLE_REDIRECT_URI": os.environ.get("GOOGLE_REDIRECT_URI", "Não configurado")
            }
        }
    except Exception as e:
        logger.error(f"Erro ao debug configurações: {e}")
        raise HTTPException(status_code=500, detail=f"Erro no debug: {str(e)}")

@app.post("/google/send-test-email")
async def send_test_email(request: GoogleAuthRequest):
    """Envia email de teste"""
    try:
        gmail_service = GmailService()
        
        success = await gmail_service.send_simple_email(
            to_email=request.email,
            subject="🧪 Teste - API de Transcrição",
            body="Este é um email de teste da API de Transcrição de Vídeos. Se você recebeu este email, a configuração do Gmail está funcionando corretamente!"
        )
        
        if success:
            return {
                "status": "success",
                "message": f"📧 Email de teste enviado para {request.email}"
            }
        else:
            raise HTTPException(status_code=500, detail="Falha ao enviar email de teste")
            
    except Exception as e:
        logger.error(f"Erro ao enviar email de teste: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao enviar email: {str(e)}")

# Log da versão na inicialização
logger.info("API de Transcrição de Vídeo iniciada. Versão: 1.3.3")
logger.info(f"Diretórios criados: {[str(d) for d in [TEMP_DIR, DOWNLOADS_DIR, TRANSCRIPTIONS_DIR, TASKS_DIR]]}")
logger.info(f"Tarefas carregadas: {len(transcription_tasks)}")
logger.info("Aplicação pronta para receber requisições!")
logger.info("=" * 50)