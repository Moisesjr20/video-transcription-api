from fastapi import FastAPI, HTTPException, BackgroundTasks, Form, Request, Depends, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator
import os
import uuid
import httpx
from pathlib import Path
import logging
from datetime import datetime, timedelta
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
import time
from typing import Optional, List, Dict, Any

# Imports de segurança
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from config import settings
from auth import AuthManager, get_current_user, require_scope

# Configuração de logging seguro
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(settings.LOG_FILE, encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Log de segurança
security_logger = logging.getLogger('security')
security_handler = logging.FileHandler('logs/security.log', encoding='utf-8')
security_handler.setFormatter(logging.Formatter(
    '%(asctime)s - SECURITY - %(levelname)s - %(message)s'
))
security_logger.addHandler(security_handler)
security_logger.setLevel(logging.INFO)

logger.info("=" * 60)
logger.info("INICIANDO TRANSCRITOR API - ASSEMBLYAI SEGURO")
logger.info("=" * 60)
logger.info(f"Python version: {os.sys.version}")
logger.info(f"Working directory: {os.getcwd()}")
logger.info(f"Environment: {settings.ENVIRONMENT}")
logger.info(f"Debug mode: {settings.DEBUG}")
logger.info(f"Max concurrent tasks: {settings.MAX_CONCURRENT_TASKS}")
logger.info(f"Rate limit: {settings.RATE_LIMIT_REQUESTS}/{settings.RATE_LIMIT_MINUTES}min")
if not settings.ASSEMBLYAI_API_KEY:
    logger.error("❌ ASSEMBLYAI_API_KEY não configurada!")
else:
    logger.info(f"✅ AssemblyAI API configurada (key: ...{settings.ASSEMBLYAI_API_KEY[-4:]})")

# Configurar AssemblyAI com variável de ambiente
aai.settings.api_key = settings.ASSEMBLYAI_API_KEY

# Configurar Rate Limiter
limiter = Limiter(key_func=get_remote_address)

# Configurar WEBHOOK_URL
WEBHOOK_URL = settings.WEBHOOK_URL

app = FastAPI(
    title="Transcritor API - AssemblyAI Seguro",
    description="API segura para transcrição de vídeos do Google Drive ou URL usando AssemblyAI",
    version="2.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None
)

# Configurar Rate Limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else ["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
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
    language: Optional[str] = "pt"
    
    @validator('google_drive_url', 'url')
    def validate_url(cls, v):
        if v and not (v.startswith('http://') or v.startswith('https://')):
            raise ValueError('URL deve começar com http:// ou https://')
        return v
    
    @validator('filename')
    def validate_filename(cls, v):
        if v:
            # Remover caracteres perigosos
            safe_chars = re.sub(r'[^\w\s.-]', '', v)
            if len(safe_chars) > 255:
                raise ValueError('Nome do arquivo muito longo')
            return safe_chars
        return v
    
    @validator('max_segment_minutes')
    def validate_segment_minutes(cls, v):
        if v < 1 or v > 60:
            raise ValueError('max_segment_minutes deve estar entre 1 e 60')
        return v

class TranscriptionResponse(BaseModel):
    task_id: str
    status: str
    message: str
    upload_status: str
    estimated_time: Optional[str] = None
    check_status_url: Optional[str] = None
    
class LoginRequest(BaseModel):
    username: str
    password: str
    
    @validator('username', 'password')
    def validate_credentials(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Campo obrigatório')
        return v.strip()
        
class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int

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
MAX_CONCURRENT_TASKS = settings.MAX_CONCURRENT_TASKS

def save_task_to_file(task_id: str, task_data: dict):
    try:
        # Validar task_id para evitar path traversal
        if not re.match(r'^[a-zA-Z0-9-]+$', task_id):
            logger.error(f"Task ID inválido: {task_id}")
            return
            
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
        
        # Adicionar timestamp e informações de auditoria
        serializable_data.update({
            'saved_at': datetime.now().isoformat(),
            'task_id': task_id
        })
        
        task_file = TASKS_DIR / f"{task_id}.json"
        with open(task_file, 'w', encoding='utf-8') as f:
            json.dump(serializable_data, f, indent=2, ensure_ascii=False)
            
        logger.info(f"✅ Tarefa {task_id} salva com sucesso")
        
    except Exception as e:
        logger.error(f"❌ Erro ao salvar tarefa {task_id}: {e}")
        security_logger.error(f"Falha ao salvar tarefa {task_id}: {e}")

def load_task_from_file(task_id: str) -> Optional[dict]:
    try:
        # Validar task_id para evitar path traversal
        if not re.match(r'^[a-zA-Z0-9-]+$', task_id):
            logger.error(f"Task ID inválido ao carregar: {task_id}")
            security_logger.warning(f"Tentativa de path traversal com task_id: {task_id}")
            return None
            
        task_file = TASKS_DIR / f"{task_id}.json"
        if task_file.exists():
            with open(task_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.debug(f"✅ Tarefa {task_id} carregada com sucesso")
                return data
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON inválido na tarefa {task_id}: {e}")
    except Exception as e:
        logger.error(f"❌ Erro ao carregar tarefa {task_id}: {e}")
    return None

def get_file_size_mb(file_path: Path) -> float:
    """Obtém tamanho do arquivo em MB"""
    try:
        return file_path.stat().st_size / (1024 * 1024)
    except (OSError, FileNotFoundError) as e:
        logger.error(f"Erro ao obter tamanho do arquivo {file_path}: {e}")
        return 0.0

def validate_file_extension(filename: str) -> bool:
    """Valida extensão do arquivo"""
    if not filename:
        return False
    
    extension = filename.lower().split('.')[-1]
    allowed = settings.allowed_extensions_list
    is_valid = extension in allowed
    
    if not is_valid:
        security_logger.warning(f"Tentativa de upload de arquivo com extensão não permitida: {extension}")
    
    return is_valid

def validate_file_size(file_path: Path) -> bool:
    """Valida tamanho do arquivo"""
    try:
        size_mb = get_file_size_mb(file_path)
        is_valid = size_mb <= settings.MAX_FILE_SIZE_MB
        
        if not is_valid:
            security_logger.warning(f"Arquivo muito grande: {size_mb}MB (limite: {settings.MAX_FILE_SIZE_MB}MB)")
            
        return is_valid
    except Exception as e:
        logger.error(f"Erro ao validar tamanho do arquivo: {e}")
        return False

def extract_google_drive_id(url: str) -> str:
    """Extração segura de ID do Google Drive"""
    if not url or not isinstance(url, str):
        raise ValueError("URL inválida")
    
    # Verificar se é realmente do Google Drive
    if 'drive.google.com' not in url:
        security_logger.warning(f"Tentativa de usar URL não-Google Drive: {url[:50]}...")
        raise ValueError("URL deve ser do Google Drive")
    
    patterns = [
        r'drive\.google\.com/file/d/([a-zA-Z0-9-_]{25,50})',
        r'drive\.google\.com/open\?id=([a-zA-Z0-9-_]{25,50})',
        r'drive\.google\.com/uc\?id=([a-zA-Z0-9-_]{25,50})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            file_id = match.group(1)
            # Validar formato do ID
            if len(file_id) >= 25 and len(file_id) <= 50:
                return file_id
    
    security_logger.warning(f"URL do Google Drive com formato inválido: {url[:50]}...")
    raise ValueError("URL do Google Drive inválida ou ID não encontrado")

def extract_gdrive_id(url: str) -> str:
    """Alias para extract_google_drive_id para compatibilidade"""
    return extract_google_drive_id(url)

def download_from_google_drive(file_id: str, destination: Path) -> Path:
    """Download seguro do Google Drive"""
    try:
        # Validar file_id
        if not file_id or not re.match(r'^[a-zA-Z0-9-_]{25,50}$', file_id):
            raise ValueError("ID do arquivo inválido")
        
        url = f'https://drive.google.com/uc?id={file_id}'
        logger.info(f"📥 Iniciando download do Google Drive: ...{file_id[-8:]}")
        
        output_path = str(destination)
        
        # Timeout e retry para download
        max_retries = 3
        for attempt in range(max_retries):
            try:
                gdown.download(url, output_path, quiet=False, fuzzy=True)
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                logger.warning(f"Tentativa {attempt + 1} falhou, tentando novamente: {e}")
                time.sleep(2)
        
        # Verificar se o download foi bem-sucedido
        if not destination.exists():
            raise Exception("Arquivo de destino não foi criado")
            
        if destination.stat().st_size == 0:
            raise Exception("Arquivo de destino está vazio")
        
        # Validar tamanho do arquivo
        if not validate_file_size(destination):
            destination.unlink()  # Remover arquivo muito grande
            raise Exception(f"Arquivo excede limite de {settings.MAX_FILE_SIZE_MB}MB")
        
        file_size_mb = get_file_size_mb(destination)
        logger.info(f"✅ Download concluído: {file_size_mb:.1f}MB em {destination}")
        
        return destination
        
    except Exception as e:
        logger.error(f"❌ Erro no download do Google Drive: {e}")
        security_logger.error(f"Falha no download - file_id: {file_id[:10]}..., erro: {e}")
        raise

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

def process_video_transcription(task_id: str, url: str, username: str = "system"):
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
                        # Log de auditoria para webhook
                        security_logger.info(f"Enviando webhook para tarefa {task_id} de usuário {username}")
                        logging.info(f"🔗 Enviando resultado para webhook: {WEBHOOK_URL[:30]}...")
                        
                        webhook_data = {
                            "task_id": task_id,
                            "status": "completed",
                            "text": result.get('text', ''),
                            "segments": result.get('segments', []),
                            "duration": result.get('audio_duration', 0),
                            "filename": result.get('filename', ''),
                            "completed_at": datetime.now().isoformat(),
                            "user": username
                        }
                        
                        # Usar httpx com timeout
                        with httpx.Client() as client:
                            response = client.post(
                                WEBHOOK_URL, 
                                json=webhook_data, 
                                timeout=30.0,
                                headers={"Content-Type": "application/json"}
                            )
                            response.raise_for_status()
                            
                        logging.info(f"✅ Webhook enviado com sucesso. Status: {response.status_code}")
                        security_logger.info(f"Webhook enviado com sucesso para tarefa {task_id}")
                        
                    except httpx.HTTPError as e:
                        error_msg = f"Erro HTTP no webhook: {e}"
                        logging.error(f"❌ {error_msg}")
                        security_logger.error(f"Falha no webhook para tarefa {task_id}: {error_msg}")
                    except Exception as e:
                        error_msg = f"Erro no webhook: {str(e)}"
                        logging.error(f"❌ {error_msg}")
                        security_logger.error(f"Falha no webhook para tarefa {task_id}: {error_msg}")
                
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

# Endpoint de login
@app.post("/login", response_model=TokenResponse)
@limiter.limit(f"{settings.RATE_LIMIT_REQUESTS * 2}/{settings.RATE_LIMIT_MINUTES}minute")
async def login(request: Request, login_data: LoginRequest):
    """Endpoint para autenticação e obtenção de token"""
    try:
        user = AuthManager.authenticate_user(login_data.username, login_data.password)
        if not user:
            security_logger.warning(f"Tentativa de login falhada para usuário: {login_data.username} - IP: {get_remote_address(request)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciais inválidas"
            )
        
        access_token = AuthManager.create_access_token(
            data={"sub": user["username"]}
        )
        
        security_logger.info(f"Login bem-sucedido para usuário: {user['username']} - IP: {get_remote_address(request)}")
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.JWT_EXPIRATION_HOURS * 3600
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro no login: {e}")
        raise HTTPException(status_code=500, detail="Erro interno no servidor")

# Dependency para verificar scope de transcrição
async def require_transcribe_scope(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    if "transcribe" not in current_user.get("scopes", []):
        logger.warning(f"Usuário {current_user['username']} não tem permissão 'transcribe'")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permissão insuficiente. Requer: transcribe"
        )
    return current_user

# Dependency para verificar scope de admin
async def require_admin_scope(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    if "admin" not in current_user.get("scopes", []):
        logger.warning(f"Usuário {current_user['username']} não tem permissão 'admin'")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permissão insuficiente. Requer: admin"
        )
    return current_user

# Endpoint seguro de transcrição
@app.post("/transcribe-secure")
@limiter.limit(f"{settings.RATE_LIMIT_REQUESTS}/{settings.RATE_LIMIT_MINUTES}minute")
async def transcribe_video_secure(
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(require_transcribe_scope)
):
    """Endpoint seguro para transcrever vídeo do Google Drive"""
    try:
        # Log de auditoria
        client_ip = get_remote_address(request)
        security_logger.info(f"Solicitação de transcrição de {current_user['username']} - IP: {client_ip}")
        
        # Verificar se o servidor está sobrecarregado
        if len(active_tasks) >= MAX_CONCURRENT_TASKS:
            logger.warning(f"Servidor sobrecarregado: {len(active_tasks)}/{MAX_CONCURRENT_TASKS} tarefas ativas")
            raise HTTPException(
                status_code=503, 
                detail=f"Servidor sobrecarregado. {len(active_tasks)} tarefas ativas. Tente novamente em alguns minutos."
            )
        
        # Tentar obter URL de diferentes formas
        url = None
        filename = None
        
        # Primeiro, tentar como JSON
        try:
            body = await request.json()
            url = body.get('google_drive_url') or body.get('url')
            filename = body.get('filename')
        except:
            pass
        
        # Se não encontrou no JSON, tentar como form data
        if not url:
            form_data = await request.form()
            url = form_data.get('url')
            filename = form_data.get('filename')
        
        if not url:
            raise HTTPException(status_code=400, detail="URL do Google Drive não fornecida")
        
        # Validar URL
        try:
            file_id = extract_google_drive_id(url)
        except ValueError as e:
            security_logger.warning(f"URL inválida fornecida por {current_user['username']}: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        
        # Validar filename se fornecido
        if filename and not validate_file_extension(filename):
            raise HTTPException(
                status_code=400, 
                detail=f"Extensão de arquivo não permitida. Permitidas: {', '.join(settings.allowed_extensions_list)}"
            )
        
        # Gerar ID único para a tarefa
        task_id = str(uuid.uuid4())
        
        # Adicionar à lista de tarefas ativas
        active_tasks.add(task_id)
        
        # Salvar informações iniciais da tarefa
        initial_task_data = {
            "task_id": task_id,
            "status": "iniciando",
            "created_at": datetime.now().isoformat(),
            "user": current_user['username'],
            "client_ip": client_ip,
            "url": url[:50] + "..." if len(url) > 50 else url,
            "filename": filename
        }
        save_task_to_file(task_id, initial_task_data)
        
        # Iniciar processamento em background
        background_tasks.add_task(process_video_transcription, task_id, url, current_user['username'])
        
        logger.info(f"🎦 Iniciando processamento da tarefa {task_id} para usuário {current_user['username']}")
        
        return {
            "task_id": task_id,
            "status": "processing",
            "message": "Transcrição iniciada com sucesso!",
            "estimated_time": "2-5 minutos",
            "check_status_url": f"/status/{task_id}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao iniciar transcrição: {str(e)}")
        security_logger.error(f"Erro na transcrição para {current_user.get('username', 'unknown')}: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@app.post("/transcribe")
@limiter.limit(f"{settings.RATE_LIMIT_REQUESTS}/{settings.RATE_LIMIT_MINUTES}minute")
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
        background_tasks.add_task(process_video_transcription, task_id, url, "anonymous")
        
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

# Endpoint administrativo para listar tarefas
@app.get("/admin/tasks")
@limiter.limit(f"{settings.RATE_LIMIT_REQUESTS}/{settings.RATE_LIMIT_MINUTES}minute")
async def list_tasks(
    request: Request,
    current_user: Dict[str, Any] = Depends(require_admin_scope),
    limit: int = 50,
    offset: int = 0
):
    """Endpoint administrativo para listar todas as tarefas"""
    try:
        security_logger.info(f"Admin {current_user['username']} consultando lista de tarefas")
        
        # Listar arquivos de tarefas
        task_files = list(TASKS_DIR.glob("*.json"))
        task_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        # Aplicar paginação
        task_files = task_files[offset:offset + limit]
        
        tasks = []
        for task_file in task_files:
            try:
                with open(task_file, 'r', encoding='utf-8') as f:
                    task_data = json.load(f)
                    # Remover dados sensíveis para lista
                    safe_task = {
                        "task_id": task_data.get("task_id"),
                        "status": task_data.get("status"),
                        "created_at": task_data.get("created_at"),
                        "user": task_data.get("user", "unknown"),
                        "filename": task_data.get("filename")
                    }
                    tasks.append(safe_task)
            except Exception as e:
                logger.warning(f"Erro ao carregar tarefa {task_file.name}: {e}")
        
        return {
            "tasks": tasks,
            "total": len(list(TASKS_DIR.glob("*.json"))),
            "limit": limit,
            "offset": offset,
            "active_tasks": len(active_tasks)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao listar tarefas: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

# Endpoint seguro de status
@app.get("/status-secure/{task_id}")
@limiter.limit(f"{settings.RATE_LIMIT_REQUESTS * 3}/{settings.RATE_LIMIT_MINUTES}minute")
async def get_transcription_status_secure(
    task_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Endpoint seguro para consultar status da transcrição"""
    try:
        # Validar task_id
        if not re.match(r'^[a-zA-Z0-9-]+$', task_id):
            security_logger.warning(f"Task ID inválido solicitado por {current_user['username']}: {task_id}")
            raise HTTPException(status_code=400, detail="ID da tarefa inválido")
        
        task = transcription_tasks.get(task_id) or load_task_from_file(task_id)
        if not task:
            logger.warning(f"Tarefa {task_id} não encontrada (solicitada por {current_user['username']})")
            raise HTTPException(status_code=404, detail="Tarefa não encontrada")
        
        # Verificar se o usuário tem permissão para ver esta tarefa
        # Admin pode ver todas, outros usuários só as próprias
        if "admin" not in current_user.get("scopes", []):
            task_user = task.get("user")
            if task_user and task_user != current_user["username"]:
                security_logger.warning(f"Usuário {current_user['username']} tentou acessar tarefa de {task_user}")
                raise HTTPException(status_code=403, detail="Acesso negado a esta tarefa")
        
        # Garantir que os dados sejam serializáveis antes de retornar
        if 'segments' in task and task['segments']:
            logger.debug(f"🔍 Verificando {len(task['segments'])} segmentos para serialização")
            for i, segment in enumerate(task['segments']):
                if not isinstance(segment, dict):
                    logger.warning(f"⚠️ Segmento {i} não é dict: {type(segment)}")
        
        # Remover informações sensíveis
        safe_task = task.copy()
        if "client_ip" in safe_task:
            del safe_task["client_ip"]
        
        return safe_task
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro inesperado ao obter status da tarefa {task_id}: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@app.get("/status/{task_id}")
@limiter.limit(f"{settings.RATE_LIMIT_REQUESTS * 2}/{settings.RATE_LIMIT_MINUTES}minute")
async def get_transcription_status(task_id: str, request: Request):
    """Endpoint público para consultar status (compatibilidade)"""
    try:
        # Validar task_id
        if not re.match(r'^[a-zA-Z0-9-]+$', task_id):
            security_logger.warning(f"Task ID inválido solicitado: {task_id} - IP: {get_remote_address(request)}")
            raise HTTPException(status_code=400, detail="ID da tarefa inválido")
            
        task = transcription_tasks.get(task_id) or load_task_from_file(task_id)
        if not task:
            logger.warning(f"Tarefa {task_id} não encontrada - IP: {get_remote_address(request)}")
            raise HTTPException(status_code=404, detail="Tarefa não encontrada")
            
        # Para endpoint público, remover informações sensíveis
        safe_task = task.copy()
        sensitive_fields = ["client_ip", "user", "url"]
        for field in sensitive_fields:
            if field in safe_task:
                del safe_task[field]
        
        # Garantir que os dados sejam serializáveis antes de retornar
        if 'segments' in safe_task and safe_task['segments']:
            logger.debug(f"🔍 Verificando {len(safe_task['segments'])} segmentos para serialização")
            for i, segment in enumerate(safe_task['segments']):
                if not isinstance(segment, dict):
                    logger.warning(f"⚠️ Segmento {i} não é dict: {type(segment)}")
                    
        return safe_task
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro inesperado ao obter status da tarefa {task_id}: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")