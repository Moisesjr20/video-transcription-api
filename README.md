# 🎬 API de Transcrição de Vídeos com Monitoramento Automático

API FastAPI robusta para transcrição automática de vídeos com **monitoramento automático** de pastas do Google Drive e envio de transcrições por email.

## 🚀 Recursos

- 🤖 **Automação completa** para download do Google Drive
- 📁 **Monitoramento automático** de pastas do Google Drive
- 📧 **Envio automático** de transcrições por email
- 🎬 **Divisão automática** de vídeos longos
- 🔊 **Transcrição com Whisper AI**
- 🌐 **API RESTful** com interface Swagger
- 🎨 **Interface web moderna** para gerenciamento
- 🐳 **Deploy fácil** com Docker

## 🔄 **NOVA FUNCIONALIDADE: Monitoramento Automático**

### ✨ O que faz:
- 🔍 **Monitora automaticamente** uma pasta específica do Google Drive
- 📹 **Detecta novos vídeos** assim que são adicionados
- 🎬 **Transcreve automaticamente** cada novo vídeo
- 📧 **Envia transcrição por email** com formatação HTML
- 🔄 **Processa em background** sem intervenção manual

### 🎯 Caso de uso perfeito:
- Reuniões gravadas automaticamente no Google Drive
- Transcrições enviadas por email assim que concluídas
- Zero intervenção manual necessária

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

### 🌐 Interface Web
Acesse `http://localhost:8000` para usar a interface web moderna com:
- 📊 Dashboard em tempo real
- 🎮 Controles de monitoramento
- 📧 Testes de email
- 📈 Logs de atividade

### Transcrever vídeo manualmente
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

## 🔧 **Novos Endpoints de Monitoramento**

### Iniciar monitoramento automático
```bash
curl -X POST "http://localhost:8000/monitor/start"
```

### Verificar status do monitoramento
```bash
curl "http://localhost:8000/monitor/status"
```

### Forçar verificação de novos vídeos
```bash
curl -X POST "http://localhost:8000/monitor/check-now"
```

### Parar monitoramento
```bash
curl -X POST "http://localhost:8000/monitor/stop"
```

### Testar conexão com Google APIs
```bash
curl "http://localhost:8000/google/test-connection"
```

### Enviar email de teste
```bash
curl -X POST "http://localhost:8000/google/send-test-email" \
  -H "Content-Type: application/json" \
  -d '{"email": "seu-email@gmail.com"}'
```

## ⚙️ Configuração do Monitoramento Automático

### 1. Configurar credenciais Google
Edite `google_config.py`:
```python
# Seu ID e chave secreta do Google
GOOGLE_CLIENT_ID = "seu-client-id"
GOOGLE_CLIENT_SECRET = "sua-client-secret"

# ID da pasta do Google Drive para monitorar
GOOGLE_DRIVE_FOLDER_ID = "14BFqXqjV1MsQIkafQ8oWPPvKASnQLiQG"

# Email de destino para transcrições
DESTINATION_EMAIL = "seu-email@gmail.com"
```

### 2. Configurar Google Console
1. Acesse [Google Cloud Console](https://console.cloud.google.com/)
2. Crie um projeto ou selecione existente
3. Ative as APIs:
   - Google Drive API
   - Gmail API
4. Configure OAuth2:
   - Tipo: Aplicação Desktop
   - URIs de redirecionamento: `http://localhost:8000/auth/callback`

### 3. Executar script de configuração
```bash
python setup_google_auth.py
```

## 🔧 Endpoints Completos

### Transcrição
- `POST /transcribe` - Iniciar transcrição
- `GET /status/{task_id}` - Verificar progresso
- `GET /download/{filename}` - Download da transcrição

### Monitoramento Automático
- `POST /monitor/start` - Iniciar monitoramento
- `POST /monitor/stop` - Parar monitoramento
- `GET /monitor/status` - Status do monitoramento
- `POST /monitor/check-now` - Verificar vídeos agora

### Google APIs
- `GET /google/auth-url` - URL de autenticação
- `GET /google/test-connection` - Testar conexões
- `POST /google/send-test-email` - Email de teste

### Sistema
- `GET /health` - Health check
- `GET /` - Interface Swagger UI

## ⚙️ Configuração

### Recursos Mínimos
- 2GB RAM, 1 CPU
- 10GB armazenamento

### Recursos Recomendados
- 4GB RAM, 2 CPU
- Conexão estável com internet

## 🛠️ Desenvolvimento Local

```bash
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000
```

### 🎨 Testar Interface Web
```bash
python test_interface.py
```

## 📊 Monitoramento

```bash
# Health check
curl http://localhost:8000/health

# Status do monitoramento
curl http://localhost:8000/monitor/status

# Logs Docker
docker logs video-transcription-api
```

## 🔄 Fluxo de Monitoramento Automático

1. **Configuração inicial**:
   - Configure credenciais Google
   - Execute script de setup
   - Inicie monitoramento

2. **Funcionamento automático**:
   - API verifica pasta a cada 5 minutos
   - Detecta novos vídeos automaticamente
   - Inicia transcrição em background
   - Envia resultado por email

3. **Resultado**:
   - Transcrição formatada em HTML
   - Informações do vídeo (tamanho, duração)
   - Task ID para rastreamento

## 📧 Formato do Email

O email de transcrição inclui:
- 📁 Nome do arquivo
- 📅 Data e hora
- ⏱️ Duração do vídeo
- 📏 Tamanho do arquivo
- 📝 Transcrição completa
- 🔗 Task ID para rastreamento

---

**Desenvolvido para automação completa de transcrição de vídeos** 🎯 