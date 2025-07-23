from fastapi import FastAPI, HTTPException, BackgroundTasks, Form, Request
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
active_tasks = set()
MAX_CONCURRENT_TASKS = 3

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

def extract_gdrive_id(url: str) -> str:
    """Alias para extract_google_drive_id para compatibilidade"""
    return extract_google_drive_id(url)

def download_from_google_drive(file_id: str, destination: Path) -> Path:
    url = f'https://drive.google.com/uc?id={file_id}'
    logger.info(f"📥 Iniciando download do Google Drive com gdown: {url}")
    output_path = str(destination)
    gdown.download(url, output_path, quiet=False, fuzzy=True)
    if not destination.exists() or destination.stat().st_size == 0:
        raise Exception(f"Falha no download com gdown. O arquivo de destino não foi criado ou está vazio: {destination}")
    logger.info(f"✅ Download via gdown concluído. Arquivo salvo em: {destination}")
    return destination

def transcribe_with_assemblyai(file_path: str) -> dict:
    try:
        logger.info(f"🎤 Transcrevendo com AssemblyAI: {file_path}")
        
        # Converter para path absoluto e normalizar
        file_path_abs = Path(file_path).resolve()
        logger.info(f"📁 Path absoluto: {file_path_abs}")
        
        # Verificar se o arquivo existe
        if not file_path_abs.exists():
            logger.error(f"❌ Arquivo não encontrado: {file_path_abs}")
            return {
                'text': f"[ERRO: Arquivo não encontrado - {file_path_abs}]",
                'segments': [],
                'language': 'unknown'
            }
        
        # Verificar tamanho do arquivo
        file_size = file_path_abs.stat().st_size
        logger.info(f"📁 Tamanho do arquivo: {file_size} bytes")
        
        if file_size == 0:
            logger.error(f"❌ Arquivo vazio: {file_path_abs}")
            return {
                'text': "[ERRO: Arquivo de áudio vazio]",
                'segments': [],
                'language': 'unknown'
            }
        
        # Configurar transcrição
        config = aai.TranscriptionConfig(
            language_code="pt",  # Português como padrão
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
            shutil.copy2(file_path_abs, temp_path)
            
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

def process_video_transcription(task_id: str, url: str):
    """Processa a transcrição do vídeo em background"""
    try:
        logging.info(f"🎬 Iniciando processamento da tarefa {task_id}")
        
        # Criar diretório temporário para o arquivo
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file_path = os.path.join(temp_dir, f"temp_video_{task_id[:8]}.mp4")
            
            # Download do Google Drive
            logging.info(f"📥 Iniciando download do Google Drive com gdown: {url}")
            gdrive_id = extract_gdrive_id(url)
            gdrive_url = f"https://drive.google.com/uc?id={gdrive_id}"
            
            try:
                gdown.download(gdrive_url, temp_file_path, quiet=False)
                logging.info(f"✅ Download via gdown concluído. Arquivo salvo em: {temp_file_path}")
            except Exception as e:
                logging.error(f"❌ Erro no download: {str(e)}")
                save_task_to_file(task_id, {"status": "error", "error": f"Erro no download: {str(e)}"})
                return
            
            # Verificar se o arquivo foi baixado
            if not os.path.exists(temp_file_path):
                error_msg = "Arquivo não foi baixado corretamente"
                logging.error(f"❌ {error_msg}")
                save_task_to_file(task_id, {"status": "error", "error": error_msg})
                return
            
            # Log de checkpoint antes da transcrição
            logging.info(f"🔜 CHECKPOINT: Arquivo baixado, iniciando transcrição AssemblyAI")
            logging.info(f"📁 Path absoluto: {os.path.abspath(temp_file_path)}")
            logging.info(f"📁 Tamanho do arquivo: {os.path.getsize(temp_file_path)} bytes")
            
            # Transcrição com AssemblyAI
            try:
                logging.info(f"🎬 Iniciando transcrição com AssemblyAI: {temp_file_path}")
                result = transcribe_with_assemblyai(temp_file_path)
                
                # Log de checkpoint após transcrição
                logging.info(f"✅ CHECKPOINT: Transcrição AssemblyAI concluída")
                logging.info(f"📊 Resultado: {len(result.get('segments', []))} segmentos")
                
                # Salvar resultado
                save_task_to_file(task_id, {
                    "status": "completed",
                    "result": result,
                    "segments": result.get('segments', []),
                    "text": result.get('text', ''),
                    "duration": result.get('audio_duration', 0)
                })
                
                # Enviar webhook se configurado
                if WEBHOOK_URL:
                    try:
                        logging.info(f"🔗 Enviando resultado para webhook: {WEBHOOK_URL}")
                        webhook_data = {
                            "task_id": task_id,
                            "status": "completed",
                            "text": result.get('text', ''),
                            "segments": result.get('segments', []),
                            "duration": result.get('audio_duration', 0)
                        }
                        
                        response = httpx.post(WEBHOOK_URL, json=webhook_data, timeout=30.0)
                        logging.info(f"✅ Webhook enviado com sucesso. Status: {response.status_code}")
                        
                    except Exception as e:
                        logging.error(f"❌ Erro ao enviar webhook: {str(e)}")
                
                logging.info(f"✅ Processamento concluído com sucesso para tarefa {task_id}")
                
            except Exception as e:
                error_msg = f"Erro na transcrição AssemblyAI: {str(e)}"
                logging.error(f"❌ {error_msg}")
                save_task_to_file(task_id, {"status": "error", "error": error_msg})
                
    except Exception as e:
        error_msg = f"Erro geral no processamento: {str(e)}"
        logging.error(f"❌ {error_msg}")
        save_task_to_file(task_id, {"status": "error", "error": error_msg})
    finally:
        # Remover da lista de tarefas ativas
        if task_id in active_tasks:
            active_tasks.remove(task_id)
            logging.info(f"🧹 Tarefa {task_id} removida da lista ativa")

@app.post("/transcribe")
async def transcribe_video(background_tasks: BackgroundTasks, request: Request):
    """Endpoint para transcrever vídeo do Google Drive"""
    try:
        # Verificar se o servidor está sobrecarregado
        if len(active_tasks) >= MAX_CONCURRENT_TASKS:
            raise HTTPException(status_code=503, detail="Servidor sobrecarregado. Tente novamente em alguns minutos.")
        
        # Tentar obter URL de diferentes formas
        url = None
        
        # Primeiro, tentar como JSON
        try:
            body = await request.json()
            url = body.get('google_drive_url') or body.get('url')
        except:
            pass
        
        # Se não encontrou no JSON, tentar como form data
        if not url:
            form_data = await request.form()
            url = form_data.get('url')
        
        if not url:
            raise HTTPException(status_code=400, detail="URL do Google Drive não fornecida")
        
        # Gerar ID único para a tarefa
        task_id = str(uuid.uuid4())
        
        # Adicionar à lista de tarefas ativas
        active_tasks.add(task_id)
        
        # Iniciar processamento em background
        background_tasks.add_task(process_video_transcription, task_id, url)
        
        logging.info(f"🎬 Iniciando processamento da tarefa {task_id}")
        
        return {
            "task_id": task_id,
            "status": "processing",
            "message": "Transcrição iniciada. Use o endpoint /status/{task_id} para acompanhar o progresso."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"❌ Erro ao iniciar transcrição: {str(e)}")
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