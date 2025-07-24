# 🔐 Transcritor API Seguro - AssemblyAI

Uma API **segura** e **robusta** para transcrição de vídeos do Google Drive usando AssemblyAI com autenticação, rate limiting e auditoria.

## ✨ Funcionalidades

### 🔐 **Segurança**
- **Autenticação JWT**: Sistema de login com tokens seguros
- **Rate Limiting**: Proteção contra spam e sobrecarga
- **Validação rigorosa**: Validação de URLs, extensões e tamanhos
- **Logs de auditoria**: Registro detalhado de ações de segurança
- **Sanitização de dados**: Proteção contra ataques de injeção

### 🎬 **Transcrição**
- **Transcrição sob demanda**: Envie URLs do Google Drive
- **Processamento assíncrono**: Processamento em background
- **Status em tempo real**: Consulte o progresso das transcrições
- **Identificação de falantes**: Detecta diferentes pessoas falando
- **Pontuação automática**: Formatação inteligente do texto
- **Suporte multilíngue**: Otimizado para português

### 🛡️ **Robustez**
- **Tratamento de erros**: Recuperação graceful de falhas
- **Timeouts configuráveis**: Evita travamentos
- **Webhooks seguros**: Notificações automáticas
- **Monitoramento**: Health checks e métricas

## 🚀 Como Funciona

### Fluxo Seguro (Recomendado)
1. **Login**: `POST /login` com credenciais para obter token JWT
2. **Transcrição**: `POST /transcribe-secure` com token no header Authorization
3. **Status**: `GET /status-secure/{task_id}` para acompanhar o progresso
4. **Webhook**: Receba notificação automática quando concluído

### Fluxo Público (Compatibilidade)
1. **Transcrição**: `POST /transcribe` com URL do Google Drive
2. **Status**: `GET /status/{task_id}` para ver o progresso

## 🛠️ Tecnologias

- **Backend**: FastAPI + Python
- **IA**: AssemblyAI Speech-to-Text API

## 📋 Pré-requisitos

- Python 3.8+
- Dependências do `requirements.txt`
- Chave de API da AssemblyAI (já configurada no código)

## ⚙️ Configuração Segura

### 1. Configurar Variáveis de Ambiente
Copie o arquivo de exemplo e configure suas chaves:
```bash
cp env.example .env
nano .env
```

**Configurações obrigatórias:**
```env
# API da AssemblyAI (já configurada para desenvolvimento)
ASSEMBLYAI_API_KEY=245ef4a0549d4808bb382cd40d9c054d

# Segurança (gere chaves fortes!)
API_SECRET_KEY=sua_chave_secreta_32_caracteres_min
JWT_SECRET_KEY=sua_chave_jwt_32_caracteres_min

# Webhook (opcional)
WEBHOOK_URL=https://seu-webhook.com/callback
```

> 💡 **Dica**: Para desenvolvimento, as chaves já estão configuradas. Para produção, altere todas as chaves!

### 2. Instalar Dependências
```bash
pip install -r requirements.txt
```

### 3. Usuários Demo
**Admin:** `admin` / `admin123`  
**Usuário:** `user` / `user123`  
> ⚠️ **Altere essas senhas em produção!**

## 🎯 Uso Seguro

### 1. Iniciar o servidor
```bash
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### 2. Autenticação (Login)
**POST /login**
```json
{
  "username": "admin",
  "password": "admin123"
}
```

**Resposta:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

### 3. Enviar vídeo para transcrição (Seguro)
**POST /transcribe-secure**  
**Header:** `Authorization: Bearer SEU_TOKEN`
```json
{
  "google_drive_url": "https://drive.google.com/file/d/SEU_ID_AQUI/view?usp=sharing",
  "filename": "meu_video.mp4"
}
```

**Resposta:**
```json
{
  "task_id": "uuid-da-tarefa",
  "status": "processing",
  "message": "Transcrição iniciada com sucesso!",
  "estimated_time": "2-5 minutos",
  "check_status_url": "/status/uuid-da-tarefa"
}
```

### 4. Consultar status (Seguro)
**GET /status-secure/{task_id}**  
**Header:** `Authorization: Bearer SEU_TOKEN`

**Resposta:**
```json
{
  "task_id": "uuid-da-tarefa",
  "status": "completed",
  "transcription": "Texto da transcrição...",
  "segments": [
    {
      "start": 0,
      "end": 1000,
      "text": "Olá, como você está?",
      "speaker": "A"
    }
  ],
  "created_at": "2024-01-01T10:00:00",
  "completed_at": "2024-01-01T10:03:00"
}
```

### 5. Administração
**GET /admin/tasks** (requer permissão admin)  
Lista todas as tarefas do sistema para auditoria.

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

## 🔒 Segurança Implementada

### ✅ **Correções Aplicadas**
- ✅ **API Keys**: Removidas do código, agora em variáveis de ambiente
- ✅ **Autenticação JWT**: Sistema completo com login e tokens
- ✅ **Rate Limiting**: Proteção contra spam (10 req/min por IP)
- ✅ **Validação rigorosa**: URLs, extensões, tamanhos de arquivo
- ✅ **Logs de auditoria**: Rastreamento de ações e tentativas de acesso
- ✅ **Sanitização**: Proteção contra path traversal e injeções
- ✅ **CORS configurado**: Proteção contra cross-origin attacks
- ✅ **Timeouts**: Prevenção de travamentos e DoS

### 🛡️ **Para Produção**
1. **Altere as senhas padrão** nos usuários demo
2. **Configure HTTPS** com certificados SSL
3. **Use banco de dados** para usuários (não hardcoded)
4. **Configure firewall** e reverse proxy
5. **Monitore logs** regularmente
6. **Atualize dependências** periodicamente

## 📊 Vantagens da AssemblyAI

- **Velocidade**: Transcrições mais rápidas (2-5 minutos vs 5-10 minutos)
- **Precisão**: Melhor reconhecimento de fala em português
- **Identificação de falantes**: Detecta automaticamente diferentes pessoas falando
- **Pontuação**: Adiciona pontuação e formatação automaticamente
- **Formatação**: Texto mais limpo e legível

## 🤝 Contribuição
Pull requests são bem-vindos! 