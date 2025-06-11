# 🎬 API de Transcrição de Vídeos com Automação Completa

API FastAPI robusta para transcrição automática de vídeos com suporte completo ao Google Drive.

## 🚀 Recursos

- 🤖 **Automação completa** para download do Google Drive
- 🎬 **Divisão automática** de vídeos longos
- 🔊 **Transcrição com Whisper AI**
- 🌐 **API RESTful** com interface Swagger
- 🐳 **Deploy fácil** com Docker

## 🚀 Deploy no EasyPanel

### Método 1: Git Repository
1. Fork este repositório
2. No EasyPanel: New Project → Git Repository
3. Cole a URL do seu fork
4. Deploy automático com `easypanel.yml`

### Método 2: Docker Compose
```bash
git clone <seu-repo>
cd video-transcription-api
docker-compose up -d
```

## 📖 Uso da API

### Transcrever vídeo
```bash
curl -X POST "http://localhost:8000/transcribe" \
  -H "Content-Type: application/json" \
  -d '{
    "google_drive_url": "https://drive.google.com/uc?id=FILE_ID&export=download",
    "language": "pt"
  }'
```

### Verificar status
```bash
curl "http://localhost:8000/status/TASK_ID"
```

## 🔧 Endpoints

- `POST /transcribe` - Iniciar transcrição
- `GET /status/{task_id}` - Verificar progresso
- `GET /health` - Health check
- `GET /` - Interface Swagger UI

## ⚙️ Configuração

### Recursos Mínimos
- 2GB RAM, 1 CPU
- 10GB armazenamento

### Recursos Recomendados
- 4GB RAM, 2 CPU
- Chrome instalado (para Selenium)

## 🛠️ Desenvolvimento Local

```bash
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000
```

## 📊 Monitoramento

```bash
# Health check
curl http://localhost:8000/health

# Logs Docker
docker logs video-transcription-api
```

---

**Desenvolvido para automação completa de transcrição de vídeos** 🎯 