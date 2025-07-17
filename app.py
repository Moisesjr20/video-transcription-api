from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import uuid
import requests
from pathlib import Path
import logging
from datetime import datetime
import re
import json
import moviepy.editor as mp
from moviepy.video.io.VideoFileClip import VideoFileClip
import whisper
import gdown
from typing import Optional, List

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

logger.info("=" * 50)
logger.info("INICIANDO TRANSCRITOR API")
logger.info("=" * 50)
logger.info(f"Python version: {os.sys.version}")
logger.info(f"Working directory: {os.getcwd()}")
logger.info(f"Build date: {os.environ.get('BUILD_DATE', 'Unknown')}")

app = FastAPI(
    title="Transcritor API",
    description="API para transcrição de vídeos do Google Drive ou URL",
    version="1.0.0"
)

# Servir arquivos estáticos
if not os.path.exists("static"): 
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

TEMP_DIR = Path("temp")
DOWNLOADS_DIR = Path("downloads")
TRANSCRIPTIONS_DIR = Path("transcriptions")
TASKS_DIR = Path("tasks")
for directory in [TEMP_DIR, DOWNLOADS_DIR, TRANSCRIPTIONS_DIR, TASKS_DIR]:
    directory.mkdir(exist_ok=True)

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
    language: Optional[str] = None

class TranscriptionResponse(BaseModel):
    task_id: str
    status: str
    message: str
    upload_status: str
    estimated_time: Optional[str] = None
    check_status_url: Optional[str] = None

class TranscriptionStatus(BaseModel):
    task_id: str
    status: str
    progress: float
    message: str
    transcription: Optional[str] = None
    segments: Optional[List[dict]] = None
    filename: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None
    file_info: Optional[dict] = None

transcription_tasks = {}

def save_task_to_file(task_id: str, task_data: dict):
    try:
        task_file = TASKS_DIR / f"{task_id}.json"
        with open(task_file, 'w', encoding='utf-8') as f:
            json.dump(task_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Erro ao salvar tarefa {task_id}: {e}")

def load_task_from_file(task_id: str) -> Optional[dict]:
    try:
        task_file = TASKS_DIR / f"{task_id}.json"
        if task_file.exists():
            with open(task_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Erro ao carregar tarefa {task_id}: {e}")
    return None

def get_file_size_mb(file_path: Path) -> float:
    return file_path.stat().st_size / (1024 * 1024)

def extract_google_drive_id(url: str) -> str:
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
    url = f'https://drive.google.com/uc?id={file_id}'
    logger.info(f"📥 Iniciando download do Google Drive com gdown: {url}")
    output_path = str(destination)
    gdown.download(url, output_path, quiet=False, fuzzy=True)
    if not destination.exists() or destination.stat().st_size == 0:
        raise Exception(f"Falha no download com gdown. O arquivo de destino não foi criado ou está vazio: {destination}")
    logger.info(f"✅ Download via gdown concluído. Arquivo salvo em: {destination}")
    return destination

def transcribe_audio_segment(audio_path: Path, model, language: Optional[str] = None) -> dict:
    try:
        logger.info(f"🎤 Transcrevendo segmento: {audio_path.name}")
        
        # Converter para path absoluto e normalizar
        audio_path_abs = audio_path.resolve()
        logger.info(f"📁 Path absoluto: {audio_path_abs}")
        
        # Verificar se o arquivo existe
        if not audio_path_abs.exists():
            logger.error(f"❌ Arquivo não encontrado: {audio_path_abs}")
            return {
                'text': f"[ERRO: Arquivo não encontrado - {audio_path_abs}]",
                'segments': [],
                'language': 'unknown'
            }
        
        # Verificar tamanho do arquivo
        file_size = audio_path_abs.stat().st_size
        logger.info(f"📁 Tamanho do arquivo: {file_size} bytes")
        
        if file_size == 0:
            logger.error(f"❌ Arquivo vazio: {audio_path_abs}")
            return {
                'text': "[ERRO: Arquivo de áudio vazio]",
                'segments': [],
                'language': 'unknown'
            }
        
        # Usar path absoluto como string e garantir que está correto
        audio_file_str = str(audio_path_abs)
        logger.info(f"🎵 Iniciando transcrição do arquivo: {audio_file_str}")
        
        # Verificar se o arquivo ainda existe antes de transcrever
        if not os.path.exists(audio_file_str):
            logger.error(f"❌ Arquivo não encontrado no momento da transcrição: {audio_file_str}")
            return {
                'text': f"[ERRO: Arquivo não encontrado no momento da transcrição - {audio_file_str}]",
                'segments': [],
                'language': 'unknown'
            }
        
        # Tentar abrir o arquivo para verificar se é acessível
        try:
            with open(audio_file_str, 'rb') as test_file:
                test_file.read(1024)  # Ler apenas os primeiros bytes para testar
            logger.info(f"✅ Arquivo acessível para leitura: {audio_file_str}")
        except Exception as test_error:
            logger.error(f"❌ Erro ao testar acesso ao arquivo: {test_error}")
            return {
                'text': f"[ERRO: Arquivo não acessível - {test_error}]",
                'segments': [],
                'language': 'unknown'
            }
        
        result = model.transcribe(
            audio_file_str,
            language=language,
            task="transcribe"
        )
        
        logger.info(f"✅ Transcrição concluída: {len(result.get('text', ''))} caracteres")
        return {
            'text': result['text'],
            'segments': result.get('segments', []),
            'language': result.get('language', 'unknown')
        }
    except Exception as e:
        logger.error(f"❌ Erro ao transcrever segmento {audio_path}: {e}")
        return {
            'text': f"[ERRO: {str(e)}]",
            'segments': [],
            'language': 'unknown'
        }

async def process_video_transcription(task_id: str, request: VideoTranscriptionRequest):
    try:
        logger.info(f"🎬 Iniciando processamento da tarefa {task_id}")
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
        
        video_path = None
        if request.google_drive_url:
            file_id = extract_google_drive_id(request.google_drive_url)
            video_path = DOWNLOADS_DIR / f"{task_id}_{request.filename or 'video.mp4'}"
            video_path = download_from_google_drive(file_id, video_path)
            transcription_tasks[task_id]['progress'] = 0.1
            transcription_tasks[task_id]['message'] = 'Download concluído, extraindo áudio...'
            save_task_to_file(task_id, transcription_tasks[task_id])
        elif request.url:
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
        
        file_size_mb = get_file_size_mb(video_path)
        transcription_tasks[task_id]['file_info'] = {
            'size_mb': file_size_mb,
            'path': str(video_path)
        }
        
        transcription_tasks[task_id]['progress'] = 0.2
        transcription_tasks[task_id]['message'] = 'Carregando modelo Whisper...'
        save_task_to_file(task_id, transcription_tasks[task_id])
        
        model = load_whisper_model()
        
        transcription_tasks[task_id]['progress'] = 0.3
        transcription_tasks[task_id]['message'] = 'Modelo carregado, iniciando transcrição...'
        save_task_to_file(task_id, transcription_tasks[task_id])
        
        # Transcrição direta do vídeo (sem extrair áudio)
        logger.info(f"🎬 Iniciando transcrição direta do vídeo: {video_path}")
        
        # Tentar transcrição com o path original
        result = transcribe_audio_segment(video_path, model, request.language)
        
        # Se falhar, tentar copiar para um path mais simples
        if "[ERRO:" in result['text']:
            logger.info("🔄 Tentando com path simplificado...")
            try:
                # Criar um path mais simples sem caracteres especiais
                simple_path = DOWNLOADS_DIR / f"simple_{task_id}.mp4"
                import shutil
                shutil.copy2(video_path, simple_path)
                logger.info(f"📋 Arquivo copiado para: {simple_path}")
                
                # Tentar transcrição com o path simplificado
                result = transcribe_audio_segment(simple_path, model, request.language)
                
                # Limpar arquivo temporário
                try:
                    simple_path.unlink()
                except:
                    pass
                    
            except Exception as copy_error:
                logger.error(f"❌ Erro ao copiar arquivo: {copy_error}")
        
        final_transcription = result['text']
        all_segments = result['segments']
        
        transcription_tasks[task_id]['progress'] = 0.9
        transcription_tasks[task_id]['message'] = 'Transcrição concluída, salvando...'
        save_task_to_file(task_id, transcription_tasks[task_id])
        
        transcription_file = TRANSCRIPTIONS_DIR / f"{task_id}_transcription.txt"
        with open(transcription_file, 'w', encoding='utf-8') as f:
            f.write(final_transcription)
        
        transcription_tasks[task_id].update({
            'status': 'sucesso',
            'progress': 1.0,
            'message': 'Transcrição concluída com sucesso!',
            'transcription': final_transcription,
            'segments': all_segments,
            'completed_at': datetime.now().isoformat()
        })
        save_task_to_file(task_id, transcription_tasks[task_id])
        
        try:
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

@app.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_video(request: VideoTranscriptionRequest, background_tasks: BackgroundTasks):
    try:
        task_id = str(uuid.uuid4())
        if not any([request.url, request.google_drive_url, request.base64_data]):
            raise HTTPException(status_code=400, detail="Forneça uma URL, Google Drive URL ou dados base64")
        background_tasks.add_task(process_video_transcription, task_id, request)
        estimated_time = "5-10 minutos"
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

@app.get("/")
def root():
    return FileResponse("static/index.html")

@app.get("/health")
async def health_check():
    """Health check endpoint para o Easypanel"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

@app.get("/status/{task_id}", response_model=TranscriptionStatus)
async def get_transcription_status(task_id: str):
    task = transcription_tasks.get(task_id) or load_task_from_file(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    return task