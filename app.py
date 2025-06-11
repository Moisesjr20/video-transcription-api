from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
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

# Imports para processamento de vídeo
import moviepy.editor as mp
from moviepy.video.io.VideoFileClip import VideoFileClip
import whisper
import re

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Video Transcription API",
    description="API para transcrição de vídeos com suporte a Google Drive, divisão automática e extração de legendas",
    version="1.0.0"
)

# Diretórios de trabalho
TEMP_DIR = Path("temp")
DOWNLOADS_DIR = Path("downloads")
TRANSCRIPTIONS_DIR = Path("transcriptions")

# Criar diretórios se não existirem
for directory in [TEMP_DIR, DOWNLOADS_DIR, TRANSCRIPTIONS_DIR]:
    directory.mkdir(exist_ok=True)

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
    download_url: Optional[str] = None

class TranscriptionStatus(BaseModel):
    task_id: str
    status: str  # processing, completed, error
    progress: float
    message: str
    transcription: Optional[str] = None
    segments: Optional[List[dict]] = None
    filename: Optional[str] = None

# Storage para tarefas em andamento
transcription_tasks = {}

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

def download_with_selenium_fallback(file_id: str, destination: Path) -> Path:
    """Automação com Selenium como fallback para casos difíceis"""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from webdriver_manager.chrome import ChromeDriverManager
        import time
        
        logger.info("🤖 Iniciando automação com Selenium...")
        
        # Configurar Chrome headless
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        # Configurar downloads
        prefs = {
            "download.default_directory": str(destination.parent),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        # Inicializar driver
        service = webdriver.chrome.service.Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        try:
            logger.info("🌐 Acessando página do Google Drive...")
            driver.get(f"https://drive.google.com/file/d/{file_id}/view")
            
            # Aguardar página carregar
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Tentar encontrar botão de download - seletores atualizados baseados no debug
            download_selectors = [
                "[aria-label*='Fazer o download']",  # Português brasileiro
                "[aria-label*='Download']",          # Inglês
                "[data-tooltip*='Fazer o download']", # Tooltip português
                "[data-tooltip*='Download']",         # Tooltip inglês
                "div.ndfHFb-c4YZDc-to915-LgbsSe[aria-label*='download' i]",  # Classe específica encontrada
                "div.VIpgJd-TzA9Ye-eEGnhe[aria-label*='download' i]",        # Classe alternativa
                "button[aria-label*='Download']",
                "[jsaction*='download']"
            ]
            
            download_button = None
            for selector in download_selectors:
                try:
                    download_button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    logger.info(f"✅ Botão de download encontrado: {selector}")
                    break
                except:
                    continue
            
            if download_button:
                # Clicar no download
                logger.info("🖱️ Clicando no botão de download...")
                driver.execute_script("arguments[0].click();", download_button)
                
                # Aguardar download iniciar
                time.sleep(5)
                
                # Verificar se apareceu confirmação para arquivo grande
                try:
                    confirm_button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Download anyway') or contains(text(), 'Baixar mesmo assim')]"))
                    )
                    logger.info("⚠️ Confirmação de arquivo grande detectada - clicando...")
                    driver.execute_script("arguments[0].click();", confirm_button)
                except:
                    logger.info("ℹ️ Sem confirmação adicional necessária")
                
                # Aguardar download completar
                logger.info("⏳ Aguardando download completar...")
                max_wait = 600  # 10 minutos para arquivos grandes
                waited = 0
                
                while waited < max_wait:
                    # Verificar se arquivo existe
                    if destination.exists():
                        logger.info(f"✅ Download via Selenium concluído: {destination.stat().st_size} bytes")
                        return destination
                    
                    # Verificar downloads na pasta
                    download_files = list(destination.parent.glob(f"*{file_id}*"))
                    if download_files:
                        # Renomear arquivo baixado
                        downloaded_file = download_files[0]
                        downloaded_file.rename(destination)
                        logger.info(f"✅ Arquivo renomeado e download concluído: {destination.stat().st_size} bytes")
                        return destination
                    
                    time.sleep(5)  # Verificar a cada 5 segundos
                    waited += 5
                
                raise Exception("Timeout: Download não completou em 10 minutos")
            else:
                raise Exception("Botão de download não encontrado na página")
                
        finally:
            driver.quit()
            
    except ImportError:
        logger.warning("⚠️ Selenium não disponível - usando método tradicional")
        raise Exception("Selenium não instalado - instale com: pip install selenium webdriver-manager")
    except Exception as e:
        logger.error(f"❌ Erro na automação Selenium: {e}")
        raise

def download_from_google_drive(file_id: str, destination: Path) -> Path:
    """Baixa arquivo do Google Drive com automação completa para páginas de confirmação"""
    import re
    from urllib.parse import parse_qs, urlparse
    
    session = requests.Session()
    
    # Headers para simular navegador real
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    session.headers.update(headers)
    
    def parse_html_for_download_info(html_content):
        """Extrai informações de download de páginas HTML do Google Drive"""
        
        # Método 1: Buscar por tokens de confirmação
        confirm_patterns = [
            r'confirm=([a-zA-Z0-9_-]+)',
            r'"confirm":"([^"]+)"',
            r'confirm%3D([a-zA-Z0-9_-]+)',
            r'&amp;confirm=([a-zA-Z0-9_-]+)',
            r'confirm=([^&]+)&',
        ]
        
        for pattern in confirm_patterns:
            match = re.search(pattern, html_content)
            if match:
                return {'confirm_token': match.group(1)}
        
        # Método 2: Buscar por URLs de download direto
        download_patterns = [
            r'href="([^"]*uc[^"]*download[^"]*)"',
            r'action="([^"]*uc[^"]*)"',
            r'"downloadUrl":"([^"]+)"',
        ]
        
        for pattern in download_patterns:
            matches = re.findall(pattern, html_content)
            if matches:
                return {'download_url': matches[0].replace('\\u003d', '=').replace('\\u0026', '&')}
        
        # Método 3: Buscar por formulários de download
        form_match = re.search(r'<form[^>]*action="([^"]*)"[^>]*>(.*?)</form>', html_content, re.DOTALL)
        if form_match:
            form_action = form_match.group(1)
            form_content = form_match.group(2)
            
            # Buscar inputs hidden
            inputs = re.findall(r'<input[^>]*name="([^"]*)"[^>]*value="([^"]*)"', form_content)
            if inputs:
                return {'form_action': form_action, 'form_data': dict(inputs)}
        
        return None

    def attempt_download_with_info(download_info):
        """Tenta download usando informações extraídas"""
        
        if 'confirm_token' in download_info:
            confirm_token = download_info['confirm_token']
            confirm_url = f"https://drive.google.com/uc?confirm={confirm_token}&id={file_id}&export=download"
            logger.info(f"🔑 Usando token de confirmação automático: {confirm_token[:10]}...")
            return session.get(confirm_url, stream=True)
            
        elif 'download_url' in download_info:
            download_url = download_info['download_url']
            if not download_url.startswith('http'):
                download_url = 'https://drive.google.com' + download_url
            logger.info("🔗 Usando URL de download extraída...")
            return session.get(download_url, stream=True)
            
        elif 'form_action' in download_info:
            form_action = download_info['form_action']
            form_data = download_info['form_data']
            if not form_action.startswith('http'):
                form_action = 'https://drive.google.com' + form_action
            logger.info("📝 Submetendo formulário de confirmação automático...")
            return session.post(form_action, data=form_data, stream=True)
        
        return None

    # Tentativa 1: URL direta
    logger.info("📥 Tentativa 1: Download direto...")
    url = f"https://drive.google.com/uc?id={file_id}&export=download"
    response = session.get(url, stream=True)
    
    # Verificar se retornou arquivo ou HTML
    content_type = response.headers.get('content-type', '')
    
    if response.status_code == 200 and 'text/html' not in content_type:
        logger.info("✅ Download direto bem-sucedido!")
    else:
        logger.info("🔄 Página HTML detectada - iniciando automação...")
        
        # Ler conteúdo HTML para análise
        html_content = response.text
        logger.info(f"📄 Página HTML recebida ({len(html_content)} caracteres)")
        
        # Tentar extrair informações de download
        download_info = parse_html_for_download_info(html_content)
        
        if download_info:
            logger.info(f"🎯 Informações de download encontradas: {list(download_info.keys())}")
            response = attempt_download_with_info(download_info)
            
            if response and response.status_code == 200:
                content_type = response.headers.get('content-type', '')
                if 'text/html' not in content_type:
                    logger.info("✅ Download automático bem-sucedido!")
                else:
                    logger.warning("⚠️ Ainda recebendo HTML - tentando métodos alternativos...")
                    
                    # Tentativa adicional: URLs alternativas
                    alternative_urls = [
                        f"https://drive.google.com/u/0/uc?id={file_id}&export=download&confirm=t&uuid={file_id}",
                        f"https://drive.google.com/uc?authuser=0&id={file_id}&export=download",
                        f"https://drive.usercontent.google.com/download?id={file_id}&export=download&authuser=0",
                    ]
                    
                    for alt_url in alternative_urls:
                        logger.info(f"🔄 Tentando URL alternativa...")
                        response = session.get(alt_url, stream=True)
                        if response.status_code == 200 and 'text/html' not in response.headers.get('content-type', ''):
                            logger.info("✅ URL alternativa funcionou!")
                            break
                    else:
                        # Se ainda não funcionou, tentar with browser simulation
                        logger.info("🤖 Última tentativa: simulação completa de navegador...")
                        response = session.get(f"https://drive.google.com/file/d/{file_id}/view")
                        if response.status_code == 200:
                            # Buscar por link de download na página de visualização
                            download_match = re.search(r'"downloadUrl":"([^"]+)"', response.text)
                            if download_match:
                                download_url = download_match.group(1).replace('\\u003d', '=').replace('\\u0026', '&')
                                response = session.get(download_url, stream=True)
                                if response.status_code == 200:
                                    logger.info("✅ Simulação de navegador bem-sucedida!")
        else:
            logger.warning("❌ Não foi possível extrair informações de download automaticamente")
            raise Exception("Falha na automação: não foi possível encontrar método de download na página HTML")
    
    # Verificar se finalmente conseguimos o arquivo
    if response.status_code == 200:
        content_type = response.headers.get('content-type', '')
        
        if 'text/html' in content_type:
            # Última verificação - salvar HTML para debug
            debug_file = destination.parent / f"debug_{file_id}.html"
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(response.text[:5000])  # Primeiros 5000 caracteres
            
            raise Exception(f"Download ainda retorna HTML após automação. HTML salvo em {debug_file} para debug.")
        
        # Download do arquivo
        logger.info(f"📦 Iniciando download do arquivo ({response.headers.get('content-length', 'tamanho desconhecido')} bytes)...")
        
        total_size = 0
        with open(destination, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    total_size += len(chunk)
                    
                    # Log a cada 50MB
                    if total_size % (50 * 1024 * 1024) == 0:
                        logger.info(f"📊 Baixados: {total_size / (1024*1024):.1f} MB...")
        
        # Verificar arquivo final
        file_size = destination.stat().st_size
        
        if file_size < 1024:
            # Arquivo muito pequeno - verificar se é erro
            with open(destination, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            if 'html' in content.lower() or 'error' in content.lower():
                raise Exception(f"Download resultou em arquivo inválido ({file_size} bytes). Conteúdo: {content[:200]}")
        
        logger.info(f"✅ Download concluído com sucesso: {file_size / (1024*1024):.1f} MB")
        return destination
    else:
        # Última tentativa com Selenium
        logger.warning("⚠️ Métodos tradicionais falharam - tentando automação com Selenium...")
        try:
            return download_with_selenium_fallback(file_id, destination)
        except Exception as selenium_error:
            logger.error(f"❌ Selenium também falhou: {selenium_error}")
            raise Exception(f"Todos os métodos falharam. Último erro HTTP: {response.status_code} - {response.text[:200]}, Selenium: {selenium_error}")

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
        # Atualizar status
        transcription_tasks[task_id]["status"] = "processing"
        transcription_tasks[task_id]["progress"] = 0.1
        transcription_tasks[task_id]["message"] = "Baixando vídeo..."
        
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
        
        transcription_tasks[task_id]["progress"] = 0.2
        transcription_tasks[task_id]["message"] = "Vídeo baixado. Verificando legendas..."
        
        # Extrair legendas se solicitado
        subtitles_text = None
        if request.extract_subtitles:
            subtitles_text = extract_subtitles_from_video(temp_video_path)
            if subtitles_text:
                logger.info("Legendas encontradas no vídeo")
        
        transcription_tasks[task_id]["progress"] = 0.3
        transcription_tasks[task_id]["message"] = "Analisando duração do vídeo..."
        
        # Dividir vídeo se necessário
        max_minutes = request.max_segment_minutes or 10
        video_segments = split_video_by_duration(temp_video_path, max_minutes)
        
        transcription_tasks[task_id]["progress"] = 0.4
        transcription_tasks[task_id]["message"] = f"Vídeo dividido em {len(video_segments)} segmento(s). Convertendo para áudio..."
        
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
        transcription_tasks[task_id]["message"] = "Carregando modelo de transcrição..."
        
        # Carregar modelo Whisper
        model = load_whisper_model()
        
        transcription_tasks[task_id]["progress"] = 0.6
        transcription_tasks[task_id]["message"] = "Iniciando transcrição..."
        
        # Transcrever cada segmento
        all_transcriptions = []
        all_segments_data = []
        
        for i, audio_path in enumerate(audio_segments):
            transcription_tasks[task_id]["message"] = f"Transcrevendo segmento {i+1}/{len(audio_segments)}..."
            transcription_tasks[task_id]["progress"] = 0.6 + (0.3 * (i / len(audio_segments)))
            
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
        transcription_tasks[task_id]["message"] = "Salvando resultado..."
        
        # Salvar transcrição final
        transcription_filename = f"transcription_{task_id}.txt"
        transcription_path = TRANSCRIPTIONS_DIR / transcription_filename
        
        with open(transcription_path, 'w', encoding='utf-8') as f:
            f.write(result_text)
        
        # Atualizar status final
        transcription_tasks[task_id].update({
            "status": "completed",
            "progress": 1.0,
            "message": "Transcrição concluída com sucesso!",
            "transcription": result_text,
            "segments": all_segments_data,
            "filename": transcription_filename
        })
        
        # Limpar arquivo de vídeo temporário
        if temp_video_path and temp_video_path.exists():
            temp_video_path.unlink()
            
        logger.info(f"Transcrição {task_id} concluída com sucesso")
        
    except Exception as e:
        logger.error(f"Erro na transcrição {task_id}: {e}")
        transcription_tasks[task_id].update({
            "status": "error",
            "message": f"Erro: {str(e)}",
            "progress": 0.0
        })

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
        "status": "queued",
        "progress": 0.0,
        "message": "Tarefa adicionada à fila",
        "created_at": datetime.now().isoformat(),
        "transcription": None,
        "segments": None,
        "filename": None
    }
    
    # Adicionar tarefa ao background
    background_tasks.add_task(process_video_transcription, task_id, request)
    
    return TranscriptionResponse(
        task_id=task_id,
        status="queued",
        message="Transcrição iniciada. Use /status/{task_id} para acompanhar o progresso."
    )

@app.get("/status/{task_id}", response_model=TranscriptionStatus)
async def get_transcription_status(task_id: str):
    """Obtém o status de uma transcrição"""
    
    if task_id not in transcription_tasks:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    
    task_data = transcription_tasks[task_id]
    
    return TranscriptionStatus(
        task_id=task_id,
        status=task_data["status"],
        progress=task_data["progress"],
        message=task_data["message"],
        transcription=task_data.get("transcription"),
        segments=task_data.get("segments"),
        filename=task_data.get("filename")
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
    """Endpoint raiz com informações da API"""
    return {
        "message": "Video Transcription API",
        "version": "1.0.0",
        "description": "API para transcrição de vídeos com suporte a Google Drive, divisão automática e extração de legendas",
        "endpoints": [
            "POST /transcribe - Iniciar transcrição",
            "GET /status/{task_id} - Verificar status",
            "GET /download/{filename} - Download da transcrição",
            "GET /tasks - Listar todas as tarefas",
            "DELETE /tasks/{task_id} - Remover tarefa"
        ]
    }

@app.get("/health")
async def health_check():
    """Health check da API"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "whisper_loaded": whisper_model is not None
    }