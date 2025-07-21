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
import assemblyai as aai
import gdown
import tempfile
import shutil
import signal
import threading
from typing import Optional, List

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

logger.info("=" * 50)
logger.info("INICIANDO TRANSCRITOR API - ASSEMBLYAI")
logger.info("=" * 50)
logger.info(f"Python version: {os.sys.version}")
logger.info(f"Working directory: {os.getcwd()}")
logger.info(f"Build date: {os.environ.get('BUILD_DATE', 'Unknown')}")

# Configurar AssemblyAI
ASSEMBLYAI_API_KEY = "245ef4a0549d4808bb382cd40d9c054d"
aai.settings.api_key = ASSEMBLYAI_API_KEY

app = FastAPI(
    title="Transcritor API - AssemblyAI",
    description="API para transcrição de vídeos do Google Drive ou URL usando AssemblyAI",
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
        # Garantir que todos os dados sejam serializáveis
        def make_serializable(obj):
            if isinstance(obj, dict):
                return {k: make_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [make_serializable(item) for item in obj]
            elif hasattr(obj, '__dict__'):
                # Para objetos customizados, tentar converter para dict
                return str(obj)
            else:
                return obj
        
        serializable_data = make_serializable(task_data)
        
        task_file = TASKS_DIR / f"{task_id}.json"
        with open(task_file, 'w', encoding='utf-8') as f:
            json.dump(serializable_data, f, indent=2, ensure_ascii=False)
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

def transcribe_with_assemblyai(audio_path: Path, language: Optional[str] = None) -> dict:
    try:
        logger.info(f"🎤 Transcrevendo com AssemblyAI: {audio_path.name}")
        
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
        
        # Configurar transcrição
        config = aai.TranscriptionConfig(
            language_code=language if language else "pt",  # Português como padrão
            speaker_labels=True,
            punctuate=True,
            format_text=True
        )
        
        # Criar transcrição
        transcriber = aai.Transcriber()
        
        # Usar diretório temporário para evitar problemas de path
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir) / f"temp_video_{uuid.uuid4().hex[:8]}.mp4"
            logger.info(f"📋 Copiando arquivo para diretório temporário: {temp_path}")
            
            # Copiar arquivo para diretório temporário
            shutil.copy2(audio_path_abs, temp_path)
            
            # Verificar se a cópia foi bem-sucedida
            if not temp_path.exists():
                logger.error(f"❌ Falha ao copiar arquivo para diretório temporário")
                return {
                    'text': "[ERRO: Falha ao copiar arquivo para diretório temporário]",
                    'segments': [],
                    'language': 'unknown'
                }
            
            logger.info(f"✅ Arquivo copiado com sucesso para: {temp_path}")
            logger.info(f"📁 Tamanho do arquivo temporário: {temp_path.stat().st_size} bytes")
            
            # Tentar transcrição com o arquivo temporário
            try:
                # Adicionar timeout para evitar travamento
                def transcribe_with_timeout():
                    return transcriber.transcribe(str(temp_path), config=config)
                
                # Executar com timeout de 10 minutos
                result = None
                def run_transcription():
                    nonlocal result
                    result = transcribe_with_timeout()
                
                thread = threading.Thread(target=run_transcription)
                thread.daemon = True
                thread.start()
                thread.join(timeout=600)  # 10 minutos de timeout
                
                if thread.is_alive():
                    logger.error("❌ Timeout na transcrição (10 minutos)")
                    return {
                        'text': "[ERRO: Timeout na transcrição - processo demorou mais de 10 minutos]",
                        'segments': [],
                        'language': 'unknown'
                    }
                
                if result is None:
                    logger.error("❌ Transcrição falhou")
                    return {
                        'text': "[ERRO: Falha na transcrição]",
                        'segments': [],
                        'language': 'unknown'
                    }
                
                # Converter resultado da AssemblyAI para formato compatível
                segments = []
                sentences = result.get_sentences()
                logger.info(f"📝 Processando {len(sentences)} sentenças da AssemblyAI")
                
                for i, sentence in enumerate(sentences):
                    # Garantir que o texto seja uma string válida
                    sentence_text = str(sentence) if sentence else ""
                    logger.debug(f"📝 Sentença {i}: {sentence_text[:50]}...")
                    
                    segments.append({
                        'start': i * 1000,  # Estimativa de tempo em milissegundos
                        'end': (i + 1) * 1000,  # Estimativa de tempo em milissegundos
                        'text': sentence_text,
                        'speaker': 'A'
                    })
                
                logger.info(f"✅ {len(segments)} segmentos processados")
                
                logger.info(f"✅ Transcrição AssemblyAI concluída: {len(result.text)} caracteres")
                
                # Garantir que o texto seja uma string válida
                transcription_text = str(result.text) if result.text else ""
                
                return {
                    'text': transcription_text,
                    'segments': segments,
                    'language': result.language_code if hasattr(result, 'language_code') else 'pt'
                }
                
            except Exception as transcribe_error:
                logger.error(f"❌ Erro na transcrição com AssemblyAI: {transcribe_error}")
                return {
                    'text': f"[ERRO: Falha na transcrição - {transcribe_error}]",
                    'segments': [],
                    'language': 'unknown'
                }
        
    except Exception as e:
        logger.error(f"❌ Erro ao transcrever com AssemblyAI {audio_path}: {e}")
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
            transcription_tasks[task_id]['message'] = 'Download concluído, iniciando transcrição...'
            save_task_to_file(task_id, transcription_tasks[task_id])
        elif request.url:
            video_path = DOWNLOADS_DIR / f"{task_id}_{request.filename or 'video.mp4'}"
            response = requests.get(request.url, stream=True)
            response.raise_for_status()
            with open(video_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            transcription_tasks[task_id]['progress'] = 0.1
            transcription_tasks[task_id]['message'] = 'Download concluído, iniciando transcrição...'
            save_task_to_file(task_id, transcription_tasks[task_id])
        elif request.base64_data:
            import base64
            video_path = DOWNLOADS_DIR / f"{task_id}_{request.filename or 'video.mp4'}"
            video_data = base64.b64decode(request.base64_data)
            with open(video_path, 'wb') as f:
                f.write(video_data)
            transcription_tasks[task_id]['progress'] = 0.1
            transcription_tasks[task_id]['message'] = 'Arquivo salvo, iniciando transcrição...'
            save_task_to_file(task_id, transcription_tasks[task_id])
        else:
            raise ValueError("Nenhuma fonte de vídeo fornecida")
        
        file_size_mb = get_file_size_mb(video_path)
        transcription_tasks[task_id]['file_info'] = {
            'size_mb': file_size_mb,
            'path': str(video_path)
        }
        
        transcription_tasks[task_id]['progress'] = 0.2
        transcription_tasks[task_id]['message'] = 'Iniciando transcrição com AssemblyAI...'
        save_task_to_file(task_id, transcription_tasks[task_id])
        
        transcription_tasks[task_id]['progress'] = 0.3
        transcription_tasks[task_id]['message'] = 'Transcrevendo com AssemblyAI...'
        save_task_to_file(task_id, transcription_tasks[task_id])
        
        # Transcrição direta do vídeo com AssemblyAI
        logger.info(f"🎬 Iniciando transcrição com AssemblyAI: {video_path}")
        
        transcription_tasks[task_id]['progress'] = 0.4
        transcription_tasks[task_id]['message'] = 'Processando transcrição...'
        save_task_to_file(task_id, transcription_tasks[task_id])
        
        result = transcribe_with_assemblyai(video_path, request.language)
        
        # Verificar se houve erro na transcrição
        if "[ERRO:" in result['text']:
            raise Exception(f"Falha na transcrição: {result['text']}")
        
        final_transcription = result['text']
        all_segments = result['segments']
        
        transcription_tasks[task_id]['progress'] = 0.9
        transcription_tasks[task_id]['message'] = 'Transcrição concluída, salvando...'
        save_task_to_file(task_id, transcription_tasks[task_id])
        
        transcription_file = TRANSCRIPTIONS_DIR / f"{task_id}_transcription.txt"
        with open(transcription_file, 'w', encoding='utf-8') as f:
            f.write(final_transcription)
        
        # Garantir que os segments sejam serializáveis
        serializable_segments = []
        logger.info(f"🔧 Convertendo {len(all_segments)} segmentos para formato serializável")
        
        for i, segment in enumerate(all_segments):
            if isinstance(segment, dict):
                serializable_segments.append(segment)
            else:
                # Se não for dict, converter para dict
                logger.debug(f"🔧 Convertendo segmento {i} de tipo {type(segment)}")
                serializable_segments.append({
                    'start': getattr(segment, 'start', 0),
                    'end': getattr(segment, 'end', 0),
                    'text': str(getattr(segment, 'text', '')),
                    'speaker': getattr(segment, 'speaker', 'A')
                })
        
        logger.info(f"✅ {len(serializable_segments)} segmentos convertidos com sucesso")
        
        transcription_tasks[task_id].update({
            'status': 'sucesso',
            'progress': 1.0,
            'message': 'Transcrição concluída com sucesso!',
            'transcription': final_transcription,
            'segments': serializable_segments,
            'completed_at': datetime.now().isoformat()
        })
        
        logger.info(f"💾 Salvando tarefa {task_id} com {len(serializable_segments)} segmentos")
        save_task_to_file(task_id, transcription_tasks[task_id])
        logger.info(f"✅ Tarefa {task_id} salva com sucesso")
        
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
        # Verificar se há muitas tarefas ativas
        active_tasks = len([t for t in transcription_tasks.values() if t.get('status') == 'em_progresso'])
        if active_tasks >= 3:
            raise HTTPException(status_code=503, detail="Servidor ocupado. Tente novamente em alguns minutos.")
        
        task_id = str(uuid.uuid4())
        if not any([request.url, request.google_drive_url, request.base64_data]):
            raise HTTPException(status_code=400, detail="Forneça uma URL, Google Drive URL ou dados base64")
        
        # Iniciar tarefa em background
        background_tasks.add_task(process_video_transcription, task_id, request)
        
        estimated_time = "2-5 minutos"
        return TranscriptionResponse(
            task_id=task_id,
            status="iniciado",
            message="Transcrição iniciada com sucesso",
            upload_status="concluido",
            estimated_time=estimated_time,
            check_status_url=f"/status/{task_id}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao iniciar transcrição: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@app.get("/")
def root():
    return FileResponse("static/index.html")

@app.get("/favicon.ico")
def favicon():
    return FileResponse("static/favicon.ico")

@app.get("/health")
async def health_check():
    """Health check endpoint para o Easypanel"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "active_tasks": len(transcription_tasks),
        "provider": "AssemblyAI"
    }

@app.get("/ping")
async def ping():
    """Endpoint simples para verificar se o servidor está respondendo"""
    return {"pong": datetime.now().isoformat()}

@app.get("/status/{task_id}", response_model=TranscriptionStatus)
async def get_transcription_status(task_id: str):
    try:
        task = transcription_tasks.get(task_id) or load_task_from_file(task_id)
        if not task:
            logger.error(f"❌ Tarefa {task_id} não encontrada ao consultar status.")
            raise HTTPException(status_code=404, detail="Tarefa não encontrada")
        # Garantir que os dados sejam serializáveis antes de retornar
        if 'segments' in task and task['segments']:
            logger.debug(f"🔍 Verificando {len(task['segments'])} segmentos para serialização")
            for i, segment in enumerate(task['segments']):
                if not isinstance(segment, dict):
                    logger.warning(f"⚠️ Segmento {i} não é dict: {type(segment)}")
        return task
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro inesperado ao obter status da tarefa {task_id}: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno ao buscar status: {type(e).__name__}: {str(e)}")