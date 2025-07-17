# 🤖 Transcritor API

Uma API simples para transcrição de vídeos do Google Drive ou URL usando Whisper AI.

## ✨ Funcionalidades

- **Transcrição sob demanda**: Envie uma URL de vídeo ou link do Google Drive e receba a transcrição.
- **Processamento assíncrono**: As transcrições são processadas em background.
- **Status da tarefa**: Consulte o status e resultado da transcrição por ID.

## 🚀 Como Funciona

1. Envie uma requisição para `/transcribe` com a URL do vídeo ou link do Google Drive.
2. Receba um `task_id` para consultar o status.
3. Consulte `/status/{task_id}` para ver o progresso e obter a transcrição.

## 🛠️ Tecnologias

- **Backend**: FastAPI + Python
- **IA**: OpenAI Whisper

## 📋 Pré-requisitos

- Python 3.8+
- Dependências do `requirements.txt`

## ⚙️ Configuração

1. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
2. (Opcional) Configure variáveis de ambiente se necessário.

## 🎯 Uso

### 1. Iniciar o servidor
```bash
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### 2. Enviar vídeo para transcrição

**POST /transcribe**
```json
{
  "google_drive_url": "https://drive.google.com/file/d/SEU_ID_AQUI/view?usp=sharing",
  "filename": "meu_video.mp4",
  "language": "pt"
}
```

**Resposta:**
```json
{
  "task_id": "...",
  "status": "iniciado",
  "message": "Transcrição iniciada com sucesso",
  "upload_status": "concluido",
  "estimated_time": "5-10 minutos",
  "check_status_url": "/status/SEU_TASK_ID"
}
```

### 3. Consultar status da transcrição

**GET /status/{task_id}**

**Resposta:**
```json
{
  "task_id": "...",
  "status": "sucesso",
  "progress": 1.0,
  "message": "Transcrição concluída com sucesso!",
  "transcription": "...texto...",
  ...
}
```

## 🐳 Deploy com Docker

```bash
# Build da imagem
docker build -t transcritor-api .
# Executar container
docker run -d -p 8000:8000 transcritor-api
```

## 🔒 Segurança
- Assegure-se de proteger a API se for expor publicamente.

## 🤝 Contribuição
Pull requests são bem-vindos! 