# 🤖 Transcritor API - AssemblyAI

Uma API simples para transcrição de vídeos do Google Drive ou URL usando AssemblyAI.

## ✨ Funcionalidades

- **Transcrição sob demanda**: Envie uma URL de vídeo ou link do Google Drive e receba a transcrição.
- **Processamento assíncrono**: As transcrições são processadas em background.
- **Status da tarefa**: Consulte o status e resultado da transcrição por ID.
- **Identificação de falantes**: Detecta automaticamente diferentes falantes na transcrição.
- **Pontuação automática**: Adiciona pontuação e formatação ao texto transcrito.
- **Suporte multilíngue**: Suporte para português e outros idiomas.

## 🚀 Como Funciona

1. Envie uma requisição para `/transcribe` com a URL do vídeo ou link do Google Drive.
2. Receba um `task_id` para consultar o status.
3. Consulte `/status/{task_id}` para ver o progresso e obter a transcrição.

## 🛠️ Tecnologias

- **Backend**: FastAPI + Python
- **IA**: AssemblyAI Speech-to-Text API

## 📋 Pré-requisitos

- Python 3.8+
- Dependências do `requirements.txt`
- Chave de API da AssemblyAI (já configurada no código)

## ⚙️ Configuração

1. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

2. A chave da API da AssemblyAI já está configurada no código:
   ```python
   ASSEMBLYAI_API_KEY = "245ef4a0549d4808bb382cd40d9c054d"
   ```

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
  "estimated_time": "2-5 minutos",
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
  "segments": [
    {
      "start": 0.0,
      "end": 5.2,
      "text": "Olá, como você está?",
      "speaker": "A"
    }
  ],
  ...
}
```

## 🌐 Interface Web

Acesse `http://localhost:8000` para usar a interface web simples que permite:
- Inserir URLs do Google Drive
- Iniciar transcrições
- Visualizar status e resultados

## 🐳 Deploy com Docker

```bash
# Build da imagem
docker build -t transcritor-api .
# Executar container
docker run -d -p 8000:8000 transcritor-api
```

## 🔒 Segurança
- Assegure-se de proteger a API se for expor publicamente.
- A chave da API da AssemblyAI está hardcoded no código - considere usar variáveis de ambiente em produção.

## 📊 Vantagens da AssemblyAI

- **Velocidade**: Transcrições mais rápidas (2-5 minutos vs 5-10 minutos)
- **Precisão**: Melhor reconhecimento de fala em português
- **Identificação de falantes**: Detecta automaticamente diferentes pessoas falando
- **Pontuação**: Adiciona pontuação e formatação automaticamente
- **Formatação**: Texto mais limpo e legível

## 🤝 Contribuição
Pull requests são bem-vindos! 