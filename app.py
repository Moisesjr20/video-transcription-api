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
from drive_monitor import DriveMonitor
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
logger.info("INICIANDO TRANSCRITOR AUTOMÁTICO")
logger.info("=" * 50)
logger.info(f"Python version: {os.sys.version}")
logger.info(f"Working directory: {os.getcwd()}")
logger.info(f"Build date: {os.environ.get('BUILD_DATE', 'Unknown')}")

app = FastAPI(
    title="Transcritor Automático",
    description="Aplicação para monitoramento automático de vídeos no Google Drive e transcrição automática",
    version="2.0.0"
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

# Instância do monitor
drive_monitor = DriveMonitor()

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
    """Transcreve um segmento de áudio"""
    try:
        logger.info(f"🎤 Transcrevendo segmento: {audio_path.name}")
        
        # Transcrever com Whisper
        result = model.transcribe(
            str(audio_path),
            language=language,
            task="transcribe"
        )
        
        return {
            'text': result['text'],
            'segments': result.get('segments', []),
            'language': result.get('language', 'unknown')
        }
        
    except Exception as e:
        logger.error(f"Erro ao transcrever segmento {audio_path}: {e}")
        return {
            'text': f"[ERRO: {str(e)}]",
            'segments': [],
            'language': 'unknown'
        }

async def process_video_transcription(task_id: str, request: VideoTranscriptionRequest):
    """Processa a transcrição de um vídeo em background"""
    try:
        logger.info(f"🎬 Iniciando processamento da tarefa {task_id}")
        
        # Atualizar status inicial
        transcription_tasks[task_id] = {
            'task_id': task_id,
            'status': 'em_progresso',
            'progress': 0.0,
            'message': 'Iniciando download...',
            'transcription': None,
            'segments': [],
            'filename': request.filename or 'video',
            'created_at': datetime.now().isoformat(),
            'completed_at': None,
            'file_info': {}
        }
        save_task_to_file(task_id, transcription_tasks[task_id])
        
        # Determinar fonte do vídeo
        video_path = None
        if request.google_drive_url:
            # Download do Google Drive
            file_id = extract_google_drive_id(request.google_drive_url)
            video_path = DOWNLOADS_DIR / f"{task_id}_{request.filename or 'video.mp4'}"
            video_path = download_from_google_drive(file_id, video_path)
            
            transcription_tasks[task_id]['progress'] = 0.1
            transcription_tasks[task_id]['message'] = 'Download concluído, extraindo áudio...'
            save_task_to_file(task_id, transcription_tasks[task_id])
            
        elif request.url:
            # Download de URL
            video_path = DOWNLOADS_DIR / f"{task_id}_{request.filename or 'video.mp4'}"
            response = requests.get(request.url, stream=True)
            response.raise_for_status()
            
            with open(video_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
            transcription_tasks[task_id]['progress'] = 0.1
            transcription_tasks[task_id]['message'] = 'Download concluído, extraindo áudio...'
            save_task_to_file(task_id, transcription_tasks[task_id])
            
        elif request.base64_data:
            # Dados base64
            import base64
            video_path = DOWNLOADS_DIR / f"{task_id}_{request.filename or 'video.mp4'}"
            video_data = base64.b64decode(request.base64_data)
            
            with open(video_path, 'wb') as f:
                f.write(video_data)
                
            transcription_tasks[task_id]['progress'] = 0.1
            transcription_tasks[task_id]['message'] = 'Arquivo salvo, extraindo áudio...'
            save_task_to_file(task_id, transcription_tasks[task_id])
        else:
            raise ValueError("Nenhuma fonte de vídeo fornecida")
        
        # Informações do arquivo
        file_size_mb = get_file_size_mb(video_path)
        transcription_tasks[task_id]['file_info'] = {
            'size_mb': file_size_mb,
            'path': str(video_path)
        }
        
        # Extrair áudio
        audio_path = TEMP_DIR / f"{task_id}_audio.wav"
        video = VideoFileClip(str(video_path))
        video.audio.write_audiofile(str(audio_path), verbose=False, logger=None)
        video.close()
        
        transcription_tasks[task_id]['progress'] = 0.2
        transcription_tasks[task_id]['message'] = 'Áudio extraído, carregando modelo...'
        save_task_to_file(task_id, transcription_tasks[task_id])
        
        # Carregar modelo Whisper
        model = load_whisper_model()
        
        transcription_tasks[task_id]['progress'] = 0.3
        transcription_tasks[task_id]['message'] = 'Modelo carregado, iniciando transcrição...'
        save_task_to_file(task_id, transcription_tasks[task_id])
        
        # Verificar se precisa dividir o vídeo
        duration = VideoFileClip(str(video_path)).duration
        max_duration = request.max_segment_minutes * 60
        
        if duration > max_duration:
            # Dividir vídeo em segmentos
            transcription_tasks[task_id]['message'] = f'Vídeo longo ({duration/60:.1f}min), dividindo em segmentos...'
            save_task_to_file(task_id, transcription_tasks[task_id])
            
            segments = split_video_by_duration(video_path, request.max_segment_minutes)
            all_transcriptions = []
            all_segments = []
            
            for i, segment_path in enumerate(segments):
                # Extrair áudio do segmento
                segment_audio = TEMP_DIR / f"{task_id}_segment_{i}_audio.wav"
                segment_video = VideoFileClip(str(segment_path))
                segment_video.audio.write_audiofile(str(segment_audio), verbose=False, logger=None)
                segment_video.close()
                
                # Transcrever segmento
                progress = 0.3 + (0.6 * (i + 1) / len(segments))
                transcription_tasks[task_id]['progress'] = progress
                transcription_tasks[task_id]['message'] = f'Transcrevendo segmento {i+1}/{len(segments)}...'
                save_task_to_file(task_id, transcription_tasks[task_id])
                
                result = transcribe_audio_segment(segment_audio, model, request.language)
                all_transcriptions.append(result['text'])
                all_segments.extend(result['segments'])
                
                # Limpar arquivo temporário
                segment_audio.unlink()
                segment_path.unlink()
            
            final_transcription = ' '.join(all_transcriptions)
        else:
            # Transcrever vídeo completo
            transcription_tasks[task_id]['message'] = 'Transcrevendo vídeo...'
            save_task_to_file(task_id, transcription_tasks[task_id])
            
            result = transcribe_audio_segment(audio_path, model, request.language)
            final_transcription = result['text']
            all_segments = result['segments']
        
        transcription_tasks[task_id]['progress'] = 0.9
        transcription_tasks[task_id]['message'] = 'Transcrição concluída, salvando...'
        save_task_to_file(task_id, transcription_tasks[task_id])
        
        # Salvar transcrição
        transcription_file = TRANSCRIPTIONS_DIR / f"{task_id}_transcription.txt"
        with open(transcription_file, 'w', encoding='utf-8') as f:
            f.write(final_transcription)
        
        # Atualizar status final
        transcription_tasks[task_id].update({
            'status': 'sucesso',
            'progress': 1.0,
            'message': 'Transcrição concluída com sucesso!',
            'transcription': final_transcription,
            'segments': all_segments,
            'completed_at': datetime.now().isoformat()
        })
        save_task_to_file(task_id, transcription_tasks[task_id])
        
        # Limpar arquivos temporários
        try:
            audio_path.unlink()
            video_path.unlink()
        except:
            pass
        
        logger.info(f"✅ Transcrição {task_id} concluída com sucesso!")
        
    except Exception as e:
        logger.error(f"❌ Erro na transcrição {task_id}: {e}")
        transcription_tasks[task_id].update({
            'status': 'erro',
            'progress': 0.0,
            'message': f'Erro: {str(e)}',
            'completed_at': datetime.now().isoformat()
        })
        save_task_to_file(task_id, transcription_tasks[task_id])

# Rotas da API
@app.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_video(request: VideoTranscriptionRequest, background_tasks: BackgroundTasks):
    """Endpoint para transcrição de vídeo"""
    try:
        task_id = str(uuid.uuid4())
        
        # Validar entrada
        if not any([request.url, request.google_drive_url, request.base64_data]):
            raise HTTPException(status_code=400, detail="Forneça uma URL, Google Drive URL ou dados base64")
        
        # Iniciar processamento em background
        background_tasks.add_task(process_video_transcription, task_id, request)
        
        # Estimar tempo
        estimated_time = "5-10 minutos"  # Estimativa padrão
        
        return TranscriptionResponse(
            task_id=task_id,
            status="iniciado",
            message="Transcrição iniciada com sucesso",
            upload_status="concluido",
            estimated_time=estimated_time,
            check_status_url=f"/status/{task_id}"
        )
        
    except Exception as e:
        logger.error(f"Erro ao iniciar transcrição: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/{task_id}", response_model=TranscriptionStatus)
async def get_transcription_status(task_id: str):
    """Retorna o status de uma transcrição"""
    try:
        task_data = transcription_tasks.get(task_id)
        if not task_data:
            task_data = load_task_from_file(task_id)
        
        if not task_data:
            raise HTTPException(status_code=404, detail="Tarefa não encontrada")
        
        return TranscriptionStatus(**task_data)
        
    except Exception as e:
        logger.error(f"Erro ao obter status da tarefa {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/download/{filename}")
async def download_transcription(filename: str):
    """Download de arquivo de transcrição"""
    try:
        file_path = TRANSCRIPTIONS_DIR / filename
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Arquivo não encontrado")
        
        return FileResponse(file_path, filename=filename)
        
    except Exception as e:
        logger.error(f"Erro ao fazer download: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tasks")
async def list_tasks():
    """Lista todas as tarefas"""
    try:
        tasks = []
        for task_id, task_data in transcription_tasks.items():
            tasks.append(task_data)
        
        # Carregar tarefas salvas
        for task_file in TASKS_DIR.glob("*.json"):
            task_id = task_file.stem
            if task_id not in transcription_tasks:
                task_data = load_task_from_file(task_id)
                if task_data:
                    tasks.append(task_data)
        
        return tasks
        
    except Exception as e:
        logger.error(f"Erro ao listar tarefas: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    """Deleta uma tarefa"""
    try:
        if task_id in transcription_tasks:
            del transcription_tasks[task_id]
        
        # Deletar arquivo salvo
        task_file = TASKS_DIR / f"{task_id}.json"
        if task_file.exists():
            task_file.unlink()
        
        return {"message": "Tarefa deletada com sucesso"}
        
    except Exception as e:
        logger.error(f"Erro ao deletar tarefa {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Rotas da interface web
@app.get("/")
async def root():
    """Página principal"""
    return FileResponse("static/index.html")

@app.get("/health")
async def health_check():
    """Verificação de saúde da API"""
    try:
        import psutil
        import platform
        
        # Informações do sistema
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        system_info = {
            'memory_usage_percent': memory.percent,
            'disk_usage_percent': disk.percent,
            'cpu_percent': psutil.cpu_percent(),
            'platform': platform.platform(),
            'python_version': platform.python_version()
        }
        
        return {
            "status": "healthy",
            "version": "2.0.0",
            "timestamp": datetime.now().isoformat(),
            "whisper_loaded": whisper_model is not None,
            "system_info": system_info,
            "monitor_active": drive_monitor.monitoring_active
        }
        
    except Exception as e:
        logger.error(f"Erro no health check: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# Rotas de monitoramento
class MonitorStatus(BaseModel):
    active: bool
    last_check: Optional[str] = None
    processed_files_count: int
    next_check_in_seconds: Optional[int] = None

@app.post("/monitor/start")
async def start_automated_monitoring():
    """Inicia o monitoramento automático"""
    try:
        await drive_monitor.start_monitoring()
        return {"message": "Monitoramento iniciado com sucesso"}
    except Exception as e:
        logger.error(f"Erro ao iniciar monitoramento: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/monitor/stop")
async def stop_automated_monitoring():
    """Para o monitoramento automático"""
    try:
        drive_monitor.stop_monitoring()
        return {"message": "Monitoramento parado com sucesso"}
    except Exception as e:
        logger.error(f"Erro ao parar monitoramento: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/monitor/status", response_model=MonitorStatus)
async def get_monitor_status():
    """Retorna o status do monitoramento"""
    try:
        return MonitorStatus(
            active=drive_monitor.monitoring_active,
            last_check=drive_monitor.last_check.isoformat() if hasattr(drive_monitor, 'last_check') and drive_monitor.last_check else None,
            processed_files_count=len(drive_monitor.processed_files),
            next_check_in_seconds=drive_monitor.check_interval if hasattr(drive_monitor, 'check_interval') else None
        )
    except Exception as e:
        logger.error(f"Erro ao obter status do monitoramento: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/monitor/check-now")
async def check_new_videos_now():
    """Verifica novos vídeos imediatamente"""
    try:
        new_videos = await drive_monitor.check_new_videos()
        
        if new_videos:
            # Processar vídeos encontrados
            for video in new_videos:
                await drive_monitor.process_video(video)
            
            return {
                "message": f"Verificação concluída. {len(new_videos)} novos vídeos processados.",
                "new_videos": new_videos
            }
        else:
            return {
                "message": "Verificação concluída. Nenhum novo vídeo encontrado.",
                "new_videos": []
            }
            
    except Exception as e:
        logger.error(f"Erro na verificação manual: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Rotas de configuração do Google
@app.get("/google/auth-url")
async def get_google_auth_url():
    """Gera URL de autenticação do Google"""
    try:
        from google_config import get_google_credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        
        creds = get_google_credentials()
        scopes = creds['scopes']
        
        flow = InstalledAppFlow.from_client_config(
            {
                "installed": {
                    "client_id": creds['client_id'],
                    "client_secret": creds['client_secret'],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [creds['redirect_uri']]
                }
            },
            scopes=scopes
        )
        
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            redirect_uri=creds['redirect_uri']
        )
        
        return {"auth_url": auth_url}
        
    except Exception as e:
        logger.error(f"Erro ao gerar URL de autenticação: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/auth/callback")
async def oauth_callback(code: str = None, error: str = None):
    """Callback do OAuth"""
    try:
        if error:
            return HTMLResponse(f"""
            <html>
            <head><title>Erro de Autenticação</title></head>
            <body>
                <h1>Erro de Autenticação</h1>
                <p>Erro: {error}</p>
                <a href="/">Voltar ao início</a>
            </body>
            </html>
            """)
        
        if not code:
            return HTMLResponse("""
            <html>
            <head><title>Erro</title></head>
            <body>
                <h1>Erro</h1>
                <p>Código de autorização não fornecido</p>
                <a href="/">Voltar ao início</a>
            </body>
            </html>
            """)
        
        # Processar código de autorização
        from google_config import get_google_credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        
        creds = get_google_credentials()
        scopes = creds['scopes']
        
        flow = InstalledAppFlow.from_client_config(
            {
                "installed": {
                    "client_id": creds['client_id'],
                    "client_secret": creds['client_secret'],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [creds['redirect_uri']]
                }
            },
            scopes=scopes
        )
        
        flow.fetch_token(code=code)
        
        # Salvar credenciais
        with open('token.pickle', 'wb') as token:
            pickle.dump(flow.credentials, token)
        
        return HTMLResponse(f"""
        <html>
        <head><title>Autenticação Concluída</title></head>
        <body>
            <h1>✅ Autenticação Concluída!</h1>
            <p>As credenciais do Google foram configuradas com sucesso.</p>
            <p>Você pode fechar esta janela e voltar à aplicação.</p>
            <script>
                setTimeout(() => {{
                    window.close();
                }}, 3000);
            </script>
        </body>
        </html>
        """)
        
    except Exception as e:
        logger.error(f"Erro no callback OAuth: {e}")
        return HTMLResponse(f"""
        <html>
        <head><title>Erro</title></head>
        <body>
            <h1>Erro de Autenticação</h1>
            <p>Erro: {str(e)}</p>
            <a href="/">Voltar ao início</a>
        </body>
        </html>
        """)

@app.get("/google/test-connection")
async def test_google_connection():
    """Testa a conexão com Google APIs"""
    try:
        # Testar Drive
        drive_service = DriveService()
        drive_status = await drive_service.test_connection()
        
        # Testar Gmail
        gmail_service = GmailService()
        gmail_status = await gmail_service.test_connection()
        
        return {
            "drive_connection": "✅ OK" if drive_status else "❌ Erro",
            "gmail_connection": "✅ OK" if gmail_status else "❌ Erro",
            "overall_status": "✅ OK" if (drive_status and gmail_status) else "❌ Erro"
        }
        
    except Exception as e:
        logger.error(f"Erro no teste de conexão Google: {e}")
        return {
            "drive_connection": "❌ Erro",
            "gmail_connection": "❌ Erro",
            "overall_status": "❌ Erro",
            "error": str(e)
        }

@app.get("/google/debug-config")
async def debug_google_config():
    """Retorna configurações do Google para debug"""
    try:
        from google_config import get_drive_config, get_email_config
        
        drive_config = get_drive_config()
        email_config = get_email_config()
        
        return {
            "drive_config": drive_config,
            "email_config": {
                "destination_email": email_config['destination_email'],
                "sender_name": email_config['sender_name']
            },
            "monitor_interval": drive_config['monitor_interval'],
            "max_file_size": drive_config['max_file_size']
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter configurações: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/google/test-deps")
async def test_google_dependencies():
    """Testa dependências do Google"""
    try:
        results = {}
        
        # Testar imports
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow
            results['google_auth_oauthlib'] = "✅ OK"
        except ImportError as e:
            results['google_auth_oauthlib'] = f"❌ Erro: {e}"
        
        try:
            from google.oauth2.credentials import Credentials
            results['google_oauth2'] = "✅ OK"
        except ImportError as e:
            results['google_oauth2'] = f"❌ Erro: {e}"
        
        try:
            from google.auth.transport.requests import Request
            results['google_auth_transport'] = "✅ OK"
        except ImportError as e:
            results['google_auth_transport'] = f"❌ Erro: {e}"
        
        try:
            from googleapiclient.discovery import build
            results['googleapiclient'] = "✅ OK"
        except ImportError as e:
            results['googleapiclient'] = f"❌ Erro: {e}"
        
        # Testar arquivos de configuração
        config_files = ['gmail_credentials.json', 'token.pickle']
        for file in config_files:
            if Path(file).exists():
                results[f'file_{file}'] = "✅ Existe"
            else:
                results[f'file_{file}'] = "❌ Não encontrado"
        
        return results
        
    except Exception as e:
        logger.error(f"Erro no teste de dependências: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/google/setup-auth")
async def setup_google_auth():
    """Configura autenticação do Google"""
    try:
        from google_config import get_google_credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        
        creds = get_google_credentials()
        scopes = creds['scopes']
        
        flow = InstalledAppFlow.from_client_config(
            {
                "installed": {
                    "client_id": creds['client_id'],
                    "client_secret": creds['client_secret'],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [creds['redirect_uri']]
                }
            },
            scopes=scopes
        )
        
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            redirect_uri=creds['redirect_uri']
        )
        
        return {"auth_url": auth_url}
        
    except Exception as e:
        logger.error(f"Erro na configuração de autenticação: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/google/complete-auth")
async def complete_google_auth(code: str):
    """Completa autenticação do Google"""
    try:
        from google_config import get_google_credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        
        creds = get_google_credentials()
        scopes = creds['scopes']
        
        flow = InstalledAppFlow.from_client_config(
            {
                "installed": {
                    "client_id": creds['client_id'],
                    "client_secret": creds['client_secret'],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [creds['redirect_uri']]
                }
            },
            scopes=scopes
        )
        
        flow.fetch_token(code=code)
        
        # Salvar credenciais
        with open('token.pickle', 'wb') as token:
            pickle.dump(flow.credentials, token)
        
        return {"message": "Autenticação concluída com sucesso"}
        
    except Exception as e:
        logger.error(f"Erro ao completar autenticação: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class GoogleAuthRequest(BaseModel):
    email: str

@app.post("/google/send-test-email")
async def send_test_email(request: GoogleAuthRequest):
    """Envia email de teste"""
    try:
        gmail_service = GmailService()
        await gmail_service.send_test_email(request.email)
        return {"message": "Email de teste enviado com sucesso"}
    except Exception as e:
        logger.error(f"Erro ao enviar email de teste: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Inicialização
if __name__ == "__main__":
    import uvicorn
    
    # Carregar tarefas salvas
    load_all_tasks()
    
    # Iniciar servidor
    uvicorn.run(app, host="0.0.0.0", port=8000)