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
        
        audio_path = TEMP_DIR / f"{task_id}_audio.wav"
        
        # Verificar se o vídeo tem áudio
        video = VideoFileClip(str(video_path))
        if video.audio is None:
            raise Exception("O vídeo não possui áudio para transcrever")
        
        # Extrair áudio com tratamento de erro
        try:
            video.audio.write_audiofile(str(audio_path), verbose=False, logger=None)
            video.close()
            
            # Verificar se o arquivo de áudio foi criado
            if not audio_path.exists():
                raise Exception("Falha ao criar arquivo de áudio")
                
        except Exception as e:
            video.close()
            raise Exception(f"Erro ao extrair áudio: {str(e)}")
        
        transcription_tasks[task_id]['progress'] = 0.2
        transcription_tasks[task_id]['message'] = 'Áudio extraído, carregando modelo...'
        save_task_to_file(task_id, transcription_tasks[task_id])
        
        model = load_whisper_model()
        
        transcription_tasks[task_id]['progress'] = 0.3
        transcription_tasks[task_id]['message'] = 'Modelo carregado, iniciando transcrição...'
        save_task_to_file(task_id, transcription_tasks[task_id])
        
        result = transcribe_audio_segment(audio_path, model, request.language)
        final_transcription = result['text']
        all_segments = result['segments']
        
        # Se a transcrição do áudio falhou, tentar transcrição direta do vídeo
        if not final_transcription or final_transcription.strip() == "":
            logger.warning("Transcrição do áudio falhou, tentando transcrição direta do vídeo...")
            result = transcribe_audio_segment(video_path, model, request.language)
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